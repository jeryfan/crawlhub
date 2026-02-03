# Spider 多文件管理与在线编辑 - 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现爬虫的多文件上传、在线编辑和测试运行功能

**Architecture:** 新增 SpiderFile 模型存储文件元数据，文件内容存入 OpenDal 对象存储。前端新增独立编辑器页面，集成 Monaco Editor 和文件树组件。测试运行通过 SSE 实时返回输出。

**Tech Stack:** FastAPI + SQLAlchemy (后端), Next.js + Monaco Editor + React Query (前端), OpenDal (存储), Docker (沙箱执行)

---

## 阶段一：后端数据模型与基础 API

### Task 1: 新增 SpiderFile 模型

**Files:**
- Create: `app/models/crawlhub/spider_file.py`
- Modify: `app/models/crawlhub/__init__.py`
- Modify: `app/models/__init__.py`

**Step 1: 创建 SpiderFile 模型文件**

```python
# app/models/crawlhub/spider_file.py
import enum

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, DefaultFieldsMixin
from models.types import StringUUID


class SpiderFile(DefaultFieldsMixin, Base):
    """爬虫项目文件"""

    __tablename__ = "crawlhub_spider_files"

    spider_id: Mapped[str] = mapped_column(
        StringUUID, ForeignKey("crawlhub_spiders.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件相对路径")
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, comment="存储Key")
    file_size: Mapped[int] = mapped_column(Integer, default=0, comment="文件大小(字节)")
    content_type: Mapped[str] = mapped_column(String(100), default="text/plain", comment="MIME类型")

    # Relationships
    spider: Mapped["Spider"] = relationship("Spider", back_populates="files")

    def __repr__(self) -> str:
        return f"<SpiderFile {self.file_path}>"
```

**Step 2: 更新 models/crawlhub/__init__.py**

在 `app/models/crawlhub/__init__.py` 添加导出:

```python
from .spider_file import SpiderFile
```

并在 `__all__` 中添加 `"SpiderFile"`。

**Step 3: 更新 models/__init__.py**

在 `app/models/__init__.py` 的 CrawlHub models 部分添加:

```python
from .crawlhub import SpiderFile
```

**Step 4: 提交**

```bash
git add app/models/crawlhub/spider_file.py app/models/crawlhub/__init__.py app/models/__init__.py
git commit -m "feat(crawlhub): add SpiderFile model for multi-file spider projects"
```

---

### Task 2: 修改 Spider 模型

**Files:**
- Modify: `app/models/crawlhub/spider.py`

**Step 1: 添加新字段和关系**

在 `app/models/crawlhub/spider.py` 中:

1. 添加 `ProjectType` 枚举:

```python
class ProjectType(str, enum.Enum):
    """项目类型"""
    SINGLE_FILE = "single_file"
    MULTI_FILE = "multi_file"
```

2. 在 Spider 类中添加字段（在 `cron_expr` 之后）:

```python
    project_type: Mapped[ProjectType] = mapped_column(
        Enum(ProjectType), default=ProjectType.SINGLE_FILE, comment="项目类型"
    )
    entry_point: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="入口点")
```

3. 添加 files 关系（在 tasks 关系之后）:

```python
    files: Mapped[list["SpiderFile"]] = relationship(
        "SpiderFile", back_populates="spider", cascade="all, delete-orphan"
    )
```

4. 在文件顶部添加导入 `Enum`。

**Step 2: 更新 crawlhub/__init__.py 导出 ProjectType**

```python
from .spider import Spider, ScriptType, ProjectType
```

并在 `__all__` 中添加 `"ProjectType"`。

**Step 3: 提交**

```bash
git add app/models/crawlhub/spider.py app/models/crawlhub/__init__.py
git commit -m "feat(crawlhub): add project_type and entry_point fields to Spider model"
```

---

### Task 3: 修改 SpiderTask 模型

**Files:**
- Modify: `app/models/crawlhub/task.py`

**Step 1: 添加 is_test 字段**

在 `app/models/crawlhub/task.py` 的 SpiderTask 类中，在 `error_message` 字段之后添加:

```python
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为测试运行")
```

同时在文件顶部的 sqlalchemy 导入中添加 `Boolean`。

**Step 2: 提交**

```bash
git add app/models/crawlhub/task.py
git commit -m "feat(crawlhub): add is_test field to SpiderTask model"
```

---

### Task 4: 创建数据库迁移

**Files:**
- Create: `app/alembic/versions/xxxxx_spider_files.py`

**Step 1: 生成迁移文件**

运行命令:

```bash
cd app && uv run alembic revision --autogenerate -m "spider_files"
```

**Step 2: 检查生成的迁移文件**

确保迁移文件包含:
- 创建 `crawlhub_spider_files` 表
- 为 `crawlhub_spiders` 添加 `project_type` 和 `entry_point` 列
- 为 `crawlhub_tasks` 添加 `is_test` 列
- 创建 `projecttype` 枚举类型

**Step 3: 提交**

```bash
git add app/alembic/versions/
git commit -m "chore(crawlhub): add migration for spider files"
```

---

### Task 5: 新增 SpiderFile Schema

**Files:**
- Create: `app/schemas/crawlhub/spider_file.py`
- Modify: `app/schemas/crawlhub/__init__.py`

**Step 1: 创建 spider_file.py**

```python
# app/schemas/crawlhub/spider_file.py
from datetime import datetime

from pydantic import BaseModel, Field


class SpiderFileBase(BaseModel):
    file_path: str = Field(..., min_length=1, max_length=500, description="文件相对路径")


class SpiderFileCreate(SpiderFileBase):
    pass


class SpiderFileResponse(SpiderFileBase):
    id: str
    spider_id: str
    storage_key: str
    file_size: int
    content_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SpiderFileListResponse(BaseModel):
    items: list[SpiderFileResponse]
    total: int


class SpiderFileContentResponse(BaseModel):
    id: str
    file_path: str
    content: str
    content_type: str


class SpiderFileUpdateContent(BaseModel):
    content: str = Field(..., description="文件内容")


class SpiderFileTreeNode(BaseModel):
    """文件树节点"""
    id: str | None = None  # 目录节点没有 id
    name: str
    path: str
    is_dir: bool
    children: list["SpiderFileTreeNode"] = []
    file_size: int | None = None


SpiderFileTreeNode.model_rebuild()
```

**Step 2: 更新 schemas/crawlhub/__init__.py**

添加导入和导出:

```python
from .spider_file import (
    SpiderFileCreate,
    SpiderFileResponse,
    SpiderFileListResponse,
    SpiderFileContentResponse,
    SpiderFileUpdateContent,
    SpiderFileTreeNode,
)
```

并在 `__all__` 中添加这些类名。

**Step 3: 提交**

```bash
git add app/schemas/crawlhub/spider_file.py app/schemas/crawlhub/__init__.py
git commit -m "feat(crawlhub): add SpiderFile schemas"
```

---

### Task 6: 更新 Spider Schema

**Files:**
- Modify: `app/schemas/crawlhub/spider.py`

**Step 1: 更新导入和添加字段**

1. 更新导入:

```python
from models.crawlhub import ScriptType, ProjectType
```

2. 在 `SpiderBase` 中添加字段（在 `cron_expr` 之后）:

```python
    project_type: ProjectType = Field(default=ProjectType.SINGLE_FILE, description="项目类型")
    entry_point: str | None = Field(None, description="入口点")
```

3. 在 `SpiderUpdate` 中添加:

```python
    project_type: ProjectType | None = None
    entry_point: str | None = None
```

4. 移除 `SpiderBase` 和 `SpiderUpdate` 中的 `script_content` 字段（如果需要兼容，可以保留但标记为 deprecated）。

**Step 2: 提交**

```bash
git add app/schemas/crawlhub/spider.py
git commit -m "feat(crawlhub): update Spider schema with project_type and entry_point"
```

---

### Task 7: 创建 SpiderFileService

**Files:**
- Create: `app/services/crawlhub/spider_file_service.py`
- Modify: `app/services/crawlhub/__init__.py`

**Step 1: 创建服务文件**

```python
# app/services/crawlhub/spider_file_service.py
import io
import os
import re
import tempfile
import uuid
import zipfile
from pathlib import Path

from sqlalchemy import func, select

from extensions.ext_storage import storage
from models.crawlhub import Spider, SpiderFile
from schemas.crawlhub import SpiderFileCreate, SpiderFileTreeNode
from services.base_service import BaseService

# 文件大小限制
MAX_SINGLE_FILE_SIZE = 1 * 1024 * 1024  # 1MB
MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILE_COUNT = 200

# 忽略的文件和目录
IGNORED_PATTERNS = [
    r"^__pycache__$",
    r"^\.git$",
    r"^\.venv$",
    r"^venv$",
    r"^env$",
    r"^node_modules$",
    r"\.pyc$",
    r"\.pyo$",
    r"^\.DS_Store$",
    r"^Thumbs\.db$",
]


def should_ignore(name: str) -> bool:
    """检查文件或目录是否应该被忽略"""
    for pattern in IGNORED_PATTERNS:
        if re.match(pattern, name):
            return True
    return False


def get_content_type(file_path: str) -> str:
    """根据文件扩展名获取 MIME 类型"""
    ext = Path(file_path).suffix.lower()
    content_types = {
        ".py": "text/x-python",
        ".txt": "text/plain",
        ".json": "application/json",
        ".yaml": "application/x-yaml",
        ".yml": "application/x-yaml",
        ".md": "text/markdown",
        ".cfg": "text/plain",
        ".ini": "text/plain",
        ".toml": "application/toml",
    }
    return content_types.get(ext, "text/plain")


class SpiderFileService(BaseService):
    async def get_files(self, spider_id: str) -> list[SpiderFile]:
        """获取爬虫的所有文件"""
        query = select(SpiderFile).where(SpiderFile.spider_id == spider_id)
        query = query.order_by(SpiderFile.file_path)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_file_by_id(self, file_id: str) -> SpiderFile | None:
        """根据 ID 获取文件"""
        query = select(SpiderFile).where(SpiderFile.id == file_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_file_content(self, file_id: str) -> tuple[SpiderFile, str] | None:
        """获取文件内容"""
        file = await self.get_file_by_id(file_id)
        if not file:
            return None

        content_bytes = await storage.load_once(file.storage_key)
        content = content_bytes.decode("utf-8")
        return file, content

    async def create_file(
        self,
        spider_id: str,
        file_path: str,
        content: bytes,
    ) -> SpiderFile:
        """创建单个文件"""
        # 生成存储 key
        file_uuid = str(uuid.uuid4())
        ext = Path(file_path).suffix or ".py"
        storage_key = f"spider_files/{spider_id}/{file_uuid}{ext}"

        # 保存到存储
        await storage.save(storage_key, content)

        # 创建数据库记录
        spider_file = SpiderFile(
            spider_id=spider_id,
            file_path=file_path,
            storage_key=storage_key,
            file_size=len(content),
            content_type=get_content_type(file_path),
        )
        self.db.add(spider_file)
        await self.db.commit()
        await self.db.refresh(spider_file)
        return spider_file

    async def update_file_content(self, file_id: str, content: str) -> SpiderFile | None:
        """更新文件内容"""
        file = await self.get_file_by_id(file_id)
        if not file:
            return None

        content_bytes = content.encode("utf-8")

        # 更新存储
        await storage.save(file.storage_key, content_bytes)

        # 更新文件大小
        file.file_size = len(content_bytes)
        await self.db.commit()
        await self.db.refresh(file)
        return file

    async def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        file = await self.get_file_by_id(file_id)
        if not file:
            return False

        # 删除存储中的文件
        try:
            await storage.delete(file.storage_key)
        except Exception:
            pass  # 存储中不存在也继续删除数据库记录

        await self.db.delete(file)
        await self.db.commit()
        return True

    async def delete_all_files(self, spider_id: str) -> int:
        """删除爬虫的所有文件"""
        files = await self.get_files(spider_id)
        count = 0
        for file in files:
            try:
                await storage.delete(file.storage_key)
            except Exception:
                pass
            await self.db.delete(file)
            count += 1
        await self.db.commit()
        return count

    async def upload_zip(self, spider_id: str, zip_content: bytes) -> tuple[list[SpiderFile], str | None]:
        """
        上传 ZIP 文件并解压
        返回: (创建的文件列表, 错误信息)
        """
        # 先删除现有文件
        await self.delete_all_files(spider_id)

        created_files = []
        total_size = 0
        file_count = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "upload.zip"
            zip_path.write_bytes(zip_content)

            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    # 获取所有文件
                    for info in zf.infolist():
                        if info.is_dir():
                            continue

                        # 规范化路径
                        file_path = info.filename
                        parts = Path(file_path).parts

                        # 检查是否应该忽略
                        if any(should_ignore(part) for part in parts):
                            continue

                        # 检查文件大小
                        if info.file_size > MAX_SINGLE_FILE_SIZE:
                            return [], f"文件 {file_path} 超过大小限制 (最大 1MB)"

                        total_size += info.file_size
                        if total_size > MAX_TOTAL_SIZE:
                            return [], f"解压后总大小超过限制 (最大 50MB)"

                        file_count += 1
                        if file_count > MAX_FILE_COUNT:
                            return [], f"文件数量超过限制 (最大 {MAX_FILE_COUNT} 个)"

                        # 读取并保存文件
                        content = zf.read(info.filename)
                        spider_file = await self.create_file(spider_id, file_path, content)
                        created_files.append(spider_file)

            except zipfile.BadZipFile:
                return [], "无效的 ZIP 文件"

        return created_files, None

    def build_file_tree(self, files: list[SpiderFile]) -> list[SpiderFileTreeNode]:
        """构建文件树"""
        root: dict = {}

        for file in files:
            parts = Path(file.file_path).parts
            current = root

            # 构建目录结构
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {"__is_dir__": True, "__children__": {}}
                current = current[part]["__children__"]

            # 添加文件
            filename = parts[-1]
            current[filename] = {
                "__is_dir__": False,
                "__file__": file,
            }

        def build_nodes(tree: dict, path_prefix: str = "") -> list[SpiderFileTreeNode]:
            nodes = []
            for name, value in sorted(tree.items()):
                if name.startswith("__"):
                    continue

                current_path = f"{path_prefix}/{name}" if path_prefix else name

                if value.get("__is_dir__"):
                    nodes.append(SpiderFileTreeNode(
                        id=None,
                        name=name,
                        path=current_path,
                        is_dir=True,
                        children=build_nodes(value["__children__"], current_path),
                    ))
                else:
                    file = value["__file__"]
                    nodes.append(SpiderFileTreeNode(
                        id=file.id,
                        name=name,
                        path=current_path,
                        is_dir=False,
                        file_size=file.file_size,
                    ))

            # 目录排在前面
            return sorted(nodes, key=lambda n: (not n.is_dir, n.name.lower()))

        return build_nodes(root)

    async def validate_project_structure(self, spider_id: str, script_type: str) -> tuple[bool, str | None, str | None]:
        """
        验证项目结构
        返回: (是否有效, 错误信息, 检测到的入口点)
        """
        files = await self.get_files(spider_id)
        file_paths = {f.file_path for f in files}

        # Scrapy 项目检测
        if "scrapy.cfg" in file_paths:
            return True, None, "scrapy"

        # 检查 settings.py 中是否有 BOT_NAME
        for f in files:
            if f.file_path.endswith("settings.py"):
                _, content = await self.get_file_content(f.id)
                if "BOT_NAME" in content:
                    return True, None, "scrapy"

        # 普通项目检测 - 必须有 main.py
        main_file = None
        for f in files:
            if f.file_path == "main.py" or f.file_path.endswith("/main.py"):
                main_file = f
                break

        if not main_file:
            return False, "普通项目必须包含 main.py 文件", None

        # 检查 main.py 中是否有 run 函数
        _, content = await self.get_file_content(main_file.id)
        if "def run(" not in content and "async def run(" not in content:
            return False, "main.py 必须定义 run() 函数作为入口", None

        return True, None, "main.py:run"
```

**Step 2: 更新 services/crawlhub/__init__.py**

```python
from .spider_file_service import SpiderFileService
```

并在 `__all__` 中添加 `"SpiderFileService"`。

**Step 3: 提交**

```bash
git add app/services/crawlhub/spider_file_service.py app/services/crawlhub/__init__.py
git commit -m "feat(crawlhub): add SpiderFileService for file management"
```

---

### Task 8: 创建文件管理 API 路由

**Files:**
- Create: `app/routers/admin/crawlhub/spider_files.py`
- Modify: `app/routers/admin/crawlhub/__init__.py`

**Step 1: 创建路由文件**

```python
# app/routers/admin/crawlhub/spider_files.py
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from schemas.crawlhub import (
    SpiderFileContentResponse,
    SpiderFileListResponse,
    SpiderFileResponse,
    SpiderFileTreeNode,
    SpiderFileUpdateContent,
)
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub import SpiderFileService, SpiderService

router = APIRouter(prefix="/spiders/{spider_id}/files", tags=["CrawlHub - Spider Files"])


@router.get("", response_model=ApiResponse[list[SpiderFileTreeNode]])
async def list_files(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取爬虫文件列表（树结构）"""
    spider_service = SpiderService(db)
    spider = await spider_service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    file_service = SpiderFileService(db)
    files = await file_service.get_files(spider_id)
    tree = file_service.build_file_tree(files)
    return ApiResponse(data=tree)


@router.get("/{file_id}/content", response_model=ApiResponse[SpiderFileContentResponse])
async def get_file_content(
    spider_id: str,
    file_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取文件内容"""
    file_service = SpiderFileService(db)
    result = await file_service.get_file_content(file_id)
    if not result:
        raise HTTPException(status_code=404, detail="文件不存在")

    file, content = result
    if file.spider_id != spider_id:
        raise HTTPException(status_code=404, detail="文件不存在")

    return ApiResponse(data=SpiderFileContentResponse(
        id=file.id,
        file_path=file.file_path,
        content=content,
        content_type=file.content_type,
    ))


@router.post("/upload", response_model=ApiResponse[SpiderFileResponse])
async def upload_file(
    spider_id: str,
    file_path: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """上传单个文件"""
    spider_service = SpiderService(db)
    spider = await spider_service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    content = await file.read()
    if len(content) > 1 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小超过限制 (最大 1MB)")

    file_service = SpiderFileService(db)
    spider_file = await file_service.create_file(spider_id, file_path, content)
    return ApiResponse(data=SpiderFileResponse.model_validate(spider_file))


@router.post("/upload-zip", response_model=ApiResponse[list[SpiderFileResponse]])
async def upload_zip(
    spider_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """上传 ZIP 压缩包"""
    spider_service = SpiderService(db)
    spider = await spider_service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="请上传 ZIP 文件")

    content = await file.read()

    file_service = SpiderFileService(db)
    files, error = await file_service.upload_zip(spider_id, content)

    if error:
        raise HTTPException(status_code=400, detail=error)

    # 验证项目结构
    valid, err_msg, entry_point = await file_service.validate_project_structure(
        spider_id, spider.script_type.value
    )
    if not valid:
        # 删除已上传的文件
        await file_service.delete_all_files(spider_id)
        raise HTTPException(status_code=400, detail=err_msg)

    # 更新 spider 的 entry_point
    if entry_point:
        from models.crawlhub import ProjectType
        spider.project_type = ProjectType.MULTI_FILE
        spider.entry_point = entry_point
        await db.commit()

    return ApiResponse(data=[SpiderFileResponse.model_validate(f) for f in files])


@router.post("/new", response_model=ApiResponse[SpiderFileResponse])
async def create_new_file(
    spider_id: str,
    file_path: str,
    db: AsyncSession = Depends(get_db),
):
    """创建新的空文件"""
    spider_service = SpiderService(db)
    spider = await spider_service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    file_service = SpiderFileService(db)
    spider_file = await file_service.create_file(spider_id, file_path, b"")
    return ApiResponse(data=SpiderFileResponse.model_validate(spider_file))


@router.put("/{file_id}", response_model=ApiResponse[SpiderFileResponse])
async def update_file(
    spider_id: str,
    file_id: str,
    data: SpiderFileUpdateContent,
    db: AsyncSession = Depends(get_db),
):
    """更新文件内容"""
    file_service = SpiderFileService(db)
    file = await file_service.get_file_by_id(file_id)
    if not file or file.spider_id != spider_id:
        raise HTTPException(status_code=404, detail="文件不存在")

    updated_file = await file_service.update_file_content(file_id, data.content)
    return ApiResponse(data=SpiderFileResponse.model_validate(updated_file))


@router.delete("/{file_id}", response_model=MessageResponse)
async def delete_file(
    spider_id: str,
    file_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除文件"""
    file_service = SpiderFileService(db)
    file = await file_service.get_file_by_id(file_id)
    if not file or file.spider_id != spider_id:
        raise HTTPException(status_code=404, detail="文件不存在")

    await file_service.delete_file(file_id)
    return MessageResponse(msg="文件删除成功")
```

**Step 2: 更新路由 __init__.py**

在 `app/routers/admin/crawlhub/__init__.py` 中添加:

```python
from .spider_files import router as spider_files_router

router.include_router(spider_files_router)
```

**Step 3: 提交**

```bash
git add app/routers/admin/crawlhub/spider_files.py app/routers/admin/crawlhub/__init__.py
git commit -m "feat(crawlhub): add spider files API endpoints"
```

---

## 阶段二：前端实现

### Task 9: 新增前端类型定义

**Files:**
- Modify: `admin/types/crawlhub.ts`

**Step 1: 添加新类型**

在 `admin/types/crawlhub.ts` 中添加:

```typescript
// Project Type
export type ProjectType = 'single_file' | 'multi_file'

// Spider File Types
export type SpiderFile = {
  id: string
  spider_id: string
  file_path: string
  storage_key: string
  file_size: number
  content_type: string
  created_at: string
  updated_at: string
}

export type SpiderFileTreeNode = {
  id: string | null
  name: string
  path: string
  is_dir: boolean
  children: SpiderFileTreeNode[]
  file_size?: number
}

export type SpiderFileContent = {
  id: string
  file_path: string
  content: string
  content_type: string
}
```

同时更新 Spider 类型，添加:

```typescript
  project_type: ProjectType
  entry_point: string | null
```

**Step 2: 提交**

```bash
git add admin/types/crawlhub.ts
git commit -m "feat(admin): add spider file types"
```

---

### Task 10: 新增前端 API hooks

**Files:**
- Modify: `admin/service/use-crawlhub.ts`

**Step 1: 添加文件相关 hooks**

在 `admin/service/use-crawlhub.ts` 的 Spiders API 部分后添加:

```typescript
// ============ Spider Files API ============

export const useSpiderFiles = (spiderId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'spiders', spiderId, 'files'],
    queryFn: () => get<SpiderFileTreeNode[]>(`/crawlhub/spiders/${spiderId}/files`),
    enabled: !!spiderId,
  })
}

export const useSpiderFileContent = (spiderId: string, fileId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'spiders', spiderId, 'files', fileId, 'content'],
    queryFn: () => get<SpiderFileContent>(`/crawlhub/spiders/${spiderId}/files/${fileId}/content`),
    enabled: !!spiderId && !!fileId,
  })
}

export const useUpdateSpiderFile = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spiderId, fileId, content }: { spiderId: string, fileId: string, content: string }) =>
      put<SpiderFile>(`/crawlhub/spiders/${spiderId}/files/${fileId}`, { body: { content } }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spiders', variables.spiderId, 'files'] })
    },
  })
}

export const useDeleteSpiderFile = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spiderId, fileId }: { spiderId: string, fileId: string }) =>
      del(`/crawlhub/spiders/${spiderId}/files/${fileId}`),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spiders', variables.spiderId, 'files'] })
    },
  })
}

export const useCreateSpiderFile = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spiderId, filePath }: { spiderId: string, filePath: string }) =>
      post<SpiderFile>(`/crawlhub/spiders/${spiderId}/files/new?file_path=${encodeURIComponent(filePath)}`, {}),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spiders', variables.spiderId, 'files'] })
    },
  })
}
```

同时在文件顶部添加类型导入:

```typescript
import type {
  // ... 现有的
  SpiderFile,
  SpiderFileTreeNode,
  SpiderFileContent,
} from '@/types/crawlhub'
```

**Step 2: 提交**

```bash
git add admin/service/use-crawlhub.ts
git commit -m "feat(admin): add spider files API hooks"
```

---

### Task 11: 创建文件树组件

**Files:**
- Create: `admin/app/components/crawlhub/file-tree.tsx`

**Step 1: 创建组件**

```tsx
// admin/app/components/crawlhub/file-tree.tsx
'use client'

import type { SpiderFileTreeNode } from '@/types/crawlhub'
import {
  RiAddLine,
  RiDeleteBinLine,
  RiFile3Line,
  RiFolder3Line,
  RiFolderOpenLine,
} from '@remixicon/react'
import { useCallback, useState } from 'react'
import cn from '@/utils/classnames'

type FileTreeProps = {
  files: SpiderFileTreeNode[]
  selectedFileId: string | null
  onSelectFile: (fileId: string, filePath: string) => void
  onDeleteFile?: (fileId: string) => void
  onCreateFile?: () => void
}

type TreeNodeProps = {
  node: SpiderFileTreeNode
  level: number
  selectedFileId: string | null
  onSelectFile: (fileId: string, filePath: string) => void
  onDeleteFile?: (fileId: string) => void
}

const TreeNode = ({ node, level, selectedFileId, onSelectFile, onDeleteFile }: TreeNodeProps) => {
  const [expanded, setExpanded] = useState(true)
  const isSelected = node.id === selectedFileId

  const handleClick = useCallback(() => {
    if (node.is_dir) {
      setExpanded(!expanded)
    } else if (node.id) {
      onSelectFile(node.id, node.path)
    }
  }, [node, expanded, onSelectFile])

  const handleDelete = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    if (node.id && onDeleteFile) {
      onDeleteFile(node.id)
    }
  }, [node.id, onDeleteFile])

  return (
    <div>
      <div
        className={cn(
          'group flex items-center gap-1.5 px-2 py-1 cursor-pointer rounded hover:bg-background-section',
          isSelected && 'bg-components-button-secondary-bg',
        )}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={handleClick}
      >
        {node.is_dir ? (
          expanded ? (
            <RiFolderOpenLine className="h-4 w-4 text-util-colors-warning-warning-500 shrink-0" />
          ) : (
            <RiFolder3Line className="h-4 w-4 text-util-colors-warning-warning-500 shrink-0" />
          )
        ) : (
          <RiFile3Line className="h-4 w-4 text-text-tertiary shrink-0" />
        )}
        <span className="text-sm text-text-secondary truncate flex-1">{node.name}</span>
        {!node.is_dir && onDeleteFile && (
          <button
            className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-state-destructive-hover rounded"
            onClick={handleDelete}
          >
            <RiDeleteBinLine className="h-3.5 w-3.5 text-text-tertiary hover:text-text-destructive" />
          </button>
        )}
      </div>
      {node.is_dir && expanded && node.children.length > 0 && (
        <div>
          {node.children.map(child => (
            <TreeNode
              key={child.path}
              node={child}
              level={level + 1}
              selectedFileId={selectedFileId}
              onSelectFile={onSelectFile}
              onDeleteFile={onDeleteFile}
            />
          ))}
        </div>
      )}
    </div>
  )
}

const FileTree = ({ files, selectedFileId, onSelectFile, onDeleteFile, onCreateFile }: FileTreeProps) => {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-divider-subtle">
        <span className="text-xs font-medium text-text-tertiary uppercase">文件</span>
        {onCreateFile && (
          <button
            className="p-1 hover:bg-background-section rounded"
            onClick={onCreateFile}
          >
            <RiAddLine className="h-4 w-4 text-text-tertiary" />
          </button>
        )}
      </div>
      <div className="flex-1 overflow-auto py-1">
        {files.length === 0 ? (
          <div className="px-3 py-4 text-sm text-text-tertiary text-center">
            暂无文件
          </div>
        ) : (
          files.map(node => (
            <TreeNode
              key={node.path}
              node={node}
              level={0}
              selectedFileId={selectedFileId}
              onSelectFile={onSelectFile}
              onDeleteFile={onDeleteFile}
            />
          ))
        )}
      </div>
    </div>
  )
}

export default FileTree
```

**Step 2: 提交**

```bash
git add admin/app/components/crawlhub/file-tree.tsx
git commit -m "feat(admin): add file tree component for spider editor"
```

---

### Task 12: 创建代码编辑器页面

**Files:**
- Create: `admin/app/(commonLayout)/crawlhub/spiders/[id]/editor/page.tsx`

**Step 1: 创建编辑器页面**

```tsx
// admin/app/(commonLayout)/crawlhub/spiders/[id]/editor/page.tsx
'use client'

import type { SpiderFileTreeNode } from '@/types/crawlhub'
import {
  RiArrowLeftLine,
  RiPlayLine,
  RiSave3Line,
  RiUpload2Line,
} from '@remixicon/react'
import dynamic from 'next/dynamic'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useCallback, useEffect, useRef, useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import Skeleton from '@/app/components/base/skeleton'
import Toast from '@/app/components/base/toast'
import FileTree from '@/app/components/crawlhub/file-tree'
import {
  useCreateSpiderFile,
  useDeleteSpiderFile,
  useSpider,
  useSpiderFileContent,
  useSpiderFiles,
  useUpdateSpiderFile,
} from '@/service/use-crawlhub'
import { upload } from '@/service/base'

// 动态导入 Monaco Editor
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
})

const SpiderEditorPage = () => {
  const params = useParams()
  const spiderId = params.id as string

  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [selectedFilePath, setSelectedFilePath] = useState<string>('')
  const [editorContent, setEditorContent] = useState<string>('')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [fileToDelete, setFileToDelete] = useState<string | null>(null)
  const [showNewFileModal, setShowNewFileModal] = useState(false)
  const [newFileName, setNewFileName] = useState('')
  const uploadInputRef = useRef<HTMLInputElement>(null)

  const { data: spider, isLoading: isLoadingSpider } = useSpider(spiderId)
  const { data: files, isLoading: isLoadingFiles, refetch: refetchFiles } = useSpiderFiles(spiderId)
  const { data: fileContent, isLoading: isLoadingContent } = useSpiderFileContent(spiderId, selectedFileId || '')

  const updateFileMutation = useUpdateSpiderFile()
  const deleteFileMutation = useDeleteSpiderFile()
  const createFileMutation = useCreateSpiderFile()

  // 当文件内容加载完成时，更新编辑器内容
  useEffect(() => {
    if (fileContent) {
      setEditorContent(fileContent.content)
      setHasUnsavedChanges(false)
    }
  }, [fileContent])

  // 自动选择第一个文件
  useEffect(() => {
    if (files && files.length > 0 && !selectedFileId) {
      const findFirstFile = (nodes: SpiderFileTreeNode[]): { id: string, path: string } | null => {
        for (const node of nodes) {
          if (!node.is_dir && node.id) {
            return { id: node.id, path: node.path }
          }
          if (node.is_dir && node.children.length > 0) {
            const found = findFirstFile(node.children)
            if (found) return found
          }
        }
        return null
      }
      const first = findFirstFile(files)
      if (first) {
        setSelectedFileId(first.id)
        setSelectedFilePath(first.path)
      }
    }
  }, [files, selectedFileId])

  const handleSelectFile = useCallback((fileId: string, filePath: string) => {
    if (hasUnsavedChanges) {
      if (!confirm('当前文件有未保存的更改，是否放弃更改？')) {
        return
      }
    }
    setSelectedFileId(fileId)
    setSelectedFilePath(filePath)
  }, [hasUnsavedChanges])

  const handleEditorChange = useCallback((value: string | undefined) => {
    setEditorContent(value || '')
    setHasUnsavedChanges(true)
  }, [])

  const handleSave = useCallback(async () => {
    if (!selectedFileId) return

    try {
      await updateFileMutation.mutateAsync({
        spiderId,
        fileId: selectedFileId,
        content: editorContent,
      })
      setHasUnsavedChanges(false)
      Toast.notify({ type: 'success', message: '保存成功' })
    } catch {
      Toast.notify({ type: 'error', message: '保存失败' })
    }
  }, [spiderId, selectedFileId, editorContent, updateFileMutation])

  // Ctrl+S 快捷键保存
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleSave])

  const handleDeleteFile = useCallback((fileId: string) => {
    setFileToDelete(fileId)
    setShowDeleteConfirm(true)
  }, [])

  const confirmDelete = useCallback(async () => {
    if (!fileToDelete) return

    try {
      await deleteFileMutation.mutateAsync({ spiderId, fileId: fileToDelete })
      Toast.notify({ type: 'success', message: '文件已删除' })
      setShowDeleteConfirm(false)
      setFileToDelete(null)
      if (selectedFileId === fileToDelete) {
        setSelectedFileId(null)
        setSelectedFilePath('')
        setEditorContent('')
      }
      refetchFiles()
    } catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }, [spiderId, fileToDelete, selectedFileId, deleteFileMutation, refetchFiles])

  const handleCreateFile = useCallback(async () => {
    if (!newFileName.trim()) {
      Toast.notify({ type: 'error', message: '请输入文件名' })
      return
    }

    try {
      await createFileMutation.mutateAsync({
        spiderId,
        filePath: newFileName.trim(),
      })
      Toast.notify({ type: 'success', message: '文件创建成功' })
      setShowNewFileModal(false)
      setNewFileName('')
      refetchFiles()
    } catch {
      Toast.notify({ type: 'error', message: '创建失败' })
    }
  }, [spiderId, newFileName, createFileMutation, refetchFiles])

  const handleUploadZip = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    try {
      const xhr = new XMLHttpRequest()
      await upload(
        { xhr, data: formData },
        false,
        `/crawlhub/spiders/${spiderId}/files/upload-zip`,
      )
      Toast.notify({ type: 'success', message: 'ZIP 文件上传成功' })
      refetchFiles()
    } catch {
      Toast.notify({ type: 'error', message: '上传失败' })
    }

    // 清空 input
    if (uploadInputRef.current) {
      uploadInputRef.current.value = ''
    }
  }, [spiderId, refetchFiles])

  if (isLoadingSpider) {
    return (
      <div className="h-full flex items-center justify-center">
        <Skeleton className="h-8 w-48" />
      </div>
    )
  }

  if (!spider) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-text-secondary">爬虫不存在</p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-divider-subtle shrink-0">
        <div className="flex items-center gap-3">
          <Link
            href="/crawlhub/spiders"
            className="p-1.5 hover:bg-background-section rounded"
          >
            <RiArrowLeftLine className="h-5 w-5 text-text-tertiary" />
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-text-primary">{spider.name}</h1>
            <p className="text-xs text-text-tertiary">
              {selectedFilePath || '选择一个文件开始编辑'}
              {hasUnsavedChanges && <span className="text-util-colors-warning-warning-500 ml-1">●</span>}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={uploadInputRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={handleUploadZip}
          />
          <Button
            variant="secondary"
            onClick={() => uploadInputRef.current?.click()}
          >
            <RiUpload2Line className="h-4 w-4 mr-1" />
            上传 ZIP
          </Button>
          <Button
            variant="secondary"
            onClick={handleSave}
            disabled={!hasUnsavedChanges || updateFileMutation.isPending}
            loading={updateFileMutation.isPending}
          >
            <RiSave3Line className="h-4 w-4 mr-1" />
            保存
          </Button>
          <Button variant="primary">
            <RiPlayLine className="h-4 w-4 mr-1" />
            测试运行
          </Button>
        </div>
      </div>

      {/* 主体内容 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 文件树 */}
        <div className="w-56 border-r border-divider-subtle shrink-0">
          {isLoadingFiles ? (
            <div className="p-3 space-y-2">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
            </div>
          ) : (
            <FileTree
              files={files || []}
              selectedFileId={selectedFileId}
              onSelectFile={handleSelectFile}
              onDeleteFile={handleDeleteFile}
              onCreateFile={() => setShowNewFileModal(true)}
            />
          )}
        </div>

        {/* 编辑器 */}
        <div className="flex-1 overflow-hidden">
          {isLoadingContent ? (
            <Skeleton className="h-full w-full" />
          ) : selectedFileId ? (
            <MonacoEditor
              height="100%"
              language="python"
              theme="vs-dark"
              value={editorContent}
              onChange={handleEditorChange}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 4,
                insertSpaces: true,
              }}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-text-tertiary">
              选择一个文件开始编辑
            </div>
          )}
        </div>
      </div>

      {/* 删除确认弹窗 */}
      <Confirm
        isShow={showDeleteConfirm}
        onCancel={() => {
          setShowDeleteConfirm(false)
          setFileToDelete(null)
        }}
        onConfirm={confirmDelete}
        isLoading={deleteFileMutation.isPending}
        title="确认删除"
        content="确定要删除这个文件吗？此操作不可恢复。"
      />

      {/* 新建文件弹窗 */}
      <Modal isShow={showNewFileModal} onClose={() => setShowNewFileModal(false)} className="!max-w-sm">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">新建文件</h3>
          <Input
            value={newFileName}
            onChange={e => setNewFileName(e.target.value)}
            placeholder="例如: utils/helper.py"
            className="mb-4"
          />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowNewFileModal(false)}>取消</Button>
            <Button
              variant="primary"
              onClick={handleCreateFile}
              loading={createFileMutation.isPending}
            >
              创建
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default SpiderEditorPage
```

**Step 2: 提交**

```bash
git add admin/app/\(commonLayout\)/crawlhub/spiders/\[id\]/editor/page.tsx
git commit -m "feat(admin): add spider code editor page"
```

---

### Task 13: 更新爬虫列表页面添加编辑器入口

**Files:**
- Modify: `admin/app/(commonLayout)/crawlhub/spiders/page.tsx`

**Step 1: 添加代码编辑按钮**

1. 在顶部导入中添加:

```typescript
import { RiCodeSSlashLine } from '@remixicon/react'
import { useRouter } from 'next/navigation'
```

2. 在组件内添加 router:

```typescript
const router = useRouter()
```

3. 在 actions 数组中添加新操作（在"执行"之后）:

```typescript
{
  icon: RiCodeSSlashLine,
  label: '编辑代码',
  onClick: (row) => {
    router.push(`/crawlhub/spiders/${row.id}/editor`)
  },
},
```

**Step 2: 提交**

```bash
git add admin/app/\(commonLayout\)/crawlhub/spiders/page.tsx
git commit -m "feat(admin): add code editor entry in spider list"
```

---

### Task 14: 安装 Monaco Editor 依赖

**Files:**
- Modify: `admin/package.json`

**Step 1: 安装依赖**

```bash
cd admin && npm install @monaco-editor/react
```

**Step 2: 提交**

```bash
git add admin/package.json admin/package-lock.json
git commit -m "chore(admin): add monaco-editor dependency"
```

---

## 阶段三：测试运行功能

### Task 15: 创建测试运行 API

**Files:**
- Modify: `app/routers/admin/crawlhub/spiders.py`
- Create: `app/services/crawlhub/spider_runner_service.py`

**Step 1: 创建 SpiderRunnerService**

```python
# app/services/crawlhub/spider_runner_service.py
import asyncio
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from extensions.ext_storage import storage
from models.crawlhub import Spider, SpiderTask, SpiderTaskStatus, ProjectType
from services.crawlhub import SpiderFileService


class SpiderRunnerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_test_task(self, spider: Spider) -> SpiderTask:
        """创建测试任务"""
        task = SpiderTask(
            spider_id=spider.id,
            status=SpiderTaskStatus.PENDING,
            is_test=True,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def prepare_project_files(self, spider: Spider, work_dir: Path) -> None:
        """准备项目文件到工作目录"""
        file_service = SpiderFileService(self.db)
        files = await file_service.get_files(spider.id)

        for file in files:
            file_path = work_dir / file.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            content = await storage.load_once(file.storage_key)
            file_path.write_bytes(content)

    async def run_test(
        self,
        spider: Spider,
        task: SpiderTask,
    ) -> AsyncGenerator[dict, None]:
        """
        运行测试任务
        返回 SSE 事件生成器
        """
        task.status = SpiderTaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        await self.db.commit()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                work_dir = Path(temp_dir)

                # 准备文件
                await self.prepare_project_files(spider, work_dir)

                yield {"event": "status", "data": {"status": "preparing", "message": "准备执行环境..."}}

                # 确定入口点
                if spider.project_type == ProjectType.MULTI_FILE:
                    entry_point = spider.entry_point or "main.py:run"
                else:
                    # 单文件项目，找到主文件
                    entry_point = "main.py:run"

                # 执行脚本
                if spider.script_type.value == "scrapy":
                    cmd = ["scrapy", "crawl", spider.name]
                else:
                    # httpx 或 playwright
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

                # 设置超时 (5 分钟)
                timeout = 300

                async def read_stream(stream, event_type):
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        yield {
                            "event": event_type,
                            "data": {
                                "line": line.decode("utf-8", errors="replace").rstrip(),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        }

                # 读取 stdout 和 stderr
                try:
                    async for event in read_stream(process.stdout, "stdout"):
                        yield event
                    async for event in read_stream(process.stderr, "stderr"):
                        yield event

                    await asyncio.wait_for(process.wait(), timeout=timeout)

                except asyncio.TimeoutError:
                    process.kill()
                    yield {
                        "event": "error",
                        "data": {"message": "执行超时 (最大 5 分钟)"}
                    }
                    task.status = SpiderTaskStatus.FAILED
                    task.error_message = "执行超时"
                else:
                    if process.returncode == 0:
                        task.status = SpiderTaskStatus.COMPLETED
                    else:
                        task.status = SpiderTaskStatus.FAILED
                        task.error_message = f"进程退出码: {process.returncode}"

        except Exception as e:
            task.status = SpiderTaskStatus.FAILED
            task.error_message = str(e)
            yield {"event": "error", "data": {"message": str(e)}}

        finally:
            task.finished_at = datetime.utcnow()
            await self.db.commit()

            duration = (task.finished_at - task.started_at).total_seconds() if task.started_at else 0
            yield {
                "event": "status",
                "data": {
                    "status": task.status.value,
                    "duration": duration,
                }
            }
```

**Step 2: 在 spiders.py 中添加测试运行端点**

在 `app/routers/admin/crawlhub/spiders.py` 中添加:

```python
from fastapi.responses import StreamingResponse
from services.crawlhub.spider_runner_service import SpiderRunnerService
import json

@router.post("/{spider_id}/test-run")
async def test_run_spider(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """启动测试运行"""
    service = SpiderService(db)
    spider = await service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    runner = SpiderRunnerService(db)
    task = await runner.create_test_task(spider)

    async def event_generator():
        async for event in runner.run_test(spider, task):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
```

**Step 3: 更新 services/crawlhub/__init__.py**

```python
from .spider_runner_service import SpiderRunnerService
```

**Step 4: 提交**

```bash
git add app/services/crawlhub/spider_runner_service.py app/routers/admin/crawlhub/spiders.py app/services/crawlhub/__init__.py
git commit -m "feat(crawlhub): add test run API with SSE output"
```

---

### Task 16: 前端集成测试运行

**Files:**
- Modify: `admin/app/(commonLayout)/crawlhub/spiders/[id]/editor/page.tsx`

**Step 1: 添加输出面板和测试运行逻辑**

在编辑器页面中:

1. 添加状态:

```typescript
const [showOutput, setShowOutput] = useState(false)
const [outputLines, setOutputLines] = useState<Array<{ type: string; line: string; timestamp: string }>>([])
const [isRunning, setIsRunning] = useState(false)
```

2. 添加测试运行处理函数:

```typescript
const handleTestRun = useCallback(async () => {
  setIsRunning(true)
  setShowOutput(true)
  setOutputLines([])

  try {
    const response = await fetch(`/platform/api/crawlhub/spiders/${spiderId}/test-run`, {
      method: 'POST',
      credentials: 'include',
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    while (reader) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value)
      const lines = text.split('\n\n')

      for (const line of lines) {
        if (!line.trim()) continue

        const eventMatch = line.match(/^event: (.+)$/)
        const dataMatch = line.match(/^data: (.+)$/m)

        if (eventMatch && dataMatch) {
          const eventType = eventMatch[1]
          const data = JSON.parse(dataMatch[1])

          if (eventType === 'stdout' || eventType === 'stderr') {
            setOutputLines(prev => [...prev, {
              type: eventType,
              line: data.line,
              timestamp: data.timestamp,
            }])
          } else if (eventType === 'status' && data.status !== 'preparing') {
            setIsRunning(false)
          }
        }
      }
    }
  } catch (error) {
    Toast.notify({ type: 'error', message: '运行失败' })
    setIsRunning(false)
  }
}, [spiderId])
```

3. 更新测试运行按钮:

```tsx
<Button
  variant="primary"
  onClick={handleTestRun}
  disabled={isRunning}
  loading={isRunning}
>
  <RiPlayLine className="h-4 w-4 mr-1" />
  {isRunning ? '运行中...' : '测试运行'}
</Button>
```

4. 添加输出面板:

```tsx
{/* 输出面板 */}
{showOutput && (
  <div className="h-48 border-t border-divider-subtle flex flex-col shrink-0">
    <div className="flex items-center justify-between px-3 py-2 border-b border-divider-subtle">
      <span className="text-xs font-medium text-text-tertiary uppercase">输出</span>
      <button
        className="p-1 hover:bg-background-section rounded"
        onClick={() => setShowOutput(false)}
      >
        <RiCloseLine className="h-4 w-4 text-text-tertiary" />
      </button>
    </div>
    <div className="flex-1 overflow-auto bg-gray-900 p-2 font-mono text-xs">
      {outputLines.map((item, index) => (
        <div
          key={index}
          className={item.type === 'stderr' ? 'text-red-400' : 'text-green-400'}
        >
          {item.line}
        </div>
      ))}
      {outputLines.length === 0 && !isRunning && (
        <div className="text-gray-500">暂无输出</div>
      )}
    </div>
  </div>
)}
```

**Step 2: 提交**

```bash
git add admin/app/\(commonLayout\)/crawlhub/spiders/\[id\]/editor/page.tsx
git commit -m "feat(admin): add test run output panel in editor"
```

---

## 完成检查清单

- [ ] Task 1: SpiderFile 模型创建
- [ ] Task 2: Spider 模型修改
- [ ] Task 3: SpiderTask 模型修改
- [ ] Task 4: 数据库迁移
- [ ] Task 5: SpiderFile Schema
- [ ] Task 6: Spider Schema 更新
- [ ] Task 7: SpiderFileService
- [ ] Task 8: 文件管理 API
- [ ] Task 9: 前端类型定义
- [ ] Task 10: 前端 API hooks
- [ ] Task 11: 文件树组件
- [ ] Task 12: 代码编辑器页面
- [ ] Task 13: 爬虫列表添加入口
- [ ] Task 14: Monaco Editor 依赖
- [ ] Task 15: 测试运行 API
- [ ] Task 16: 前端测试运行集成
