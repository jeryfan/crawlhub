# CrawlHub Phase 1: 基础框架实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成 CrawlHub 爬虫管理平台的基础框架，包括数据模型、CRUD API 和前端页面框架。

**Architecture:** 复用 fastapi-template 现有架构，扩展 CrawlHub 专用的 models、routers、services。后端使用 PostgreSQL 存储元数据，MongoDB 存储抓取数据。前端在 admin 端添加 crawlhub 模块。

**Tech Stack:** FastAPI + SQLAlchemy + MongoDB (Motor) + Next.js 15 + React 19

---

## 前置准备

### 确认 MongoDB 扩展已启用

检查 `app/extensions/ext_mongodb.py` 已存在，确认配置正确。

---

## Task 1: 添加 CrawlHub 依赖

**Files:**
- Modify: `app/pyproject.toml`

**Step 1: 添加 Docker SDK 和爬虫相关依赖**

在 `app/pyproject.toml` 的 `[project.dependencies]` 中添加：

```toml
# Docker SDK for container management
docker>=7.1.0

# Spider frameworks (for type hints and utilities)
httpx>=0.26.0
```

**Step 2: 安装依赖**

Run: `cd /Users/fanjunjie/Documents/repositories/personal/crawlhub/app && uv sync`

Expected: 依赖安装成功

**Step 3: Commit**

```bash
git add app/pyproject.toml app/uv.lock
git commit -m "chore: add docker SDK dependency for CrawlHub"
```

---

## Task 2: 创建 Project 数据模型

**Files:**
- Create: `app/models/crawlhub/__init__.py`
- Create: `app/models/crawlhub/project.py`

**Step 1: 创建模块目录和 __init__.py**

```python
# app/models/crawlhub/__init__.py
from .project import Project

__all__ = ["Project"]
```

**Step 2: 创建 Project 模型**

```python
# app/models/crawlhub/project.py
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, DefaultFieldsMixin


class Project(DefaultFieldsMixin, Base):
    """爬虫项目"""

    __tablename__ = "crawlhub_projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="项目名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="项目描述")

    # Relationships
    spiders: Mapped[list["Spider"]] = relationship(
        "Spider", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project {self.name}>"
```

**Step 3: Commit**

```bash
git add app/models/crawlhub/
git commit -m "feat(crawlhub): add Project model"
```

---

## Task 3: 创建 Spider 数据模型

**Files:**
- Modify: `app/models/crawlhub/__init__.py`
- Create: `app/models/crawlhub/spider.py`

**Step 1: 创建 Spider 模型**

```python
# app/models/crawlhub/spider.py
import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, DefaultFieldsMixin
from models.types import StringUUID


class ScriptType(str, enum.Enum):
    """脚本类型"""
    HTTPX = "httpx"
    SCRAPY = "scrapy"
    PLAYWRIGHT = "playwright"


class Spider(DefaultFieldsMixin, Base):
    """爬虫定义"""

    __tablename__ = "crawlhub_spiders"

    project_id: Mapped[str] = mapped_column(
        StringUUID, ForeignKey("crawlhub_projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="爬虫名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="爬虫描述")
    script_type: Mapped[ScriptType] = mapped_column(
        Enum(ScriptType), default=ScriptType.HTTPX, comment="脚本类型"
    )
    script_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="脚本内容")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    cron_expr: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Cron表达式")

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="spiders")
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="spider", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Spider {self.name}>"
```

**Step 2: 更新 __init__.py**

```python
# app/models/crawlhub/__init__.py
from .project import Project
from .spider import Spider, ScriptType

__all__ = ["Project", "Spider", "ScriptType"]
```

**Step 3: Commit**

```bash
git add app/models/crawlhub/
git commit -m "feat(crawlhub): add Spider model"
```

---

## Task 4: 创建 Task 数据模型

**Files:**
- Modify: `app/models/crawlhub/__init__.py`
- Create: `app/models/crawlhub/task.py`

**Step 1: 创建 Task 模型**

```python
# app/models/crawlhub/task.py
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, DefaultFieldsMixin
from models.types import StringUUID


class TaskStatus(str, enum.Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(DefaultFieldsMixin, Base):
    """爬虫任务"""

    __tablename__ = "crawlhub_tasks"

    spider_id: Mapped[str] = mapped_column(
        StringUUID, ForeignKey("crawlhub_spiders.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.PENDING, comment="任务状态"
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, comment="进度百分比")
    total_count: Mapped[int] = mapped_column(Integer, default=0, comment="总数量")
    success_count: Mapped[int] = mapped_column(Integer, default=0, comment="成功数量")
    failed_count: Mapped[int] = mapped_column(Integer, default=0, comment="失败数量")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="结束时间")
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Worker ID")
    container_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="容器ID")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    # Relationships
    spider: Mapped["Spider"] = relationship("Spider", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task {self.id} status={self.status}>"
```

**Step 2: 更新 __init__.py**

```python
# app/models/crawlhub/__init__.py
from .project import Project
from .spider import Spider, ScriptType
from .task import Task, TaskStatus

__all__ = ["Project", "Spider", "ScriptType", "Task", "TaskStatus"]
```

**Step 3: Commit**

```bash
git add app/models/crawlhub/
git commit -m "feat(crawlhub): add Task model"
```

---

## Task 5: 创建 Proxy 数据模型

**Files:**
- Modify: `app/models/crawlhub/__init__.py`
- Create: `app/models/crawlhub/proxy.py`

**Step 1: 创建 Proxy 模型**

```python
# app/models/crawlhub/proxy.py
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin


class ProxyStatus(str, enum.Enum):
    """代理状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COOLDOWN = "cooldown"


class ProxyProtocol(str, enum.Enum):
    """代理协议"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class Proxy(DefaultFieldsMixin, Base):
    """代理配置"""

    __tablename__ = "crawlhub_proxies"

    host: Mapped[str] = mapped_column(String(255), nullable=False, comment="主机地址")
    port: Mapped[int] = mapped_column(Integer, nullable=False, comment="端口")
    protocol: Mapped[ProxyProtocol] = mapped_column(
        Enum(ProxyProtocol), default=ProxyProtocol.HTTP, comment="协议"
    )
    username: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="用户名")
    password: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="密码")
    status: Mapped[ProxyStatus] = mapped_column(
        Enum(ProxyStatus), default=ProxyStatus.ACTIVE, comment="状态"
    )
    last_check_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最后检测时间"
    )
    success_rate: Mapped[float] = mapped_column(Float, default=1.0, comment="成功率")
    fail_count: Mapped[int] = mapped_column(Integer, default=0, comment="连续失败次数")

    @property
    def url(self) -> str:
        """获取代理 URL"""
        if self.username and self.password:
            return f"{self.protocol.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol.value}://{self.host}:{self.port}"

    def __repr__(self) -> str:
        return f"<Proxy {self.host}:{self.port}>"
```

**Step 2: 更新 __init__.py**

```python
# app/models/crawlhub/__init__.py
from .project import Project
from .spider import Spider, ScriptType
from .task import Task, TaskStatus
from .proxy import Proxy, ProxyStatus, ProxyProtocol

__all__ = [
    "Project",
    "Spider",
    "ScriptType",
    "Task",
    "TaskStatus",
    "Proxy",
    "ProxyStatus",
    "ProxyProtocol",
]
```

**Step 3: Commit**

```bash
git add app/models/crawlhub/
git commit -m "feat(crawlhub): add Proxy model"
```

---

## Task 6: 创建数据库迁移

**Files:**
- Create: `app/alembic/versions/xxxx_add_crawlhub_tables.py` (自动生成)

**Step 1: 在 models/__init__.py 中导入新模型**

编辑 `app/models/__init__.py`，添加导入：

```python
# 在文件末尾添加
from models.crawlhub import Project, Spider, Task, Proxy
```

**Step 2: 生成迁移文件**

Run: `cd /Users/fanjunjie/Documents/repositories/personal/crawlhub/app && alembic revision --autogenerate -m "add crawlhub tables"`

Expected: 生成新的迁移文件

**Step 3: 检查生成的迁移文件**

确认迁移文件包含：
- `crawlhub_projects` 表
- `crawlhub_spiders` 表
- `crawlhub_tasks` 表
- `crawlhub_proxies` 表

**Step 4: Commit**

```bash
git add app/alembic/versions/ app/models/__init__.py
git commit -m "feat(crawlhub): add database migration for crawlhub tables"
```

---

## Task 7: 创建 CrawlHub Schemas

**Files:**
- Create: `app/schemas/crawlhub/__init__.py`
- Create: `app/schemas/crawlhub/project.py`
- Create: `app/schemas/crawlhub/spider.py`
- Create: `app/schemas/crawlhub/task.py`
- Create: `app/schemas/crawlhub/proxy.py`

**Step 1: 创建 Project Schema**

```python
# app/schemas/crawlhub/project.py
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="项目名称")
    description: str | None = Field(None, description="项目描述")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime
    spider_count: int = 0

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
```

**Step 2: 创建 Spider Schema**

```python
# app/schemas/crawlhub/spider.py
from datetime import datetime

from pydantic import BaseModel, Field

from models.crawlhub import ScriptType


class SpiderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="爬虫名称")
    description: str | None = Field(None, description="爬虫描述")
    script_type: ScriptType = Field(default=ScriptType.HTTPX, description="脚本类型")
    script_content: str | None = Field(None, description="脚本内容")
    is_active: bool = Field(default=True, description="是否启用")
    cron_expr: str | None = Field(None, description="Cron表达式")


class SpiderCreate(SpiderBase):
    project_id: str = Field(..., description="项目ID")


class SpiderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    script_type: ScriptType | None = None
    script_content: str | None = None
    is_active: bool | None = None
    cron_expr: str | None = None


class SpiderResponse(SpiderBase):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SpiderListResponse(BaseModel):
    items: list[SpiderResponse]
    total: int
```

**Step 3: 创建 Task Schema**

```python
# app/schemas/crawlhub/task.py
from datetime import datetime

from pydantic import BaseModel, Field

from models.crawlhub import TaskStatus


class TaskResponse(BaseModel):
    id: str
    spider_id: str
    status: TaskStatus
    progress: int
    total_count: int
    success_count: int
    failed_count: int
    started_at: datetime | None
    finished_at: datetime | None
    worker_id: str | None
    container_id: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int


class TaskCreate(BaseModel):
    spider_id: str = Field(..., description="爬虫ID")
```

**Step 4: 创建 Proxy Schema**

```python
# app/schemas/crawlhub/proxy.py
from datetime import datetime

from pydantic import BaseModel, Field

from models.crawlhub import ProxyProtocol, ProxyStatus


class ProxyBase(BaseModel):
    host: str = Field(..., min_length=1, max_length=255, description="主机地址")
    port: int = Field(..., ge=1, le=65535, description="端口")
    protocol: ProxyProtocol = Field(default=ProxyProtocol.HTTP, description="协议")
    username: str | None = Field(None, max_length=100, description="用户名")
    password: str | None = Field(None, max_length=100, description="密码")


class ProxyCreate(ProxyBase):
    pass


class ProxyBatchCreate(BaseModel):
    proxies: list[ProxyCreate] = Field(..., min_length=1, description="代理列表")


class ProxyUpdate(BaseModel):
    host: str | None = Field(None, min_length=1, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    protocol: ProxyProtocol | None = None
    username: str | None = None
    password: str | None = None
    status: ProxyStatus | None = None


class ProxyResponse(ProxyBase):
    id: str
    status: ProxyStatus
    last_check_at: datetime | None
    success_rate: float
    fail_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProxyListResponse(BaseModel):
    items: list[ProxyResponse]
    total: int
```

**Step 5: 创建 __init__.py**

```python
# app/schemas/crawlhub/__init__.py
from .project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from .spider import SpiderCreate, SpiderUpdate, SpiderResponse, SpiderListResponse
from .task import TaskCreate, TaskResponse, TaskListResponse
from .proxy import (
    ProxyCreate,
    ProxyBatchCreate,
    ProxyUpdate,
    ProxyResponse,
    ProxyListResponse,
)

__all__ = [
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectListResponse",
    "SpiderCreate",
    "SpiderUpdate",
    "SpiderResponse",
    "SpiderListResponse",
    "TaskCreate",
    "TaskResponse",
    "TaskListResponse",
    "ProxyCreate",
    "ProxyBatchCreate",
    "ProxyUpdate",
    "ProxyResponse",
    "ProxyListResponse",
]
```

**Step 6: Commit**

```bash
git add app/schemas/crawlhub/
git commit -m "feat(crawlhub): add Pydantic schemas"
```

---

## Task 8: 创建 Project Service

**Files:**
- Create: `app/services/crawlhub/__init__.py`
- Create: `app/services/crawlhub/project_service.py`

**Step 1: 创建 Project Service**

```python
# app/services/crawlhub/project_service.py
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.crawlhub import Project, Spider
from schemas.crawlhub import ProjectCreate, ProjectUpdate
from services.base_service import BaseService


class ProjectService(BaseService):
    async def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
    ) -> tuple[list[Project], int]:
        """获取项目列表"""
        query = select(Project)

        if keyword:
            query = query.where(Project.name.ilike(f"%{keyword}%"))

        # 统计总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # 分页查询
        query = query.order_by(Project.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        projects = list(result.scalars().all())

        # 获取每个项目的爬虫数量
        for project in projects:
            spider_count_query = select(func.count()).where(Spider.project_id == project.id)
            project.spider_count = await self.db.scalar(spider_count_query) or 0

        return projects, total

    async def get_by_id(self, project_id: str) -> Project | None:
        """根据 ID 获取项目"""
        query = select(Project).where(Project.id == project_id)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()

        if project:
            spider_count_query = select(func.count()).where(Spider.project_id == project.id)
            project.spider_count = await self.db.scalar(spider_count_query) or 0

        return project

    async def create(self, data: ProjectCreate) -> Project:
        """创建项目"""
        project = Project(**data.model_dump())
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        project.spider_count = 0
        return project

    async def update(self, project_id: str, data: ProjectUpdate) -> Project | None:
        """更新项目"""
        project = await self.get_by_id(project_id)
        if not project:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete(self, project_id: str) -> bool:
        """删除项目"""
        project = await self.get_by_id(project_id)
        if not project:
            return False

        await self.db.delete(project)
        await self.db.commit()
        return True
```

**Step 2: 创建 __init__.py**

```python
# app/services/crawlhub/__init__.py
from .project_service import ProjectService

__all__ = ["ProjectService"]
```

**Step 3: Commit**

```bash
git add app/services/crawlhub/
git commit -m "feat(crawlhub): add ProjectService"
```

---

## Task 9: 创建 Spider Service

**Files:**
- Modify: `app/services/crawlhub/__init__.py`
- Create: `app/services/crawlhub/spider_service.py`

**Step 1: 创建 Spider Service**

```python
# app/services/crawlhub/spider_service.py
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub import Spider
from schemas.crawlhub import SpiderCreate, SpiderUpdate
from services.base_service import BaseService


class SpiderService(BaseService):
    async def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        project_id: str | None = None,
        keyword: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Spider], int]:
        """获取爬虫列表"""
        query = select(Spider)

        if project_id:
            query = query.where(Spider.project_id == project_id)
        if keyword:
            query = query.where(Spider.name.ilike(f"%{keyword}%"))
        if is_active is not None:
            query = query.where(Spider.is_active == is_active)

        # 统计总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # 分页查询
        query = query.order_by(Spider.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        spiders = list(result.scalars().all())

        return spiders, total

    async def get_by_id(self, spider_id: str) -> Spider | None:
        """根据 ID 获取爬虫"""
        query = select(Spider).where(Spider.id == spider_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: SpiderCreate) -> Spider:
        """创建爬虫"""
        spider = Spider(**data.model_dump())
        self.db.add(spider)
        await self.db.commit()
        await self.db.refresh(spider)
        return spider

    async def update(self, spider_id: str, data: SpiderUpdate) -> Spider | None:
        """更新爬虫"""
        spider = await self.get_by_id(spider_id)
        if not spider:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(spider, key, value)

        await self.db.commit()
        await self.db.refresh(spider)
        return spider

    async def delete(self, spider_id: str) -> bool:
        """删除爬虫"""
        spider = await self.get_by_id(spider_id)
        if not spider:
            return False

        await self.db.delete(spider)
        await self.db.commit()
        return True

    async def get_templates(self) -> dict[str, str]:
        """获取脚本模板"""
        return {
            "httpx": '''import httpx
from bs4 import BeautifulSoup

def run(config):
    """
    config: {
        "urls": [...],
        "proxy": "http://...",  # 可选
        "headers": {...}        # 可选
    }
    """
    results = []
    client = httpx.Client(proxy=config.get("proxy"))

    for url in config["urls"]:
        resp = client.get(url, headers=config.get("headers", {}))
        soup = BeautifulSoup(resp.text, "lxml")
        # 自定义解析逻辑
        data = {"title": soup.title.string if soup.title else None}
        results.append({"url": url, "data": data})

    return results
''',
            "scrapy": '''import scrapy

class MySpider(scrapy.Spider):
    name = "my_spider"

    def __init__(self, config=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config or {}
        self.start_urls = self.config.get("urls", [])

    def parse(self, response):
        # 自定义解析逻辑
        yield {
            "url": response.url,
            "title": response.css("title::text").get(),
        }
''',
            "playwright": '''from playwright.sync_api import sync_playwright

def run(config):
    """
    config: {
        "urls": [...],
        "proxy": "http://...",  # 可选
    }
    """
    results = []

    with sync_playwright() as p:
        browser_args = {}
        if config.get("proxy"):
            browser_args["proxy"] = {"server": config["proxy"]}

        browser = p.chromium.launch(**browser_args)
        page = browser.new_page()

        for url in config["urls"]:
            page.goto(url)
            # 自定义交互和解析逻辑
            data = {"title": page.title()}
            results.append({"url": url, "data": data})

        browser.close()

    return results
''',
        }
```

**Step 2: 更新 __init__.py**

```python
# app/services/crawlhub/__init__.py
from .project_service import ProjectService
from .spider_service import SpiderService

__all__ = ["ProjectService", "SpiderService"]
```

**Step 3: Commit**

```bash
git add app/services/crawlhub/
git commit -m "feat(crawlhub): add SpiderService with script templates"
```

---

## Task 10: 创建 Proxy Service

**Files:**
- Modify: `app/services/crawlhub/__init__.py`
- Create: `app/services/crawlhub/proxy_service.py`

**Step 1: 创建 Proxy Service**

```python
# app/services/crawlhub/proxy_service.py
import random
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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

        # 统计总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # 分页查询
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

        # 按成功率加权随机选择
        weights = [p.success_rate for p in proxies]
        selected = random.choices(proxies, weights=weights, k=1)[0]

        # 标记为冷却状态
        selected.status = ProxyStatus.COOLDOWN
        await self.db.commit()

        return selected

    async def report_result(self, proxy_id: str, success: bool) -> None:
        """上报代理使用结果"""
        proxy = await self.get_by_id(proxy_id)
        if not proxy:
            return

        if success:
            # 成功：重置失败计数，更新成功率
            proxy.fail_count = 0
            proxy.success_rate = min(1.0, proxy.success_rate + 0.01)
            proxy.status = ProxyStatus.ACTIVE
        else:
            # 失败：增加失败计数
            proxy.fail_count += 1
            proxy.success_rate = max(0.0, proxy.success_rate - 0.05)

            # 连续失败 3 次，标记为 inactive
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
```

**Step 2: 更新 __init__.py**

```python
# app/services/crawlhub/__init__.py
from .project_service import ProjectService
from .spider_service import SpiderService
from .proxy_service import ProxyService

__all__ = ["ProjectService", "SpiderService", "ProxyService"]
```

**Step 3: Commit**

```bash
git add app/services/crawlhub/
git commit -m "feat(crawlhub): add ProxyService with weighted selection"
```

---

## Task 11: 创建 Project Router

**Files:**
- Create: `app/routers/admin/crawlhub/__init__.py`
- Create: `app/routers/admin/crawlhub/projects.py`

**Step 1: 创建 Project Router**

```python
# app/routers/admin/crawlhub/projects.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db
from schemas.crawlhub import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from services.crawlhub import ProjectService

router = APIRouter(prefix="/projects", tags=["CrawlHub - Projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取项目列表"""
    service = ProjectService(db)
    projects, total = await service.get_list(page, page_size, keyword)
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取项目详情"""
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.post("", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建项目"""
    service = ProjectService(db)
    project = await service.create(data)
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新项目"""
    service = ProjectService(db)
    project = await service.update(project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除项目"""
    service = ProjectService(db)
    success = await service.delete(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted"}
```

**Step 2: 创建 __init__.py**

```python
# app/routers/admin/crawlhub/__init__.py
from fastapi import APIRouter

from .projects import router as projects_router

router = APIRouter(prefix="/crawlhub")
router.include_router(projects_router)
```

**Step 3: Commit**

```bash
git add app/routers/admin/crawlhub/
git commit -m "feat(crawlhub): add Project API router"
```

---

## Task 12: 创建 Spider Router

**Files:**
- Modify: `app/routers/admin/crawlhub/__init__.py`
- Create: `app/routers/admin/crawlhub/spiders.py`

**Step 1: 创建 Spider Router**

```python
# app/routers/admin/crawlhub/spiders.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db
from schemas.crawlhub import (
    SpiderCreate,
    SpiderUpdate,
    SpiderResponse,
    SpiderListResponse,
)
from services.crawlhub import SpiderService

router = APIRouter(prefix="/spiders", tags=["CrawlHub - Spiders"])


@router.get("", response_model=SpiderListResponse)
async def list_spiders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: str | None = Query(None),
    keyword: str | None = Query(None),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取爬虫列表"""
    service = SpiderService(db)
    spiders, total = await service.get_list(page, page_size, project_id, keyword, is_active)
    return SpiderListResponse(
        items=[SpiderResponse.model_validate(s) for s in spiders],
        total=total,
    )


@router.get("/templates")
async def get_templates(
    db: AsyncSession = Depends(get_db),
):
    """获取脚本模板"""
    service = SpiderService(db)
    return service.get_templates()


@router.get("/{spider_id}", response_model=SpiderResponse)
async def get_spider(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取爬虫详情"""
    service = SpiderService(db)
    spider = await service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="Spider not found")
    return SpiderResponse.model_validate(spider)


@router.post("", response_model=SpiderResponse)
async def create_spider(
    data: SpiderCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建爬虫"""
    service = SpiderService(db)
    spider = await service.create(data)
    return SpiderResponse.model_validate(spider)


@router.put("/{spider_id}", response_model=SpiderResponse)
async def update_spider(
    spider_id: str,
    data: SpiderUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新爬虫"""
    service = SpiderService(db)
    spider = await service.update(spider_id, data)
    if not spider:
        raise HTTPException(status_code=404, detail="Spider not found")
    return SpiderResponse.model_validate(spider)


@router.delete("/{spider_id}")
async def delete_spider(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除爬虫"""
    service = SpiderService(db)
    success = await service.delete(spider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Spider not found")
    return {"message": "Spider deleted"}
```

**Step 2: 更新 __init__.py**

```python
# app/routers/admin/crawlhub/__init__.py
from fastapi import APIRouter

from .projects import router as projects_router
from .spiders import router as spiders_router

router = APIRouter(prefix="/crawlhub")
router.include_router(projects_router)
router.include_router(spiders_router)
```

**Step 3: Commit**

```bash
git add app/routers/admin/crawlhub/
git commit -m "feat(crawlhub): add Spider API router"
```

---

## Task 13: 创建 Proxy Router

**Files:**
- Modify: `app/routers/admin/crawlhub/__init__.py`
- Create: `app/routers/admin/crawlhub/proxies.py`

**Step 1: 创建 Proxy Router**

```python
# app/routers/admin/crawlhub/proxies.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db
from models.crawlhub import ProxyStatus
from schemas.crawlhub import (
    ProxyCreate,
    ProxyBatchCreate,
    ProxyUpdate,
    ProxyResponse,
    ProxyListResponse,
)
from services.crawlhub import ProxyService

router = APIRouter(prefix="/proxies", tags=["CrawlHub - Proxies"])


@router.get("", response_model=ProxyListResponse)
async def list_proxies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: ProxyStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取代理列表"""
    service = ProxyService(db)
    proxies, total = await service.get_list(page, page_size, status)
    return ProxyListResponse(
        items=[ProxyResponse.model_validate(p) for p in proxies],
        total=total,
    )


@router.get("/{proxy_id}", response_model=ProxyResponse)
async def get_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取代理详情"""
    service = ProxyService(db)
    proxy = await service.get_by_id(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return ProxyResponse.model_validate(proxy)


@router.post("", response_model=ProxyResponse)
async def create_proxy(
    data: ProxyCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建代理"""
    service = ProxyService(db)
    proxy = await service.create(data)
    return ProxyResponse.model_validate(proxy)


@router.post("/batch")
async def batch_create_proxies(
    data: ProxyBatchCreate,
    db: AsyncSession = Depends(get_db),
):
    """批量创建代理"""
    service = ProxyService(db)
    count = await service.batch_create(data.proxies)
    return {"message": f"Created {count} proxies"}


@router.put("/{proxy_id}", response_model=ProxyResponse)
async def update_proxy(
    proxy_id: str,
    data: ProxyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新代理"""
    service = ProxyService(db)
    proxy = await service.update(proxy_id, data)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return ProxyResponse.model_validate(proxy)


@router.delete("/{proxy_id}")
async def delete_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除代理"""
    service = ProxyService(db)
    success = await service.delete(proxy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return {"message": "Proxy deleted"}
```

**Step 2: 更新 __init__.py**

```python
# app/routers/admin/crawlhub/__init__.py
from fastapi import APIRouter

from .projects import router as projects_router
from .spiders import router as spiders_router
from .proxies import router as proxies_router

router = APIRouter(prefix="/crawlhub")
router.include_router(projects_router)
router.include_router(spiders_router)
router.include_router(proxies_router)
```

**Step 3: Commit**

```bash
git add app/routers/admin/crawlhub/
git commit -m "feat(crawlhub): add Proxy API router"
```

---

## Task 14: 注册 CrawlHub Router

**Files:**
- Modify: `app/routers/admin/__init__.py`

**Step 1: 在 admin router 中注册 crawlhub**

编辑 `app/routers/admin/__init__.py`，添加 crawlhub router 的导入和注册：

```python
# 在 imports 部分添加
from routers.admin.crawlhub import router as crawlhub_router

# 在 router.include_router(...) 列表中添加
router.include_router(crawlhub_router)
```

**Step 2: Commit**

```bash
git add app/routers/admin/__init__.py
git commit -m "feat(crawlhub): register CrawlHub router in admin"
```

---

## Task 15: 添加前端侧边栏菜单配置

**Files:**
- Modify: `admin/components/sidebar/menu-config.tsx`

**Step 1: 添加 CrawlHub 菜单项**

在 `menu-config.tsx` 中添加 CrawlHub 相关菜单：

```typescript
// 在合适的位置添加 CrawlHub 菜单组
{
  title: t('crawlhub.title'),
  icon: <RiSpiderLine className="w-4 h-4" />,
  children: [
    {
      title: t('crawlhub.dashboard'),
      href: '/crawlhub/dashboard',
      icon: <RiDashboardLine className="w-4 h-4" />,
    },
    {
      title: t('crawlhub.projects'),
      href: '/crawlhub/projects',
      icon: <RiFolderLine className="w-4 h-4" />,
    },
    {
      title: t('crawlhub.spiders'),
      href: '/crawlhub/spiders',
      icon: <RiCodeLine className="w-4 h-4" />,
    },
    {
      title: t('crawlhub.tasks'),
      href: '/crawlhub/tasks',
      icon: <RiTaskLine className="w-4 h-4" />,
    },
    {
      title: t('crawlhub.proxies'),
      href: '/crawlhub/proxies',
      icon: <RiShieldLine className="w-4 h-4" />,
    },
  ],
},
```

**Step 2: Commit**

```bash
git add admin/components/sidebar/menu-config.tsx
git commit -m "feat(crawlhub): add CrawlHub menu items to sidebar"
```

---

## Task 16: 创建前端 CrawlHub 页面目录结构

**Files:**
- Create: `admin/app/(commonLayout)/crawlhub/layout.tsx`
- Create: `admin/app/(commonLayout)/crawlhub/dashboard/page.tsx`
- Create: `admin/app/(commonLayout)/crawlhub/projects/page.tsx`
- Create: `admin/app/(commonLayout)/crawlhub/spiders/page.tsx`
- Create: `admin/app/(commonLayout)/crawlhub/proxies/page.tsx`

**Step 1: 创建 CrawlHub Layout**

```typescript
// admin/app/(commonLayout)/crawlhub/layout.tsx
export default function CrawlHubLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
```

**Step 2: 创建 Dashboard 页面（占位）**

```typescript
// admin/app/(commonLayout)/crawlhub/dashboard/page.tsx
'use client'

export default function CrawlHubDashboard() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">CrawlHub Dashboard</h1>
      <p className="text-gray-500">统计信息将在 Phase 4 实现</p>
    </div>
  )
}
```

**Step 3: 创建 Projects 页面（占位）**

```typescript
// admin/app/(commonLayout)/crawlhub/projects/page.tsx
'use client'

export default function ProjectsPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">项目管理</h1>
      <p className="text-gray-500">项目列表功能开发中...</p>
    </div>
  )
}
```

**Step 4: 创建 Spiders 页面（占位）**

```typescript
// admin/app/(commonLayout)/crawlhub/spiders/page.tsx
'use client'

export default function SpidersPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">爬虫管理</h1>
      <p className="text-gray-500">爬虫列表功能开发中...</p>
    </div>
  )
}
```

**Step 5: 创建 Proxies 页面（占位）**

```typescript
// admin/app/(commonLayout)/crawlhub/proxies/page.tsx
'use client'

export default function ProxiesPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">代理管理</h1>
      <p className="text-gray-500">代理列表功能开发中...</p>
    </div>
  )
}
```

**Step 6: Commit**

```bash
git add admin/app/\(commonLayout\)/crawlhub/
git commit -m "feat(crawlhub): add frontend page structure (placeholder)"
```

---

## Task 17: 创建前端 CrawlHub API Service

**Files:**
- Create: `admin/service/use-crawlhub.ts`

**Step 1: 创建 CrawlHub API Service**

```typescript
// admin/service/use-crawlhub.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, put, del } from './base'

// Types
export interface Project {
  id: string
  name: string
  description: string | null
  spider_count: number
  created_at: string
  updated_at: string
}

export interface ProjectListResponse {
  items: Project[]
  total: number
}

export interface Spider {
  id: string
  project_id: string
  name: string
  description: string | null
  script_type: 'httpx' | 'scrapy' | 'playwright'
  script_content: string | null
  is_active: boolean
  cron_expr: string | null
  created_at: string
  updated_at: string
}

export interface SpiderListResponse {
  items: Spider[]
  total: number
}

export interface Proxy {
  id: string
  host: string
  port: number
  protocol: 'http' | 'https' | 'socks5'
  username: string | null
  password: string | null
  status: 'active' | 'inactive' | 'cooldown'
  last_check_at: string | null
  success_rate: number
  fail_count: number
  created_at: string
  updated_at: string
}

export interface ProxyListResponse {
  items: Proxy[]
  total: number
}

// API Base URL
const CRAWLHUB_API = '/admin/crawlhub'

// Projects API
export function useProjects(params: { page?: number; page_size?: number; keyword?: string }) {
  return useQuery({
    queryKey: ['crawlhub', 'projects', params],
    queryFn: () => get<ProjectListResponse>(`${CRAWLHUB_API}/projects`, { params }),
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ['crawlhub', 'project', id],
    queryFn: () => get<Project>(`${CRAWLHUB_API}/projects/${id}`),
    enabled: !!id,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      post<Project>(`${CRAWLHUB_API}/projects`, { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawlhub', 'projects'] })
    },
  })
}

export function useUpdateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; description?: string } }) =>
      put<Project>(`${CRAWLHUB_API}/projects/${id}`, { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawlhub', 'projects'] })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => del(`${CRAWLHUB_API}/projects/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawlhub', 'projects'] })
    },
  })
}

// Spiders API
export function useSpiders(params: {
  page?: number
  page_size?: number
  project_id?: string
  keyword?: string
  is_active?: boolean
}) {
  return useQuery({
    queryKey: ['crawlhub', 'spiders', params],
    queryFn: () => get<SpiderListResponse>(`${CRAWLHUB_API}/spiders`, { params }),
  })
}

export function useSpider(id: string) {
  return useQuery({
    queryKey: ['crawlhub', 'spider', id],
    queryFn: () => get<Spider>(`${CRAWLHUB_API}/spiders/${id}`),
    enabled: !!id,
  })
}

export function useSpiderTemplates() {
  return useQuery({
    queryKey: ['crawlhub', 'spider-templates'],
    queryFn: () => get<Record<string, string>>(`${CRAWLHUB_API}/spiders/templates`),
  })
}

export function useCreateSpider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      project_id: string
      name: string
      description?: string
      script_type?: string
      script_content?: string
    }) => post<Spider>(`${CRAWLHUB_API}/spiders`, { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawlhub', 'spiders'] })
    },
  })
}

export function useUpdateSpider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Spider> }) =>
      put<Spider>(`${CRAWLHUB_API}/spiders/${id}`, { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawlhub', 'spiders'] })
    },
  })
}

export function useDeleteSpider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => del(`${CRAWLHUB_API}/spiders/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawlhub', 'spiders'] })
    },
  })
}

// Proxies API
export function useProxies(params: {
  page?: number
  page_size?: number
  status?: string
}) {
  return useQuery({
    queryKey: ['crawlhub', 'proxies', params],
    queryFn: () => get<ProxyListResponse>(`${CRAWLHUB_API}/proxies`, { params }),
  })
}

export function useCreateProxy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      host: string
      port: number
      protocol?: string
      username?: string
      password?: string
    }) => post<Proxy>(`${CRAWLHUB_API}/proxies`, { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawlhub', 'proxies'] })
    },
  })
}

export function useBatchCreateProxies() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (proxies: Array<{
      host: string
      port: number
      protocol?: string
      username?: string
      password?: string
    }>) => post(`${CRAWLHUB_API}/proxies/batch`, { body: { proxies } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawlhub', 'proxies'] })
    },
  })
}

export function useDeleteProxy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => del(`${CRAWLHUB_API}/proxies/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawlhub', 'proxies'] })
    },
  })
}
```

**Step 2: Commit**

```bash
git add admin/service/use-crawlhub.ts
git commit -m "feat(crawlhub): add frontend API service"
```

---

## Task 18: Phase 1 完成提交

**Step 1: 确认所有文件已提交**

Run: `git status`

Expected: 工作区干净

**Step 2: 创建 Phase 1 完成标签**

```bash
git tag -a v0.1.0-phase1 -m "CrawlHub Phase 1: 基础框架完成"
```

**Step 3: 更新设计文档**

在 `docs/plans/2026-01-25-crawlhub-design.md` 的 Phase 1 部分标记为完成。

---

## 验收清单

- [ ] 后端数据模型：Project, Spider, Task, Proxy
- [ ] 数据库迁移文件已生成
- [ ] Pydantic Schemas 已创建
- [ ] Services：ProjectService, SpiderService, ProxyService
- [ ] API Routers：/projects, /spiders, /proxies
- [ ] 前端页面目录结构已创建
- [ ] 前端 API Service 已创建
- [ ] 侧边栏菜单配置已添加

---

## 下一阶段预告

**Phase 2: 核心爬虫功能**
- Docker 基础镜像构建
- 脚本模板实现
- Celery 任务执行逻辑
- 容器生命周期管理
- 结果收集写入 MongoDB
- Monaco Editor 集成
