# Phase 2 & 3: 数据能力增强 + 体验提升 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 Phase 1 核心闭环基础上，增强数据推送能力（Webhook）、完善代理健康检查、补齐 Celery Worker 监控，让平台具备生产级可靠性。

**Architecture:** 在现有 FastAPI + Celery + PostgreSQL + MongoDB 架构上扩展。Webhook 通知挂载在 spider_tasks 完成后触发；代理健康检查作为独立 Celery Beat 任务；Worker 监控通过 Celery inspect API 实时查询，无需额外存储。

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), Celery 5.5+ (shared_task + inspect), httpx (Webhook HTTP calls), Motor (MongoDB)

---

## Task 1: Webhook 回调通知

**背景:** 爬取完成后需要通知下游系统。在 Spider 模型上添加 `webhook_url` 字段，任务完成/失败时自动 POST 通知。

**Files:**
- Modify: `app/models/crawlhub/spider.py` — 添加 webhook_url 字段
- Modify: `app/schemas/crawlhub/spider.py` — schema 同步
- Create: Alembic migration
- Create: `app/services/crawlhub/webhook_service.py` — Webhook 发送服务
- Modify: `app/tasks/spider_tasks.py` — 任务完成后触发 Webhook
- Modify: `app/services/crawlhub/__init__.py` — 导出 WebhookService

### Step 1: Spider 模型添加 webhook_url

在 `app/models/crawlhub/spider.py` 的 Spider 类末尾（`coder_workspace_name` 后）添加：

```python
webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="Webhook 回调 URL")
```

### Step 2: 更新 Spider schema

在 `app/schemas/crawlhub/spider.py`:

SpiderBase 添加：
```python
webhook_url: str | None = Field(None, max_length=500, description="Webhook 回调 URL")
```

SpiderUpdate 添加：
```python
webhook_url: str | None = None
```

### Step 3: 生成迁移

Run: `cd /Users/fanjunjie/Documents/repositories/personal/crawlhub/app && alembic revision --autogenerate -m "add spider webhook_url field"`

Run: `cd /Users/fanjunjie/Documents/repositories/personal/crawlhub/app && alembic upgrade head`

### Step 4: 创建 WebhookService

Create `app/services/crawlhub/webhook_service.py`:

```python
import json
import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = 10  # seconds


class WebhookService:
    """Webhook 回调通知服务"""

    @staticmethod
    async def send(
        url: str,
        event: str,
        payload: dict[str, Any],
    ) -> bool:
        """
        发送 Webhook 通知

        Args:
            url: Webhook 回调 URL
            event: 事件类型 (task_completed / task_failed)
            payload: 事件数据

        Returns:
            是否发送成功
        """
        body = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload,
        }

        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                response = await client.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code < 400:
                    logger.info(f"Webhook sent to {url}: {event} (status={response.status_code})")
                    return True
                else:
                    logger.warning(
                        f"Webhook failed for {url}: status={response.status_code}"
                    )
                    return False
        except httpx.TimeoutException:
            logger.warning(f"Webhook timeout for {url}")
            return False
        except Exception as e:
            logger.error(f"Webhook error for {url}: {e}")
            return False

    @staticmethod
    async def notify_task_result(
        webhook_url: str,
        spider_name: str,
        spider_id: str,
        task_id: str,
        status: str,
        total_count: int = 0,
        success_count: int = 0,
        error_message: str | None = None,
        duration: float = 0,
    ) -> bool:
        """任务结果通知的快捷方法"""
        event = "task_completed" if status == "completed" else "task_failed"
        payload = {
            "spider_id": spider_id,
            "spider_name": spider_name,
            "task_id": task_id,
            "status": status,
            "total_count": total_count,
            "success_count": success_count,
            "duration_seconds": duration,
        }
        if error_message:
            payload["error_message"] = error_message

        return await WebhookService.send(webhook_url, event, payload)
```

### Step 5: 集成到 spider_tasks.py

在 `app/tasks/spider_tasks.py` 的 `execute_spider` 中，任务执行完成后（无论成功失败），如果 spider 有 webhook_url，发送通知。

在 `await runner.run_spider_sync(spider, task)` 之后、retry_count 更新之后添加：

```python
# Webhook 通知
if spider.webhook_url:
    from services.crawlhub.webhook_service import WebhookService
    duration = (task.finished_at - task.started_at).total_seconds() if task.started_at and task.finished_at else 0
    await WebhookService.notify_task_result(
        webhook_url=spider.webhook_url,
        spider_name=spider.name,
        spider_id=spider_id,
        task_id=str(task.id),
        status=task.status.value,
        total_count=task.total_count,
        success_count=task.success_count,
        error_message=task.error_message,
        duration=duration,
    )
```

**注意:** Webhook 通知应在每次执行后都发（包括重试），这样下游可以追踪每次尝试。放在 retry 逻辑之前。

### Step 6: 更新 services __init__

在 `app/services/crawlhub/__init__.py` 添加：
```python
from .webhook_service import WebhookService
# __all__ 中添加 "WebhookService"
```

---

## Task 2: 代理健康检查

**背景:** `POST /proxies/{id}/check` 端点有 TODO，代理池 `report_result` 和 `reset_cooldown_proxies` 已实现但没有定时触发。需要：1) 实现真实的代理可用性检测；2) 定时 Beat 任务自动检查所有代理。

**Files:**
- Modify: `app/services/crawlhub/proxy_service.py` — 添加 `check_proxy` 方法
- Create: `app/tasks/proxy_tasks.py` — 代理健康检查 Celery 任务
- Modify: `app/extensions/ext_celery.py` — 注册 Beat schedule
- Modify: `app/routers/admin/crawlhub/proxies.py` — 实现 check 端点 + 添加 check-all 端点

### Step 1: ProxyService 添加健康检查方法

在 `app/services/crawlhub/proxy_service.py` 中添加：

```python
async def check_proxy(self, proxy: Proxy) -> bool:
    """检测代理可用性，返回是否可用"""
    import httpx

    test_url = "https://httpbin.org/ip"
    proxy_url = proxy.url

    try:
        async with httpx.AsyncClient(
            proxy=proxy_url,
            timeout=10,
        ) as client:
            response = await client.get(test_url)
            success = response.status_code == 200
    except Exception:
        success = False

    # 上报结果
    await self.report_result(proxy.id, success)

    return success
```

### Step 2: 创建代理检查 Celery 任务

Create `app/tasks/proxy_tasks.py`:

```python
import logging

from celery import shared_task
from sqlalchemy import select

from models.crawlhub import Proxy, ProxyStatus
from models.engine import AsyncSessionLocal
from services.crawlhub.proxy_service import ProxyService

logger = logging.getLogger(__name__)


@shared_task
async def check_all_proxies():
    """定时检查所有活跃代理的可用性"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Proxy).where(Proxy.status == ProxyStatus.ACTIVE)
        )
        proxies = list(result.scalars().all())

        service = ProxyService(session)
        checked = 0
        failed = 0

        for proxy in proxies:
            try:
                success = await service.check_proxy(proxy)
                checked += 1
                if not success:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to check proxy {proxy.host}:{proxy.port}: {e}")

        logger.info(f"Proxy health check: {checked} checked, {failed} failed")


@shared_task
async def reset_cooldown_proxies():
    """重置冷却中的代理"""
    async with AsyncSessionLocal() as session:
        service = ProxyService(session)
        count = await service.reset_cooldown_proxies()
        if count > 0:
            logger.info(f"Reset {count} cooldown proxies to active")
```

### Step 3: 注册 Beat schedule

在 `app/extensions/ext_celery.py` 中：

1. `imports` 列表添加 `"tasks.proxy_tasks"`
2. `beat_schedule` 字典添加：

```python
# 代理健康检查
"crawlhub.check_all_proxies": {
    "task": "tasks.proxy_tasks.check_all_proxies",
    "schedule": crontab(minute="*/5"),  # 每5分钟检查
},
"crawlhub.reset_cooldown_proxies": {
    "task": "tasks.proxy_tasks.reset_cooldown_proxies",
    "schedule": crontab(minute="*/1"),  # 每分钟重置冷却
},
```

### Step 4: 实现 check 端点 + 添加 check-all

在 `app/routers/admin/crawlhub/proxies.py` 中：

替换现有的 TODO check 端点：

```python
@router.post("/{proxy_id}/check", response_model=MessageResponse)
async def check_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
):
    """检测单个代理可用性"""
    service = ProxyService(db)
    proxy = await service.get_by_id(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="代理不存在")

    success = await service.check_proxy(proxy)
    if success:
        return MessageResponse(msg="代理可用")
    else:
        return MessageResponse(msg="代理不可用")


@router.post("/check-all", response_model=MessageResponse)
async def check_all_proxies():
    """检测所有代理可用性（异步）"""
    from tasks.proxy_tasks import check_all_proxies
    check_all_proxies.delay()
    return MessageResponse(msg="代理批量检测已提交")
```

**注意:** `check-all` 路由必须定义在 `/{proxy_id}` 路由之前，否则 FastAPI 会把 `check-all` 当做 proxy_id 参数。

---

## Task 3: Celery Worker 监控

**背景:** 多节点部署场景下需要查看 Worker 状态。通过 Celery inspect API 实时查询，不需要额外的数据库表。

**Files:**
- Create: `app/services/crawlhub/worker_service.py` — Worker 状态查询
- Create: `app/routers/admin/crawlhub/workers.py` — Worker API
- Modify: `app/routers/admin/crawlhub/__init__.py` — 注册 workers 路由
- Modify: `app/services/crawlhub/__init__.py` — 导出 WorkerService

### Step 1: 创建 WorkerService

Create `app/services/crawlhub/worker_service.py`:

```python
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
```

### Step 2: 创建 Workers API

Create `app/routers/admin/crawlhub/workers.py`:

```python
from fastapi import APIRouter, Request

from schemas.response import ApiResponse

router = APIRouter(prefix="/workers", tags=["CrawlHub - Workers"])


@router.get("")
async def list_workers(request: Request):
    """获取所有 Worker 状态"""
    from services.crawlhub.worker_service import WorkerService

    celery_app = request.app.state.celery
    service = WorkerService(celery_app)
    workers = service.get_workers()

    return ApiResponse(data={
        "workers": workers,
        "total": len(workers),
    })


@router.get("/active-tasks")
async def get_active_tasks(request: Request):
    """获取正在执行的任务"""
    from services.crawlhub.worker_service import WorkerService

    celery_app = request.app.state.celery
    service = WorkerService(celery_app)
    tasks = service.get_active_tasks()

    return ApiResponse(data={
        "tasks": tasks,
        "total": len(tasks),
    })


@router.get("/queued-tasks")
async def get_queued_tasks(request: Request):
    """获取排队中的任务"""
    from services.crawlhub.worker_service import WorkerService

    celery_app = request.app.state.celery
    service = WorkerService(celery_app)
    tasks = service.get_queued_tasks()

    return ApiResponse(data={
        "tasks": tasks,
        "total": len(tasks),
    })
```

### Step 3: 注册路由

在 `app/routers/admin/crawlhub/__init__.py` 添加：

```python
from .workers import router as workers_router
# ...
router.include_router(workers_router)
```

### Step 4: 更新 services __init__

在 `app/services/crawlhub/__init__.py` 添加：
```python
from .worker_service import WorkerService
# __all__ 中添加 "WorkerService"
```

---

## Task 4: Dashboard 统计 API

**背景:** 管理后台需要一个仪表盘概览页面的数据支撑。提供任务统计、爬虫活跃度、代理池状态等聚合数据。

**Files:**
- Create: `app/routers/admin/crawlhub/dashboard.py` — Dashboard API
- Modify: `app/routers/admin/crawlhub/__init__.py` — 注册 dashboard 路由

### Step 1: 创建 Dashboard API

Create `app/routers/admin/crawlhub/dashboard.py`:

```python
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub import (
    Proxy, ProxyStatus,
    Spider, SpiderTask, SpiderTaskStatus,
)
from models.crawlhub.alert import Alert
from models.engine import get_db
from schemas.response import ApiResponse

router = APIRouter(prefix="/dashboard", tags=["CrawlHub - Dashboard"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """获取仪表盘统计数据"""

    # 爬虫统计
    spider_total = await db.scalar(select(func.count()).select_from(Spider)) or 0
    spider_active = await db.scalar(
        select(func.count()).select_from(
            select(Spider).where(Spider.is_active == True).subquery()
        )
    ) or 0

    # 任务统计 (最近24小时)
    since = datetime.utcnow() - timedelta(hours=24)
    tasks_24h = await db.scalar(
        select(func.count()).select_from(
            select(SpiderTask).where(SpiderTask.created_at >= since).subquery()
        )
    ) or 0
    tasks_completed = await db.scalar(
        select(func.count()).select_from(
            select(SpiderTask).where(
                SpiderTask.created_at >= since,
                SpiderTask.status == SpiderTaskStatus.COMPLETED,
            ).subquery()
        )
    ) or 0
    tasks_failed = await db.scalar(
        select(func.count()).select_from(
            select(SpiderTask).where(
                SpiderTask.created_at >= since,
                SpiderTask.status == SpiderTaskStatus.FAILED,
            ).subquery()
        )
    ) or 0
    tasks_running = await db.scalar(
        select(func.count()).select_from(
            select(SpiderTask).where(
                SpiderTask.status == SpiderTaskStatus.RUNNING,
            ).subquery()
        )
    ) or 0

    # 代理统计
    proxy_total = await db.scalar(select(func.count()).select_from(Proxy)) or 0
    proxy_active = await db.scalar(
        select(func.count()).select_from(
            select(Proxy).where(Proxy.status == ProxyStatus.ACTIVE).subquery()
        )
    ) or 0
    proxy_inactive = await db.scalar(
        select(func.count()).select_from(
            select(Proxy).where(Proxy.status == ProxyStatus.INACTIVE).subquery()
        )
    ) or 0

    # 未读告警数
    unread_alerts = await db.scalar(
        select(func.count()).select_from(
            select(Alert).where(Alert.is_read == False).subquery()
        )
    ) or 0

    return ApiResponse(data={
        "spiders": {
            "total": spider_total,
            "active": spider_active,
        },
        "tasks_24h": {
            "total": tasks_24h,
            "completed": tasks_completed,
            "failed": tasks_failed,
            "running": tasks_running,
            "success_rate": round(tasks_completed / tasks_24h * 100, 1) if tasks_24h > 0 else 0,
        },
        "proxies": {
            "total": proxy_total,
            "active": proxy_active,
            "inactive": proxy_inactive,
        },
        "unread_alerts": unread_alerts,
    })


@router.get("/trends")
async def get_trends(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
):
    """获取最近 N 天的任务趋势"""
    trends = []
    for i in range(days - 1, -1, -1):
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        total = await db.scalar(
            select(func.count()).select_from(
                select(SpiderTask).where(
                    SpiderTask.created_at >= day_start,
                    SpiderTask.created_at < day_end,
                ).subquery()
            )
        ) or 0

        completed = await db.scalar(
            select(func.count()).select_from(
                select(SpiderTask).where(
                    SpiderTask.created_at >= day_start,
                    SpiderTask.created_at < day_end,
                    SpiderTask.status == SpiderTaskStatus.COMPLETED,
                ).subquery()
            )
        ) or 0

        failed = await db.scalar(
            select(func.count()).select_from(
                select(SpiderTask).where(
                    SpiderTask.created_at >= day_start,
                    SpiderTask.created_at < day_end,
                    SpiderTask.status == SpiderTaskStatus.FAILED,
                ).subquery()
            )
        ) or 0

        trends.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "total": total,
            "completed": completed,
            "failed": failed,
        })

    return ApiResponse(data=trends)
```

### Step 2: 注册路由

在 `app/routers/admin/crawlhub/__init__.py` 添加：

```python
from .dashboard import router as dashboard_router
# ...
router.include_router(dashboard_router)
```

---

## 依赖关系

4 个任务完全独立，可以任意顺序执行：
- Task 1 (Webhook) — 独立
- Task 2 (代理健康检查) — 独立
- Task 3 (Worker 监控) — 独立
- Task 4 (Dashboard) — 独立

**推荐执行顺序:** Task 2 → Task 1 → Task 3 → Task 4

Task 2 最关键（代理池不可靠直接影响采集），Task 4 最后做（纯查询聚合，最简单）。
