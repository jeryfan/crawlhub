import json
import logging
from datetime import datetime, timedelta

from celery import shared_task

from models.engine import TaskSessionLocal, run_async

logger = logging.getLogger(__name__)


@shared_task
def archive_expiring_data():
    """Archive data older than 80 days"""
    run_async(_archive_expiring_data())


async def _archive_expiring_data():
    from extensions.ext_mongodb import mongodb_client
    from extensions.ext_storage import storage

    if not mongodb_client.is_enabled():
        return

    collection = mongodb_client.get_collection("spider_data")
    cutoff = datetime.utcnow() - timedelta(days=80)

    # Get distinct spider_ids with old data
    pipeline = [
        {"$match": {"created_at": {"$lt": cutoff}, "_archived": {"$ne": True}}},
        {"$group": {"_id": "$spider_id"}},
    ]
    spider_ids = [doc["_id"] async for doc in collection.aggregate(pipeline)]

    for spider_id in spider_ids:
        try:
            # Fetch old documents
            cursor = collection.find(
                {"spider_id": spider_id, "created_at": {"$lt": cutoff}, "_archived": {"$ne": True}},
                limit=10000,
            )

            lines = []
            doc_ids = []
            async for doc in cursor:
                doc_ids.append(doc["_id"])
                # Convert for JSON serialization
                doc.pop("_id")
                doc["created_at"] = doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", ""))
                lines.append(json.dumps(doc, ensure_ascii=False, default=str))

            if not lines:
                continue

            # Save as JSONL to storage
            date_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"archives/{spider_id}/{date_str}.jsonl"
            content = "\n".join(lines).encode("utf-8")
            await storage.save(filename, content)

            # Mark as archived
            await collection.update_many(
                {"_id": {"$in": doc_ids}},
                {"$set": {"_archived": True}},
            )

            logger.info(f"Archived {len(doc_ids)} docs for spider {spider_id} to {filename}")

        except Exception as e:
            logger.error(f"Failed to archive data for spider {spider_id}: {e}")
