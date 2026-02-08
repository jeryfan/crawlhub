from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

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
):
    """查询爬取数据"""
    service = DataService()
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
):
    """导出为 JSON"""
    service = DataService()
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
):
    """导出为 CSV"""
    service = DataService()
    content = await service.export_csv(spider_id, task_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=data.csv"},
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
