import io
import logging
import re
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

        # 1. 获取工作区信息并等待就绪
        ws_service = CoderWorkspaceService(self.db)
        try:
            workspace = await ws_service.ensure_workspace_running(spider)
            await ws_service.wait_for_workspace_ready(spider.coder_workspace_id, timeout=120)
        finally:
            await ws_service.close()

        # 2. 下载项目文件（FileBrowser 需要额外等待时间）
        fb_service = FileBrowserService()
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", spider.name)
        project_path = f"/workspace/{safe_name}"

        files = await fb_service.download_project(workspace, project_path, timeout=120)
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

    async def restore_to_workspace(
        self,
        spider: Spider,
        deployment_id: str | None = None,
    ) -> int:
        """将部署快照恢复到工作区

        从 GridFS 下载代码包，解压后通过 FileBrowser 上传到工作区。
        用于工作区重建后恢复代码。

        Args:
            spider: 爬虫对象（需要有 coder_workspace_id）
            deployment_id: 指定恢复的部署ID，为空则使用 active_deployment_id

        Returns:
            恢复的文件数量

        Raises:
            ValueError: 没有工作区或没有可恢复的部署
        """
        if not spider.coder_workspace_id:
            raise ValueError("爬虫没有关联的工作区")

        # 确定要恢复的部署
        target_id = deployment_id or spider.active_deployment_id
        if not target_id:
            raise ValueError("没有可恢复的部署快照")

        deployment = await self.get_deployment(target_id)
        if not deployment:
            raise ValueError("部署记录不存在")

        # 下载代码包并解压到内存
        archive_bytes = await self.download_archive(deployment.file_archive_id)
        files: list[tuple[str, bytes]] = []
        buf = io.BytesIO(archive_bytes)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.isfile():
                    f = tar.extractfile(member)
                    if f:
                        files.append((member.name, f.read()))

        if not files:
            return 0

        # 确保工作区就绪
        ws_service = CoderWorkspaceService(self.db)
        try:
            workspace = await ws_service.ensure_workspace_running(spider)
            await ws_service.wait_for_workspace_ready(spider.coder_workspace_id, timeout=120)
        finally:
            await ws_service.close()

        # 上传到工作区
        fb_service = FileBrowserService()
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", spider.name)
        base_dir = f"/workspace/{safe_name}"

        success_count, _, _ = await fb_service.upload_files(workspace, files, base_dir=base_dir)

        logger.info(
            f"Restored deployment v{deployment.version} to workspace: "
            f"{success_count}/{len(files)} files"
        )
        return success_count
