import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub.data_service import DataService

router = APIRouter(prefix="/data", tags=["CrawlHub - Data"])


@router.get("")
async def list_data(
    spider_id: str | None = Query(None),
    task_id: str | None = Query(None),
    is_test: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """查询爬取数据"""
    service = DataService(db=db)
    items, total = await service.query(spider_id, task_id, is_test, page, page_size)
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    })


@router.get("/preview/{task_id}")
async def preview_data(
    task_id: str,
    limit: int = Query(20, ge=1, le=100),
):
    """数据预览（结构化摘要）"""
    service = DataService()
    result = await service.preview(task_id, limit)
    return ApiResponse(data=result)


@router.get("/export/json")
async def export_json(
    spider_id: str | None = Query(None),
    task_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """导出为 JSON"""
    service = DataService(db=db)
    content = await service.export_json(spider_id, task_id)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=data.json"},
    )


@router.get("/export/csv")
async def export_csv(
    spider_id: str | None = Query(None),
    task_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """导出为 CSV"""
    service = DataService(db=db)
    content = await service.export_csv(spider_id, task_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=data.csv"},
    )


@router.get("/export/json/stream")
async def export_json_stream(
    spider_id: str | None = Query(None),
    task_id: str | None = Query(None),
):
    """流式导出 JSON 数据"""
    from extensions.ext_mongodb import mongodb_client

    if not mongodb_client.is_enabled():
        raise HTTPException(status_code=503, detail="MongoDB 未启用")

    collection = mongodb_client.get_collection("spider_data")
    query_filter = {}
    if spider_id:
        query_filter["spider_id"] = spider_id
    if task_id:
        query_filter["task_id"] = task_id

    async def generate():
        yield "[\n"
        first = True
        async for doc in collection.find(query_filter, {"_id": 0}):
            # Convert datetime for JSON
            if "created_at" in doc and hasattr(doc["created_at"], "isoformat"):
                doc["created_at"] = doc["created_at"].isoformat()
            if not first:
                yield ",\n"
            yield json.dumps(doc, ensure_ascii=False, default=str)
            first = False
        yield "\n]"

    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=data_stream.json"},
    )


@router.get("/export/csv/stream")
async def export_csv_stream(
    spider_id: str | None = Query(None),
    task_id: str | None = Query(None),
):
    """流式导出 CSV 数据"""
    import csv
    import io

    from extensions.ext_mongodb import mongodb_client

    if not mongodb_client.is_enabled():
        raise HTTPException(status_code=503, detail="MongoDB 未启用")

    collection = mongodb_client.get_collection("spider_data")
    query_filter = {}
    if spider_id:
        query_filter["spider_id"] = spider_id
    if task_id:
        query_filter["task_id"] = task_id

    async def generate():
        # Get headers from first batch
        sample_docs = []
        async for doc in collection.find(query_filter, {"_id": 0}).limit(100):
            sample_docs.append(doc)

        if not sample_docs:
            yield ""
            return

        # Collect all field names from data dicts
        all_fields = set()
        for doc in sample_docs:
            if isinstance(doc.get("data"), dict):
                all_fields.update(doc["data"].keys())

        fieldnames = ["task_id", "spider_id", "created_at"] + sorted(all_fields)

        # Write header
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        yield output.getvalue()

        # Write sample docs first
        for doc in sample_docs:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            row = {
                "task_id": doc.get("task_id", ""),
                "spider_id": doc.get("spider_id", ""),
                "created_at": doc["created_at"].isoformat() if hasattr(doc.get("created_at"), "isoformat") else str(doc.get("created_at", "")),
            }
            if isinstance(doc.get("data"), dict):
                row.update(doc["data"])
            writer.writerow(row)
            yield output.getvalue()

        # Continue with remaining docs
        async for doc in collection.find(query_filter, {"_id": 0}).skip(100):
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            row = {
                "task_id": doc.get("task_id", ""),
                "spider_id": doc.get("spider_id", ""),
                "created_at": doc["created_at"].isoformat() if hasattr(doc.get("created_at"), "isoformat") else str(doc.get("created_at", "")),
            }
            if isinstance(doc.get("data"), dict):
                row.update(doc["data"])
            writer.writerow(row)
            yield output.getvalue()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=data_stream.csv"},
    )


@router.delete("", response_model=MessageResponse)
async def delete_data(
    spider_id: str | None = Query(None),
    task_id: str | None = Query(None),
):
    """删除数据"""
    if not spider_id and not task_id:
        raise HTTPException(status_code=400, detail="请指定 spider_id 或 task_id")

    service = DataService()
    if task_id:
        count = await service.delete_by_task(task_id)
    else:
        count = await service.delete_by_spider(spider_id)

    return MessageResponse(msg=f"已删除 {count} 条数据")
