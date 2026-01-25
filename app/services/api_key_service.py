import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select

from exceptions.common import RevokedApiKeyError
from libs.security import hash_text
from models.api_key import ApiKey, ApiKeyStatus, ApiUsageLog
from services.base_service import BaseService

# API Key前缀
API_KEY_PREFIX = "sk-"


def generate_api_key() -> tuple[str, str, str]:
    # 生成44字符的随机字符串
    random_part = secrets.token_urlsafe(32)
    full_key = f"{API_KEY_PREFIX}{random_part}"

    # 计算前缀（用于显示）
    key_prefix = full_key[:12]

    # 计算哈希（用于存储和验证）
    key_hash = hash_text(full_key)

    return full_key, key_prefix, key_hash


class ApiKeyService(BaseService):
    async def create_api_key(
        self,
        name: str,
        tenant_id: str | None,
        created_by: str,
        whitelist: list[str] | None = None,
        rpm: int | None = None,
        rph: int | None = None,
        balance: float | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[ApiKey, str]:
        full_key, key_prefix, key_hash = generate_api_key()

        api_key = ApiKey(
            name=name,
            tenant_id=tenant_id or None,
            created_by=created_by,
            key_prefix=key_prefix,
            key_hash=key_hash,
            whitelist=whitelist,
            status=ApiKeyStatus.ACTIVE,
            rpm=rpm,
            rph=rph,
            balance=balance,
            expires_at=expires_at,
        )

        self.db.add(api_key)
        await self.db.flush()

        return api_key, full_key

    async def get_api_key(self, key_id: str) -> ApiKey | None:
        result = await self.db.execute(select(ApiKey).where(ApiKey.id == key_id))
        return result.scalar_one_or_none()

    async def get_api_key_by_tenant(
        self,
        tenant_id: str,
        key_id: str,
    ) -> ApiKey | None:
        result = await self.db.execute(
            select(ApiKey).where(
                ApiKey.id == key_id,
                ApiKey.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_api_keys(
        self,
        tenant_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[ApiKey], int]:
        query = select(ApiKey)
        count_query = select(func.count(ApiKey.id))

        if tenant_id:
            query = query.where(ApiKey.tenant_id == tenant_id)
            count_query = count_query.where(ApiKey.tenant_id == tenant_id)

        if status:
            query = query.where(ApiKey.status == status)
            count_query = count_query.where(ApiKey.status == status)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                ApiKey.name.ilike(search_pattern) | ApiKey.key_prefix.ilike(search_pattern)
            )
            count_query = count_query.where(
                ApiKey.name.ilike(search_pattern) | ApiKey.key_prefix.ilike(search_pattern)
            )

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(ApiKey.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        api_keys = list(result.scalars().all())

        return api_keys, total

    async def update_api_key(
        self,
        key_id: str,
        name: str | None = None,
        whitelist: list[str] | None = None,
        rpm: int | None = None,
        rph: int | None = None,
        balance: float | None = None,
        expires_at: datetime | None = None,
        status: str | None = None,
    ) -> ApiKey | None:
        api_key = await self.get_api_key(key_id)
        if not api_key:
            return None

        if name is not None:
            api_key.name = name
        if whitelist is not None:
            api_key.whitelist = whitelist
        if rpm is not None:
            api_key.rpm = rpm if rpm > 0 else None
        if rph is not None:
            api_key.rph = rph if rph > 0 else None
        if balance is not None:
            api_key.balance = balance
        if expires_at is not None:
            api_key.expires_at = expires_at
        if status is not None:
            api_key.status = status

        await self.db.flush()
        return api_key

    async def regenerate_api_key(self, key_id: str) -> tuple[ApiKey, str] | None:
        api_key = await self.get_api_key(key_id)
        if not api_key:
            return None

        full_key, key_prefix, key_hash = generate_api_key()

        api_key.key_prefix = key_prefix
        api_key.key_hash = key_hash
        api_key.status = ApiKeyStatus.ACTIVE

        await self.db.flush()
        return api_key, full_key

    async def revoke_api_key(self, key_id: str) -> ApiKey | None:
        api_key = await self.get_api_key(key_id)
        if not api_key:
            return None

        api_key.status = ApiKeyStatus.REVOKED
        await self.db.flush()
        return api_key

    async def disable_api_key(self, key_id: str) -> ApiKey | None:
        api_key = await self.get_api_key(key_id)
        if not api_key:
            return None

        api_key.status = ApiKeyStatus.DISABLED
        await self.db.flush()
        return api_key

    async def enable_api_key(self, key_id: str) -> ApiKey | None:
        api_key = await self.get_api_key(key_id)
        if not api_key:
            return None

        if api_key.status == ApiKeyStatus.REVOKED:
            raise RevokedApiKeyError()

        api_key.status = ApiKeyStatus.ACTIVE
        await self.db.flush()
        return api_key

    async def delete_api_key(self, key_id: str) -> bool:
        result = await self.db.execute(delete(ApiKey).where(ApiKey.id == key_id))
        return result.rowcount > 0


class ApiUsageService(BaseService):
    async def log_usage(
        self,
        api_key_id: str,
        tenant_id: str | None,
        endpoint: str,
        method: str,
        service_type: str,
        status_code: int,
        ip_address: str,
        latency_ms: int = 0,
        error_message: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> ApiUsageLog:
        usage_log = ApiUsageLog(
            api_key_id=api_key_id,
            tenant_id=tenant_id or None,
            endpoint=endpoint,
            method=method,
            service_type=service_type,
            latency_ms=latency_ms,
            status_code=status_code,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        self.db.add(usage_log)
        await self.db.flush()

        return usage_log

    async def list_usage_logs(
        self,
        tenant_id: str | None = None,
        api_key_id: str | None = None,
        endpoint: str | None = None,
        service_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ApiUsageLog], int]:
        query = select(ApiUsageLog)
        count_query = select(func.count(ApiUsageLog.id))

        if tenant_id:
            query = query.where(ApiUsageLog.tenant_id == tenant_id)
            count_query = count_query.where(ApiUsageLog.tenant_id == tenant_id)

        if api_key_id:
            query = query.where(ApiUsageLog.api_key_id == api_key_id)
            count_query = count_query.where(ApiUsageLog.api_key_id == api_key_id)

        if endpoint:
            query = query.where(ApiUsageLog.endpoint == endpoint)
            count_query = count_query.where(ApiUsageLog.endpoint == endpoint)

        if service_type:
            query = query.where(ApiUsageLog.service_type == service_type)
            count_query = count_query.where(ApiUsageLog.service_type == service_type)

        if start_date:
            query = query.where(ApiUsageLog.created_at >= start_date)
            count_query = count_query.where(ApiUsageLog.created_at >= start_date)

        if end_date:
            query = query.where(ApiUsageLog.created_at <= end_date)
            count_query = count_query.where(ApiUsageLog.created_at <= end_date)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(ApiUsageLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    async def get_usage_stats(
        self,
        tenant_id: str | None = None,
        api_key_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        query = select(
            func.count(ApiUsageLog.id).label("total_requests"),
            func.avg(ApiUsageLog.latency_ms).label("avg_latency_ms"),
            func.count(func.nullif(ApiUsageLog.status_code >= 400, False)).label("total_errors"),
        )

        if tenant_id:
            query = query.where(ApiUsageLog.tenant_id == tenant_id)
        if api_key_id:
            query = query.where(ApiUsageLog.api_key_id == api_key_id)
        if start_date:
            query = query.where(ApiUsageLog.created_at >= start_date)
        if end_date:
            query = query.where(ApiUsageLog.created_at <= end_date)

        result = await self.db.execute(query)
        row = result.one()

        return {
            "total_requests": row.total_requests or 0,
            "avg_latency_ms": float(row.avg_latency_ms or 0),
            "total_errors": row.total_errors or 0,
        }

    async def get_usage_by_endpoint(
        self,
        tenant_id: str | None = None,
        api_key_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        query = select(
            ApiUsageLog.endpoint,
            func.count(ApiUsageLog.id).label("request_count"),
            func.avg(ApiUsageLog.latency_ms).label("avg_latency_ms"),
        ).group_by(ApiUsageLog.endpoint)

        if tenant_id:
            query = query.where(ApiUsageLog.tenant_id == tenant_id)
        if api_key_id:
            query = query.where(ApiUsageLog.api_key_id == api_key_id)
        if start_date:
            query = query.where(ApiUsageLog.created_at >= start_date)
        if end_date:
            query = query.where(ApiUsageLog.created_at <= end_date)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "endpoint": row.endpoint,
                "request_count": row.request_count,
                "avg_latency_ms": float(row.avg_latency_ms or 0),
            }
            for row in rows
        ]

    async def get_usage_trends(
        self,
        tenant_id: str | None = None,
        api_key_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        granularity: str = "day",
    ) -> list[dict[str, Any]]:
        if granularity == "hour":
            date_trunc = func.date_trunc("hour", ApiUsageLog.created_at)
        else:
            date_trunc = func.date_trunc("day", ApiUsageLog.created_at)

        query = (
            select(
                date_trunc.label("period"),
                func.count(ApiUsageLog.id).label("request_count"),
            )
            .group_by(date_trunc)
            .order_by(date_trunc)
        )

        if tenant_id:
            query = query.where(ApiUsageLog.tenant_id == tenant_id)
        if api_key_id:
            query = query.where(ApiUsageLog.api_key_id == api_key_id)
        if start_date:
            query = query.where(ApiUsageLog.created_at >= start_date)
        if end_date:
            query = query.where(ApiUsageLog.created_at <= end_date)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "period": row.period.isoformat() if row.period else None,
                "request_count": row.request_count,
            }
            for row in rows
        ]
