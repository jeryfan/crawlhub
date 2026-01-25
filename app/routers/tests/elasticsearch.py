from fastapi import APIRouter
from pydantic import BaseModel

from extensions.ext_es import es_client, ESError, IndexNotFoundError
from schemas.response import ApiResponse

router = APIRouter(prefix="/tests/es")


class CreateIndexRequest(BaseModel):
    name: str
    mappings: dict | None = None
    settings: dict | None = None


@router.post("/index")
async def create_index(request: CreateIndexRequest):
    """创建 ES 索引"""
    result = es_client.create_index(
        name=request.name,
        mappings=request.mappings,
        settings=request.settings,
        ignore_existing=True,
    )
    return ApiResponse(data={"created": result, "index": request.name})


@router.delete("/index/{name}")
async def delete_index(name: str):
    """删除 ES 索引"""
    result = es_client.delete_index(name=name, ignore_missing=True)
    return ApiResponse(data={"deleted": result, "index": name})


@router.get("/index/{name}")
async def get_index_info(name: str):
    """获取 ES 索引信息"""
    info = es_client.get_index_info(name=name)
    return ApiResponse(data=info)


@router.get("/index/{name}/exists")
async def check_index_exists(name: str):
    """检查 ES 索引是否存在"""
    exists = es_client.index_exists(name=name)
    return ApiResponse(data={"exists": exists, "index": name})
