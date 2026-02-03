"""FileBrowser 上传服务

通过 FileBrowser API 上传文件到 Coder 工作区。
"""

import asyncio
import io
import logging
import os
import zipfile

import httpx

from .coder_client import CoderClient, CoderAPIError

logger = logging.getLogger(__name__)


class FileBrowserError(Exception):
    """FileBrowser API 错误"""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class FileBrowserService:
    """通过 FileBrowser API 上传文件到 Coder 工作区"""

    def __init__(self, coder_client: CoderClient | None = None):
        self.coder_client = coder_client or CoderClient()
        self.default_owner = os.getenv("CODER_DEFAULT_OWNER", "admin")
        self._session_tokens: dict[str, str] = {}  # 缓存 FileBrowser token

    async def get_filebrowser_url(self, workspace: dict) -> str | None:
        """从工作区 apps 中获取 FileBrowser URL

        Args:
            workspace: 工作区信息字典

        Returns:
            FileBrowser URL 或 None
        """
        workspace_id = workspace.get("id")
        if not workspace_id:
            return None

        try:
            apps = await self.coder_client.get_workspace_apps(workspace_id)
        except CoderAPIError:
            return None

        # 查找 filebrowser 应用
        for app in apps:
            if app.get("slug") == "filebrowser":
                agents = await self.coder_client.get_workspace_agents(workspace_id)
                if agents:
                    agent_name = agents[0].get("name", "main")
                    return self.coder_client.get_app_url(
                        workspace_owner=self.default_owner,
                        workspace_name=workspace["name"],
                        agent_name=agent_name,
                        app_slug="filebrowser",
                        subdomain=app.get("subdomain", False),
                    )
        return None

    async def _wait_for_filebrowser_ready(
        self, workspace_id: str, timeout: int = 60, poll_interval: int = 5
    ) -> str | None:
        """等待 FileBrowser 服务就绪

        Args:
            workspace_id: 工作区 ID
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）

        Returns:
            FileBrowser URL 或 None（超时）
        """
        elapsed = 0
        while elapsed < timeout:
            try:
                workspace = await self.coder_client.get_workspace(workspace_id)
                filebrowser_url = await self.get_filebrowser_url(workspace)

                if filebrowser_url:
                    # 健康检查
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        try:
                            # FileBrowser 登录页面应该返回 200
                            response = await client.get(
                                filebrowser_url,
                                follow_redirects=True,
                                headers={"Coder-Session-Token": self.coder_client.api_token},
                            )
                            if response.status_code == 200:
                                logger.info(f"FileBrowser is ready at {filebrowser_url}")
                                return filebrowser_url
                        except httpx.RequestError:
                            pass
            except (CoderAPIError, Exception) as e:
                logger.debug(f"Waiting for FileBrowser: {e}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        logger.warning(f"Timeout waiting for FileBrowser in workspace {workspace_id}")
        return None

    async def login(self, filebrowser_url: str) -> str:
        """登录 FileBrowser 获取 token

        FileBrowser 默认用户名密码都是 admin。

        Args:
            filebrowser_url: FileBrowser 基础 URL

        Returns:
            JWT token

        Raises:
            FileBrowserError: 登录失败
        """
        # 检查缓存
        if filebrowser_url in self._session_tokens:
            return self._session_tokens[filebrowser_url]

        login_url = f"{filebrowser_url.rstrip('/')}/api/login"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    login_url,
                    json={"username": "admin", "password": "admin"},
                    headers={"Coder-Session-Token": self.coder_client.api_token},
                    follow_redirects=True,
                )

                if response.status_code == 200:
                    # FileBrowser 返回的是纯文本 token
                    token = response.text.strip('"')
                    self._session_tokens[filebrowser_url] = token
                    return token
                else:
                    raise FileBrowserError(
                        f"Login failed: {response.status_code} - {response.text}",
                        status_code=response.status_code,
                    )
            except httpx.RequestError as e:
                raise FileBrowserError(f"Login request failed: {e}") from e

    async def upload_file(
        self,
        filebrowser_url: str,
        token: str,
        remote_path: str,
        content: bytes,
    ) -> bool:
        """上传单个文件

        Args:
            filebrowser_url: FileBrowser 基础 URL
            token: FileBrowser JWT token
            remote_path: 远程文件路径（相对于用户目录）
            content: 文件内容

        Returns:
            是否上传成功
        """
        # 确保路径以 / 开头
        if not remote_path.startswith("/"):
            remote_path = "/" + remote_path

        upload_url = f"{filebrowser_url.rstrip('/')}/api/resources{remote_path}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    upload_url,
                    params={"override": "true"},
                    headers={
                        "X-Auth": token,
                        "Coder-Session-Token": self.coder_client.api_token,
                    },
                    content=content,
                    follow_redirects=True,
                )

                if response.status_code in (200, 201, 204):
                    logger.debug(f"Uploaded file to {remote_path}")
                    return True
                else:
                    logger.error(
                        f"Failed to upload {remote_path}: {response.status_code} - {response.text}"
                    )
                    return False
            except httpx.RequestError as e:
                logger.error(f"Upload request failed for {remote_path}: {e}")
                return False

    async def upload_files(
        self,
        workspace: dict,
        files: list[tuple[str, bytes]],
        base_dir: str = "",
    ) -> tuple[int, list[str], list[str]]:
        """批量上传文件到工作区

        Args:
            workspace: 工作区信息字典
            files: 文件列表，格式 [(path, content), ...]
            base_dir: 基础目录（在工作区内的相对路径）

        Returns:
            (成功数量, 成功的文件列表, 失败的文件列表)
        """
        workspace_id = workspace.get("id")

        # 等待 FileBrowser 就绪
        filebrowser_url = await self._wait_for_filebrowser_ready(workspace_id)
        if not filebrowser_url:
            raise FileBrowserError(f"FileBrowser not ready for workspace {workspace_id}")

        # 登录获取 token
        token = await self.login(filebrowser_url)

        success_count = 0
        uploaded_files = []
        failed_files = []

        for path, content in files:
            # 构建远程路径
            if base_dir:
                remote_path = f"{base_dir.rstrip('/')}/{path}"
            else:
                remote_path = path

            if await self.upload_file(filebrowser_url, token, remote_path, content):
                success_count += 1
                uploaded_files.append(remote_path)
            else:
                failed_files.append(remote_path)

        return success_count, uploaded_files, failed_files

    async def upload_zip(
        self,
        workspace: dict,
        zip_content: bytes,
        extract_to: str = "",
    ) -> tuple[int, list[str], list[str]]:
        """上传并解压 ZIP 到工作区

        Args:
            workspace: 工作区信息字典
            zip_content: ZIP 文件内容
            extract_to: 解压目标目录

        Returns:
            (成功数量, 成功的文件列表, 失败的文件列表)
        """
        # 解压 ZIP 文件
        files = []
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), "r") as zf:
                for name in zf.namelist():
                    # 跳过目录
                    if name.endswith("/"):
                        continue
                    # 跳过 __MACOSX 等系统文件
                    if name.startswith("__MACOSX") or name.startswith("."):
                        continue
                    content = zf.read(name)
                    files.append((name, content))
        except zipfile.BadZipFile as e:
            raise FileBrowserError(f"Invalid ZIP file: {e}") from e

        if not files:
            return 0, [], []

        return await self.upload_files(workspace, files, base_dir=extract_to)

    async def upload_to_workspace(
        self,
        workspace_id: str,
        filename: str,
        content: bytes,
        base_dir: str = "",
    ) -> tuple[int, list[str], list[str]]:
        """上传文件/压缩包到工作区

        自动检测文件类型：
        - .zip 文件：解压后逐个上传
        - 其他文件：直接上传

        Args:
            workspace_id: 工作区 ID
            filename: 文件名
            content: 文件内容
            base_dir: 基础目录

        Returns:
            (成功数量, 成功的文件列表, 失败的文件列表)
        """
        # 获取工作区信息
        workspace = await self.coder_client.get_workspace(workspace_id)

        # 根据文件类型处理
        if filename.lower().endswith(".zip"):
            return await self.upload_zip(workspace, content, extract_to=base_dir)
        else:
            return await self.upload_files(workspace, [(filename, content)], base_dir=base_dir)
