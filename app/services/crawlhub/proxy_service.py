import random
from datetime import datetime

from sqlalchemy import func, select, update

from models.crawlhub import Proxy, ProxyStatus
from schemas.crawlhub import ProxyCreate, ProxyUpdate
from services.base_service import BaseService


class ProxyService(BaseService):
    async def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: ProxyStatus | None = None,
    ) -> tuple[list[Proxy], int]:
        """获取代理列表"""
        query = select(Proxy)

        if status:
            query = query.where(Proxy.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(Proxy.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        proxies = list(result.scalars().all())

        return proxies, total

    async def get_by_id(self, proxy_id: str) -> Proxy | None:
        """根据 ID 获取代理"""
        query = select(Proxy).where(Proxy.id == proxy_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: ProxyCreate) -> Proxy:
        """创建代理"""
        proxy = Proxy(**data.model_dump())
        self.db.add(proxy)
        await self.db.commit()
        await self.db.refresh(proxy)
        return proxy

    async def batch_create(self, proxies: list[ProxyCreate]) -> int:
        """批量创建代理"""
        proxy_objects = [Proxy(**p.model_dump()) for p in proxies]
        self.db.add_all(proxy_objects)
        await self.db.commit()
        return len(proxy_objects)

    async def update(self, proxy_id: str, data: ProxyUpdate) -> Proxy | None:
        """更新代理"""
        proxy = await self.get_by_id(proxy_id)
        if not proxy:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(proxy, key, value)

        await self.db.commit()
        await self.db.refresh(proxy)
        return proxy

    async def delete(self, proxy_id: str) -> bool:
        """删除代理"""
        proxy = await self.get_by_id(proxy_id)
        if not proxy:
            return False

        await self.db.delete(proxy)
        await self.db.commit()
        return True

    async def get_available_proxy(self, min_success_rate: float = 0.8) -> Proxy | None:
        """获取可用代理（加权随机）"""
        query = select(Proxy).where(
            Proxy.status == ProxyStatus.ACTIVE,
            Proxy.success_rate >= min_success_rate,
        )
        result = await self.db.execute(query)
        proxies = list(result.scalars().all())

        if not proxies:
            return None

        weights = [p.success_rate for p in proxies]
        selected = random.choices(proxies, weights=weights, k=1)[0]

        selected.status = ProxyStatus.COOLDOWN
        await self.db.commit()

        return selected

    async def report_result(self, proxy_id: str, success: bool) -> None:
        """上报代理使用结果"""
        proxy = await self.get_by_id(proxy_id)
        if not proxy:
            return

        if success:
            proxy.fail_count = 0
            proxy.success_rate = min(1.0, proxy.success_rate + 0.01)
            proxy.status = ProxyStatus.ACTIVE
        else:
            proxy.fail_count += 1
            proxy.success_rate = max(0.0, proxy.success_rate - 0.05)

            if proxy.fail_count >= 3:
                proxy.status = ProxyStatus.INACTIVE

        proxy.last_check_at = datetime.utcnow()
        await self.db.commit()

    async def reset_cooldown_proxies(self) -> int:
        """重置冷却中的代理为可用状态"""
        stmt = (
            update(Proxy)
            .where(Proxy.status == ProxyStatus.COOLDOWN)
            .values(status=ProxyStatus.ACTIVE)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount
