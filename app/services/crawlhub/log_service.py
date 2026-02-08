import logging
from datetime import datetime

from extensions.ext_mongodb import mongodb_client

logger = logging.getLogger(__name__)

SPIDER_LOGS_COLLECTION = "spider_logs"
SPIDER_LOG_TTL_DAYS = 90


class LogService:
    """爬虫任务日志服务"""

    _indexes_created = False

    def __init__(self):
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = mongodb_client.get_collection(SPIDER_LOGS_COLLECTION)
        return self._collection

    async def ensure_indexes(self) -> None:
        if LogService._indexes_created or not mongodb_client.is_enabled():
            return
        try:
            await mongodb_client.ensure_indexes(
                SPIDER_LOGS_COLLECTION,
                [
                    {"keys": "task_id"},
                    {"keys": "spider_id"},
                    {"keys": [("created_at", -1)]},
                ],
            )
            await mongodb_client.create_ttl_index(
                SPIDER_LOGS_COLLECTION,
                "created_at",
                expire_seconds=SPIDER_LOG_TTL_DAYS * 24 * 60 * 60,
            )
            LogService._indexes_created = True
        except Exception as e:
            logger.warning(f"Failed to create spider_logs indexes: {e}")

    async def store_log(
        self,
        task_id: str,
        spider_id: str,
        stdout: str,
        stderr: str,
    ) -> str | None:
        """存储任务日志"""
        if not mongodb_client.is_enabled():
            return None

        await self.ensure_indexes()

        try:
            result = await self.collection.insert_one({
                "task_id": task_id,
                "spider_id": spider_id,
                "stdout": stdout,
                "stderr": stderr,
                "created_at": datetime.utcnow(),
            })
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to store log: {e}")
            return None

    async def get_by_task(self, task_id: str) -> dict | None:
        """获取指定任务的日志"""
        if not mongodb_client.is_enabled():
            return None
        try:
            doc = await self.collection.find_one({"task_id": task_id})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            logger.error(f"Failed to get log for task {task_id}: {e}")
            return None

    async def get_list_by_spider(
        self,
        spider_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取指定爬虫的日志列表"""
        if not mongodb_client.is_enabled():
            return [], 0
        try:
            query_filter = {"spider_id": spider_id}
            total = await self.collection.count_documents(query_filter)

            cursor = (
                self.collection.find(query_filter)
                .sort("created_at", -1)
                .skip((page - 1) * page_size)
                .limit(page_size)
            )

            items = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                items.append(doc)

            return items, total
        except Exception as e:
            logger.error(f"Failed to get logs for spider {spider_id}: {e}")
            return [], 0
