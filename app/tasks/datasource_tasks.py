import asyncio
import logging

from celery import shared_task
from sqlalchemy import select

from models.crawlhub.datasource import DataSource, DataSourceStatus
from models.engine import TaskSessionLocal, run_async

logger = logging.getLogger(__name__)


@shared_task
def check_datasource_health():
    """检查所有活跃数据源连接状态"""
    run_async(_check_datasource_health())


async def _check_datasource_health():
    from datetime import datetime

    from services.crawlhub.datasource_writer import get_writer

    async with TaskSessionLocal() as session:
        result = await session.execute(
            select(DataSource).where(
                DataSource.status.in_([DataSourceStatus.ACTIVE, DataSourceStatus.ERROR])
            )
        )
        datasources = list(result.scalars().all())

        if not datasources:
            return

        checked = 0
        failed = 0
        semaphore = asyncio.Semaphore(5)

        async def _check(ds: DataSource):
            nonlocal checked, failed
            async with semaphore:
                try:
                    writer = get_writer(ds)
                    result = await writer.test_connection()
                    ds.last_check_at = datetime.utcnow()
                    if result["ok"]:
                        ds.status = DataSourceStatus.ACTIVE
                        ds.last_error = None
                    else:
                        ds.status = DataSourceStatus.ERROR
                        ds.last_error = result.get("message")
                        failed += 1
                    checked += 1
                except Exception as e:
                    ds.status = DataSourceStatus.ERROR
                    ds.last_error = str(e)
                    ds.last_check_at = datetime.utcnow()
                    logger.error(f"Failed to check datasource {ds.name}: {e}")
                    failed += 1
                    checked += 1

        await asyncio.gather(*[_check(ds) for ds in datasources])
        await session.commit()

        logger.info(f"Datasource health check: {checked} checked, {failed} failed")
