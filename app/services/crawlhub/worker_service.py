import logging
from typing import Any

from celery import Celery

logger = logging.getLogger(__name__)


class WorkerService:
    """Celery Worker 状态查询服务"""

    def __init__(self, celery_app: Celery):
        self.celery_app = celery_app

    def get_workers(self) -> list[dict[str, Any]]:
        """获取所有在线 Worker 状态"""
        inspect = self.celery_app.control.inspect()

        try:
            # 获取活跃信息（带超时）
            active = inspect.active() or {}
            stats = inspect.stats() or {}
            registered = inspect.registered() or {}
        except Exception as e:
            logger.error(f"Failed to inspect workers: {e}")
            return []

        workers = []
        for worker_name, worker_stats in stats.items():
            active_tasks = active.get(worker_name, [])
            registered_tasks = registered.get(worker_name, [])

            workers.append({
                "name": worker_name,
                "status": "online",
                "active_tasks": len(active_tasks),
                "active_task_details": [
                    {
                        "id": t.get("id"),
                        "name": t.get("name"),
                        "args": t.get("args"),
                        "started": t.get("time_start"),
                    }
                    for t in active_tasks
                ],
                "registered_tasks": len(registered_tasks),
                "total_completed": worker_stats.get("total", {}).get(
                    "tasks.spider_tasks.execute_spider", 0
                ),
                "pid": worker_stats.get("pid"),
                "concurrency": worker_stats.get("pool", {}).get("max-concurrency"),
                "uptime": worker_stats.get("clock"),
                "prefetch_count": worker_stats.get("prefetch_count"),
            })

        return workers

    def get_active_tasks(self) -> list[dict[str, Any]]:
        """获取所有正在执行的任务"""
        inspect = self.celery_app.control.inspect()
        try:
            active = inspect.active() or {}
        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
            return []

        tasks = []
        for worker_name, worker_tasks in active.items():
            for t in worker_tasks:
                tasks.append({
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "worker": worker_name,
                    "args": t.get("args"),
                    "kwargs": t.get("kwargs"),
                    "started": t.get("time_start"),
                })

        return tasks

    def get_queued_tasks(self) -> list[dict[str, Any]]:
        """获取排队中的任务"""
        inspect = self.celery_app.control.inspect()
        try:
            reserved = inspect.reserved() or {}
        except Exception as e:
            logger.error(f"Failed to get queued tasks: {e}")
            return []

        tasks = []
        for worker_name, worker_tasks in reserved.items():
            for t in worker_tasks:
                tasks.append({
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "worker": worker_name,
                    "args": t.get("args"),
                })

        return tasks
