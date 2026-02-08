# Spider Pipeline Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将爬虫的创建、在线开发、在线测试、部署运行、数据预览串联为完整闭环流程，使平台可以独立完成爬虫全生命周期管理。

**Architecture:** 以 Coder Workspace 为开发环境，通过 FileBrowser API 实现代码双向同步。新增 Deployment（部署快照）概念，将开发环境与生产运行解耦——测试时从 Workspace 实时拉取代码执行，部署时将代码打包存入 MongoDB GridFS 作为不可变快照，生产运行从快照中恢复代码执行，Workspace 无需常驻运行。

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, MongoDB GridFS (Motor), Celery 5.5+, FileBrowser REST API

---

## Task 1: FileBrowser 下载能力

**目标:** 给 FileBrowserService 增加从 Workspace 下载文件的能力，这是后续测试和部署的基础。

**Files:**
- Modify: `app/services/crawlhub/filebrowser_service.py`

### Step 1: 添加目录列表方法

在 `FileBrowserService` 类中添加 `list_directory` 方法（在 `upload_file` 方法之前插入）：

```python
async def list_directory(
    self,
    filebrowser_url: str,
    token: str,
    remote_path: str = "/",
) -> list[dict]:
    """列出目录内容

    Args:
        filebrowser_url: FileBrowser 基础 URL
        token: FileBrowser JWT token
        remote_path: 远程目录路径

    Returns:
        文件/目录列表，每项包含 path, name, size, isDir, type
    """
    if not remote_path.startswith("/"):
        remote_path = "/" + remote_path

    url = f"{filebrowser_url.rstrip('/')}/api/resources{remote_path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                url,
                headers={
                    "X-Auth": token,
                    "Coder-Session-Token": self.coder_client.api_token,
                },
                follow_redirects=True,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            else:
                logger.error(f"Failed to list {remote_path}: {response.status_code}")
                return []
        except httpx.RequestError as e:
            logger.error(f"List request failed for {remote_path}: {e}")
            return []
```

### Step 2: 添加单文件下载方法

在 `list_directory` 之后添加：

```python
async def download_file(
    self,
    filebrowser_url: str,
    token: str,
    remote_path: str,
) -> bytes | None:
    """下载单个文件

    Args:
        filebrowser_url: FileBrowser 基础 URL
        token: FileBrowser JWT token
        remote_path: 远程文件路径

    Returns:
        文件内容或 None
    """
    if not remote_path.startswith("/"):
        remote_path = "/" + remote_path

    url = f"{filebrowser_url.rstrip('/')}/api/raw{remote_path}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(
                url,
                headers={
                    "X-Auth": token,
                    "Coder-Session-Token": self.coder_client.api_token,
                },
                follow_redirects=True,
            )
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to download {remote_path}: {response.status_code}")
                return None
        except httpx.RequestError as e:
            logger.error(f"Download request failed for {remote_path}: {e}")
            return None
```

### Step 3: 添加项目整体下载方法

在 `download_file` 之后添加：

```python
async def download_project(
    self,
    workspace: dict,
    project_path: str,
) -> dict[str, bytes]:
    """递归下载整个项目目录

    Args:
        workspace: 工作区信息字典
        project_path: 项目在工作区内的路径（如 /workspace/my_spider）

    Returns:
        {相对路径: 文件内容} 字典
    """
    workspace_id = workspace.get("id")

    filebrowser_url = await self._wait_for_filebrowser_ready(workspace_id)
    if not filebrowser_url:
        raise FileBrowserError(f"FileBrowser not ready for workspace {workspace_id}")

    token = await self.login(filebrowser_url)

    files: dict[str, bytes] = {}
    await self._download_recursive(
        filebrowser_url, token, project_path, project_path, files
    )
    return files

async def _download_recursive(
    self,
    filebrowser_url: str,
    token: str,
    base_path: str,
    current_path: str,
    files: dict[str, bytes],
) -> None:
    """递归下载目录"""
    items = await self.list_directory(filebrowser_url, token, current_path)

    for item in items:
        item_path = item.get("path", "")
        if not item_path:
            continue

        # 跳过隐藏文件和 __pycache__
        name = item.get("name", "")
        if name.startswith(".") or name == "__pycache__" or name == ".venv":
            continue

        if item.get("isDir"):
            await self._download_recursive(
                filebrowser_url, token, base_path, item_path, files
            )
        else:
            content = await self.download_file(filebrowser_url, token, item_path)
            if content is not None:
                # 转为相对路径
                rel_path = item_path
                if rel_path.startswith(base_path):
                    rel_path = rel_path[len(base_path):].lstrip("/")
                files[rel_path] = content
```

### Step 4: 验证

检查 `filebrowser_service.py` 文件可以正常被 Python 导入，没有语法错误。

---

## Task 2: Deployment 数据模型

**目标:** 创建部署快照的数据库模型和迁移。

**Files:**
- Create: `app/models/crawlhub/deployment.py`
- Modify: `app/models/crawlhub/__init__.py`
- Modify: `app/models/crawlhub/spider.py`

### Step 1: 创建 Deployment 模型

创建 `app/models/crawlhub/deployment.py`：

```python
import enum

from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin
from models.types import EnumText, StringUUID


class DeploymentStatus(enum.StrEnum):
    """部署状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"


class Deployment(DefaultFieldsMixin, Base):
    """部署快照"""

    __tablename__ = "crawlhub_deployments"

    spider_id: Mapped[str] = mapped_column(StringUUID, nullable=False, comment="爬虫ID")
    version: Mapped[int] = mapped_column(Integer, nullable=False, comment="版本号")
    status: Mapped[DeploymentStatus] = mapped_column(
        EnumText(DeploymentStatus), default=DeploymentStatus.ACTIVE, comment="部署状态"
    )
    file_archive_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="GridFS 文件ID"
    )
    entry_point: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="入口点"
    )
    file_count: Mapped[int] = mapped_column(Integer, default=0, comment="文件数量")
    archive_size: Mapped[int] = mapped_column(Integer, default=0, comment="包大小(bytes)")
    deploy_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="部署备注")

    def __repr__(self) -> str:
        return f"<Deployment spider={self.spider_id} v{self.version}>"
```

### Step 2: Spider 模型添加 active_deployment_id

在 `app/models/crawlhub/spider.py` 的 `webhook_url` 字段之后添加：

```python
active_deployment_id: Mapped[str | None] = mapped_column(
    StringUUID, nullable=True, comment="当前活跃部署ID"
)
```

### Step 3: 更新模型导出

修改 `app/models/crawlhub/__init__.py`，添加导入：

```python
from .deployment import Deployment, DeploymentStatus
```

并在 `__all__` 中添加 `"Deployment"`, `"DeploymentStatus"`。

### Step 4: 创建 Alembic 迁移

从 `app/` 目录运行：

```bash
cd app && alembic revision --autogenerate -m "add deployment model and spider active_deployment_id"
```

检查生成的迁移文件，确保：
- 创建了 `crawlhub_deployments` 表
- `crawlhub_spiders` 表添加了 `active_deployment_id` 列

然后运行迁移：

```bash
cd app && alembic upgrade head
```

---

## Task 3: Deployment Schema

**目标:** 创建部署相关的请求/响应模型。

**Files:**
- Create: `app/schemas/crawlhub/deployment.py`
- Modify: `app/schemas/crawlhub/__init__.py`
- Modify: `app/schemas/crawlhub/spider.py`

### Step 1: 创建 Deployment schema

创建 `app/schemas/crawlhub/deployment.py`：

```python
from datetime import datetime

from pydantic import BaseModel, Field

from models.crawlhub.deployment import DeploymentStatus


class DeployRequest(BaseModel):
    deploy_note: str | None = Field(None, max_length=500, description="部署备注")


class DeploymentResponse(BaseModel):
    id: str
    spider_id: str
    version: int
    status: DeploymentStatus
    entry_point: str | None
    file_count: int
    archive_size: int
    deploy_note: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeploymentListResponse(BaseModel):
    items: list[DeploymentResponse]
    total: int
```

### Step 2: 更新 SpiderResponse

修改 `app/schemas/crawlhub/spider.py`，在 `SpiderResponse` 中添加：

```python
active_deployment_id: str | None = None
```

### Step 3: 更新 schema 导出

修改 `app/schemas/crawlhub/__init__.py`，添加：

```python
from .deployment import DeployRequest, DeploymentResponse, DeploymentListResponse
```

并在 `__all__` 中添加 `"DeployRequest"`, `"DeploymentResponse"`, `"DeploymentListResponse"`。

---

## Task 4: DeploymentService 核心服务

**目标:** 实现部署快照的核心业务逻辑，包括代码打包、GridFS 存储、版本管理。

**Files:**
- Create: `app/services/crawlhub/deployment_service.py`
- Modify: `app/services/crawlhub/__init__.py`

### Step 1: 创建 DeploymentService

创建 `app/services/crawlhub/deployment_service.py`：

```python
import io
import logging
import tarfile
from pathlib import Path

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from sqlalchemy import func, select

from extensions.ext_mongodb import mongodb_client
from models.crawlhub import Spider
from models.crawlhub.deployment import Deployment, DeploymentStatus
from services.base_service import BaseService
from services.crawlhub.coder_workspace_service import CoderWorkspaceService
from services.crawlhub.filebrowser_service import FileBrowserService

logger = logging.getLogger(__name__)

GRIDFS_BUCKET_NAME = "spider_deployments"


class DeploymentService(BaseService):
    """部署快照管理服务"""

    async def deploy_from_workspace(
        self,
        spider: Spider,
        deploy_note: str | None = None,
    ) -> Deployment:
        """从 Workspace 拉取代码并创建部署快照

        1. 确保 Workspace 运行中
        2. 下载项目文件
        3. 打包为 tar.gz
        4. 上传到 GridFS
        5. 创建 Deployment 记录
        6. 更新 Spider 的 active_deployment_id
        """
        if not spider.coder_workspace_id:
            raise ValueError("爬虫没有关联的工作区，无法部署")

        # 1. 获取工作区信息
        ws_service = CoderWorkspaceService(self.db)
        try:
            workspace = await ws_service.ensure_workspace_running(spider)
            await ws_service.wait_for_workspace_ready(spider.coder_workspace_id, timeout=60)
        finally:
            await ws_service.close()

        # 2. 下载项目文件
        fb_service = FileBrowserService()
        project_name = spider.coder_workspace_name or spider.name
        # Workspace 中项目路径约定: /workspace/{project_name}
        # FileBrowser 根目录对应 /home/coder，所以项目路径为 /workspace/{project_name}
        import re
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", spider.name)
        project_path = f"/workspace/{safe_name}"

        files = await fb_service.download_project(workspace, project_path)
        if not files:
            raise ValueError(f"工作区项目目录为空: {project_path}")

        # 3. 打包为 tar.gz
        archive_buf = io.BytesIO()
        with tarfile.open(fileobj=archive_buf, mode="w:gz") as tar:
            for rel_path, content in files.items():
                info = tarfile.TarInfo(name=rel_path)
                info.size = len(content)
                tar.addfile(info, io.BytesIO(content))
        archive_bytes = archive_buf.getvalue()

        # 4. 上传到 GridFS
        fs = AsyncIOMotorGridFSBucket(mongodb_client.db, bucket_name=GRIDFS_BUCKET_NAME)
        grid_in = fs.open_upload_stream(
            filename=f"spider-{spider.id}-deploy.tar.gz",
            metadata={
                "spider_id": str(spider.id),
                "file_count": len(files),
            },
        )
        await grid_in.write(archive_bytes)
        await grid_in.close()
        file_id = str(grid_in._id)

        # 5. 计算版本号
        max_version = await self.db.scalar(
            select(func.max(Deployment.version)).where(
                Deployment.spider_id == spider.id
            )
        )
        next_version = (max_version or 0) + 1

        # 6. 将之前的 active 部署归档
        result = await self.db.execute(
            select(Deployment).where(
                Deployment.spider_id == spider.id,
                Deployment.status == DeploymentStatus.ACTIVE,
            )
        )
        for old_deploy in result.scalars().all():
            old_deploy.status = DeploymentStatus.ARCHIVED

        # 7. 创建 Deployment 记录
        deployment = Deployment(
            spider_id=spider.id,
            version=next_version,
            status=DeploymentStatus.ACTIVE,
            file_archive_id=file_id,
            entry_point=spider.entry_point,
            file_count=len(files),
            archive_size=len(archive_bytes),
            deploy_note=deploy_note,
        )
        self.db.add(deployment)

        # 8. 更新 spider 的 active_deployment_id
        spider.active_deployment_id = deployment.id
        await self.db.commit()
        await self.db.refresh(deployment)

        logger.info(
            f"Deployed spider {spider.id} v{next_version}: "
            f"{len(files)} files, {len(archive_bytes)} bytes"
        )
        return deployment

    async def get_deployment(self, deployment_id: str) -> Deployment | None:
        """获取部署详情"""
        result = await self.db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        spider_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Deployment], int]:
        """获取部署历史"""
        query = select(Deployment).where(Deployment.spider_id == spider_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(Deployment.version.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def rollback(self, spider: Spider, deployment_id: str) -> Deployment:
        """回滚到指定版本"""
        target = await self.get_deployment(deployment_id)
        if not target or target.spider_id != spider.id:
            raise ValueError("部署记录不存在或不属于此爬虫")

        # 归档当前 active
        result = await self.db.execute(
            select(Deployment).where(
                Deployment.spider_id == spider.id,
                Deployment.status == DeploymentStatus.ACTIVE,
            )
        )
        for old_deploy in result.scalars().all():
            old_deploy.status = DeploymentStatus.ARCHIVED

        # 激活目标版本
        target.status = DeploymentStatus.ACTIVE
        spider.active_deployment_id = target.id
        await self.db.commit()
        await self.db.refresh(target)

        logger.info(f"Rolled back spider {spider.id} to deployment v{target.version}")
        return target

    @staticmethod
    async def download_archive(file_archive_id: str) -> bytes:
        """从 GridFS 下载代码包"""
        fs = AsyncIOMotorGridFSBucket(mongodb_client.db, bucket_name=GRIDFS_BUCKET_NAME)
        buf = io.BytesIO()
        await fs.download_to_stream(ObjectId(file_archive_id), buf)
        return buf.getvalue()

    @staticmethod
    async def extract_archive(archive_bytes: bytes, target_dir: Path) -> None:
        """解压代码包到目标目录"""
        buf = io.BytesIO(archive_bytes)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            tar.extractall(path=str(target_dir), filter="data")
```

### Step 2: 更新服务导出

修改 `app/services/crawlhub/__init__.py`，添加：

```python
from .deployment_service import DeploymentService
```

并在 `__all__` 中添加 `"DeploymentService"`。

---

## Task 5: 改造 SpiderRunnerService

**目标:** 让测试执行支持从 Workspace 实时拉取代码，生产执行支持从部署快照恢复代码。

**Files:**
- Modify: `app/services/crawlhub/spider_runner_service.py`

### Step 1: 重构 prepare_project_files 方法

替换现有 `prepare_project_files` 方法（第 101-110 行），支持三种代码来源：

```python
async def prepare_project_files(self, spider: Spider, work_dir: Path) -> None:
    """准备项目文件到工作目录

    代码来源优先级:
    1. 如果有 Coder Workspace 且正在运行 → 从 Workspace 拉取
    2. 如果有 script_content → 写入 main.py
    3. 否则抛出错误
    """
    if spider.coder_workspace_id:
        try:
            await self._pull_from_workspace(spider, work_dir)
            return
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to pull from workspace, falling back to script_content: {e}"
            )

    if spider.script_content:
        main_file = work_dir / "main.py"
        main_file.write_text(spider.script_content)
        return

    raise ValueError("爬虫没有可执行的代码（无工作区且无 script_content）")

async def _pull_from_workspace(self, spider: Spider, work_dir: Path) -> None:
    """从 Workspace 拉取项目文件"""
    import re
    from services.crawlhub.coder_workspace_service import CoderWorkspaceService
    from services.crawlhub.filebrowser_service import FileBrowserService

    ws_service = CoderWorkspaceService(self.db)
    try:
        workspace = await ws_service.ensure_workspace_running(spider)
        await ws_service.wait_for_workspace_ready(spider.coder_workspace_id, timeout=60)
    finally:
        await ws_service.close()

    fb_service = FileBrowserService()
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", spider.name)
    project_path = f"/workspace/{safe_name}"

    files = await fb_service.download_project(workspace, project_path)
    if not files:
        raise ValueError(f"工作区项目目录为空: {project_path}")

    for rel_path, content in files.items():
        target = work_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
```

### Step 2: 添加从部署快照准备文件的方法

在 `_pull_from_workspace` 之后添加：

```python
async def prepare_from_deployment(self, spider: Spider, work_dir: Path) -> None:
    """从部署快照准备项目文件（生产执行用）

    优先级:
    1. 有 active_deployment_id → 从 GridFS 下载快照
    2. 有 script_content → 写入 main.py
    3. 否则抛出错误
    """
    if spider.active_deployment_id:
        from services.crawlhub.deployment_service import DeploymentService

        deployment = await DeploymentService(self.db).get_deployment(
            spider.active_deployment_id
        )
        if deployment:
            archive = await DeploymentService.download_archive(deployment.file_archive_id)
            await DeploymentService.extract_archive(archive, work_dir)
            return

    if spider.script_content:
        main_file = work_dir / "main.py"
        main_file.write_text(spider.script_content)
        return

    raise ValueError("爬虫没有可执行的代码（无部署快照且无 script_content）")
```

### Step 3: 改进命令构建逻辑

在 `run_test` 和 `run_spider_sync` 中，替换简单的命令构建逻辑为可复用的方法。在 `prepare_from_deployment` 之后添加：

```python
def _build_command(self, spider: Spider, work_dir: Path) -> list[str]:
    """构建执行命令"""
    if spider.source == ProjectSource.SCRAPY:
        return ["scrapy", "crawl", spider.name]

    # 检查入口点配置
    entry_point = spider.entry_point or "main:run"
    module, _, func_name = entry_point.partition(":")
    if not func_name:
        func_name = "run"

    return ["python", "-c", f"""
import sys, json
sys.path.insert(0, '{work_dir}')
from {module} import {func_name}
result = {func_name}({{}})
if result is not None:
    print(json.dumps(result, ensure_ascii=False, default=str))
"""]
```

### Step 4: 更新 run_spider_sync 使用部署快照

修改 `run_spider_sync` 方法（第 39-99 行），将 `await self.prepare_project_files(spider, work_dir)` 替换为 `await self.prepare_from_deployment(spider, work_dir)`，并将 `cmd` 构建部分替换为 `cmd = self._build_command(spider, work_dir)`。

完整替换 `run_spider_sync`：

```python
async def run_spider_sync(self, spider: Spider, task: SpiderTask) -> None:
    """同步执行爬虫（用于 Celery worker 调用，不走 SSE）"""
    task.status = SpiderTaskStatus.RUNNING
    task.started_at = datetime.utcnow()
    await self.db.commit()

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            await self.prepare_from_deployment(spider, work_dir)

            cmd = self._build_command(spider, work_dir)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(work_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=300
                )
            except asyncio.TimeoutError:
                process.kill()
                task.status = SpiderTaskStatus.FAILED
                task.error_message = "执行超时 (最大 5 分钟)"
                return

            stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""

            if process.returncode == 0:
                task.status = SpiderTaskStatus.COMPLETED
                await self._store_spider_data(task, stdout_str)
            else:
                task.status = SpiderTaskStatus.FAILED
                task.error_message = f"进程退出码: {process.returncode}"
                if stderr_str:
                    task.error_message += f"\n{stderr_str[:2000]}"

            await self._store_task_log(task, stdout_str, stderr_str)

    except Exception as e:
        task.status = SpiderTaskStatus.FAILED
        task.error_message = str(e)
    finally:
        task.finished_at = datetime.utcnow()
        await self.db.commit()
```

### Step 5: 更新 run_test 使用 Workspace 实时代码

修改 `run_test` 方法中的文件准备和命令构建部分（保持 SSE 流逻辑不变）。将第 133 行的 `await self.prepare_project_files(spider, work_dir)` 保持不变（`prepare_project_files` 已在 Step 1 中重构为支持 Workspace 拉取），将命令构建替换为 `cmd = self._build_command(spider, work_dir)`。

同时在 `run_test` 的 finally 块中（第 210-228 行），在持久化日志之后、yield 最终状态之前，添加测试数据存储：

```python
# 持久化日志到 MongoDB
await self._store_task_log(
    task,
    "\n".join(stdout_lines),
    "\n".join(stderr_lines),
)

# 存储测试数据
if task.status == SpiderTaskStatus.COMPLETED:
    await self._store_spider_data(task, "\n".join(stdout_lines))
```

---

## Task 6: Deployment API 路由

**目标:** 提供部署、版本列表、回滚的 HTTP API。

**Files:**
- Create: `app/routers/admin/crawlhub/deployments.py`
- Modify: `app/routers/admin/crawlhub/__init__.py`

### Step 1: 创建部署路由

创建 `app/routers/admin/crawlhub/deployments.py`：

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from schemas.crawlhub.deployment import (
    DeployRequest,
    DeploymentResponse,
    DeploymentListResponse,
)
from schemas.platform import PaginatedResponse
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub import SpiderService
from services.crawlhub.deployment_service import DeploymentService

router = APIRouter(prefix="/spiders/{spider_id}/deployments", tags=["CrawlHub - Deployments"])


@router.post("", response_model=ApiResponse[DeploymentResponse])
async def create_deployment(
    spider_id: str,
    data: DeployRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """从工作区部署当前代码"""
    spider = await SpiderService(db).get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    service = DeploymentService(db)
    try:
        deployment = await service.deploy_from_workspace(
            spider,
            deploy_note=data.deploy_note if data else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ApiResponse(data=DeploymentResponse.model_validate(deployment))


@router.get("", response_model=ApiResponse[PaginatedResponse[DeploymentResponse]])
async def list_deployments(
    spider_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取部署历史"""
    service = DeploymentService(db)
    deployments, total = await service.get_list(spider_id, page, page_size)
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=[DeploymentResponse.model_validate(d) for d in deployments],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get("/{deployment_id}", response_model=ApiResponse[DeploymentResponse])
async def get_deployment(
    spider_id: str,
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取部署详情"""
    service = DeploymentService(db)
    deployment = await service.get_deployment(deployment_id)
    if not deployment or deployment.spider_id != spider_id:
        raise HTTPException(status_code=404, detail="部署记录不存在")
    return ApiResponse(data=DeploymentResponse.model_validate(deployment))


@router.post("/{deployment_id}/rollback", response_model=ApiResponse[DeploymentResponse])
async def rollback_deployment(
    spider_id: str,
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """回滚到指定版本"""
    spider = await SpiderService(db).get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    service = DeploymentService(db)
    try:
        deployment = await service.rollback(spider, deployment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ApiResponse(data=DeploymentResponse.model_validate(deployment))
```

### Step 2: 注册路由

修改 `app/routers/admin/crawlhub/__init__.py`，添加：

```python
from .deployments import router as deployments_router
```

并添加：

```python
router.include_router(deployments_router)
```

---

## Task 7: 增强数据预览

**目标:** 数据 API 支持 test/prod 分离和结构化预览。

**Files:**
- Modify: `app/services/crawlhub/data_service.py`
- Modify: `app/routers/admin/crawlhub/data.py`

### Step 1: DataService 增加 is_test 过滤和 preview 方法

在 `DataService.query` 方法中，添加 `is_test` 参数支持。修改 `query` 方法签名和过滤逻辑（第 51-90 行）：

在 `query` 方法的参数中添加 `is_test: bool | None = None`，在 `query_filter` 构建区域添加：

```python
if is_test is not None:
    # 需要关联 task 的 is_test 字段，但 spider_data 中没有这个字段
    # 所以在存储数据时需要加上 is_test 标记
    query_filter["is_test"] = is_test
```

在 `DataService` 类最后添加 `preview` 方法：

```python
async def preview(
    self,
    task_id: str,
    limit: int = 20,
) -> dict:
    """数据预览：返回结构化的数据摘要

    Returns:
        {
            "items": [...],  # 前 N 条数据
            "total": int,
            "fields": {字段名: {"type": str, "non_null_count": int, "sample": Any}},
        }
    """
    if not mongodb_client.is_enabled():
        return {"items": [], "total": 0, "fields": {}}

    await self.ensure_indexes()

    query_filter = {"task_id": task_id}

    try:
        total = await self.collection.count_documents(query_filter)

        cursor = (
            self.collection.find(query_filter)
            .sort("created_at", -1)
            .limit(limit)
        )

        items = []
        field_stats: dict[str, dict] = {}

        async for doc in cursor:
            data = doc.get("data", {})
            items.append(data)

            if isinstance(data, dict):
                for key, value in data.items():
                    if key not in field_stats:
                        field_stats[key] = {
                            "type": type(value).__name__ if value is not None else "null",
                            "non_null_count": 0,
                            "sample": None,
                        }
                    if value is not None:
                        field_stats[key]["non_null_count"] += 1
                        if field_stats[key]["sample"] is None:
                            field_stats[key]["sample"] = value

        return {
            "items": items,
            "total": total,
            "fields": field_stats,
        }
    except Exception as e:
        logger.error(f"Failed to preview data: {e}")
        return {"items": [], "total": 0, "fields": {}}
```

### Step 2: 修改 _store_spider_data 添加 is_test 标记

修改 `app/services/crawlhub/spider_runner_service.py` 中的 `_store_spider_data` 方法（第 230-270 行），在插入文档时添加 `is_test` 字段：

在构建 `docs` 列表和 `insert_one` 的 dict 中，添加 `"is_test": task.is_test`。

原代码中 `docs` 列表推导：

```python
docs = [{
    "task_id": task.id,
    "spider_id": task.spider_id,
    "data": item,
    "created_at": datetime.utcnow(),
} for item in data]
```

改为：

```python
docs = [{
    "task_id": str(task.id),
    "spider_id": str(task.spider_id),
    "data": item,
    "is_test": task.is_test,
    "created_at": datetime.utcnow(),
} for item in data]
```

同样修改 `insert_one` 的 dict，添加 `"is_test": task.is_test`。

### Step 3: Data 路由增加 preview 端点和 is_test 过滤

修改 `app/routers/admin/crawlhub/data.py`：

在 `list_data` 函数的参数中添加 `is_test: bool | None = Query(None)`，并传递给 `service.query`。

在 `list_data` 之后、`export_json` 之前添加 preview 端点（注意：静态路由要在动态路由前面）：

```python
@router.get("/preview/{task_id}")
async def preview_data(
    task_id: str,
    limit: int = Query(20, ge=1, le=100),
):
    """数据预览（结构化摘要）"""
    service = DataService()
    result = await service.preview(task_id, limit)
    return ApiResponse(data=result)
```

---

## Task 8: 整合 spider_tasks.py 生产执行流程

**目标:** 让 Celery 任务使用部署快照执行。

**Files:**
- Modify: `app/tasks/spider_tasks.py`

### Step 1: 更新 execute_spider

当前 `execute_spider`（第 43-107 行）直接调用 `runner.run_spider_sync(spider, task)`。`run_spider_sync` 已在 Task 5 中改为使用 `prepare_from_deployment`，所以 **Celery 任务本身不需要修改**，改动已透过 `run_spider_sync` 的重构自动生效。

需要验证：确保 `run_spider_sync` 中的 `prepare_from_deployment` 在没有 `active_deployment_id` 时能正确回退到 `script_content`。

---

## Task 9: 端到端验证

**目标:** 验证完整流程可以跑通。

### Step 1: 验证导入链

确认所有文件的导入没有循环依赖：

```bash
cd app && python -c "
from models.crawlhub import Deployment, DeploymentStatus
from services.crawlhub import DeploymentService
from schemas.crawlhub.deployment import DeployRequest, DeploymentResponse
print('All imports OK')
"
```

### Step 2: 验证迁移

```bash
cd app && alembic upgrade head
```

### Step 3: 验证 API 启动

确认 FastAPI 应用能正常启动，所有路由注册成功。

---

## 文件变更汇总

| 操作 | 文件 | 说明 |
|------|------|------|
| **Modify** | `app/services/crawlhub/filebrowser_service.py` | +3 方法: list_directory, download_file, download_project |
| **Create** | `app/models/crawlhub/deployment.py` | Deployment 模型 |
| **Modify** | `app/models/crawlhub/spider.py` | +active_deployment_id 字段 |
| **Modify** | `app/models/crawlhub/__init__.py` | 导出 Deployment, DeploymentStatus |
| **Create** | `app/schemas/crawlhub/deployment.py` | DeployRequest, DeploymentResponse |
| **Modify** | `app/schemas/crawlhub/spider.py` | SpiderResponse +active_deployment_id |
| **Modify** | `app/schemas/crawlhub/__init__.py` | 导出新 schemas |
| **Create** | `app/services/crawlhub/deployment_service.py` | 部署核心逻辑 |
| **Modify** | `app/services/crawlhub/__init__.py` | 导出 DeploymentService |
| **Modify** | `app/services/crawlhub/spider_runner_service.py` | 重构文件准备 + 命令构建 |
| **Create** | `app/routers/admin/crawlhub/deployments.py` | 部署 API 路由 |
| **Modify** | `app/routers/admin/crawlhub/__init__.py` | 注册部署路由 |
| **Modify** | `app/services/crawlhub/data_service.py` | +preview 方法, is_test 过滤 |
| **Modify** | `app/routers/admin/crawlhub/data.py` | +preview 端点, is_test 参数 |
| **Create** | Alembic migration | 新表 + 新字段 |

## 完整 API 端点（新增）

| Method | Endpoint | 说明 |
|--------|----------|------|
| POST | `/crawlhub/spiders/{id}/deployments` | 从工作区部署 |
| GET | `/crawlhub/spiders/{id}/deployments` | 部署历史列表 |
| GET | `/crawlhub/spiders/{id}/deployments/{did}` | 部署详情 |
| POST | `/crawlhub/spiders/{id}/deployments/{did}/rollback` | 回滚到指定版本 |
| GET | `/crawlhub/data/preview/{task_id}` | 数据预览 |
