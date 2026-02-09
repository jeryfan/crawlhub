import logging

from sqlalchemy import func, select

from models.crawlhub import DataSource, DataSourceStatus, SpiderDataSource
from schemas.crawlhub.datasource import DataSourceCreate, DataSourceTestRequest, DataSourceUpdate
from services.base_service import BaseService

logger = logging.getLogger(__name__)


class DataSourceService(BaseService):
    async def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        type_filter: str | None = None,
        mode_filter: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[DataSource], int]:
        """获取数据源列表"""
        query = select(DataSource)

        if type_filter:
            query = query.where(DataSource.type == type_filter)
        if mode_filter:
            query = query.where(DataSource.mode == mode_filter)
        if keyword:
            query = query.where(DataSource.name.ilike(f"%{keyword}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(DataSource.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id(self, datasource_id: str) -> DataSource | None:
        """根据 ID 获取数据源"""
        query = select(DataSource).where(DataSource.id == datasource_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: DataSourceCreate) -> DataSource:
        """创建数据源"""
        exclude_fields = {"create_db_if_not_exists"}
        if data.mode != "managed":
            exclude_fields.add("docker_image")
        ds = DataSource(**data.model_dump(exclude=exclude_fields))
        if data.mode == "managed":
            ds.status = DataSourceStatus.CREATING
            if data.docker_image:
                ds.docker_image = data.docker_image
        self.db.add(ds)
        await self.db.commit()
        await self.db.refresh(ds)
        return ds

    async def update(self, datasource_id: str, data: DataSourceUpdate) -> DataSource | None:
        """更新数据源"""
        ds = await self.get_by_id(datasource_id)
        if not ds:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(ds, key, value)

        await self.db.commit()
        await self.db.refresh(ds)
        return ds

    async def delete(self, datasource_id: str) -> bool:
        """删除数据源（检查关联爬虫）"""
        ds = await self.get_by_id(datasource_id)
        if not ds:
            return False

        # 检查是否有关联的爬虫
        count_query = select(func.count()).where(
            SpiderDataSource.datasource_id == datasource_id
        )
        assoc_count = await self.db.scalar(count_query) or 0
        if assoc_count > 0:
            raise ValueError(f"该数据源仍有 {assoc_count} 个爬虫关联，请先移除关联")

        await self.db.delete(ds)
        await self.db.commit()
        return True

    async def test_connection(self, datasource_id: str) -> dict:
        """测试数据源连接"""
        ds = await self.get_by_id(datasource_id)
        if not ds:
            return {"ok": False, "message": "数据源不存在", "latency_ms": 0}

        from services.crawlhub.datasource_writer import get_writer

        try:
            writer = get_writer(ds)
            result = await writer.test_connection()
            # 更新状态
            ds.status = DataSourceStatus.ACTIVE if result["ok"] else DataSourceStatus.ERROR
            ds.last_error = None if result["ok"] else result.get("message")
            from datetime import datetime
            ds.last_check_at = datetime.utcnow()
            await self.db.commit()
            return result
        except Exception as e:
            ds.status = DataSourceStatus.ERROR
            ds.last_error = str(e)
            await self.db.commit()
            return {"ok": False, "message": str(e), "latency_ms": 0}

    @staticmethod
    async def test_connection_params(data: DataSourceTestRequest) -> dict:
        """用原始参数测试连接（不需要已存在的数据源）"""
        from services.crawlhub.datasource_writer import get_writer

        # 创建一个临时的类似 DataSource 的对象
        class _TempDS:
            pass

        temp = _TempDS()
        temp.type = data.type
        temp.host = data.host
        temp.port = data.port
        temp.username = data.username
        temp.password = data.password
        temp.database = data.database
        temp.connection_options = data.connection_options

        try:
            writer = get_writer(temp)
            return await writer.test_connection()
        except Exception as e:
            return {"ok": False, "message": str(e), "latency_ms": 0}
