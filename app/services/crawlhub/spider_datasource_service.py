import logging

from sqlalchemy import select

from models.crawlhub import DataSource, SpiderDataSource
from schemas.crawlhub.datasource import (
    SpiderDataSourceCreate,
    SpiderDataSourceResponse,
    SpiderDataSourceUpdate,
)
from services.base_service import BaseService

logger = logging.getLogger(__name__)


class SpiderDataSourceService(BaseService):
    async def get_by_spider(self, spider_id: str) -> list[SpiderDataSourceResponse]:
        """获取爬虫关联的数据源列表"""
        query = (
            select(SpiderDataSource, DataSource)
            .outerjoin(DataSource, SpiderDataSource.datasource_id == DataSource.id)
            .where(SpiderDataSource.spider_id == spider_id)
            .order_by(SpiderDataSource.created_at.desc())
        )
        result = await self.db.execute(query)
        rows = result.all()

        items = []
        for assoc, ds in rows:
            resp = SpiderDataSourceResponse(
                id=str(assoc.id),
                spider_id=str(assoc.spider_id),
                datasource_id=str(assoc.datasource_id),
                target_table=assoc.target_table,
                is_enabled=assoc.is_enabled,
                datasource_name=ds.name if ds else None,
                datasource_type=ds.type if ds else None,
                datasource_status=ds.status if ds else None,
                created_at=assoc.created_at,
                updated_at=assoc.updated_at,
            )
            items.append(resp)
        return items

    async def add(self, spider_id: str, data: SpiderDataSourceCreate) -> SpiderDataSource:
        """添加爬虫-数据源关联"""
        assoc = SpiderDataSource(
            spider_id=spider_id,
            datasource_id=data.datasource_id,
            target_table=data.target_table,
            is_enabled=data.is_enabled,
        )
        self.db.add(assoc)
        await self.db.commit()
        await self.db.refresh(assoc)
        return assoc

    async def update(self, assoc_id: str, data: SpiderDataSourceUpdate) -> SpiderDataSource | None:
        """更新关联"""
        query = select(SpiderDataSource).where(SpiderDataSource.id == assoc_id)
        result = await self.db.execute(query)
        assoc = result.scalar_one_or_none()
        if not assoc:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(assoc, key, value)

        await self.db.commit()
        await self.db.refresh(assoc)
        return assoc

    async def remove(self, assoc_id: str) -> bool:
        """移除关联"""
        query = select(SpiderDataSource).where(SpiderDataSource.id == assoc_id)
        result = await self.db.execute(query)
        assoc = result.scalar_one_or_none()
        if not assoc:
            return False

        await self.db.delete(assoc)
        await self.db.commit()
        return True
