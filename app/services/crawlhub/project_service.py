from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub import Project, Spider
from schemas.crawlhub import ProjectCreate, ProjectUpdate
from services.base_service import BaseService


class ProjectService(BaseService):
    async def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
    ) -> tuple[list[Project], int]:
        """获取项目列表"""
        query = select(Project)

        if keyword:
            query = query.where(Project.name.ilike(f"%{keyword}%"))

        # 统计总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # 分页查询
        query = query.order_by(Project.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        projects = list(result.scalars().all())

        # 获取每个项目的爬虫数量
        for project in projects:
            spider_count_query = select(func.count()).where(Spider.project_id == project.id)
            project.spider_count = await self.db.scalar(spider_count_query) or 0

        return projects, total

    async def get_by_id(self, project_id: str) -> Project | None:
        """根据 ID 获取项目"""
        query = select(Project).where(Project.id == project_id)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()

        if project:
            spider_count_query = select(func.count()).where(Spider.project_id == project.id)
            project.spider_count = await self.db.scalar(spider_count_query) or 0

        return project

    async def create(self, data: ProjectCreate) -> Project:
        """创建项目"""
        project = Project(**data.model_dump())
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        project.spider_count = 0
        return project

    async def update(self, project_id: str, data: ProjectUpdate) -> Project | None:
        """更新项目"""
        project = await self.get_by_id(project_id)
        if not project:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete(self, project_id: str) -> bool:
        """删除项目"""
        project = await self.get_by_id(project_id)
        if not project:
            return False

        await self.db.delete(project)
        await self.db.commit()
        return True
