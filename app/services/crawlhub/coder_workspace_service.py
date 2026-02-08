"""Coder 工作区服务

管理 Spider 与 Coder 工作区的关联。
"""

import asyncio
import logging
import os
import re

from models.crawlhub import Spider
from services.base_service import BaseService

from .coder_client import CoderClient, CoderAPIError

logger = logging.getLogger(__name__)


class CoderWorkspaceService(BaseService):
    """Coder 工作区服务"""

    def __init__(self, db):
        super().__init__(db)
        self.coder_client = CoderClient()
        self.template_name = os.getenv("CODER_TEMPLATE_NAME", "spider")
        self.default_owner = os.getenv("CODER_DEFAULT_OWNER", "me")

    async def close(self):
        """关闭客户端连接"""
        await self.coder_client.close()

    def _generate_workspace_name(self, spider: Spider) -> str:
        """生成工作区名称

        规则:
        - 以爬虫名称为基础
        - 替换不合法字符为连字符
        - 确保以字母开头
        - 限制长度
        """
        # 只保留字母、数字、连字符
        name = re.sub(r"[^a-zA-Z0-9-]", "-", spider.name.lower())
        # 去除连续的连字符
        name = re.sub(r"-+", "-", name)
        # 去除首尾连字符
        name = name.strip("-")
        # 确保以字母开头
        if not name or not name[0].isalpha():
            name = "spider-" + name
        # 添加 spider ID 的前 8 位确保唯一
        spider_id_prefix = spider.id[:8] if spider.id else ""
        name = f"{name}-{spider_id_prefix}"
        # 限制长度 (Coder 工作区名称最长 32 字符)
        return name[:32].rstrip("-")

    async def create_workspace_for_spider(
        self,
        spider: Spider,
        source: str | None = None,
        project_name: str | None = None,
        git_repo: str | None = None,
    ) -> dict:
        """为爬虫创建 Coder 工作区

        Args:
            spider: 爬虫对象
            source: 项目来源，可选值: empty, scrapy, git, upload。未传时从 spider.source 读取
            project_name: 项目名称，默认使用爬虫名称
            git_repo: Git 仓库地址（当 source=git 时使用）。未传时从 spider.git_repo 读取

        Returns:
            工作区信息
        """
        # 未传参时从 spider 对象读取
        if source is None:
            source = spider.source.value if spider.source else "empty"
        if git_repo is None:
            git_repo = spider.git_repo
        # 检查是否已有工作区
        if spider.coder_workspace_id:
            try:
                workspace = await self.coder_client.get_workspace(spider.coder_workspace_id)
                return workspace
            except CoderAPIError:
                # 工作区不存在，继续创建新的
                pass

        # 获取模板
        try:
            template = await self.coder_client.get_template_by_name(self.template_name)
        except CoderAPIError as e:
            logger.error(f"Failed to get template {self.template_name}: {e}")
            raise

        # 生成工作区名称
        workspace_name = self._generate_workspace_name(spider)

        # 准备参数
        rich_parameter_values = [
            {"name": "source", "value": source},
            {"name": "name", "value": project_name or re.sub(r"[^a-zA-Z0-9_]", "_", spider.name)},
        ]
        # 如果是 git 来源，添加仓库地址
        if source == "git" and git_repo:
            rich_parameter_values.append({"name": "repo", "value": git_repo})

        # 创建工作区
        try:
            workspace = await self.coder_client.create_workspace(
                owner=self.default_owner,
                template_id=template["id"],
                name=workspace_name,
                rich_parameter_values=rich_parameter_values,
            )

            # 更新 spider 记录
            spider.coder_workspace_id = workspace["id"]
            spider.coder_workspace_name = workspace["name"]
            await self.db.commit()

            logger.info(
                f"Created workspace {workspace['name']} (ID: {workspace['id']}) for spider {spider.id}"
            )
            return workspace

        except CoderAPIError as e:
            logger.error(f"Failed to create workspace for spider {spider.id}: {e}")
            raise

    async def get_workspace(self, spider: Spider) -> dict | None:
        """获取爬虫关联的工作区"""
        if not spider.coder_workspace_id:
            return None
        try:
            return await self.coder_client.get_workspace(spider.coder_workspace_id)
        except CoderAPIError:
            return None

    async def get_workspace_status(self, spider: Spider) -> dict | None:
        """获取工作区状态

        Returns:
            {
                "status": "pending" | "starting" | "running" | "stopping" | "stopped" | "failed",
                "agent_status": "connecting" | "connected" | "disconnected" | "timeout" | None,
                "url": str | None,
                "last_used_at": str | None,
                "build_status": str | None,
                "build_job": str | None,
                "is_ready": bool,
            }
        """
        workspace = await self.get_workspace(spider)
        if not workspace:
            return None

        latest_build = workspace.get("latest_build", {})
        status = latest_build.get("status", "unknown")

        # 映射 Coder 状态到简化状态
        status_map = {
            "pending": "pending",
            "starting": "starting",
            "running": "running",
            "stopping": "stopping",
            "stopped": "stopped",
            "failed": "failed",
            "canceling": "stopping",
            "canceled": "stopped",
            "deleting": "stopping",
            "deleted": "stopped",
        }
        simplified_status = status_map.get(status, "unknown")

        # 获取 agent 状态
        agent_status = None
        is_ready = False
        if simplified_status == "running":
            try:
                agents = await self.coder_client.get_workspace_agents(spider.coder_workspace_id)
                if agents:
                    agent = agents[0]
                    agent_status = agent.get("status")
                    is_ready = agent_status == "connected"
            except CoderAPIError:
                pass

        # 获取 code-server URL
        url = None
        if is_ready:
            url = await self.get_workspace_url(spider)

        return {
            "status": simplified_status,
            "agent_status": agent_status,
            "url": url,
            "last_used_at": workspace.get("last_used_at"),
            "build_status": status,
            "build_job": latest_build.get("job", {}).get("status"),
            "is_ready": is_ready,
        }

    async def get_workspace_url(self, spider: Spider) -> str | None:
        """获取 code-server 访问 URL

        优先获取 code-server 应用的 URL，如果没有则返回 None。
        """
        workspace = await self.get_workspace(spider)
        if not workspace:
            return None

        # 检查工作区是否运行中
        latest_build = workspace.get("latest_build", {})
        if latest_build.get("status") != "running":
            return None

        # 获取工作区的 apps
        try:
            apps = await self.coder_client.get_workspace_apps(spider.coder_workspace_id)
        except CoderAPIError:
            return None

        # 查找 code-server 应用
        for app in apps:
            if app.get("slug") == "code-server" or "code" in app.get("slug", "").lower():
                # 获取 agent 信息来构建 URL
                agents = await self.coder_client.get_workspace_agents(spider.coder_workspace_id)
                if agents:
                    agent_name = agents[0].get("name", "main")
                    return self.coder_client.get_app_url(
                        workspace_owner=workspace.get("owner_name", self.default_owner),
                        workspace_name=workspace["name"],
                        agent_name=agent_name,
                        app_slug=app.get("slug", "code-server"),
                        subdomain=app.get("subdomain", False),
                    )
        return None

    async def ensure_workspace_running(self, spider: Spider) -> dict:
        """确保工作区处于运行状态

        如果工作区不存在，创建一个；如果已停止，则启动它。

        Returns:
            工作区信息
        """
        # 如果没有工作区，先创建
        if not spider.coder_workspace_id:
            return await self.create_workspace_for_spider(spider)

        workspace = await self.get_workspace(spider)
        if not workspace:
            # 工作区已被删除，重新创建
            spider.coder_workspace_id = None
            spider.coder_workspace_name = None
            return await self.create_workspace_for_spider(spider)

        # 检查状态
        latest_build = workspace.get("latest_build", {})
        status = latest_build.get("status")

        if status == "running":
            return workspace

        if status in ("stopped", "failed", "canceled"):
            # 启动工作区
            await self.coder_client.start_workspace(spider.coder_workspace_id)
            logger.info(f"Started workspace {workspace['name']} for spider {spider.id}")

        # 返回最新状态
        return await self.coder_client.get_workspace(spider.coder_workspace_id)

    async def wait_for_workspace_ready(
        self, workspace_id: str, timeout: int = 120, poll_interval: int = 3
    ) -> bool:
        """等待工作区完全就绪

        检查条件:
        1. workspace.latest_build.status == "running"
        2. workspace.latest_build.resources[].agents[].status == "connected"

        Args:
            workspace_id: 工作区 ID
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）

        Returns:
            True 表示就绪，False 表示超时
        """
        elapsed = 0
        while elapsed < timeout:
            try:
                workspace = await self.coder_client.get_workspace(workspace_id)
                latest_build = workspace.get("latest_build", {})

                # 检查构建状态
                if latest_build.get("status") == "failed":
                    logger.error(f"Workspace build failed: {workspace_id}")
                    return False

                if latest_build.get("status") == "running":
                    # 检查 agent 状态
                    agents = await self.coder_client.get_workspace_agents(workspace_id)
                    if agents and all(
                        agent.get("status") == "connected" for agent in agents
                    ):
                        logger.info(f"Workspace {workspace_id} is ready")
                        return True

            except CoderAPIError as e:
                logger.warning(f"Error checking workspace status: {e}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        logger.warning(f"Timeout waiting for workspace {workspace_id} to be ready")
        return False

    async def stop_workspace(self, spider: Spider) -> bool:
        """停止工作区"""
        if not spider.coder_workspace_id:
            return False

        try:
            await self.coder_client.stop_workspace(spider.coder_workspace_id)
            logger.info(f"Stopped workspace for spider {spider.id}")
            return True
        except CoderAPIError as e:
            logger.error(f"Failed to stop workspace for spider {spider.id}: {e}")
            return False

    async def delete_workspace(self, spider: Spider) -> bool:
        """删除工作区"""
        if not spider.coder_workspace_id:
            return True

        try:
            await self.coder_client.delete_workspace(spider.coder_workspace_id)
            logger.info(f"Deleted workspace for spider {spider.id}")

            # 清除 spider 的工作区信息
            spider.coder_workspace_id = None
            spider.coder_workspace_name = None
            await self.db.commit()

            return True
        except CoderAPIError as e:
            logger.error(f"Failed to delete workspace for spider {spider.id}: {e}")
            return False
