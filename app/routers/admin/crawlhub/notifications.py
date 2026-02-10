import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub.notification_channel import (
    NotificationChannelConfig,
    NotificationChannelType,
)
from models.engine import get_db
from schemas.platform import PaginatedResponse
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["CrawlHub - Notifications"])


# ============ Pydantic Schemas ============

class NotificationChannelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="渠道名称")
    channel_type: NotificationChannelType = Field(..., description="渠道类型")
    config: str = Field(..., description="渠道配置 JSON 字符串")
    is_enabled: bool = Field(default=True, description="是否启用")


class NotificationChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    channel_type: NotificationChannelType | None = None
    config: str | None = None
    is_enabled: bool | None = None


class NotificationChannelResponse(BaseModel):
    id: str
    name: str
    channel_type: NotificationChannelType
    config: str
    is_enabled: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ============ Routes ============

@router.get("/channels")
async def list_channels(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取通知渠道列表"""
    query = select(NotificationChannelConfig)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    total_pages = (total + page_size - 1) // page_size

    query = query.order_by(NotificationChannelConfig.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    channels = list(result.scalars().all())

    return ApiResponse(data=PaginatedResponse(
        items=[
            NotificationChannelResponse(
                id=c.id,
                name=c.name,
                channel_type=c.channel_type,
                config=c.config,
                is_enabled=c.is_enabled,
                created_at=c.created_at.isoformat(),
                updated_at=c.updated_at.isoformat(),
            )
            for c in channels
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    ))


@router.post("/channels")
async def create_channel(
    body: NotificationChannelCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建通知渠道"""
    # Validate config is valid JSON
    try:
        json.loads(body.config)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="config 必须是有效的 JSON 字符串")

    channel = NotificationChannelConfig(
        name=body.name,
        channel_type=body.channel_type,
        config=body.config,
        is_enabled=body.is_enabled,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    return ApiResponse(data=NotificationChannelResponse(
        id=channel.id,
        name=channel.name,
        channel_type=channel.channel_type,
        config=channel.config,
        is_enabled=channel.is_enabled,
        created_at=channel.created_at.isoformat(),
        updated_at=channel.updated_at.isoformat(),
    ))


@router.put("/channels/{channel_id}")
async def update_channel(
    channel_id: str,
    body: NotificationChannelUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新通知渠道"""
    result = await db.execute(
        select(NotificationChannelConfig).where(NotificationChannelConfig.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="通知渠道不存在")

    if body.name is not None:
        channel.name = body.name
    if body.channel_type is not None:
        channel.channel_type = body.channel_type
    if body.config is not None:
        try:
            json.loads(body.config)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="config 必须是有效的 JSON 字符串")
        channel.config = body.config
    if body.is_enabled is not None:
        channel.is_enabled = body.is_enabled

    await db.commit()
    await db.refresh(channel)

    return ApiResponse(data=NotificationChannelResponse(
        id=channel.id,
        name=channel.name,
        channel_type=channel.channel_type,
        config=channel.config,
        is_enabled=channel.is_enabled,
        created_at=channel.created_at.isoformat(),
        updated_at=channel.updated_at.isoformat(),
    ))


@router.delete("/channels/{channel_id}", response_model=MessageResponse)
async def delete_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除通知渠道"""
    result = await db.execute(
        select(NotificationChannelConfig).where(NotificationChannelConfig.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="通知渠道不存在")

    await db.delete(channel)
    await db.commit()
    return MessageResponse(msg="通知渠道已删除")


@router.post("/channels/{channel_id}/test", response_model=MessageResponse)
async def test_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
):
    """测试通知渠道"""
    result = await db.execute(
        select(NotificationChannelConfig).where(NotificationChannelConfig.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="通知渠道不存在")

    service = NotificationService(db)
    success = await service.send(
        channel=channel,
        title="CrawlHub 测试通知",
        message="这是一条测试通知，如果您收到此消息，说明通知渠道配置正确。",
    )

    if success:
        return MessageResponse(msg="测试通知发送成功")
    else:
        raise HTTPException(status_code=500, detail="测试通知发送失败，请检查渠道配置")
