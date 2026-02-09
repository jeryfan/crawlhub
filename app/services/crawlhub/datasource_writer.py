import abc
import logging
import time
from datetime import datetime

from models.crawlhub.datasource import DataSource, DataSourceType

logger = logging.getLogger(__name__)


class DataSourceWriter(abc.ABC):
    """数据源写入/读取器基类"""

    def __init__(self, datasource: DataSource):
        self.datasource = datasource

    @abc.abstractmethod
    async def write_items(
        self, items: list[dict], task_id: str, spider_id: str, target_table: str
    ) -> int:
        """写入数据项，返回写入条数"""

    @abc.abstractmethod
    async def read_items(
        self,
        target_table: str,
        spider_id: str | None = None,
        task_id: str | None = None,
        is_test: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """读取数据项，返回 (items, total)"""

    @abc.abstractmethod
    async def ensure_table(self, target_table: str) -> None:
        """确保目标表/集合存在"""

    @abc.abstractmethod
    async def test_connection(self) -> dict:
        """测试连接，返回 {ok, message, latency_ms}"""

    @abc.abstractmethod
    async def create_database(self) -> dict:
        """创建数据库（如果不存在）"""

    @abc.abstractmethod
    async def close(self) -> None:
        """关闭连接"""


class SQLWriter(DataSourceWriter):
    """PostgreSQL / MySQL 写入器"""

    def _get_connection_url(self) -> str:
        ds = self.datasource
        if ds.type == DataSourceType.POSTGRESQL:
            driver = "postgresql+asyncpg"
        else:
            driver = "mysql+aiomysql"
        auth = ""
        if ds.username:
            auth = ds.username
            if ds.password:
                auth += f":{ds.password}"
            auth += "@"
        host = ds.host or "localhost"
        port = ds.port or (5432 if ds.type == DataSourceType.POSTGRESQL else 3306)
        database = ds.database or ""
        return f"{driver}://{auth}{host}:{port}/{database}"

    async def _get_engine(self):
        from sqlalchemy.ext.asyncio import create_async_engine
        url = self._get_connection_url()
        engine = create_async_engine(url, pool_size=3, max_overflow=2, pool_timeout=10)
        return engine

    async def ensure_table(self, target_table: str) -> None:
        engine = await self._get_engine()
        try:
            if self.datasource.type == DataSourceType.POSTGRESQL:
                ddl = f"""
                CREATE TABLE IF NOT EXISTS {target_table} (
                    id BIGSERIAL PRIMARY KEY,
                    data JSONB NOT NULL,
                    task_id VARCHAR(36),
                    spider_id VARCHAR(36),
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_{target_table}_task_id ON {target_table}(task_id);
                CREATE INDEX IF NOT EXISTS idx_{target_table}_spider_id ON {target_table}(spider_id);
                """
            else:
                ddl = f"""
                CREATE TABLE IF NOT EXISTS {target_table} (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    data JSON NOT NULL,
                    task_id VARCHAR(36),
                    spider_id VARCHAR(36),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_{target_table}_task_id (task_id),
                    INDEX idx_{target_table}_spider_id (spider_id)
                );
                """
            async with engine.begin() as conn:
                from sqlalchemy import text
                for stmt in ddl.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await conn.execute(text(stmt))
        finally:
            await engine.dispose()

    async def write_items(
        self, items: list[dict], task_id: str, spider_id: str, target_table: str
    ) -> int:
        import json
        from sqlalchemy import text

        engine = await self._get_engine()
        try:
            await self.ensure_table(target_table)
            async with engine.begin() as conn:
                for item in items:
                    await conn.execute(
                        text(
                            f"INSERT INTO {target_table} (data, task_id, spider_id, created_at) "
                            f"VALUES (:data, :task_id, :spider_id, :created_at)"
                        ),
                        {
                            "data": json.dumps(item, ensure_ascii=False, default=str),
                            "task_id": task_id,
                            "spider_id": spider_id,
                            "created_at": datetime.utcnow(),
                        },
                    )
            return len(items)
        finally:
            await engine.dispose()

    async def read_items(
        self,
        target_table: str,
        spider_id: str | None = None,
        task_id: str | None = None,
        is_test: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        import json
        from sqlalchemy import text

        engine = await self._get_engine()
        try:
            conditions = []
            params: dict = {}
            if spider_id:
                conditions.append("spider_id = :spider_id")
                params["spider_id"] = spider_id
            if task_id:
                conditions.append("task_id = :task_id")
                params["task_id"] = task_id
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            async with engine.connect() as conn:
                # Count
                count_result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM {target_table} {where}"), params
                )
                total = count_result.scalar() or 0

                # Query
                offset = (page - 1) * page_size
                result = await conn.execute(
                    text(
                        f"SELECT id, data, task_id, spider_id, created_at "
                        f"FROM {target_table} {where} "
                        f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                    ),
                    {**params, "limit": page_size, "offset": offset},
                )
                items = []
                for row in result:
                    data = row[1]
                    if isinstance(data, str):
                        data = json.loads(data)
                    created_at = row[4]
                    items.append({
                        "_id": str(row[0]),
                        "data": data,
                        "task_id": row[2],
                        "spider_id": row[3],
                        "created_at": created_at.isoformat() if created_at else None,
                    })
            return items, total
        except Exception as e:
            logger.error(f"Failed to read from SQL datasource: {e}")
            return [], 0
        finally:
            await engine.dispose()

    async def test_connection(self) -> dict:
        from sqlalchemy import text

        start = time.monotonic()
        engine = await self._get_engine()
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            latency = int((time.monotonic() - start) * 1000)
            return {"ok": True, "message": "连接成功", "latency_ms": latency}
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            return {"ok": False, "message": str(e), "latency_ms": latency}
        finally:
            await engine.dispose()

    async def create_database(self) -> dict:
        """创建数据库（如果不存在）"""
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        ds = self.datasource
        db_name = ds.database
        if not db_name:
            return {"ok": False, "message": "未指定数据库名"}

        # 连接到默认库来执行 CREATE DATABASE
        if ds.type == DataSourceType.POSTGRESQL:
            driver = "postgresql+asyncpg"
            default_db = "postgres"
        else:
            driver = "mysql+aiomysql"
            default_db = ""

        auth = ""
        if ds.username:
            auth = ds.username
            if ds.password:
                auth += f":{ds.password}"
            auth += "@"
        host = ds.host or "localhost"
        port = ds.port or (5432 if ds.type == DataSourceType.POSTGRESQL else 3306)

        url = f"{driver}://{auth}{host}:{port}/{default_db}"
        engine = create_async_engine(url, pool_size=1, isolation_level="AUTOCOMMIT")
        try:
            async with engine.connect() as conn:
                if ds.type == DataSourceType.POSTGRESQL:
                    # Check if database exists
                    result = await conn.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = :name"),
                        {"name": db_name},
                    )
                    if not result.scalar():
                        # PostgreSQL requires AUTOCOMMIT for CREATE DATABASE
                        await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                        return {"ok": True, "message": f"数据库 {db_name} 创建成功"}
                    return {"ok": True, "message": f"数据库 {db_name} 已存在"}
                else:
                    # MySQL
                    await conn.execute(
                        text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    )
                    return {"ok": True, "message": f"数据库 {db_name} 创建成功"}
        except Exception as e:
            return {"ok": False, "message": f"创建数据库失败: {e}"}
        finally:
            await engine.dispose()

    async def close(self) -> None:
        pass


class MongoDBWriter(DataSourceWriter):
    """MongoDB 写入器"""

    def _get_client(self):
        from motor.motor_asyncio import AsyncIOMotorClient

        ds = self.datasource
        auth = ""
        if ds.username:
            auth = ds.username
            if ds.password:
                auth += f":{ds.password}"
            auth += "@"
        host = ds.host or "localhost"
        port = ds.port or 27017
        uri = f"mongodb://{auth}{host}:{port}"
        opts = ds.connection_options or {}
        return AsyncIOMotorClient(uri, **opts)

    async def ensure_table(self, target_table: str) -> None:
        pass  # MongoDB 无需预建集合

    async def write_items(
        self, items: list[dict], task_id: str, spider_id: str, target_table: str
    ) -> int:
        client = self._get_client()
        try:
            db = client[self.datasource.database or "crawlhub"]
            collection = db[target_table]
            docs = []
            for item in items:
                doc = {**item}
                doc["task_id"] = task_id
                doc["spider_id"] = spider_id
                doc["created_at"] = datetime.utcnow()
                docs.append(doc)
            if docs:
                await collection.insert_many(docs)
            return len(docs)
        finally:
            client.close()

    async def read_items(
        self,
        target_table: str,
        spider_id: str | None = None,
        task_id: str | None = None,
        is_test: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        client = self._get_client()
        try:
            db = client[self.datasource.database or "crawlhub"]
            collection = db[target_table]

            query_filter: dict = {}
            if spider_id:
                query_filter["spider_id"] = spider_id
            if task_id:
                query_filter["task_id"] = task_id

            total = await collection.count_documents(query_filter)
            cursor = (
                collection.find(query_filter)
                .sort("created_at", -1)
                .skip((page - 1) * page_size)
                .limit(page_size)
            )

            items = []
            async for doc in cursor:
                # 将 MongoDB 文档转换为统一格式
                item_data = {k: v for k, v in doc.items()
                             if k not in ("_id", "task_id", "spider_id", "created_at")}
                created_at = doc.get("created_at")
                items.append({
                    "_id": str(doc["_id"]),
                    "data": item_data,
                    "task_id": doc.get("task_id"),
                    "spider_id": doc.get("spider_id"),
                    "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
                })
            return items, total
        except Exception as e:
            logger.error(f"Failed to read from MongoDB datasource: {e}")
            return [], 0
        finally:
            client.close()

    async def test_connection(self) -> dict:
        start = time.monotonic()
        client = self._get_client()
        try:
            await client.admin.command("ping")
            latency = int((time.monotonic() - start) * 1000)
            return {"ok": True, "message": "连接成功", "latency_ms": latency}
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            return {"ok": False, "message": str(e), "latency_ms": latency}
        finally:
            client.close()

    async def create_database(self) -> dict:
        """MongoDB 数据库无需显式创建"""
        return {"ok": True, "message": "MongoDB 数据库会在写入时自动创建"}

    async def close(self) -> None:
        pass


def get_writer(datasource: DataSource) -> DataSourceWriter:
    """工厂函数：根据数据源类型返回对应写入器"""
    if datasource.type in (DataSourceType.POSTGRESQL, DataSourceType.MYSQL):
        return SQLWriter(datasource)
    elif datasource.type == DataSourceType.MONGODB:
        return MongoDBWriter(datasource)
    else:
        raise ValueError(f"不支持的数据源类型: {datasource.type}")
