# Phase 1: 核心闭环 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 补齐 CrawlHub 核心闭环 — 定时调度、数据导出、任务失败重试/告警、日志持久化，让平台从"能跑"变成"能用"。

**Architecture:** 4 个独立功能模块，共享现有 FastAPI + Celery + PostgreSQL + MongoDB 基础设施。每个模块遵循 Model → Service → Router 分层，Celery task 走 `app/tasks/` 目录，数据存 MongoDB `spider_data` / `spider_logs` 集合。

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), Celery 5.5+ (shared_task), Motor (MongoDB async), Pydantic 2.12+

---

## Task 1: Celery 定时调度接入

**背景:** Spider 模型已有 `cron_expr` 字段，Celery Beat 配置已就绪（`app/extensions/ext_celery.py`），但没有 Celery task 真正消费 Spider 的 cron 配置来触发执行。当前执行只有手动 test-run（`POST /spiders/{id}/test-run`）。

**Files:**
- Create: `app/tasks/spider_tasks.py` — Celery task：定时扫描 + 执行爬虫
- Modify: `app/extensions/ext_celery.py:97-128` — 注册新 task 和 beat schedule
- Modify: `app/services/crawlhub/spider_runner_service.py` — 新增 `create_task` (非 test) 和 `run_spider` (同步 Celery 可调用)
- Modify: `app/models/crawlhub/task.py` — 添加 `retry_count`、`max_retries`、`trigger_type` 字段
- Create: `app/alembic/versions/xxxx_add_task_retry_and_trigger_fields.py` — 数据库迁移

### Step 1: 添加 Task 模型字段

在 `app/models/crawlhub/task.py` 的 SpiderTask 中添加：

```python
# 在 is_test 字段后添加
trigger_type: Mapped[str] = mapped_column(String(20), default="manual", comment="触发类型: manual/schedule")
retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="已重试次数")
max_retries: Mapped[int] = mapped_column(Integer, default=3, comment="最大重试次数")
```

需要 `from sqlalchemy import ..., String` (String 已在 task.py 中导入)。

### Step 2: 生成数据库迁移

Run: `cd /Users/fanjunjie/Documents/repositories/personal/crawlhub/app && alembic revision --autogenerate -m "add task retry and trigger fields"`

Run: `cd /Users/fanjunjie/Documents/repositories/personal/crawlhub/app && alembic upgrade head`

### Step 3: 更新 TaskResponse schema

在 `app/schemas/crawlhub/task.py` 的 `TaskResponse` 中添加：

```python
trigger_type: str = "manual"
retry_count: int = 0
max_retries: int = 3
```

### Step 4: SpiderRunnerService 新增同步执行方法

在 `app/services/crawlhub/spider_runner_service.py` 中添加：

```python
async def create_scheduled_task(self, spider: Spider) -> SpiderTask:
    """创建定时调度任务"""
    task = SpiderTask(
        spider_id=spider.id,
        status=SpiderTaskStatus.PENDING,
        is_test=False,
        trigger_type="schedule",
    )
    self.db.add(task)
    await self.db.commit()
    await self.db.refresh(task)
    return task

async def run_spider_sync(self, spider: Spider, task: SpiderTask) -> None:
    """同步执行爬虫（用于 Celery worker 调用，不走 SSE）"""
    task.status = SpiderTaskStatus.RUNNING
    task.started_at = datetime.utcnow()
    await self.db.commit()

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            await self.prepare_project_files(spider, work_dir)

            if spider.source == ProjectSource.SCRAPY:
                cmd = ["scrapy", "crawl", spider.name]
            else:
                cmd = ["python", "-c", f"""
import sys
sys.path.insert(0, '{work_dir}')
from main import run
result = run({{}})
print(result)
"""]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(work_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=300
                )
            except asyncio.TimeoutError:
                process.kill()
                task.status = SpiderTaskStatus.FAILED
                task.error_message = "执行超时 (最大 5 分钟)"
                return

            if process.returncode == 0:
                task.status = SpiderTaskStatus.COMPLETED
                # 存储日志到 MongoDB
                await self._store_task_log(task, stdout, stderr)
            else:
                task.status = SpiderTaskStatus.FAILED
                task.error_message = f"进程退出码: {process.returncode}"
                if stderr:
                    task.error_message += f"\n{stderr.decode('utf-8', errors='replace')[:2000]}"

    except Exception as e:
        task.status = SpiderTaskStatus.FAILED
        task.error_message = str(e)
    finally:
        task.finished_at = datetime.utcnow()
        await self.db.commit()

async def _store_task_log(self, task: SpiderTask, stdout: bytes, stderr: bytes) -> None:
    """存储任务日志到 MongoDB"""
    from extensions.ext_mongodb import mongodb_client

    if not mongodb_client.is_enabled():
        return

    collection = mongodb_client.get_collection("spider_logs")
    await collection.insert_one({
        "task_id": task.id,
        "spider_id": task.spider_id,
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
        "created_at": datetime.utcnow(),
    })
```

### Step 5: 创建 Celery 爬虫任务

Create `app/tasks/spider_tasks.py`:

```python
import asyncio
import logging

from celery import shared_task
from sqlalchemy import select

from models.crawlhub import Spider, SpiderTask, SpiderTaskStatus
from models.engine import AsyncSessionLocal
from services.crawlhub.spider_runner_service import SpiderRunnerService

logger = logging.getLogger(__name__)


@shared_task
async def run_scheduled_spiders():
    """定时扫描并执行启用了 cron 的爬虫"""
    async with AsyncSessionLocal() as session:
        # 查询所有启用且有 cron 表达式的爬虫
        result = await session.execute(
            select(Spider).where(
                Spider.is_active == True,
                Spider.cron_expr.isnot(None),
                Spider.cron_expr != "",
            )
        )
        spiders = list(result.scalars().all())

        for spider in spiders:
            try:
                execute_spider.delay(str(spider.id))
            except Exception as e:
                logger.error(f"Failed to dispatch spider {spider.id}: {e}")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
async def execute_spider(self, spider_id: str):
    """执行单个爬虫任务"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Spider).where(Spider.id == spider_id)
        )
        spider = result.scalar_one_or_none()
        if not spider:
            logger.error(f"Spider {spider_id} not found")
            return

        runner = SpiderRunnerService(session)
        task = await runner.create_scheduled_task(spider)

        await runner.run_spider_sync(spider, task)

        # 失败时重试
        if task.status == SpiderTaskStatus.FAILED:
            task.retry_count = self.request.retries
            await session.commit()

            if self.request.retries < 3:
                raise self.retry(exc=Exception(task.error_message))
```

### Step 6: 注册 Celery Beat Schedule

在 `app/extensions/ext_celery.py` 中：

1. `imports` 列表添加 `"tasks.spider_tasks"`
2. `beat_schedule` 字典添加：

```python
"crawlhub.run_scheduled_spiders": {
    "task": "tasks.spider_tasks.run_scheduled_spiders",
    "schedule": crontab(minute="*"),  # 每分钟检查一次
},
```

**注意:** 每分钟扫描一次，但具体哪些爬虫该运行需要匹配 cron_expr。当前实现简化为：每次扫描都 dispatch 所有有 cron 的爬虫。后续优化应引入 croniter 库对比 `cron_expr` 和当前时间来精确调度。

### Step 7: 添加手动触发执行 API

在 `app/routers/admin/crawlhub/spiders.py` 中添加手动执行端点（区别于 test-run）：

```python
@router.post("/{spider_id}/run", response_model=ApiResponse[TaskResponse])
async def run_spider(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """手动触发爬虫执行（非测试，走 Celery 队列）"""
    from tasks.spider_tasks import execute_spider

    service = SpiderService(db)
    spider = await service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    execute_spider.delay(spider_id)
    return ApiResponse(data={"message": "任务已提交"})
```

需要导入 `TaskResponse` 到路由文件头部。

### Step 8: 引入 croniter 精确调度

安装依赖: `uv add croniter`

修改 `tasks/spider_tasks.py` 的 `run_scheduled_spiders`:

```python
from croniter import croniter
from datetime import datetime, timedelta

@shared_task
async def run_scheduled_spiders():
    """定时扫描并执行启用了 cron 的爬虫"""
    now = datetime.utcnow()
    one_minute_ago = now - timedelta(minutes=1)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Spider).where(
                Spider.is_active == True,
                Spider.cron_expr.isnot(None),
                Spider.cron_expr != "",
            )
        )
        spiders = list(result.scalars().all())

        for spider in spiders:
            try:
                cron = croniter(spider.cron_expr, one_minute_ago)
                next_run = cron.get_next(datetime)
                # 如果下次执行时间在当前分钟内，则触发
                if next_run <= now:
                    execute_spider.delay(str(spider.id))
            except Exception as e:
                logger.error(f"Failed to process spider {spider.id} cron '{spider.cron_expr}': {e}")
```

---

## Task 2: 数据导出（CSV/JSON）

**背景:** 爬取数据存储在 MongoDB 的 `spider_data` 集合中，但目前没有任何接口可以查询或导出这些数据。需要新增数据查询和导出 API。

**Files:**
- Create: `app/services/crawlhub/data_service.py` — 数据查询和导出服务
- Create: `app/routers/admin/crawlhub/data.py` — 数据 API 路由
- Modify: `app/routers/admin/crawlhub/__init__.py` — 注册 data 路由
- Modify: `app/services/crawlhub/spider_runner_service.py` — 执行结果写入 MongoDB spider_data

### Step 1: 确保执行结果写入 MongoDB

在 `app/services/crawlhub/spider_runner_service.py` 的 `run_spider_sync` 中，`process.returncode == 0` 分支添加数据存储：

```python
if process.returncode == 0:
    task.status = SpiderTaskStatus.COMPLETED
    await self._store_task_log(task, stdout, stderr)
    # 尝试解析 stdout 作为爬取数据
    await self._store_spider_data(task, stdout)
```

新增方法：

```python
async def _store_spider_data(self, task: SpiderTask, stdout: bytes) -> None:
    """将爬取结果存入 MongoDB spider_data"""
    import json
    from extensions.ext_mongodb import mongodb_client

    if not mongodb_client.is_enabled():
        return

    try:
        output = stdout.decode("utf-8", errors="replace").strip()
        if not output:
            return

        data = json.loads(output)
        collection = mongodb_client.get_collection("spider_data")

        if isinstance(data, list):
            docs = [{
                "task_id": task.id,
                "spider_id": task.spider_id,
                "data": item,
                "created_at": datetime.utcnow(),
            } for item in data]
            if docs:
                await collection.insert_many(docs)
                task.total_count = len(docs)
                task.success_count = len(docs)
        elif isinstance(data, dict):
            await collection.insert_one({
                "task_id": task.id,
                "spider_id": task.spider_id,
                "data": data,
                "created_at": datetime.utcnow(),
            })
            task.total_count = 1
            task.success_count = 1
    except json.JSONDecodeError:
        pass  # stdout 不是 JSON，跳过
    except Exception as e:
        logger.warning(f"Failed to store spider data for task {task.id}: {e}")
```

### Step 2: 创建 DataService

Create `app/services/crawlhub/data_service.py`:

```python
import csv
import io
import json
import logging
from datetime import datetime
from typing import Any

from bson import ObjectId

from extensions.ext_mongodb import mongodb_client

logger = logging.getLogger(__name__)

SPIDER_DATA_COLLECTION = "spider_data"


class DataService:
    """爬取数据查询和导出服务"""

    def __init__(self):
        self._collection = None
        self._indexes_created = False

    @property
    def collection(self):
        if self._collection is None:
            self._collection = mongodb_client.get_collection(SPIDER_DATA_COLLECTION)
        return self._collection

    async def ensure_indexes(self) -> None:
        if self._indexes_created or not mongodb_client.is_enabled():
            return
        try:
            await mongodb_client.ensure_indexes(
                SPIDER_DATA_COLLECTION,
                [
                    {"keys": "task_id"},
                    {"keys": "spider_id"},
                    {"keys": [("created_at", -1)]},
                ],
            )
            self._indexes_created = True
        except Exception as e:
            logger.warning(f"Failed to create spider_data indexes: {e}")

    async def query(
        self,
        spider_id: str | None = None,
        task_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """分页查询爬取数据"""
        if not mongodb_client.is_enabled():
            return [], 0

        await self.ensure_indexes()

        query_filter: dict[str, Any] = {}
        if spider_id:
            query_filter["spider_id"] = spider_id
        if task_id:
            query_filter["task_id"] = task_id

        total = await self.collection.count_documents(query_filter)

        cursor = (
            self.collection.find(query_filter)
            .sort("created_at", -1)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )

        items = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            items.append(doc)

        return items, total

    async def export_json(
        self,
        spider_id: str | None = None,
        task_id: str | None = None,
    ) -> str:
        """导出为 JSON 字符串"""
        if not mongodb_client.is_enabled():
            return "[]"

        query_filter: dict[str, Any] = {}
        if spider_id:
            query_filter["spider_id"] = spider_id
        if task_id:
            query_filter["task_id"] = task_id

        cursor = self.collection.find(query_filter).sort("created_at", -1)
        items = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if "created_at" in doc and isinstance(doc["created_at"], datetime):
                doc["created_at"] = doc["created_at"].isoformat()
            items.append(doc.get("data", doc))

        return json.dumps(items, ensure_ascii=False, indent=2)

    async def export_csv(
        self,
        spider_id: str | None = None,
        task_id: str | None = None,
    ) -> str:
        """导出为 CSV 字符串"""
        if not mongodb_client.is_enabled():
            return ""

        query_filter: dict[str, Any] = {}
        if spider_id:
            query_filter["spider_id"] = spider_id
        if task_id:
            query_filter["task_id"] = task_id

        cursor = self.collection.find(query_filter).sort("created_at", -1)
        rows = []
        all_keys: set[str] = set()

        async for doc in cursor:
            data = doc.get("data", {})
            if isinstance(data, dict):
                all_keys.update(data.keys())
                rows.append(data)
            else:
                rows.append({"value": data})
                all_keys.add("value")

        if not rows:
            return ""

        output = io.StringIO()
        fieldnames = sorted(all_keys)
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

        return output.getvalue()

    async def delete_by_task(self, task_id: str) -> int:
        """删除指定任务的数据"""
        if not mongodb_client.is_enabled():
            return 0
        result = await self.collection.delete_many({"task_id": task_id})
        return result.deleted_count

    async def delete_by_spider(self, spider_id: str) -> int:
        """删除指定爬虫的所有数据"""
        if not mongodb_client.is_enabled():
            return 0
        result = await self.collection.delete_many({"spider_id": spider_id})
        return result.deleted_count
```

### Step 3: 创建数据 API 路由

Create `app/routers/admin/crawlhub/data.py`:

```python
from fastapi import APIRouter, Query
from fastapi.responses import Response

from schemas.response import ApiResponse
from services.crawlhub.data_service import DataService

router = APIRouter(prefix="/data", tags=["CrawlHub - Data"])


@router.get("")
async def list_data(
    spider_id: str | None = Query(None),
    task_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查询爬取数据"""
    service = DataService()
    items, total = await service.query(spider_id, task_id, page, page_size)
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    })


@router.get("/export/json")
async def export_json(
    spider_id: str | None = Query(None),
    task_id: str | None = Query(None),
):
    """导出为 JSON"""
    service = DataService()
    content = await service.export_json(spider_id, task_id)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=data.json"},
    )


@router.get("/export/csv")
async def export_csv(
    spider_id: str | None = Query(None),
    task_id: str | None = Query(None),
):
    """导出为 CSV"""
    service = DataService()
    content = await service.export_csv(spider_id, task_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=data.csv"},
    )


@router.delete("")
async def delete_data(
    spider_id: str | None = Query(None),
    task_id: str | None = Query(None),
):
    """删除数据"""
    service = DataService()
    if task_id:
        count = await service.delete_by_task(task_id)
    elif spider_id:
        count = await service.delete_by_spider(spider_id)
    else:
        return ApiResponse(data={"error": "请指定 spider_id 或 task_id"})

    return ApiResponse(data={"deleted_count": count})
```

### Step 4: 注册数据路由

在 `app/routers/admin/crawlhub/__init__.py` 添加：

```python
from .data import router as data_router
# ...
router.include_router(data_router)
```

### Step 5: 更新 services __init__.py

在 `app/services/crawlhub/__init__.py` 添加：

```python
from .data_service import DataService

# __all__ 列表中添加 "DataService"
```

---

## Task 3: 任务失败重试 + 基础告警

**背景:** 当前任务失败后无自动处理，也没有通知机制。需要：1) Celery 自动重试；2) 失败告警通知。

**Files:**
- Create: `app/models/crawlhub/alert.py` — 告警模型
- Modify: `app/models/crawlhub/__init__.py` — 导出 Alert
- Create: `app/services/crawlhub/alert_service.py` — 告警服务
- Create: `app/routers/admin/crawlhub/alerts.py` — 告警 API
- Modify: `app/routers/admin/crawlhub/__init__.py` — 注册 alerts 路由
- Modify: `app/tasks/spider_tasks.py` — 失败时创建告警

### Step 1: 创建 Alert 模型

Create `app/models/crawlhub/alert.py`:

```python
import enum

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin
from models.types import EnumText, StringUUID


class AlertLevel(enum.StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Alert(DefaultFieldsMixin, Base):
    """告警记录"""

    __tablename__ = "crawlhub_alerts"

    type: Mapped[str] = mapped_column(String(50), nullable=False, comment="告警类型")
    level: Mapped[AlertLevel] = mapped_column(
        EnumText(AlertLevel), default=AlertLevel.WARNING, comment="告警级别"
    )
    message: Mapped[str] = mapped_column(Text, nullable=False, comment="告警信息")
    spider_id: Mapped[str | None] = mapped_column(StringUUID, nullable=True, comment="关联爬虫")
    task_id: Mapped[str | None] = mapped_column(StringUUID, nullable=True, comment="关联任务")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已读")

    def __repr__(self) -> str:
        return f"<Alert {self.type} level={self.level}>"
```

### Step 2: 更新 models __init__

在 `app/models/crawlhub/__init__.py` 添加：

```python
from .alert import Alert, AlertLevel

# __all__ 中添加 "Alert", "AlertLevel"
```

### Step 3: 生成迁移

Run: `cd /Users/fanjunjie/Documents/repositories/personal/crawlhub/app && alembic revision --autogenerate -m "add crawlhub alerts table"`

Run: `cd /Users/fanjunjie/Documents/repositories/personal/crawlhub/app && alembic upgrade head`

### Step 4: 创建 AlertService

Create `app/services/crawlhub/alert_service.py`:

```python
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
```

### Step 5: 创建告警 API 路由

Create `app/routers/admin/crawlhub/alerts.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub.alert import AlertLevel
from models.engine import get_db
from schemas.platform import PaginatedResponse
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["CrawlHub - Alerts"])


@router.get("")
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: AlertLevel | None = Query(None),
    is_read: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取告警列表"""
    service = AlertService(db)
    alerts, total = await service.get_list(page, page_size, level, is_read)
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(data={
        "items": [
            {
                "id": a.id,
                "type": a.type,
                "level": a.level.value,
                "message": a.message,
                "spider_id": a.spider_id,
                "task_id": a.task_id,
                "is_read": a.is_read,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    })


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
):
    """获取未读告警数"""
    service = AlertService(db)
    count = await service.get_unread_count()
    return ApiResponse(data={"count": count})


@router.post("/{alert_id}/read", response_model=MessageResponse)
async def mark_as_read(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
):
    """标记告警已读"""
    service = AlertService(db)
    success = await service.mark_as_read(alert_id)
    if not success:
        return MessageResponse(msg="告警不存在")
    return MessageResponse(msg="已标记为已读")


@router.post("/read-all", response_model=MessageResponse)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
):
    """全部标记已读"""
    service = AlertService(db)
    count = await service.mark_all_as_read()
    return MessageResponse(msg=f"已标记 {count} 条告警为已读")
```

### Step 6: 注册告警路由

在 `app/routers/admin/crawlhub/__init__.py` 添加：

```python
from .alerts import router as alerts_router
# ...
router.include_router(alerts_router)
```

### Step 7: 在 spider_tasks.py 中集成告警

修改 `app/tasks/spider_tasks.py` 的 `execute_spider`，在失败重试耗尽时创建告警：

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
async def execute_spider(self, spider_id: str):
    """执行单个爬虫任务"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Spider).where(Spider.id == spider_id)
        )
        spider = result.scalar_one_or_none()
        if not spider:
            logger.error(f"Spider {spider_id} not found")
            return

        runner = SpiderRunnerService(session)
        task = await runner.create_scheduled_task(spider)
        await runner.run_spider_sync(spider, task)

        if task.status == SpiderTaskStatus.FAILED:
            task.retry_count = self.request.retries
            await session.commit()

            if self.request.retries < 3:
                raise self.retry(exc=Exception(task.error_message))
            else:
                # 重试耗尽，创建告警
                from services.crawlhub.alert_service import AlertService
                from models.crawlhub.alert import AlertLevel

                alert_service = AlertService(session)
                await alert_service.create_alert(
                    type="task_failed",
                    level=AlertLevel.ERROR,
                    message=f"爬虫 [{spider.name}] 执行失败（已重试 3 次）: {task.error_message or '未知错误'}",
                    spider_id=spider_id,
                    task_id=task.id,
                )
```

---

## Task 4: 日志持久化

**背景:** 当前 test-run 日志通过 SSE 实时推送，容器/进程结束后日志丢失。需要将 stdout/stderr 持久化到 MongoDB，并提供查询 API。

**Files:**
- Create: `app/services/crawlhub/log_service.py` — 日志查询服务
- Create: `app/routers/admin/crawlhub/tasks.py` — 任务 + 日志 API
- Modify: `app/routers/admin/crawlhub/__init__.py` — 注册 tasks 路由
- Modify: `app/services/crawlhub/spider_runner_service.py` — test-run 也存储日志

### Step 1: 创建 LogService

Create `app/services/crawlhub/log_service.py`:

```python
import logging
from datetime import datetime
from typing import Any

from extensions.ext_mongodb import mongodb_client

logger = logging.getLogger(__name__)

SPIDER_LOGS_COLLECTION = "spider_logs"


class LogService:
    """爬虫任务日志服务"""

    def __init__(self):
        self._collection = None
        self._indexes_created = False

    @property
    def collection(self):
        if self._collection is None:
            self._collection = mongodb_client.get_collection(SPIDER_LOGS_COLLECTION)
        return self._collection

    async def ensure_indexes(self) -> None:
        if self._indexes_created or not mongodb_client.is_enabled():
            return
        try:
            await mongodb_client.ensure_indexes(
                SPIDER_LOGS_COLLECTION,
                [
                    {"keys": "task_id"},
                    {"keys": "spider_id"},
                    {"keys": [("created_at", -1)]},
                ],
            )
            self._indexes_created = True
        except Exception as e:
            logger.warning(f"Failed to create spider_logs indexes: {e}")

    async def store_log(
        self,
        task_id: str,
        spider_id: str,
        stdout: str,
        stderr: str,
    ) -> str | None:
        """存储任务日志"""
        if not mongodb_client.is_enabled():
            return None

        await self.ensure_indexes()

        try:
            result = await self.collection.insert_one({
                "task_id": task_id,
                "spider_id": spider_id,
                "stdout": stdout,
                "stderr": stderr,
                "created_at": datetime.utcnow(),
            })
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to store log: {e}")
            return None

    async def get_by_task(self, task_id: str) -> dict | None:
        """获取指定任务的日志"""
        if not mongodb_client.is_enabled():
            return None

        doc = await self.collection.find_one({"task_id": task_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def get_list_by_spider(
        self,
        spider_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取指定爬虫的日志列表"""
        if not mongodb_client.is_enabled():
            return [], 0

        query_filter = {"spider_id": spider_id}
        total = await self.collection.count_documents(query_filter)

        cursor = (
            self.collection.find(query_filter)
            .sort("created_at", -1)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )

        items = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            items.append(doc)

        return items, total
```

### Step 2: 创建 Tasks API 路由

Create `app/routers/admin/crawlhub/tasks.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub import SpiderTask, SpiderTaskStatus
from models.engine import get_db
from schemas.crawlhub import TaskResponse
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub.log_service import LogService

router = APIRouter(prefix="/tasks", tags=["CrawlHub - Tasks"])


@router.get("")
async def list_tasks(
    spider_id: str | None = Query(None),
    status: SpiderTaskStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取任务列表"""
    query = select(SpiderTask)

    if spider_id:
        query = query.where(SpiderTask.spider_id == spider_id)
    if status:
        query = query.where(SpiderTask.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    total_pages = (total + page_size - 1) // page_size

    query = query.order_by(SpiderTask.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    tasks = list(result.scalars().all())

    return ApiResponse(data={
        "items": [TaskResponse.model_validate(t).model_dump() for t in tasks],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    })


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取任务详情"""
    result = await db.execute(
        select(SpiderTask).where(SpiderTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return ApiResponse(data=TaskResponse.model_validate(task))


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: str,
):
    """获取任务日志"""
    log_service = LogService()
    log = await log_service.get_by_task(task_id)
    if not log:
        return ApiResponse(data={"stdout": "", "stderr": "", "message": "暂无日志"})
    return ApiResponse(data=log)


@router.post("/{task_id}/cancel", response_model=MessageResponse)
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """取消任务"""
    result = await db.execute(
        select(SpiderTask).where(SpiderTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in (SpiderTaskStatus.PENDING, SpiderTaskStatus.RUNNING):
        return MessageResponse(msg="任务已完成，无法取消")

    task.status = SpiderTaskStatus.CANCELLED
    await db.commit()
    return MessageResponse(msg="任务已取消")
```

### Step 3: 注册 tasks 路由

在 `app/routers/admin/crawlhub/__init__.py` 添加：

```python
from .tasks import router as tasks_router
# ...
router.include_router(tasks_router)
```

### Step 4: test-run 也持久化日志

修改 `app/services/crawlhub/spider_runner_service.py` 的 `run_test` 方法。在 `finally` 块之前，收集 stdout/stderr 并存储：

在 `run_test` 方法中，将 stdout/stderr 的行收集起来，在 finally 中写入 MongoDB：

```python
async def run_test(self, spider: Spider, task: SpiderTask) -> AsyncGenerator[dict, None]:
    """运行测试任务，返回 SSE 事件生成器"""
    task.status = SpiderTaskStatus.RUNNING
    task.started_at = datetime.utcnow()
    await self.db.commit()

    stdout_lines = []
    stderr_lines = []

    try:
        # ... (保持现有的文件准备和命令构建逻辑不变)

        # 读取 stdout 和 stderr（修改为同时收集）
        try:
            async for event in read_stream(process.stdout, "stdout"):
                stdout_lines.append(event["data"]["line"])
                yield event
            async for event in read_stream(process.stderr, "stderr"):
                stderr_lines.append(event["data"]["line"])
                yield event

            await asyncio.wait_for(process.wait(), timeout=timeout)
        # ... (保持现有的错误处理不变)

    except Exception as e:
        # ... (保持现有逻辑不变)
    finally:
        task.finished_at = datetime.utcnow()
        await self.db.commit()

        # 持久化日志
        await self._store_task_log(
            task,
            "\n".join(stdout_lines).encode("utf-8"),
            "\n".join(stderr_lines).encode("utf-8"),
        )

        # ... (保持现有的 yield status 逻辑不变)
```

### Step 5: 重构 _store_task_log 使用 LogService

修改 `_store_task_log` 方法，改用 LogService：

```python
async def _store_task_log(self, task: SpiderTask, stdout: bytes, stderr: bytes) -> None:
    """存储任务日志到 MongoDB"""
    from services.crawlhub.log_service import LogService

    log_service = LogService()
    await log_service.store_log(
        task_id=task.id,
        spider_id=task.spider_id,
        stdout=stdout.decode("utf-8", errors="replace"),
        stderr=stderr.decode("utf-8", errors="replace"),
    )
```

---

## 依赖关系

- Task 1 (定时调度) 和 Task 3 (告警) 有交叉：spider_tasks.py 在失败时创建告警。建议先做 Task 1，再做 Task 3。
- Task 2 (数据导出) 依赖 Task 1 中 `_store_spider_data` 方法，但可以先建 DataService 和路由。
- Task 4 (日志持久化) 独立于其他任务。

**推荐执行顺序:** Task 4 → Task 1 → Task 2 → Task 3

## 安装依赖

Run: `cd /Users/fanjunjie/Documents/repositories/personal/crawlhub && uv add croniter`
