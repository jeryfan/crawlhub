"""Coder API 客户端

封装 Coder REST API 调用，用于管理工作区。
"""

import os
from typing import Any

import httpx


class CoderAPIError(Exception):
    """Coder API 错误"""

    def __init__(self, message: str, status_code: int | None = None, response: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class CoderClient:
    """Coder REST API 客户端"""

    def __init__(
        self,
        api_url: str | None = None,
        api_token: str | None = None,
        access_url: str | None = None,
        timeout: float = 30.0,
    ):
        self.api_url = (api_url or os.getenv("CODER_API_URL", "http://localhost:7080")).rstrip("/")
        # access_url 用于前端访问，默认与 api_url 相同
        self.access_url = (access_url or os.getenv("CODER_ACCESS_URL", self.api_url)).rstrip("/")
        self.api_token = api_token or os.getenv("CODER_API_TOKEN", "")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers={
                    "Coder-Session-Token": self.api_token,
                    "Accept": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """发送 HTTP 请求"""
        try:
            response = await self.client.request(
                method=method,
                url=path,
                json=json,
                params=params,
            )
            if response.status_code >= 400:
                error_data = None
                error_message = response.text
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        error_message = error_data.get("message", error_message)
                except Exception:
                    pass
                raise CoderAPIError(
                    f"Coder API error: {response.status_code} - {error_message}",
                    status_code=response.status_code,
                    response=error_data,
                )
            if response.status_code == 204:
                return {}
            # Handle empty response
            if not response.text:
                return {}
            return response.json()
        except httpx.RequestError as e:
            raise CoderAPIError(f"Request failed: {e}") from e

    # ============ User API ============

    async def get_current_user(self) -> dict[str, Any]:
        """获取当前用户信息"""
        return await self._request("GET", "/api/v2/users/me")

    # ============ Template API ============

    async def get_templates(self, organization_id: str = "default") -> list[dict[str, Any]]:
        """获取模板列表"""
        return await self._request("GET", f"/api/v2/organizations/{organization_id}/templates")

    async def get_template_by_name(
        self, template_name: str, organization_id: str = "default"
    ) -> dict[str, Any]:
        """根据名称获取模板"""
        return await self._request(
            "GET", f"/api/v2/organizations/{organization_id}/templates/{template_name}"
        )

    async def get_template_version(self, template_id: str) -> dict[str, Any]:
        """获取模板当前版本"""
        template = await self._request("GET", f"/api/v2/templates/{template_id}")
        version_id = template.get("active_version_id")
        if not version_id:
            raise CoderAPIError(f"Template {template_id} has no active version")
        return await self._request("GET", f"/api/v2/templateversions/{version_id}")

    # ============ Workspace API ============

    async def create_workspace(
        self,
        owner: str,
        template_id: str,
        name: str,
        rich_parameter_values: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """创建工作区

        Args:
            owner: 工作区所有者用户名
            template_id: 模板 ID
            name: 工作区名称
            rich_parameter_values: 模板参数列表，格式 [{"name": "param_name", "value": "param_value"}]
        """
        # 获取模板的活跃版本
        template = await self._request("GET", f"/api/v2/templates/{template_id}")
        active_version_id = template.get("active_version_id")
        if not active_version_id:
            raise CoderAPIError(f"Template {template_id} has no active version")

        payload = {
            "name": name,
            "template_version_id": active_version_id,
        }
        if rich_parameter_values:
            payload["rich_parameter_values"] = rich_parameter_values

        return await self._request("POST", f"/api/v2/users/{owner}/workspaces", json=payload)

    async def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        """根据 ID 获取工作区"""
        return await self._request("GET", f"/api/v2/workspaces/{workspace_id}")

    async def get_workspace_by_name(self, owner: str, name: str) -> dict[str, Any]:
        """根据所有者和名称获取工作区"""
        return await self._request("GET", f"/api/v2/users/{owner}/workspace/{name}")

    async def list_workspaces(
        self,
        owner: str | None = None,
        template_id: str | None = None,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        """列出工作区"""
        params = {}
        if owner:
            params["owner"] = owner
        if template_id:
            params["template_id"] = template_id
        if q:
            params["q"] = q
        result = await self._request("GET", "/api/v2/workspaces", params=params)
        return result.get("workspaces", [])

    async def start_workspace(self, workspace_id: str) -> dict[str, Any]:
        """启动工作区"""
        workspace = await self.get_workspace(workspace_id)
        template_version_id = workspace.get("latest_build", {}).get("template_version_id")
        if not template_version_id:
            raise CoderAPIError(f"Cannot determine template version for workspace {workspace_id}")

        return await self._request(
            "POST",
            f"/api/v2/workspaces/{workspace_id}/builds",
            json={
                "transition": "start",
                "template_version_id": template_version_id,
            },
        )

    async def stop_workspace(self, workspace_id: str) -> dict[str, Any]:
        """停止工作区"""
        workspace = await self.get_workspace(workspace_id)
        template_version_id = workspace.get("latest_build", {}).get("template_version_id")
        if not template_version_id:
            raise CoderAPIError(f"Cannot determine template version for workspace {workspace_id}")

        return await self._request(
            "POST",
            f"/api/v2/workspaces/{workspace_id}/builds",
            json={
                "transition": "stop",
                "template_version_id": template_version_id,
            },
        )

    async def delete_workspace(self, workspace_id: str) -> dict[str, Any]:
        """删除工作区"""
        workspace = await self.get_workspace(workspace_id)
        template_version_id = workspace.get("latest_build", {}).get("template_version_id")
        if not template_version_id:
            raise CoderAPIError(f"Cannot determine template version for workspace {workspace_id}")

        return await self._request(
            "POST",
            f"/api/v2/workspaces/{workspace_id}/builds",
            json={
                "transition": "delete",
                "template_version_id": template_version_id,
            },
        )

    async def get_workspace_build(self, build_id: str) -> dict[str, Any]:
        """获取工作区构建状态"""
        return await self._request("GET", f"/api/v2/workspacebuilds/{build_id}")

    async def get_workspace_resources(self, workspace_id: str) -> list[dict[str, Any]]:
        """获取工作区资源列表"""
        workspace = await self.get_workspace(workspace_id)
        build_id = workspace.get("latest_build", {}).get("id")
        if not build_id:
            return []
        build = await self.get_workspace_build(build_id)
        return build.get("resources", [])

    async def get_workspace_agents(self, workspace_id: str) -> list[dict[str, Any]]:
        """获取工作区代理列表"""
        resources = await self.get_workspace_resources(workspace_id)
        agents = []
        for resource in resources:
            agents.extend(resource.get("agents", []))
        return agents

    async def get_workspace_apps(self, workspace_id: str) -> list[dict[str, Any]]:
        """获取工作区应用列表

        返回工作区中所有 agent 的所有 apps。
        """
        agents = await self.get_workspace_agents(workspace_id)
        apps = []
        for agent in agents:
            apps.extend(agent.get("apps", []))
        return apps

    def get_app_url(
        self,
        workspace_owner: str,
        workspace_name: str,
        agent_name: str,
        app_slug: str,
        subdomain: bool = False,
    ) -> str:
        """构建应用访问 URL

        Args:
            workspace_owner: 工作区所有者
            workspace_name: 工作区名称
            agent_name: 代理名称
            app_slug: 应用 slug
            subdomain: 是否使用子域名模式

        Returns:
            应用访问 URL（使用 access_url 供前端访问）
        """
        if subdomain:
            # 子域名模式: {app_slug}--{agent_name}--{workspace_name}--{owner}.coder.example.com
            # 这需要配置 wildcard DNS
            base_domain = self.access_url.replace("http://", "").replace("https://", "")
            return f"http://{app_slug}--{agent_name}--{workspace_name}--{workspace_owner}.{base_domain}"
        else:
            # 路径模式 - 使用 access_url 供前端访问
            return f"{self.access_url}/@{workspace_owner}/{workspace_name}.{agent_name}/apps/{app_slug}/"
