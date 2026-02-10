import hashlib
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from extensions.ext_mongodb import mongodb_client
from models.crawlhub import Spider, SpiderTask, SpiderTaskStatus
from models.engine import get_db
from schemas.crawlhub.internal import (
    CheckpointSave,
    HeartbeatReport,
    ItemsIngestRequest,
    ProgressReport,
    ProxyRotateResponse,
)
from schemas.response import ApiResponse, MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["CrawlHub - Internal"])


async def _validate_task(
    task_id: str, spider_id: str, db: AsyncSession
) -> SpiderTask:
    """Validate task is RUNNING and belongs to the given spider."""
    result = await db.execute(
        select(SpiderTask).where(SpiderTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if str(task.spider_id) != spider_id:
        raise HTTPException(status_code=400, detail="spider_id 不匹配")
    if task.status != SpiderTaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail="任务不在运行状态")
    return task


@router.post("/items", response_model=MessageResponse)
async def ingest_items(
    data: ItemsIngestRequest,
    db: AsyncSession = Depends(get_db),
):
    """接收爬虫上报的数据项"""
    task = await _validate_task(data.task_id, data.spider_id, db)

    spider_result = await db.execute(
        select(Spider).where(Spider.id == data.spider_id)
    )
    spider = spider_result.scalar_one_or_none()

    items_to_insert = data.items

    # Schema validation
    if spider and spider.item_schema:
        try:
            schema = json.loads(spider.item_schema)
            required_fields = schema.get("required", [])
            properties = schema.get("properties", {})
            type_map = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict}

            validated_items = []
            for item in items_to_insert:
                valid = True
                # Check required fields
                for field in required_fields:
                    if field not in item or item[field] is None:
                        logger.warning(f"Item missing required field '{field}', skipping")
                        valid = False
                        break
                if not valid:
                    continue
                # Check types
                for field, field_schema in properties.items():
                    if field in item and item[field] is not None:
                        expected_type = type_map.get(field_schema.get("type"))
                        if expected_type and not isinstance(item[field], expected_type):
                            logger.warning(f"Item field '{field}' type mismatch, skipping")
                            valid = False
                            break
                if valid:
                    validated_items.append(item)

            items_to_insert = validated_items
            if not items_to_insert:
                return MessageResponse(msg="所有数据未通过 Schema 校验")
        except json.JSONDecodeError:
            logger.warning(f"Invalid item_schema for spider {data.spider_id}")

    # 检查是否配置了外部数据源
    has_datasources = await _has_active_datasources(db, data.spider_id)

    # 去重检查（仅在写入默认 MongoDB 时生效）
    if not has_datasources and spider and spider.dedup_enabled and spider.dedup_fields:
        if not mongodb_client.is_enabled():
            raise HTTPException(status_code=503, detail="MongoDB 未启用且未配置外部数据源")
        collection = mongodb_client.get_collection("spider_data")
        dedup_fields = [f.strip() for f in spider.dedup_fields.split(",") if f.strip()]
        if dedup_fields:
            filtered = []
            for item in data.items:
                hash_parts = {k: item.get(k) for k in sorted(dedup_fields)}
                dedup_hash = hashlib.md5(
                    json.dumps(hash_parts, sort_keys=True, default=str).encode()
                ).hexdigest()
                existing = await collection.find_one({
                    "spider_id": data.spider_id,
                    "dedup_hash": dedup_hash,
                })
                if not existing:
                    item["_dedup_hash"] = dedup_hash
                    filtered.append(item)
            items_to_insert = filtered

    if not items_to_insert:
        return MessageResponse(msg="所有数据已去重，无新数据")

    count = len(items_to_insert)

    if has_datasources:
        # 有外部数据源 → 只写外部数据源
        await _fanout_to_datasources(db, data.spider_id, data.task_id, items_to_insert)
    else:
        # 无外部数据源 → 写默认 MongoDB
        if not mongodb_client.is_enabled():
            raise HTTPException(status_code=503, detail="MongoDB 未启用且未配置外部数据源")

        collection = mongodb_client.get_collection("spider_data")
        docs = []
        for item in items_to_insert:
            dedup_hash = item.pop("_dedup_hash", None)
            doc = {
                "task_id": data.task_id,
                "spider_id": data.spider_id,
                "data": item,
                "is_test": task.is_test,
                "created_at": datetime.utcnow(),
            }
            if dedup_hash:
                doc["dedup_hash"] = dedup_hash
            docs.append(doc)
        await collection.insert_many(docs)

    # Atomic increment total_count
    await db.execute(
        text(
            "UPDATE crawlhub_tasks SET total_count = total_count + :n, "
            "success_count = success_count + :n WHERE id = :task_id"
        ),
        {"n": count, "task_id": data.task_id},
    )
    await db.commit()

    return MessageResponse(msg=f"已接收 {count} 条数据")


@router.post("/progress", response_model=MessageResponse)
async def report_progress(
    data: ProgressReport,
    db: AsyncSession = Depends(get_db),
):
    """接收进度上报"""
    result = await db.execute(
        select(SpiderTask).where(SpiderTask.id == data.task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != SpiderTaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail="任务不在运行状态")

    task.progress = data.progress
    await db.commit()

    return MessageResponse(msg="进度已更新")


@router.post("/heartbeat", response_model=MessageResponse)
async def report_heartbeat(
    data: HeartbeatReport,
    db: AsyncSession = Depends(get_db),
):
    """接收心跳上报"""
    result = await db.execute(
        select(SpiderTask).where(SpiderTask.id == data.task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != SpiderTaskStatus.RUNNING:
        return MessageResponse(msg="任务不在运行状态")

    task.last_heartbeat = datetime.utcnow()
    if data.memory_mb is not None:
        if task.peak_memory_mb is None or data.memory_mb > task.peak_memory_mb:
            task.peak_memory_mb = int(data.memory_mb)
    if data.items_count is not None:
        # Calculate items_per_second
        if task.started_at:
            elapsed = (datetime.utcnow() - task.started_at).total_seconds()
            if elapsed > 0:
                task.items_per_second = round(data.items_count / elapsed, 2)
    await db.commit()

    return MessageResponse(msg="心跳已更新")


@router.post("/checkpoint", response_model=MessageResponse)
async def save_checkpoint(
    data: CheckpointSave,
    db: AsyncSession = Depends(get_db),
):
    """保存断点数据"""
    result = await db.execute(
        select(SpiderTask).where(SpiderTask.id == data.task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    task.checkpoint_data = json.dumps(data.checkpoint_data, ensure_ascii=False)
    await db.commit()

    return MessageResponse(msg="断点已保存")


@router.get("/checkpoint", response_model=ApiResponse)
async def get_checkpoint(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取最近失败任务的断点数据"""
    result = await db.execute(
        select(SpiderTask)
        .where(
            SpiderTask.spider_id == spider_id,
            SpiderTask.status == SpiderTaskStatus.FAILED,
            SpiderTask.checkpoint_data.isnot(None),
        )
        .order_by(SpiderTask.created_at.desc())
        .limit(1)
    )
    task = result.scalar_one_or_none()

    if not task or not task.checkpoint_data:
        return ApiResponse(data=None)

    try:
        checkpoint = json.loads(task.checkpoint_data)
    except json.JSONDecodeError:
        return ApiResponse(data=None)

    return ApiResponse(data={"checkpoint_data": checkpoint, "task_id": str(task.id)})


@router.get("/task/status")
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取任务状态（供 SDK 心跳检查取消）"""
    result = await db.execute(
        select(SpiderTask).where(SpiderTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return ApiResponse(data={"status": task.status.value, "task_id": str(task.id)})


async def _has_active_datasources(db: AsyncSession, spider_id: str) -> bool:
    """检查爬虫是否配置了活跃的外部数据源"""
    from sqlalchemy import func

    from models.crawlhub import DataSource, DataSourceStatus, SpiderDataSource

    result = await db.execute(
        select(func.count())
        .select_from(SpiderDataSource)
        .join(DataSource, SpiderDataSource.datasource_id == DataSource.id)
        .where(
            SpiderDataSource.spider_id == spider_id,
            SpiderDataSource.is_enabled.is_(True),
            DataSource.status == DataSourceStatus.ACTIVE,
        )
    )
    return (result.scalar() or 0) > 0


async def _fanout_to_datasources(
    db: AsyncSession, spider_id: str, task_id: str, items: list[dict]
) -> None:
    """将数据扇出写入关联的外部数据源"""
    import asyncio

    from models.crawlhub import DataSource, DataSourceStatus, SpiderDataSource
    from services.crawlhub.datasource_writer import get_writer

    # 查询启用的关联数据源
    result = await db.execute(
        select(SpiderDataSource, DataSource)
        .join(DataSource, SpiderDataSource.datasource_id == DataSource.id)
        .where(
            SpiderDataSource.spider_id == spider_id,
            SpiderDataSource.is_enabled.is_(True),
            DataSource.status == DataSourceStatus.ACTIVE,
        )
    )
    rows = result.all()
    if not rows:
        return

    semaphore = asyncio.Semaphore(5)

    async def _write_to_ds(assoc: SpiderDataSource, datasource: DataSource):
        async with semaphore:
            try:
                writer = get_writer(datasource)
                await writer.write_items(items, task_id, spider_id, assoc.target_table)
            except Exception as e:
                logger.error(
                    f"Failed to write to datasource {datasource.name} "
                    f"(table={assoc.target_table}): {e}"
                )

    await asyncio.gather(*[_write_to_ds(assoc, ds) for assoc, ds in rows])


@router.get("/proxy/rotate", response_model=ApiResponse)
async def rotate_proxy(
    task_id: str,
    spider_id: str,
    failed_proxy: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """代理轮换 - SDK 请求新的可用代理"""
    # Validate task
    task = await _validate_task(task_id, spider_id, db)

    # Report failed proxy if provided
    if failed_proxy:
        from services.crawlhub.proxy_service import ProxyService
        proxy_service = ProxyService(db)
        # Find the proxy by URL pattern and report failure
        from sqlalchemy import select
        from models.crawlhub.proxy import Proxy
        # Simple search by host:port in the failed_proxy URL
        proxies_result = await db.execute(select(Proxy))
        for proxy in proxies_result.scalars().all():
            if proxy.url and proxy.url in failed_proxy:
                await proxy_service.report_result(str(proxy.id), success=False)
                break

    # Get new proxy
    from services.crawlhub.proxy_service import ProxyService
    proxy_service = ProxyService(db)
    proxy = await proxy_service.get_available_proxy(min_success_rate=0.5)

    if not proxy:
        return ApiResponse(data={"proxy_url": None, "message": "无可用代理"})

    # Build proxy URL
    auth = ""
    if proxy.username and proxy.password:
        auth = f"{proxy.username}:{proxy.password}@"
    proxy_url = f"{proxy.protocol}://{auth}{proxy.host}:{proxy.port}"

    return ApiResponse(data={"proxy_url": proxy_url, "message": "代理轮换成功"})


@router.post("/files/upload", response_model=MessageResponse)
async def upload_file(
    task_id: str = Form(...),
    spider_id: str = Form(...),
    filename: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """接收爬虫上传的文件"""
    await _validate_task(task_id, spider_id, db)

    from extensions.ext_storage import storage

    content = await file.read()
    storage_path = f"spider_files/{spider_id}/{task_id}/{filename}"
    await storage.save(storage_path, content)

    return MessageResponse(msg=f"文件已上传: {storage_path}")
