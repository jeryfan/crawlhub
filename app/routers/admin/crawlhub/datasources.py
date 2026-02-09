import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub import DataSourceMode, DataSourceStatus
from models.engine import get_db
from schemas.crawlhub.datasource import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceTestRequest,
    DataSourceUpdate,
    SpiderDataSourceCreate,
    SpiderDataSourceResponse,
    SpiderDataSourceUpdate,
)
from schemas.platform import PaginatedResponse
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub.datasource_service import DataSourceService
from services.crawlhub.spider_datasource_service import SpiderDataSourceService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["CrawlHub - DataSources"])


# ============ DataSource CRUD ============

@router.get("/datasources", response_model=ApiResponse[PaginatedResponse[DataSourceResponse]])
async def list_datasources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None),
    mode: str | None = Query(None),
    keyword: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取数据源列表"""
    service = DataSourceService(db)
    datasources, total = await service.get_list(page, page_size, type, mode, keyword)
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=[DataSourceResponse.model_validate(ds) for ds in datasources],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.post("/datasources", response_model=ApiResponse[DataSourceResponse])
async def create_datasource(
    data: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建数据源"""
    service = DataSourceService(db)
    ds = await service.create(data)

    # 如果需要自动创建数据库
    if data.create_db_if_not_exists and data.mode != DataSourceMode.MANAGED:
        try:
            from services.crawlhub.datasource_writer import get_writer
            writer = get_writer(ds)
            create_result = await writer.create_database()
            if not create_result["ok"]:
                logger.warning(f"Auto-create database failed for datasource {ds.id}: {create_result['message']}")
        except Exception as e:
            logger.error(f"Auto-create database error for datasource {ds.id}: {e}")

    # 如果是托管模式，自动创建 Docker 容器
    if data.mode == DataSourceMode.MANAGED:
        try:
            from services.crawlhub.docker_datasource_service import DockerDataSourceManager
            manager = DockerDataSourceManager()
            result = await manager.create_container(ds)
            ds.container_id = result["container_id"]
            ds.container_name = result["container_name"]
            ds.host = result["host"]
            ds.port = result["port"]
            ds.mapped_port = result["mapped_port"]
            ds.username = result["username"]
            ds.password = result["password"]
            ds.database = result["database"]
            ds.status = DataSourceStatus.ACTIVE
            await db.commit()
            await db.refresh(ds)
        except Exception as e:
            logger.error(f"Failed to create container for datasource {ds.id}: {e}")
            ds.status = DataSourceStatus.ERROR
            ds.last_error = str(e)
            await db.commit()
            await db.refresh(ds)

    return ApiResponse(data=DataSourceResponse.model_validate(ds))


@router.post("/datasources/test", response_model=ApiResponse)
async def test_datasource_params(
    data: DataSourceTestRequest,
):
    """用连接参数测试数据源连接（无需先创建）"""
    result = await DataSourceService.test_connection_params(data)
    return ApiResponse(data=result)


@router.get("/datasources/{datasource_id}", response_model=ApiResponse[DataSourceResponse])
async def get_datasource(
    datasource_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取数据源详情"""
    service = DataSourceService(db)
    ds = await service.get_by_id(datasource_id)
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return ApiResponse(data=DataSourceResponse.model_validate(ds))


@router.put("/datasources/{datasource_id}", response_model=ApiResponse[DataSourceResponse])
async def update_datasource(
    datasource_id: str,
    data: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新数据源"""
    service = DataSourceService(db)
    ds = await service.update(datasource_id, data)
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return ApiResponse(data=DataSourceResponse.model_validate(ds))


@router.delete("/datasources/{datasource_id}", response_model=MessageResponse)
async def delete_datasource(
    datasource_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除数据源"""
    service = DataSourceService(db)
    ds = await service.get_by_id(datasource_id)
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    # 如果是托管模式，删除 Docker 容器
    if ds.mode == DataSourceMode.MANAGED and ds.container_id:
        try:
            from services.crawlhub.docker_datasource_service import DockerDataSourceManager
            manager = DockerDataSourceManager()
            await manager.remove_container(ds.container_id, remove_volume=True)
        except Exception as e:
            logger.warning(f"Failed to remove container for datasource {datasource_id}: {e}")

    try:
        success = await service.delete(datasource_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not success:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return MessageResponse(msg="数据源删除成功")


@router.post("/datasources/{datasource_id}/test", response_model=ApiResponse)
async def test_datasource_connection(
    datasource_id: str,
    db: AsyncSession = Depends(get_db),
):
    """测试数据源连接"""
    service = DataSourceService(db)
    result = await service.test_connection(datasource_id)
    return ApiResponse(data=result)


@router.post("/datasources/{datasource_id}/start", response_model=MessageResponse)
async def start_datasource_container(
    datasource_id: str,
    db: AsyncSession = Depends(get_db),
):
    """启动托管数据源容器"""
    service = DataSourceService(db)
    ds = await service.get_by_id(datasource_id)
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    if ds.mode != DataSourceMode.MANAGED:
        raise HTTPException(status_code=400, detail="仅托管数据源可启动容器")
    if not ds.container_id:
        raise HTTPException(status_code=400, detail="容器尚未创建")

    from services.crawlhub.docker_datasource_service import DockerDataSourceManager
    manager = DockerDataSourceManager()
    await manager.start_container(ds.container_id)
    ds.status = DataSourceStatus.ACTIVE
    await db.commit()
    return MessageResponse(msg="容器已启动")


@router.post("/datasources/{datasource_id}/stop", response_model=MessageResponse)
async def stop_datasource_container(
    datasource_id: str,
    db: AsyncSession = Depends(get_db),
):
    """停止托管数据源容器"""
    service = DataSourceService(db)
    ds = await service.get_by_id(datasource_id)
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    if ds.mode != DataSourceMode.MANAGED:
        raise HTTPException(status_code=400, detail="仅托管数据源可停止容器")
    if not ds.container_id:
        raise HTTPException(status_code=400, detail="容器尚未创建")

    from services.crawlhub.docker_datasource_service import DockerDataSourceManager
    manager = DockerDataSourceManager()
    await manager.stop_container(ds.container_id)
    ds.status = DataSourceStatus.INACTIVE
    await db.commit()
    return MessageResponse(msg="容器已停止")


# ============ Spider-DataSource Associations ============

@router.get(
    "/spiders/{spider_id}/datasources",
    response_model=ApiResponse[list[SpiderDataSourceResponse]],
)
async def list_spider_datasources(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取爬虫关联的数据源"""
    service = SpiderDataSourceService(db)
    items = await service.get_by_spider(spider_id)
    return ApiResponse(data=items)


@router.post(
    "/spiders/{spider_id}/datasources",
    response_model=ApiResponse[SpiderDataSourceResponse],
)
async def add_spider_datasource(
    spider_id: str,
    data: SpiderDataSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """添加爬虫-数据源关联"""
    service = SpiderDataSourceService(db)
    assoc = await service.add(spider_id, data)

    # 重新查询以获取 datasource 信息
    items = await service.get_by_spider(spider_id)
    for item in items:
        if item.id == str(assoc.id):
            return ApiResponse(data=item)

    return ApiResponse(data=SpiderDataSourceResponse.model_validate(assoc))


@router.put(
    "/spiders/{spider_id}/datasources/{assoc_id}",
    response_model=ApiResponse[SpiderDataSourceResponse],
)
async def update_spider_datasource(
    spider_id: str,
    assoc_id: str,
    data: SpiderDataSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新爬虫-数据源关联"""
    service = SpiderDataSourceService(db)
    assoc = await service.update(assoc_id, data)
    if not assoc:
        raise HTTPException(status_code=404, detail="关联不存在")

    # 重新查询以获取 datasource 信息
    items = await service.get_by_spider(spider_id)
    for item in items:
        if item.id == str(assoc.id):
            return ApiResponse(data=item)

    return ApiResponse(data=SpiderDataSourceResponse.model_validate(assoc))


@router.delete(
    "/spiders/{spider_id}/datasources/{assoc_id}",
    response_model=MessageResponse,
)
async def remove_spider_datasource(
    spider_id: str,
    assoc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """移除爬虫-数据源关联"""
    service = SpiderDataSourceService(db)
    success = await service.remove(assoc_id)
    if not success:
        raise HTTPException(status_code=404, detail="关联不存在")
    return MessageResponse(msg="关联已移除")
