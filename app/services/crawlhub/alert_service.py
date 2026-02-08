import logging

from sqlalchemy import func, select, update

from models.crawlhub.alert import Alert, AlertLevel
from services.base_service import BaseService

logger = logging.getLogger(__name__)


class AlertService(BaseService):
    async def create_alert(
        self,
        type: str,
        level: AlertLevel,
        message: str,
        spider_id: str | None = None,
        task_id: str | None = None,
    ) -> Alert:
        """创建告警"""
        alert = Alert(
            type=type,
            level=level,
            message=message,
            spider_id=spider_id,
            task_id=task_id,
        )
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        level: AlertLevel | None = None,
        is_read: bool | None = None,
    ) -> tuple[list[Alert], int]:
        """获取告警列表"""
        query = select(Alert)

        if level:
            query = query.where(Alert.level == level)
        if is_read is not None:
            query = query.where(Alert.is_read == is_read)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(Alert.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        alerts = list(result.scalars().all())
        return alerts, total

    async def mark_as_read(self, alert_id: str) -> bool:
        """标记已读"""
        stmt = update(Alert).where(Alert.id == alert_id).values(is_read=True)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_as_read(self) -> int:
        """全部标记已读"""
        stmt = update(Alert).where(Alert.is_read == False).values(is_read=True)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def get_unread_count(self) -> int:
        """获取未读告警数"""
        query = select(func.count()).select_from(
            select(Alert).where(Alert.is_read == False).subquery()
        )
        return await self.db.scalar(query) or 0
