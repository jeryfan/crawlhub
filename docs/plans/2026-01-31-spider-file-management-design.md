# Spider 多文件管理与在线编辑设计

## 概述

增强爬虫文件管理功能，支持单文件上传、ZIP 项目压缩包上传、在线代码编辑、测试运行与正式任务执行。

## 一、数据模型变更

### Spider 模型调整

- **移除** `script_content` 字段
- **新增** `project_type` 字段：`SINGLE_FILE` | `MULTI_FILE`
- **新增** `entry_point` 字段：入口信息，Scrapy 项目自动识别，普通项目默认为 `main.py:run`

### 新增 SpiderFile 模型 (`crawlhub_spider_files`)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| spider_id | UUID FK | 所属爬虫 |
| file_path | String | 文件在项目中的相对路径，如 `spiders/my_spider.py` |
| storage_key | String | OpenDal 中的存储 key |
| file_size | Integer | 文件大小（字节） |
| content_type | String | MIME 类型 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

单文件项目也通过 SpiderFile 统一管理，只是只有一条记录。

### SpiderTask 模型调整

- **新增** `is_test` (Boolean, default=False) - 标记是否为测试运行

## 二、后端 API 设计

### 文件管理接口

基础路径：`/platform/api/crawlhub/spiders/{spider_id}`

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/files` | 获取文件列表（树结构） |
| `GET` | `/files/{file_id}/content` | 获取文件内容（编辑用） |
| `POST` | `/files/upload` | 上传单文件 |
| `POST` | `/files/upload-zip` | 上传 ZIP 压缩包（解压后存储） |
| `PUT` | `/files/{file_id}` | 保存编辑后的文件内容 |
| `DELETE` | `/files/{file_id}` | 删除文件 |
| `POST` | `/files/new` | 在线新建空文件 |

### 创建爬虫流程

两步操作：
1. `POST /spiders` 创建 Spider 基本信息（名称、类型等），返回 spider_id
2. 通过文件接口上传代码

### 运行接口

现有 `POST /spiders/{spider_id}/run` 保持不变（正式任务），新增：

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/spiders/{spider_id}/test-run` | 测试运行，返回 task_id |
| `GET` | `/spiders/{spider_id}/test-run/{task_id}/output` | SSE 流式获取测试运行输出 |
| `POST` | `/spiders/{spider_id}/test-run/{task_id}/stop` | 停止测试运行 |

## 三、前端编辑器页面

### 路由

`/crawlhub/spiders/{spider_id}/editor`

### 页面布局（三栏式）

```
┌─────────────────────────────────────────────────────────────┐
│  工具栏: [保存] [测试运行] [正式运行] [上传文件] [新建文件]    │
├──────────┬─────────────────────────────┬────────────────────┤
│          │                             │                    │
│  文件树   │      Monaco Editor          │    输出面板        │
│          │      (多标签页)              │    (可收起)        │
│          │                             │                    │
│  - 新建   │  - 语法高亮                 │  - stdout/stderr   │
│  - 删除   │  - 自动补全                 │  - 运行状态        │
│  - 重命名 │  - 错误提示                 │  - 日志筛选        │
│          │                             │                    │
├──────────┴─────────────────────────────┴────────────────────┤
│  状态栏: 当前文件 | 行号:列号 | 保存状态 | 运行状态           │
└─────────────────────────────────────────────────────────────┘
```

### 关键交互

- **文件树**：点击文件在编辑器中打开新标签，右键菜单支持删除/重命名
- **多标签页**：已修改的文件标签显示圆点标记，关闭时提示保存
- **保存**：Ctrl+S 快捷键保存当前文件，调用 PUT 接口
- **测试运行**：点击后输出面板自动展开，SSE 实时显示输出
- **上传文件**：支持拖拽上传，ZIP 文件自动解压

### Monaco Editor 配置

- Python 语言模式
- 基础语法检查
- 自动补全基于当前项目文件 + Python 标准库提示

## 四、ZIP 上传与项目识别

### ZIP 上传处理流程

```
用户上传 ZIP → 后端解压到临时目录 → 扫描目录结构识别项目类型
    → 逐个文件上传到 OpenDal 并创建 SpiderFile 记录
    → 清理临时文件 → 返回文件列表
```

### 项目类型识别规则

**Scrapy 项目**（满足以下任一）：
- 存在 `scrapy.cfg` 文件
- 存在 `settings.py` 且包含 `BOT_NAME` 变量

**普通 Python 项目**：
- 必须存在 `main.py`
- `main.py` 中必须定义 `run()` 函数
- 上传时校验，不符合则返回错误提示

### 文件过滤规则

上传时自动忽略：
- `__pycache__/` 目录
- `.git/` 目录
- `*.pyc`, `*.pyo` 文件
- `.DS_Store`, `Thumbs.db`
- `venv/`, `.venv/`, `env/` 虚拟环境目录

### 大小限制

- 单个文件：最大 1MB
- ZIP 解压后总大小：最大 50MB
- 单个项目文件数量：最大 200 个

## 五、测试运行执行机制

### 与正式任务的区别

| 特性 | 测试运行 | 正式任务 |
|------|----------|----------|
| 执行方式 | 同步等待，实时输出 | 进入 Celery 队列异步执行 |
| 时长限制 | 5 分钟 | 无限制（可配置） |
| 输出方式 | SSE 实时流式返回 | 日志存储，完成后查看 |
| 数据存储 | 不存储抓取结果 | 存入 MongoDB |
| 资源隔离 | Docker 容器（复用现有沙箱） | Docker 容器 |
| 任务记录 | 存入 SpiderTask，标记 `is_test=True` | 正常任务记录 |

### 执行流程

```
前端调用 POST /test-run → 创建 SpiderTask 记录 (is_test=True)
    → 从 OpenDal 下载项目文件到临时目录
    → 启动 Docker 容器执行（复用现有 sandbox）
    → 通过 SSE 端点实时推送 stdout/stderr
    → 超时或完成后清理容器和临时文件
    → 更新 SpiderTask 状态
```

### SSE 输出格式

```
event: stdout
data: {"line": "Crawling page 1...", "timestamp": "2026-01-31T19:10:00Z"}

event: stderr
data: {"line": "Warning: rate limit detected", "timestamp": "2026-01-31T19:10:01Z"}

event: status
data: {"status": "completed", "duration": 12.5}
```

## 六、实现阶段

### 阶段一：核心功能

- 数据库模型变更（Spider 调整、新增 SpiderFile）
- 文件 CRUD API（上传、下载、编辑、删除）
- ZIP 上传与解压处理
- 前端编辑器页面基础版（文件树 + Monaco Editor + 保存）

### 阶段二：运行功能

- 测试运行 API 与 SSE 输出
- 前端输出面板集成
- 正式运行适配多文件项目

### 阶段三：体验优化

- 多标签页编辑
- 语法检查与自动补全增强
- 拖拽上传
- 快捷键支持

## 七、涉及的主要文件

| 类型 | 路径 |
|------|------|
| 数据库模型 | `app/models/crawlhub.py` |
| 数据库迁移 | `app/alembic/versions/xxx_spider_files.py` |
| Pydantic Schema | `app/schemas/crawlhub.py` |
| API 路由 | `app/routers/admin/crawlhub/spiders.py` |
| 服务层 | `app/services/crawlhub/spider_file_service.py` |
| 前端页面 | `admin/app/(commonLayout)/crawlhub/spiders/[id]/editor/page.tsx` |
| 前端服务 | `admin/service/use-crawlhub.ts` |
