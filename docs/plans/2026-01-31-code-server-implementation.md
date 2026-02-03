# Code-Server 集成实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为爬虫项目提供完整的 VS Code 在线编辑体验，支持多用户并发，按需启动独立容器。

**Architecture:** 后端通过 Docker SDK 管理 code-server 容器生命周期，用户编辑时从 OpenDAL 拉取文件到容器，保存时同步回 OpenDAL。前端新窗口打开 code-server，通过 Nginx 反向代理访问。

**Tech Stack:** Docker SDK for Python (`docker`), code-server, Nginx, FastAPI, OpenDAL

---

## 阶段一：后端基础设施

### Task 1: 创建 CodeSession 数据模型

**Files:**
- Create: `app/models/crawlhub/code_session.py`
- Modify: `app/models/crawlhub/__init__.py`
- Modify: `app/models/__init__.py`

**Step 1: 创建模型文件**

```python
# app/models/crawlhub/code_session.py
import enum
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin
from models.types import EnumText, StringUUID


class CodeSessionStatus(enum.StrEnum):
    """代码编辑会话状态"""
    PENDING = "pending"
    STARTING = "starting"
    READY = "ready"
    SYNCING = "syncing"
    STOPPED = "stopped"
    FAILED = "failed"


class CodeSession(DefaultFieldsMixin, Base):
    """代码编辑会话"""

    __tablename__ = "crawlhub_code_sessions"

    spider_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    user_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    container_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Docker 容器 ID")
    port: Mapped[int] = mapped_column(Integer, nullable=False, comment="分配的端口号")
    status: Mapped[CodeSessionStatus] = mapped_column(
        EnumText(CodeSessionStatus), default=CodeSessionStatus.PENDING, comment="会话状态"
    )
    access_token: Mapped[str] = mapped_column(String(64), nullable=False, comment="访问令牌")
    last_active_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="最后活跃时间")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")

    def __repr__(self) -> str:
        return f"<CodeSession {self.id} status={self.status}>"
```

**Step 2: 更新 models/crawlhub/__init__.py**

在文件中添加导入和导出：

```python
from .code_session import CodeSession, CodeSessionStatus
```

在 `__all__` 列表中添加：

```python
"CodeSession",
"CodeSessionStatus",
```

**Step 3: 更新 models/__init__.py**

添加导入：

```python
from .crawlhub import CodeSession, CodeSessionStatus
```

**Step 4: 生成数据库迁移**

手动执行：

```bash
cd app && alembic revision --autogenerate -m "add_code_sessions"
alembic upgrade head
```

---

### Task 2: 创建 CodeSession Schema

**Files:**
- Create: `app/schemas/crawlhub/code_session.py`
- Modify: `app/schemas/crawlhub/__init__.py`

**Step 1: 创建 schema 文件**

```python
# app/schemas/crawlhub/code_session.py
from datetime import datetime

from pydantic import BaseModel

from models.crawlhub import CodeSessionStatus


class CodeSessionCreate(BaseModel):
    """创建会话请求（内部使用）"""
    spider_id: str
    user_id: str


class CodeSessionResponse(BaseModel):
    """会话响应"""
    id: str
    spider_id: str
    status: CodeSessionStatus
    url: str | None = None
    token: str | None = None
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class CodeSessionStatusResponse(BaseModel):
    """会话状态响应"""
    id: str
    status: CodeSessionStatus
    last_active_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class CodeSessionSyncResponse(BaseModel):
    """同步响应"""
    success: bool
    files_synced: int
    message: str | None = None
```

**Step 2: 更新 schemas/crawlhub/__init__.py**

添加导入和导出：

```python
from .code_session import (
    CodeSessionCreate,
    CodeSessionResponse,
    CodeSessionStatusResponse,
    CodeSessionSyncResponse,
)
```

在 `__all__` 中添加相应项。

---

### Task 3: 安装 Docker SDK 依赖

**Files:**
- Modify: `app/pyproject.toml` 或 `app/requirements.txt`

**Step 1: 添加依赖**

在项目依赖中添加：

```
docker>=7.0.0
```

**Step 2: 安装依赖**

```bash
cd app && pip install docker
```

---

### Task 4: 创建 CodeServerManager 服务

**Files:**
- Create: `app/services/crawlhub/code_server_manager.py`

**Step 1: 创建服务文件**

```python
# app/services/crawlhub/code_server_manager.py
import asyncio
import secrets
from datetime import datetime, timedelta

import docker
from docker.errors import NotFound, APIError
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub import CodeSession, CodeSessionStatus
from services.base_service import BaseService

# 配置常量
CODE_SERVER_IMAGE = "crawlhub-code-server:latest"
PORT_RANGE_START = 10000
PORT_RANGE_END = 10100
CONTAINER_CPU_LIMIT = 1.0  # 1 核
CONTAINER_MEM_LIMIT = "1g"  # 1GB
STARTUP_TIMEOUT = 30  # 秒
IDLE_TIMEOUT_MINUTES = 30
MAX_SESSION_HOURS = 4


class CodeServerManager(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self._docker_client = None

    @property
    def docker_client(self):
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client

    async def _allocate_port(self) -> int | None:
        """分配一个未使用的端口"""
        # 获取所有活跃会话使用的端口
        query = select(CodeSession.port).where(
            CodeSession.status.in_([
                CodeSessionStatus.PENDING,
                CodeSessionStatus.STARTING,
                CodeSessionStatus.READY,
                CodeSessionStatus.SYNCING,
            ])
        )
        result = await self.db.execute(query)
        used_ports = {row[0] for row in result.fetchall()}

        # 找到第一个未使用的端口
        for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
            if port not in used_ports:
                return port
        return None

    async def get_active_session(self, spider_id: str, user_id: str) -> CodeSession | None:
        """获取用户对该爬虫的活跃会话"""
        query = select(CodeSession).where(
            and_(
                CodeSession.spider_id == spider_id,
                CodeSession.user_id == user_id,
                CodeSession.status.in_([
                    CodeSessionStatus.PENDING,
                    CodeSessionStatus.STARTING,
                    CodeSessionStatus.READY,
                    CodeSessionStatus.SYNCING,
                ])
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_session(self, spider_id: str, user_id: str) -> CodeSession:
        """创建新会话"""
        # 检查是否已有活跃会话
        existing = await self.get_active_session(spider_id, user_id)
        if existing:
            return existing

        # 分配端口
        port = await self._allocate_port()
        if port is None:
            raise RuntimeError("没有可用端口，请稍后重试")

        # 生成访问令牌
        access_token = secrets.token_urlsafe(32)

        # 创建会话记录
        now = datetime.utcnow()
        session = CodeSession(
            spider_id=spider_id,
            user_id=user_id,
            port=port,
            status=CodeSessionStatus.PENDING,
            access_token=access_token,
            last_active_at=now,
            expires_at=now + timedelta(hours=MAX_SESSION_HOURS),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def start_container(self, session: CodeSession) -> str:
        """启动 code-server 容器，返回容器 ID"""
        session.status = CodeSessionStatus.STARTING
        await self.db.commit()

        try:
            # 在线程池中运行 Docker 操作（阻塞操作）
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                self._create_container,
                session.port,
                session.access_token,
                str(session.id),
            )

            session.container_id = container.id
            await self.db.commit()

            # 启动容器
            await loop.run_in_executor(None, container.start)

            # 等待容器就绪
            ready = await self._wait_for_ready(container.id)
            if not ready:
                raise RuntimeError("容器启动超时")

            session.status = CodeSessionStatus.READY
            await self.db.commit()

            return container.id

        except Exception as e:
            session.status = CodeSessionStatus.FAILED
            await self.db.commit()
            raise e

    def _create_container(self, port: int, password: str, session_id: str):
        """创建 Docker 容器（同步方法）"""
        return self.docker_client.containers.create(
            image=CODE_SERVER_IMAGE,
            name=f"code-server-{session_id}",
            environment={
                "PASSWORD": password,
            },
            ports={"8080/tcp": port},
            cpu_quota=int(CONTAINER_CPU_LIMIT * 100000),
            mem_limit=CONTAINER_MEM_LIMIT,
            detach=True,
            labels={
                "crawlhub.session_id": session_id,
                "crawlhub.type": "code-server",
            },
        )

    async def _wait_for_ready(self, container_id: str, timeout: int = STARTUP_TIMEOUT) -> bool:
        """等待容器就绪"""
        loop = asyncio.get_event_loop()
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                container = await loop.run_in_executor(
                    None,
                    self.docker_client.containers.get,
                    container_id,
                )
                if container.status == "running":
                    # 检查健康状态或端口
                    return True
            except NotFound:
                pass
            await asyncio.sleep(1)

        return False

    async def stop_container(self, session: CodeSession) -> None:
        """停止并删除容器"""
        if not session.container_id:
            return

        loop = asyncio.get_event_loop()

        try:
            container = await loop.run_in_executor(
                None,
                self.docker_client.containers.get,
                session.container_id,
            )
            await loop.run_in_executor(None, container.stop, 10)  # 10秒超时
            await loop.run_in_executor(None, container.remove)
        except NotFound:
            pass  # 容器已不存在
        except APIError as e:
            print(f"停止容器失败: {e}")

        session.status = CodeSessionStatus.STOPPED
        session.container_id = None
        await self.db.commit()

    async def update_heartbeat(self, session_id: str) -> bool:
        """更新心跳时间"""
        query = select(CodeSession).where(CodeSession.id == session_id)
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()

        if not session or session.status != CodeSessionStatus.READY:
            return False

        session.last_active_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def get_expired_sessions(self) -> list[CodeSession]:
        """获取过期的会话"""
        now = datetime.utcnow()
        idle_threshold = now - timedelta(minutes=IDLE_TIMEOUT_MINUTES)

        query = select(CodeSession).where(
            and_(
                CodeSession.status.in_([
                    CodeSessionStatus.READY,
                    CodeSessionStatus.STARTING,
                ]),
                or_(
                    CodeSession.last_active_at < idle_threshold,
                    CodeSession.expires_at < now,
                )
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
```

---

### Task 5: 扩展 SpiderFileService 支持容器文件同步

**Files:**
- Modify: `app/services/crawlhub/spider_file_service.py`

**Step 1: 添加容器同步方法**

在 `SpiderFileService` 类中添加以下方法：

```python
import io
import tarfile

import docker

async def pull_to_container(self, spider_id: str, container_id: str, work_dir: str = "/workspace") -> int:
    """
    将文件从 OpenDAL 拉取到容器
    返回同步的文件数量
    """
    files = await self.get_files(spider_id)
    if not files:
        return 0

    client = docker.from_env()
    container = client.containers.get(container_id)

    # 创建 tar 包
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        for file in files:
            content = await storage.load_once(file.storage_key)
            file_info = tarfile.TarInfo(name=file.file_path)
            file_info.size = len(content)
            tar.addfile(file_info, io.BytesIO(content))

    tar_buffer.seek(0)

    # 上传到容器
    container.put_archive(work_dir, tar_buffer.getvalue())

    return len(files)


async def sync_from_container(self, spider_id: str, container_id: str, work_dir: str = "/workspace") -> int:
    """
    将文件从容器同步回 OpenDAL
    返回同步的文件数量
    """
    client = docker.from_env()
    container = client.containers.get(container_id)

    # 从容器获取 tar 包
    bits, _ = container.get_archive(work_dir)
    tar_buffer = io.BytesIO()
    for chunk in bits:
        tar_buffer.write(chunk)
    tar_buffer.seek(0)

    # 解析 tar 包
    new_files: dict[str, bytes] = {}
    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        for member in tar.getmembers():
            if member.isdir():
                continue

            # 移除 work_dir 前缀（tar 中的路径通常是 workspace/xxx）
            file_path = member.name
            if file_path.startswith("workspace/"):
                file_path = file_path[len("workspace/"):]

            # 检查是否应该忽略
            parts = Path(file_path).parts
            if any(should_ignore(part) for part in parts):
                continue

            # 读取文件内容
            f = tar.extractfile(member)
            if f:
                new_files[file_path] = f.read()

    # 获取现有文件
    existing_files = await self.get_files(spider_id)
    existing_paths = {f.file_path: f for f in existing_files}

    synced_count = 0

    # 处理新增和修改的文件
    for file_path, content in new_files.items():
        if file_path in existing_paths:
            # 更新现有文件
            existing_file = existing_paths[file_path]
            await storage.save(existing_file.storage_key, content)
            existing_file.file_size = len(content)
            synced_count += 1
        else:
            # 创建新文件
            await self.create_file(spider_id, file_path, content)
            synced_count += 1

    # 删除容器中不存在的文件
    for file_path, existing_file in existing_paths.items():
        if file_path not in new_files:
            await self.delete_file(existing_file.id)

    await self.db.commit()
    return synced_count
```

**Step 2: 添加必要的导入**

在文件顶部添加：

```python
import io
import tarfile

import docker
```

---

### Task 6: 创建 CodeSession API 路由

**Files:**
- Create: `app/routers/admin/crawlhub/code_sessions.py`
- Modify: `app/routers/admin/crawlhub/__init__.py`

**Step 1: 创建路由文件**

```python
# app/routers/admin/crawlhub/code_sessions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub import CodeSessionStatus
from models.engine import get_db
from schemas.crawlhub import (
    CodeSessionResponse,
    CodeSessionStatusResponse,
    CodeSessionSyncResponse,
)
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub import SpiderService, SpiderFileService
from services.crawlhub.code_server_manager import CodeServerManager

router = APIRouter(prefix="/spiders/{spider_id}/code-session", tags=["CrawlHub - Code Sessions"])

# TODO: 从认证中间件获取真实用户 ID
MOCK_USER_ID = "00000000-0000-0000-0000-000000000001"


def get_code_server_url(session_id: str, port: int) -> str:
    """生成 code-server 访问 URL"""
    # 生产环境应使用配置的域名
    return f"/code-server/{session_id}/"


@router.post("", response_model=ApiResponse[CodeSessionResponse])
async def create_or_get_session(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """创建或获取代码编辑会话"""
    # 验证爬虫存在
    spider_service = SpiderService(db)
    spider = await spider_service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    manager = CodeServerManager(db)

    # 创建或获取会话
    session = await manager.create_session(spider_id, MOCK_USER_ID)

    # 如果是新会话，启动容器
    if session.status == CodeSessionStatus.PENDING:
        try:
            await manager.start_container(session)

            # 同步文件到容器
            file_service = SpiderFileService(db)
            await file_service.pull_to_container(spider_id, session.container_id)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"启动编辑器失败: {str(e)}")

    url = get_code_server_url(str(session.id), session.port)

    return ApiResponse(data=CodeSessionResponse(
        id=str(session.id),
        spider_id=session.spider_id,
        status=session.status,
        url=url,
        token=session.access_token,
        created_at=session.created_at,
        expires_at=session.expires_at,
    ))


@router.get("", response_model=ApiResponse[CodeSessionStatusResponse])
async def get_session_status(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取当前会话状态"""
    manager = CodeServerManager(db)
    session = await manager.get_active_session(spider_id, MOCK_USER_ID)

    if not session:
        raise HTTPException(status_code=404, detail="没有活跃的编辑会话")

    return ApiResponse(data=CodeSessionStatusResponse(
        id=str(session.id),
        status=session.status,
        last_active_at=session.last_active_at,
        expires_at=session.expires_at,
    ))


@router.post("/sync", response_model=ApiResponse[CodeSessionSyncResponse])
async def sync_files(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """同步文件到服务器"""
    manager = CodeServerManager(db)
    session = await manager.get_active_session(spider_id, MOCK_USER_ID)

    if not session:
        raise HTTPException(status_code=404, detail="没有活跃的编辑会话")

    if session.status != CodeSessionStatus.READY:
        raise HTTPException(status_code=400, detail="会话未就绪")

    if not session.container_id:
        raise HTTPException(status_code=400, detail="容器不存在")

    # 更新状态
    session.status = CodeSessionStatus.SYNCING
    await db.commit()

    try:
        file_service = SpiderFileService(db)
        count = await file_service.sync_from_container(spider_id, session.container_id)

        session.status = CodeSessionStatus.READY
        await db.commit()

        return ApiResponse(data=CodeSessionSyncResponse(
            success=True,
            files_synced=count,
            message=f"成功同步 {count} 个文件",
        ))
    except Exception as e:
        session.status = CodeSessionStatus.READY
        await db.commit()
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.delete("", response_model=MessageResponse)
async def close_session(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """关闭编辑会话"""
    manager = CodeServerManager(db)
    session = await manager.get_active_session(spider_id, MOCK_USER_ID)

    if not session:
        raise HTTPException(status_code=404, detail="没有活跃的编辑会话")

    # 先同步文件
    if session.container_id and session.status == CodeSessionStatus.READY:
        try:
            file_service = SpiderFileService(db)
            await file_service.sync_from_container(spider_id, session.container_id)
        except Exception:
            pass  # 同步失败也继续关闭

    # 停止容器
    await manager.stop_container(session)

    return MessageResponse(msg="编辑会话已关闭")


@router.post("/heartbeat", response_model=MessageResponse)
async def heartbeat(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """心跳保活"""
    manager = CodeServerManager(db)
    session = await manager.get_active_session(spider_id, MOCK_USER_ID)

    if not session:
        raise HTTPException(status_code=404, detail="没有活跃的编辑会话")

    success = await manager.update_heartbeat(str(session.id))
    if not success:
        raise HTTPException(status_code=400, detail="更新心跳失败")

    return MessageResponse(msg="ok")
```

**Step 2: 更新路由 __init__.py**

在 `app/routers/admin/crawlhub/__init__.py` 中添加：

```python
from .code_sessions import router as code_sessions_router

router.include_router(code_sessions_router)
```

---

### Task 7: 更新 services/crawlhub/__init__.py

**Files:**
- Modify: `app/services/crawlhub/__init__.py`

**Step 1: 添加导出**

```python
from .code_server_manager import CodeServerManager

# 在 __all__ 中添加
"CodeServerManager",
```

---

## 阶段二：Docker 镜像与 Nginx 配置

### Task 8: 创建 code-server Docker 镜像

**Files:**
- Create: `docker/code-server/Dockerfile`
- Create: `docker/code-server/settings.json`

**Step 1: 创建 Dockerfile**

```dockerfile
# docker/code-server/Dockerfile
FROM codercom/code-server:latest

USER root

# 安装 Python
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nodejs \
    npm \
    git \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python 默认版本
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# 安装常用爬虫依赖
RUN pip3 install --no-cache-dir \
    scrapy \
    httpx \
    playwright \
    beautifulsoup4 \
    lxml \
    requests \
    aiohttp \
    parsel \
    fake-useragent

# 安装 Playwright 浏览器
RUN playwright install chromium

# 安装 pnpm
RUN npm install -g pnpm

# 安装 VS Code 扩展
RUN code-server --install-extension ms-python.python \
    && code-server --install-extension ms-python.vscode-pylance \
    && code-server --install-extension dbaeumer.vscode-eslint \
    && code-server --install-extension esbenp.prettier-vscode

# 复制默认设置
COPY settings.json /root/.local/share/code-server/User/settings.json

# 工作目录
WORKDIR /workspace

USER coder

EXPOSE 8080

ENTRYPOINT ["code-server", "--bind-addr", "0.0.0.0:8080", "--auth", "password", "/workspace"]
```

**Step 2: 创建 VS Code 默认设置**

```json
// docker/code-server/settings.json
{
    "python.defaultInterpreterPath": "/usr/bin/python3",
    "python.languageServer": "Pylance",
    "editor.fontSize": 14,
    "editor.tabSize": 4,
    "editor.formatOnSave": true,
    "files.autoSave": "afterDelay",
    "files.autoSaveDelay": 1000,
    "workbench.colorTheme": "Default Dark+"
}
```

**Step 3: 构建镜像**

```bash
cd docker/code-server
docker build -t crawlhub-code-server:latest .
```

---

### Task 9: 配置 Nginx 反向代理

**Files:**
- Modify: `docker/nginx/fastapi.conf`
- Create: `docker/nginx/code-server.conf`

**Step 1: 创建 code-server 代理配置**

```nginx
# docker/nginx/code-server.conf
# code-server 会话代理
# 需要配合后端 API 获取 session_id -> port 的映射

map $uri $code_server_port {
    default "";
    # 动态映射将通过 Lua 或外部服务实现
    # 此处为简化版本，生产环境建议使用 OpenResty + Lua
}

location ~ ^/code-server/([a-f0-9-]+)/(.*)$ {
    set $session_id $1;
    set $path $2;

    # 从后端 API 获取端口映射（简化：直接使用静态端口范围）
    # 生产环境应通过 Lua 脚本或 auth_request 动态获取

    # 临时方案：使用 X-Code-Server-Port header
    # 需要前端在请求时携带端口信息

    proxy_pass http://host.docker.internal:$http_x_code_server_port/$path$is_args$args;

    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Accept-Encoding gzip;

    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
    proxy_buffering off;
}
```

**Step 2: 更新 fastapi.conf**

在 `server` 块中添加 include：

```nginx
include code-server.conf;
```

---

### Task 10: 更新 docker-compose.yaml

**Files:**
- Modify: `docker/docker-compose.yaml`

**Step 1: 添加 code-server 构建配置**

在 `services` 部分添加网络和端口映射配置说明：

```yaml
# 注意：code-server 容器由后端动态创建，不在 compose 中定义
# 需要确保以下配置：
# 1. 端口范围 10000-10100 在宿主机上可用
# 2. Docker socket 挂载到 app 容器（如果后端在容器中运行）
```

在 `app` 服务中添加 Docker socket 挂载（如果 app 在容器中运行）：

```yaml
services:
  app:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

---

## 阶段三：前端集成

### Task 11: 添加前端 API hooks

**Files:**
- Modify: `admin/service/use-crawlhub.ts`

**Step 1: 添加 code session 相关 hooks**

```typescript
// 添加类型
export interface CodeSession {
  id: string
  spider_id: string
  status: 'pending' | 'starting' | 'ready' | 'syncing' | 'stopped' | 'failed'
  url: string | null
  token: string | null
  created_at: string
  expires_at: string
}

export interface CodeSessionStatus {
  id: string
  status: CodeSession['status']
  last_active_at: string
  expires_at: string
}

export interface CodeSessionSyncResult {
  success: boolean
  files_synced: number
  message: string | null
}

// 创建或获取会话
export const useCreateCodeSession = () => {
  return useMutation({
    mutationFn: async (spiderId: string) => {
      const res = await post<{ data: CodeSession }>(`/crawlhub/spiders/${spiderId}/code-session`)
      return res.data
    },
  })
}

// 获取会话状态
export const useCodeSessionStatus = (spiderId: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: ['code-session', spiderId],
    queryFn: async () => {
      const res = await get<{ data: CodeSessionStatus }>(`/crawlhub/spiders/${spiderId}/code-session`)
      return res.data
    },
    enabled,
    refetchInterval: 30000, // 每 30 秒刷新
  })
}

// 同步文件
export const useSyncCodeSession = () => {
  return useMutation({
    mutationFn: async (spiderId: string) => {
      const res = await post<{ data: CodeSessionSyncResult }>(`/crawlhub/spiders/${spiderId}/code-session/sync`)
      return res.data
    },
  })
}

// 关闭会话
export const useCloseCodeSession = () => {
  return useMutation({
    mutationFn: async (spiderId: string) => {
      await del(`/crawlhub/spiders/${spiderId}/code-session`)
    },
  })
}

// 心跳
export const useSendHeartbeat = () => {
  return useMutation({
    mutationFn: async (spiderId: string) => {
      await post(`/crawlhub/spiders/${spiderId}/code-session/heartbeat`)
    },
  })
}
```

---

### Task 12: 更新前端类型定义

**Files:**
- Modify: `admin/types/crawlhub.ts`

**Step 1: 添加 CodeSession 类型**

```typescript
export type CodeSessionStatus = 'pending' | 'starting' | 'ready' | 'syncing' | 'stopped' | 'failed'

export interface CodeSession {
  id: string
  spider_id: string
  status: CodeSessionStatus
  url: string | null
  token: string | null
  created_at: string
  expires_at: string
}
```

---

### Task 13: 更新爬虫列表页操作按钮

**Files:**
- Modify: `admin/app/(commonLayout)/crawlhub/spiders/page.tsx`

**Step 1: 更新 "编辑代码" 按钮逻辑**

将现有的 `RiCodeSSlashLine` 按钮的 `onClick` 处理改为：

```typescript
import { useCreateCodeSession } from '@/service/use-crawlhub'

// 在组件中
const createCodeSessionMutation = useCreateCodeSession()

const handleOpenCodeEditor = async (spider: Spider) => {
  try {
    const session = await createCodeSessionMutation.mutateAsync(spider.id)
    if (session.url && session.token) {
      // 新窗口打开，带上 token 参数
      window.open(`${session.url}?tkn=${session.token}`, '_blank')
    } else {
      Toast.notify({ type: 'error', message: '获取编辑器地址失败' })
    }
  } catch {
    Toast.notify({ type: 'error', message: '启动编辑器失败' })
  }
}

// 在 actions 数组中更新
{
  icon: RiCodeSSlashLine,
  label: '在线编辑',
  onClick: (row) => handleOpenCodeEditor(row),
},
```

---

### Task 14: 创建会话清理定时任务

**Files:**
- Create: `app/tasks/cleanup_code_sessions.py`
- Modify: `app/tasks/__init__.py` (如果存在)

**Step 1: 创建清理任务**

```python
# app/tasks/cleanup_code_sessions.py
from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from configs import dify_config
from models.crawlhub import CodeSessionStatus
from services.crawlhub import SpiderFileService
from services.crawlhub.code_server_manager import CodeServerManager


@shared_task(name="cleanup_expired_code_sessions")
def cleanup_expired_code_sessions():
    """清理过期的代码编辑会话"""
    from models.engine import get_sync_db

    with get_sync_db() as db:
        # 注意：需要将异步服务改为同步版本，或使用同步 wrapper
        # 此处为伪代码，实际实现需要根据项目的 Celery 配置调整

        manager = CodeServerManager(db)

        # 获取过期会话
        # 由于 Celery 任务是同步的，需要使用同步版本的数据库操作
        # 或者使用 asyncio.run() 包装异步调用

        import asyncio

        async def cleanup():
            sessions = await manager.get_expired_sessions()
            for session in sessions:
                if session.container_id and session.status == CodeSessionStatus.READY:
                    try:
                        file_service = SpiderFileService(db)
                        await file_service.sync_from_container(
                            session.spider_id,
                            session.container_id
                        )
                    except Exception as e:
                        print(f"同步失败: {e}")

                await manager.stop_container(session)
                print(f"已清理会话: {session.id}")

        asyncio.run(cleanup())
```

**Step 2: 注册定时任务**

在 Celery beat 配置中添加：

```python
CELERY_BEAT_SCHEDULE = {
    'cleanup-code-sessions': {
        'task': 'cleanup_expired_code_sessions',
        'schedule': 300.0,  # 每 5 分钟
    },
}
```

---

## 阶段四：测试与完善

### Task 15: 端到端测试

**Step 1: 手动测试流程**

1. 创建一个爬虫，上传一些测试文件
2. 点击"在线编辑"按钮
3. 确认新窗口打开 code-server
4. 在 code-server 中编辑文件
5. 调用同步 API 或关闭会话
6. 确认文件已同步回 OpenDAL

**Step 2: 检查清理任务**

1. 创建会话但不发送心跳
2. 等待 30 分钟或手动触发清理任务
3. 确认容器已被销毁

---

## 实现检查清单

- [ ] Task 1: CodeSession 数据模型
- [ ] Task 2: CodeSession Schema
- [ ] Task 3: Docker SDK 依赖
- [ ] Task 4: CodeServerManager 服务
- [ ] Task 5: SpiderFileService 容器同步
- [ ] Task 6: CodeSession API 路由
- [ ] Task 7: 更新 services 导出
- [ ] Task 8: code-server Docker 镜像
- [ ] Task 9: Nginx 反向代理配置
- [ ] Task 10: docker-compose 配置
- [ ] Task 11: 前端 API hooks
- [ ] Task 12: 前端类型定义
- [ ] Task 13: 爬虫列表页按钮
- [ ] Task 14: 会话清理定时任务
- [ ] Task 15: 端到端测试
