import asyncio
import logging

from celery import shared_task
from sqlalchemy import select

from models.crawlhub import Proxy, ProxyStatus
from models.engine import TaskSessionLocal, run_async
from services.crawlhub.proxy_service import ProxyService

logger = logging.getLogger(__name__)


@shared_task
def check_all_proxies():
    """定时检查所有活跃代理的可用性"""
    run_async(_check_all_proxies())


async def _check_all_proxies():
    async with TaskSessionLocal() as session:
        result = await session.execute(
            select(Proxy).where(Proxy.status.in_([ProxyStatus.ACTIVE, ProxyStatus.COOLDOWN]))
        )
        proxies = list(result.scalars().all())

        if not proxies:
            return

        service = ProxyService(session)
        checked = 0
        failed = 0

        semaphore = asyncio.Semaphore(10)

        async def _check(proxy):
            nonlocal checked, failed
            async with semaphore:
                try:
                    success = await service.check_proxy(proxy)
                    checked += 1
                    if not success:
                        failed += 1
                except Exception as e:
                    logger.error(f"Failed to check proxy {proxy.host}:{proxy.port}: {e}")

        await asyncio.gather(*[_check(p) for p in proxies])
        await session.commit()

        logger.info(f"Proxy health check: {checked} checked, {failed} failed")


@shared_task
def reset_cooldown_proxies():
    """重置冷却中的代理"""
    run_async(_reset_cooldown_proxies())


async def _reset_cooldown_proxies():
    async with TaskSessionLocal() as session:
        service = ProxyService(session)
        count = await service.reset_cooldown_proxies()
        if count > 0:
            logger.info(f"Reset {count} cooldown proxies to active")
