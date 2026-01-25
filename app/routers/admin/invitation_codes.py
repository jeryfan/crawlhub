import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from dependencies.auth import get_current_admin
from libs.datetime_utils import naive_utc_now
from models.account import InvitationCode
from schemas.platform import (
    InvitationCodeCreate,
    InvitationCodeDeprecate,
    InvitationCodeListItem,
    PaginatedResponse,
)
from schemas.response import ApiResponse

router = APIRouter(tags=["Platform - Invitation Codes"])


def generate_invitation_code(length: int = 8) -> str:
    """生成邀请码"""
    return secrets.token_urlsafe(length)[:length].upper()


@router.get(
    "/invitation-codes",
    response_model=ApiResponse[PaginatedResponse[InvitationCodeListItem]],
)
async def list_invitation_codes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    batch: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取邀请码列表"""
    query = select(InvitationCode)

    # 关键词搜索
    if keyword:
        query = query.where(
            or_(
                InvitationCode.code.ilike(f"%{keyword}%"),
                InvitationCode.batch.ilike(f"%{keyword}%"),
            )
        )

    # 批次筛选
    if batch:
        query = query.where(InvitationCode.batch == batch)

    # 状态筛选
    if status:
        query = query.where(InvitationCode.status == status)

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # 分页
    query = query.order_by(InvitationCode.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    codes = result.scalars().all()

    items = [InvitationCodeListItem.model_validate(c) for c in codes]
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


# 注意：具体路径必须在参数化路径之前
@router.get("/invitation-codes/stats/summary", response_model=ApiResponse[dict])
async def get_invitation_codes_stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取邀请码统计信息"""
    # 总数
    total = await db.scalar(select(func.count()).select_from(InvitationCode))

    # 按状态统计
    status_stats = await db.execute(
        select(InvitationCode.status, func.count()).group_by(InvitationCode.status)
    )
    status_rows = status_stats.all()
    by_status = {row[0]: row[1] for row in status_rows}

    # 按批次统计
    batch_stats = await db.execute(
        select(InvitationCode.batch, func.count())
        .group_by(InvitationCode.batch)
        .order_by(func.count().desc())
        .limit(10)
    )
    batch_rows = batch_stats.all()
    by_batch = [{"batch": row[0], "count": row[1]} for row in batch_rows]

    return ApiResponse(
        data={
            "total": total or 0,
            "unused": by_status.get("unused", 0),
            "used": by_status.get("used", 0),
            "deprecated": by_status.get("deprecated", 0),
            "by_batch": by_batch,
        }
    )


@router.get("/invitation-codes/batches", response_model=ApiResponse[list[str]])
async def get_invitation_code_batches(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取所有批次列表"""
    result = await db.execute(
        select(InvitationCode.batch).distinct().order_by(InvitationCode.batch)
    )
    batches = [row[0] for row in result.all()]

    return ApiResponse(data=batches)


@router.post(
    "/invitation-codes/deprecate",
    response_model=ApiResponse,
)
async def deprecate_invitation_codes(
    data: InvitationCodeDeprecate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """批量作废邀请码"""
    codes = await db.execute(select(InvitationCode).where(InvitationCode.id.in_(data.ids)))
    codes = codes.scalars().all()

    if not codes:
        raise HTTPException(status_code=404, detail="邀请码不存在")

    deprecated_count = 0
    for code in codes:
        if code.status == "unused":
            code.status = "deprecated"
            code.deprecated_at = naive_utc_now()
            deprecated_count += 1

    await db.commit()

    return ApiResponse(data={"deprecated_count": deprecated_count})


# 参数化路径放在最后
@router.get(
    "/invitation-codes/{code_id}",
    response_model=ApiResponse[InvitationCodeListItem],
)
async def get_invitation_code(
    code_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取邀请码详情"""
    code = await db.get(InvitationCode, code_id)
    if not code:
        raise HTTPException(status_code=404, detail="邀请码不存在")

    return ApiResponse(data=InvitationCodeListItem.model_validate(code))


@router.post(
    "/invitation-codes",
    response_model=ApiResponse[list[InvitationCodeListItem]],
)
async def create_invitation_codes(
    data: InvitationCodeCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """批量创建邀请码"""
    codes = []
    for _ in range(data.count):
        code = InvitationCode(
            batch=data.batch,
            code=generate_invitation_code(),
            status="unused",
        )
        db.add(code)
        codes.append(code)

    await db.commit()

    # 刷新所有创建的邀请码
    for code in codes:
        await db.refresh(code)

    return ApiResponse(data=[InvitationCodeListItem.model_validate(c) for c in codes])


@router.delete("/invitation-codes/{code_id}", response_model=ApiResponse)
async def delete_invitation_code(
    code_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """删除邀请码"""
    code = await db.get(InvitationCode, code_id)
    if not code:
        raise HTTPException(status_code=404, detail="邀请码不存在")

    await db.delete(code)
    await db.commit()

    return ApiResponse()
