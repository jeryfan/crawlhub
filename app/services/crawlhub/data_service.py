import csv
import io
import json
import logging
from datetime import datetime
from typing import Any

from extensions.ext_mongodb import mongodb_client

logger = logging.getLogger(__name__)

SPIDER_DATA_COLLECTION = "spider_data"
SPIDER_DATA_TTL_DAYS = 90


class DataService:
    """爬取数据查询和导出服务"""

    _indexes_created = False

    def __init__(self):
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = mongodb_client.get_collection(SPIDER_DATA_COLLECTION)
        return self._collection

    async def ensure_indexes(self) -> None:
        if DataService._indexes_created or not mongodb_client.is_enabled():
            return
        try:
            await mongodb_client.ensure_indexes(
                SPIDER_DATA_COLLECTION,
                [
                    {"keys": "task_id"},
                    {"keys": "spider_id"},
                    {"keys": [("created_at", -1)]},
                ],
            )
            await mongodb_client.create_ttl_index(
                SPIDER_DATA_COLLECTION,
                "created_at",
                expire_seconds=SPIDER_DATA_TTL_DAYS * 24 * 60 * 60,
            )
            DataService._indexes_created = True
        except Exception as e:
            logger.warning(f"Failed to create spider_data indexes: {e}")

    async def query(
        self,
        spider_id: str | None = None,
        task_id: str | None = None,
        is_test: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """分页查询爬取数据"""
        if not mongodb_client.is_enabled():
            return [], 0

        await self.ensure_indexes()

        query_filter: dict[str, Any] = {}
        if spider_id:
            query_filter["spider_id"] = spider_id
        if task_id:
            query_filter["task_id"] = task_id
        if is_test is not None:
            query_filter["is_test"] = is_test

        try:
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
                if "created_at" in doc and isinstance(doc["created_at"], datetime):
                    doc["created_at"] = doc["created_at"].isoformat()
                items.append(doc)

            return items, total
        except Exception as e:
            logger.error(f"Failed to query spider data: {e}")
            return [], 0

    async def export_json(
        self,
        spider_id: str | None = None,
        task_id: str | None = None,
    ) -> str:
        """导出为 JSON 字符串"""
        if not mongodb_client.is_enabled():
            return "[]"

        query_filter: dict[str, Any] = {}
        if spider_id:
            query_filter["spider_id"] = spider_id
        if task_id:
            query_filter["task_id"] = task_id

        try:
            cursor = self.collection.find(query_filter).sort("created_at", -1)
            items = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                if "created_at" in doc and isinstance(doc["created_at"], datetime):
                    doc["created_at"] = doc["created_at"].isoformat()
                items.append(doc.get("data", doc))

            return json.dumps(items, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            return "[]"

    async def export_csv(
        self,
        spider_id: str | None = None,
        task_id: str | None = None,
    ) -> str:
        """导出为 CSV 字符串"""
        if not mongodb_client.is_enabled():
            return ""

        query_filter: dict[str, Any] = {}
        if spider_id:
            query_filter["spider_id"] = spider_id
        if task_id:
            query_filter["task_id"] = task_id

        try:
            cursor = self.collection.find(query_filter).sort("created_at", -1)
            rows = []
            all_keys: set[str] = set()

            async for doc in cursor:
                data = doc.get("data", {})
                if isinstance(data, dict):
                    all_keys.update(data.keys())
                    rows.append(data)
                else:
                    rows.append({"value": data})
                    all_keys.add("value")

            if not rows:
                return ""

            output = io.StringIO()
            fieldnames = sorted(all_keys)
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

            return output.getvalue()
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            return ""

    async def preview(
        self,
        task_id: str,
        limit: int = 20,
    ) -> dict:
        """数据预览：返回结构化的数据摘要

        Returns:
            {
                "items": [...],
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

    async def delete_by_task(self, task_id: str) -> int:
        """删除指定任务的数据"""
        if not mongodb_client.is_enabled():
            return 0
        try:
            result = await self.collection.delete_many({"task_id": task_id})
            return result.deleted_count
        except Exception as e:
            logger.error(f"Failed to delete data for task {task_id}: {e}")
            return 0

    async def delete_by_spider(self, spider_id: str) -> int:
        """删除指定爬虫的所有数据"""
        if not mongodb_client.is_enabled():
            return 0
        try:
            result = await self.collection.delete_many({"spider_id": spider_id})
            return result.deleted_count
        except Exception as e:
            logger.error(f"Failed to delete data for spider {spider_id}: {e}")
            return 0
