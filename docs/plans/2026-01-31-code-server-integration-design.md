# Code-Server 集成设计

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为爬虫项目提供完整的 VS Code 在线编辑体验，支持多用户并发，按需启动独立容器。

**Architecture:** 后端通过 Docker API 管理 code-server 容器生命周期，用户编辑时从 OpenDAL 拉取文件到容器，保存时同步回 OpenDAL。前端新窗口打开 code-server，通过 Nginx 反向代理访问。

**Tech Stack:** Docker SDK for Python, code-server, Nginx, FastAPI, OpenDAL

---

## 一、整体架构

### 核心组件

- **CodeServerManager**（后端服务）— 管理容器生命周期：创建、启动、停止、销毁、健康检查
- **FileSyncService**（扩展现有）— 启动时从 OpenDAL 拉取文件到容器，保存时从容器回写 OpenDAL
- **数据库记录** — `crawlhub_code_sessions` 表追踪活跃会话
- **前端** — 爬虫列表页添加按钮，点击后调用 API 获取 code-server URL，新窗口打开
- **反向代理** — Nginx 根据路径动态代理到对应的 code-server 容器

### 流程概览

```
用户点击"在线编辑"
    ↓
后端检查是否已有活跃会话
    ↓ (无)
创建容器 → 分配端口 → 从 OpenDAL 拉取文件
    ↓
返回 URL + Token
    ↓
前端新窗口打开 code-server
    ↓
用户编辑代码
    ↓
用户点击"保存到服务器" → 同步回 OpenDAL
    ↓
用户关闭/超时 → 同步 → 销毁容器
```

---

## 二、容器管理策略

### 容器镜像

基于 `codercom/code-server:latest` 构建自定义镜像 `crawlhub-code-server`，预装：

- Python 3.11 + pip
- Node.js 20 LTS + npm/pnpm
- 常用爬虫库：scrapy、httpx、playwright、beautifulsoup4、lxml
- VS Code 扩展：
  - Python (ms-python.python)
  - Pylance (ms-python.vscode-pylance)
  - ESLint (dbaeumer.vscode-eslint)
  - Prettier (esbenp.prettier-vscode)
- 工具：git、curl、jq

### 生命周期

| 阶段 | 说明 |
|------|------|
| 创建 | 用户点击编辑 → 检查已有会话 → 无则创建容器，分配端口 |
| 启动超时 | 容器 30 秒内未就绪视为失败 |
| 空闲检测 | 通过心跳判断，离开 30 分钟后触发同步 + 销毁 |
| 强制超时 | 最长存活 4 小时，防止资源泄漏 |
| 优雅关闭 | 销毁前先触发文件同步，确保改动不丢失 |

### 安全隔离

- 每个容器独立网络命名空间
- 限制 CPU（1核）和内存（1GB）
- 禁用特权模式
- 工作目录限制 500MB
- 允许出站网络（爬虫需要访问外部网站）

### 端口管理

- 端口池范围：10000-10100（共 100 个并发会话）
- 分配策略：从数据库查询未占用端口，分配给新会话
- 回收：会话销毁时释放端口

---

## 三、文件同步机制

### 同步策略（类 GitHub Codespaces 风格）

用户有明确的"保存"动作，改动需要显式同步回服务器。

### 启动时拉取

1. 容器启动后，后端调用 `FileSyncService.pull_to_container(spider_id, container_id)`
2. 从 `crawlhub_spider_files` 表获取文件列表
3. 逐个从 OpenDAL 读取内容，通过 Docker exec 或 tar 流写入容器 `/workspace` 目录
4. 同步完成后标记会话为 `ready`

### 保存回写

**触发时机**：
- 用户主动点击"保存到服务器"按钮
- 空闲超时销毁前
- 强制超时销毁前
- 用户主动关闭会话

**流程**：
1. 通过 Docker exec 打包容器 `/workspace` 目录为 tar
2. 解析 tar，对比现有文件列表，识别新增/修改/删除
3. 批量更新 OpenDAL 存储和数据库记录
4. 忽略目录：`__pycache__`、`.venv`、`venv`、`node_modules`、`.git`

### 冲突处理

单用户单爬虫同时只允许一个活跃会话。如果已有会话存在，返回该会话的 URL 而非创建新容器。

---

## 四、数据模型

### 新增表：crawlhub_code_sessions

```python
class CodeSessionStatus(enum.StrEnum):
    PENDING = "pending"      # 创建中
    STARTING = "starting"    # 容器启动中
    READY = "ready"          # 就绪可用
    SYNCING = "syncing"      # 同步文件中
    STOPPED = "stopped"      # 已停止
    FAILED = "failed"        # 失败

class CodeSession(DefaultFieldsMixin, Base):
    __tablename__ = "crawlhub_code_sessions"

    spider_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    user_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    container_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CodeSessionStatus] = mapped_column(
        EnumText(CodeSessionStatus), default=CodeSessionStatus.PENDING
    )
    access_token: Mapped[str] = mapped_column(String(64), nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

---

## 五、API 设计

### 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/spiders/{spider_id}/code-session` | 创建或获取会话 |
| GET | `/spiders/{spider_id}/code-session` | 获取当前会话状态 |
| POST | `/spiders/{spider_id}/code-session/sync` | 手动触发文件同步 |
| DELETE | `/spiders/{spider_id}/code-session` | 关闭会话 |
| POST | `/spiders/{spider_id}/code-session/heartbeat` | 心跳保活 |

### 响应示例

**POST /spiders/{spider_id}/code-session**

```json
{
  "code": 0,
  "data": {
    "session_id": "uuid",
    "url": "https://example.com/code-server/uuid/",
    "token": "random-access-token",
    "status": "ready"
  }
}
```

---

## 六、反向代理配置

### Nginx 配置

```nginx
location ~ ^/code-server/([a-f0-9-]+)/(.*) {
    set $session_id $1;
    set $path $2;

    # 从后端 API 或 Redis 获取端口映射
    # 此处简化为静态配置示例
    proxy_pass http://127.0.0.1:$upstream_port/$path;

    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_read_timeout 86400;
}
```

### WebSocket 支持

code-server 依赖 WebSocket 通信，Nginx 需配置：
- `proxy_http_version 1.1`
- `Upgrade` 和 `Connection` 头
- 较长的 `proxy_read_timeout`

---

## 七、清理任务

### 定时 Job（每 5 分钟）

```python
async def cleanup_expired_sessions():
    # 查找过期会话
    expired = await db.execute(
        select(CodeSession).where(
            or_(
                CodeSession.last_active_at < datetime.utcnow() - timedelta(minutes=30),
                CodeSession.expires_at < datetime.utcnow()
            ),
            CodeSession.status.in_([CodeSessionStatus.READY, CodeSessionStatus.STARTING])
        )
    )

    for session in expired.scalars():
        # 1. 同步文件
        await file_sync_service.sync_from_container(session)
        # 2. 停止并删除容器
        await code_server_manager.destroy(session.container_id)
        # 3. 更新状态
        session.status = CodeSessionStatus.STOPPED
        await db.commit()
```

---

## 八、前端交互

### 爬虫列表页

在操作列添加"在线编辑"按钮（使用 `RiCodeSSlashLine` 图标，已存在）。

### 点击流程

```typescript
const handleOpenEditor = async (spiderId: string) => {
  try {
    const res = await createCodeSession(spiderId)
    // 新窗口打开，URL 带 token 自动登录
    window.open(`${res.url}?tkn=${res.token}`, '_blank')

    // 启动心跳
    startHeartbeat(spiderId)
  } catch (error) {
    Toast.notify({ type: 'error', message: '启动编辑器失败' })
  }
}
```

### 心跳机制

页面 visible 时每 5 分钟发送心跳，页面隐藏或关闭时停止。

---

## 九、实现优先级

1. **P0 - 核心功能**
   - CodeSession 数据模型
   - CodeServerManager 容器管理
   - 文件同步（拉取 + 回写）
   - API 端点

2. **P1 - 基础设施**
   - 自定义 Docker 镜像
   - Nginx 反向代理配置
   - 清理定时任务

3. **P2 - 前端集成**
   - 创建会话 API 调用
   - 新窗口打开
   - 心跳保活

4. **P3 - 增强**
   - 同步状态提示
   - 错误恢复机制
   - 监控告警
