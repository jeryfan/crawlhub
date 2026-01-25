import base64
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from core.file.helpers import get_signed_file_url
from dependencies.auth import get_current_admin
from libs.password import hash_password, valid_password
from models.admin import Admin, AdminStatus
from schemas.platform import (
    AdminCreate,
    AdminDetail,
    AdminListItem,
    AdminPasswordUpdate,
    AdminUpdate,
    PaginatedResponse,
)
from schemas.response import ApiResponse

router = APIRouter(tags=["Platform - Admins"])


@router.get("/admins", response_model=ApiResponse[PaginatedResponse[AdminListItem]])
async def list_admins(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取管理员列表"""
    query = select(Admin)

    # 关键词搜索
    if keyword:
        query = query.where(
            or_(
                Admin.name.ilike(f"%{keyword}%"),
                Admin.email.ilike(f"%{keyword}%"),
            )
        )

    # 状态筛选
    if status:
        query = query.where(Admin.status == status)

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # 分页
    query = query.order_by(Admin.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    admins = result.scalars().all()

    # 转换为列表项并生成 avatar_url
    items = []
    for adm in admins:
        item = AdminListItem.model_validate(adm)
        if adm.avatar:
            item.avatar_url = get_signed_file_url(adm.avatar)
        items.append(item)

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


@router.get("/admins/{admin_id}", response_model=ApiResponse[AdminDetail])
async def get_admin(
    admin_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取管理员详情"""
    admin = await db.get(Admin, admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    detail = AdminDetail.model_validate(admin)
    if admin.avatar:
        detail.avatar_url = get_signed_file_url(admin.avatar)

    return ApiResponse(data=detail)


@router.post("/admins", response_model=ApiResponse[AdminDetail])
async def create_admin(
    data: AdminCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """创建管理员"""
    # 检查邮箱是否已存在
    existing = await db.scalar(select(Admin).where(Admin.email == data.email).limit(1))
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已被使用")

    # 验证密码
    valid_password(data.password)

    # 生成密码盐和哈希
    salt = secrets.token_bytes(16)
    base64_salt = base64.b64encode(salt).decode()
    password_hashed = hash_password(data.password, salt)
    base64_password_hashed = base64.b64encode(password_hashed).decode()

    admin = Admin(
        name=data.name,
        email=data.email,
        password=base64_password_hashed,
        password_salt=base64_salt,
        status=AdminStatus.ACTIVE,
    )

    db.add(admin)
    await db.commit()
    await db.refresh(admin)

    detail = AdminDetail.model_validate(admin)
    if admin.avatar:
        detail.avatar_url = get_signed_file_url(admin.avatar)

    return ApiResponse(data=detail)


@router.put("/admins/{admin_id}", response_model=ApiResponse[AdminDetail])
async def update_admin(
    admin_id: str,
    data: AdminUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """更新管理员"""
    admin = await db.get(Admin, admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    # 如果更新邮箱，检查是否已存在
    if data.email and data.email != admin.email:
        existing = await db.scalar(select(Admin).where(Admin.email == data.email).limit(1))
        if existing:
            raise HTTPException(status_code=400, detail="邮箱已被使用")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(admin, field, value)

    await db.commit()
    await db.refresh(admin)

    detail = AdminDetail.model_validate(admin)
    if admin.avatar:
        detail.avatar_url = get_signed_file_url(admin.avatar)

    return ApiResponse(data=detail)


@router.patch("/admins/{admin_id}/password", response_model=ApiResponse[dict])
async def update_admin_password(
    admin_id: str,
    data: AdminPasswordUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """更新管理员密码"""
    admin = await db.get(Admin, admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    # 验证密码
    valid_password(data.password)

    # 生成新密码
    salt = secrets.token_bytes(16)
    base64_salt = base64.b64encode(salt).decode()
    password_hashed = hash_password(data.password, salt)
    base64_password_hashed = base64.b64encode(password_hashed).decode()

    admin.password = base64_password_hashed
    admin.password_salt = base64_salt

    await db.commit()

    return ApiResponse()


@router.patch("/admins/{admin_id}/status", response_model=ApiResponse[AdminDetail])
async def update_admin_status(
    admin_id: str,
    status: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """更新管理员状态"""
    if admin_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的状态")

    admin = await db.get(Admin, admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    if status not in [s.value for s in AdminStatus]:
        raise HTTPException(status_code=400, detail="无效的状态值")

    admin.status = status
    await db.commit()
    await db.refresh(admin)

    detail = AdminDetail.model_validate(admin)
    if admin.avatar:
        detail.avatar_url = get_signed_file_url(admin.avatar)

    return ApiResponse(data=detail)


@router.delete("/admins/{admin_id}", response_model=ApiResponse)
async def delete_admin(
    admin_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """删除管理员"""
    if admin_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    admin = await db.get(Admin, admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    await db.delete(admin)
    await db.commit()

    return ApiResponse()
