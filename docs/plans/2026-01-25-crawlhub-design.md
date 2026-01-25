# CrawlHub 爬虫管理平台设计文档

## 项目概述

CrawlHub 是一个通用的爬虫管理平台，基于 fastapi-template 开发，提供数据抓取、数据入库、数据可视化、数据检索等功能。

## 技术决策

| 决策项 | 选择 |
|-------|------|
| 项目名称 | CrawlHub |
| 基础框架 | fastapi-template（仅保留 admin 端） |
| 脚本执行 | Python 脚本沙箱 + Docker 容器隔离 |
| 数据存储 | PostgreSQL（元数据）+ MongoDB（抓取数据） |
| 任务队列 | Celery + RabbitMQ |
| 框架支持 | 多框架模板（httpx、Scrapy、Playwright） |
| 代理管理 | 内置代理池（健康检查 + 自动轮换） |
| 定时调度 | Cron 表达式（Celery Beat） |
| 监控告警 | 完整系统（仪表盘 + 邮件/Webhook 通知） |
| 数据导出 | JSON、CSV、Excel |
| 代码编辑 | Monaco Editor |
| 工作流 | 暂不规划 |

## 技术栈

- **后端**：FastAPI + SQLAlchemy + Celery + Docker SDK
- **前端**：Next.js 15 + React 19 + Monaco Editor + ECharts
- **存储**：PostgreSQL + MongoDB + Redis
- **消息队列**：RabbitMQ
- **容器**：Docker

## 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        CrawlHub 架构                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐                                                │
│  │ Admin 前端  │  Next.js 15 + Monaco Editor                    │
│  │ (管理控制台) │  爬虫管理 / 任务监控 / 数据查看                   │
│  └──────┬──────┘                                                │
│         │ REST API                                              │
│  ┌──────▼──────┐     ┌─────────────┐     ┌─────────────┐       │
│  │  FastAPI    │────▶│  RabbitMQ   │────▶│   Worker    │       │
│  │  后端服务   │     │  消息队列    │     │  (Celery)   │       │
│  └──────┬──────┘     └─────────────┘     └──────┬──────┘       │
│         │                                        │              │
│  ┌──────▼──────┐                         ┌──────▼──────┐       │
│  │ PostgreSQL  │                         │   Docker    │       │
│  │  元数据存储  │                         │  爬虫容器   │       │
│  └─────────────┘                         └──────┬──────┘       │
│                                                  │              │
│  ┌─────────────┐     ┌─────────────┐            │              │
│  │   Redis     │     │   MongoDB   │◀───────────┘              │
│  │  缓存/调度   │     │  抓取数据   │                           │
│  └─────────────┘     └─────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

## 数据模型

### PostgreSQL 元数据表

#### Project（项目）
| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | 主键 |
| name | String | 项目名称 |
| description | Text | 项目描述 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### Spider（爬虫）
| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | 主键 |
| project_id | UUID | 关联项目 |
| name | String | 爬虫名称 |
| description | Text | 爬虫描述 |
| script_type | String | 脚本类型（httpx/scrapy/playwright） |
| script_content | Text | 脚本内容 |
| template | String | 使用的模板 |
| cron_expr | String | Cron 表达式 |
| is_active | Boolean | 是否启用 |
| config | JSON | 配置信息 |

#### Task（任务）
| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | 主键 |
| spider_id | UUID | 关联爬虫 |
| status | String | 状态（pending/running/completed/failed/cancelled） |
| progress | Integer | 进度百分比 |
| total_count | Integer | 总数量 |
| success_count | Integer | 成功数量 |
| failed_count | Integer | 失败数量 |
| started_at | DateTime | 开始时间 |
| finished_at | DateTime | 结束时间 |
| worker_id | String | 执行的 Worker |
| container_id | String | Docker 容器 ID |
| error_message | Text | 错误信息 |

#### Proxy（代理）
| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | 主键 |
| host | String | 主机地址 |
| port | Integer | 端口 |
| protocol | String | 协议（http/https/socks5） |
| username | String | 用户名 |
| password | String | 密码 |
| status | String | 状态（active/inactive/cooldown） |
| last_check_at | DateTime | 最后检测时间 |
| success_rate | Float | 成功率 |

#### Schedule（调度）
| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | 主键 |
| spider_id | UUID | 关联爬虫 |
| cron_expr | String | Cron 表达式 |
| is_active | Boolean | 是否启用 |
| next_run_at | DateTime | 下次执行时间 |
| last_run_at | DateTime | 上次执行时间 |

#### Worker（工作节点）
| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | 主键 |
| hostname | String | 主机名 |
| ip_address | String | IP 地址 |
| status | String | 状态（online/offline） |
| last_heartbeat | DateTime | 最后心跳时间 |
| max_concurrent | Integer | 最大并发数 |
| current_tasks | Integer | 当前任务数 |

#### Alert（告警）
| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | 主键 |
| type | String | 告警类型 |
| level | String | 告警级别（warning/error） |
| message | Text | 告警信息 |
| task_id | UUID | 关联任务 |
| is_read | Boolean | 是否已读 |
| created_at | DateTime | 创建时间 |

### MongoDB 抓取数据集合

```javascript
// spider_data 集合
{
  _id: ObjectId,
  task_id: String,        // 关联 PostgreSQL Task.id
  spider_id: String,      // 关联 PostgreSQL Spider.id
  url: String,            // 抓取的 URL
  data: Object,           // 实际抓取的数据（动态结构）
  response_time: Number,  // 响应时间(ms)
  status: String,         // success / failed
  error: String,          // 错误信息
  created_at: DateTime
}
```

## 爬虫执行流程

```
1. 任务触发
   ┌─────────┐      ┌─────────┐      ┌─────────────┐
   │ 手动执行 │  或  │ 定时调度 │ ───▶ │ 创建 Task   │
   └─────────┘      │(CeleryBeat)│    │ status=pending│
                    └─────────┘      └──────┬──────┘
                                            │
2. 任务分发                                  ▼
   ┌─────────────────────────────────────────────────┐
   │              RabbitMQ 任务队列                   │
   └────────────────────┬────────────────────────────┘
                        │
3. Worker 消费          ▼
   ┌─────────────────────────────────────────────────┐
   │  Celery Worker (可多节点部署)                    │
   │  1. 获取 Spider 配置和脚本                       │
   │  2. 选择/分配代理                               │
   │  3. 构建 Docker 镜像（如需）                     │
   │  4. 启动 Docker 容器                            │
   │  5. 监控容器状态和输出                           │
   │  6. 收集结果写入 MongoDB                        │
   │  7. 更新 Task 状态和统计                        │
   └─────────────────────────────────────────────────┘
                        │
4. Docker 容器执行      ▼
   ┌─────────────────────────────────────────────────┐
   │  Docker Container (隔离环境)                    │
   │  - 预装 Python + 爬虫框架                       │
   │  - 挂载用户脚本                                 │
   │  - 资源限制 (CPU/Memory/Network)               │
   │  - 超时控制                                     │
   │  - stdout/stderr 输出到指定路径                 │
   └─────────────────────────────────────────────────┘
```

## Docker 基础镜像

```dockerfile
# crawlhub/spider-base:latest
FROM python:3.11-slim

# 安装系统依赖（Playwright 浏览器需要）
RUN apt-get update && apt-get install -y \
    wget curl gnupg \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# 预装常用爬虫框架
RUN pip install --no-cache-dir \
    scrapy==2.11 \
    playwright==1.40 \
    httpx==0.26 \
    beautifulsoup4==4.12 \
    lxml==5.1 \
    parsel==1.8

# 安装 Playwright 浏览器
RUN playwright install chromium

# 工作目录
WORKDIR /spider
```

## 脚本模板

### httpx 模板

```python
import httpx
from bs4 import BeautifulSoup
import json

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
        # 用户自定义解析逻辑
        data = {"title": soup.title.string}
        results.append({"url": url, "data": data})

    return results
```

### Playwright 模板

```python
from playwright.sync_api import sync_playwright

def run(config):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(proxy={"server": config.get("proxy")})
        page = browser.new_page()

        for url in config["urls"]:
            page.goto(url)
            # 用户自定义交互和解析逻辑
            data = {"title": page.title()}
            results.append({"url": url, "data": data})

        browser.close()
    return results
```

### 脚本输入输出约定

- **输入**：通过环境变量或 JSON 文件传入 `config`
- **输出**：结果写入 `/spider/output.json`，日志写入 stdout/stderr

## 代理池管理

### 代理状态流转

```
    ┌─────────┐
    │ 新增录入 │
    └────┬────┘
         │
         ▼
    ┌─────────┐    检测失败(连续3次)    ┌─────────┐
    │  active │ ─────────────────────▶ │ inactive │
    │  (可用)  │                        │  (禁用)  │
    └────┬────┘ ◀───────────────────── └─────────┘
         │           手动启用/检测恢复
         │
         │ 任务使用
         ▼
    ┌─────────┐    冷却结束(30s)
    │ cooldown│ ───────────────┐
    │ (冷却中) │                │
    └─────────┘ ◀──────────────┘
```

### 代理分配策略

```python
class ProxyPool:
    def get_proxy(self, region=None, min_success_rate=0.8):
        """
        获取可用代理
        1. 过滤 status=active 且不在冷却中
        2. 按 region 筛选（可选）
        3. 过滤 success_rate >= min_success_rate
        4. 加权随机选择（成功率高的权重大）
        5. 标记为冷却状态，防止短时间重复使用
        """
        pass

    def report_result(self, proxy_id, success: bool):
        """
        上报使用结果，更新成功率
        """
        pass
```

### 健康检查机制

- Celery Beat 定时任务，每 5 分钟检查所有 active 代理
- 检测目标：可配置的测试 URL（默认 httpbin.org）
- 超时阈值：10 秒
- 连续失败 3 次自动标记为 inactive

## 监控与告警系统

### 告警规则

| 告警类型 | 触发条件 | 级别 |
|---------|---------|------|
| 任务失败 | 单个任务执行失败 | WARNING |
| 连续失败 | 同一爬虫连续失败 3 次 | ERROR |
| Worker 离线 | 心跳超时 60 秒 | ERROR |
| 代理池耗尽 | 可用代理 < 10% | ERROR |
| 任务积压 | 排队任务 > 100 且持续 10 分钟 | WARNING |

### 通知渠道

- 邮件（SMTP，复用 fastapi-template 已有服务）
- Webhook（自定义 URL）

### Worker 心跳机制

- Worker 启动时注册到数据库
- 每 15 秒上报心跳（last_heartbeat, current_tasks, cpu/memory）
- 优雅退出时注销

## API 设计

```
/api/v1/
├── /projects          # 项目管理
│   ├── GET    /                   # 项目列表
│   ├── POST   /                   # 创建项目
│   ├── GET    /{id}               # 项目详情
│   ├── PUT    /{id}               # 更新项目
│   └── DELETE /{id}               # 删除项目
│
├── /spiders           # 爬虫管理
│   ├── GET    /                   # 爬虫列表
│   ├── POST   /                   # 创建爬虫
│   ├── GET    /{id}               # 爬虫详情
│   ├── PUT    /{id}               # 更新爬虫
│   ├── DELETE /{id}               # 删除爬虫
│   ├── POST   /{id}/run           # 立即执行
│   ├── GET    /{id}/logs          # 执行日志
│   └── GET    /templates          # 获取脚本模板
│
├── /tasks             # 任务管理
│   ├── GET    /                   # 任务列表
│   ├── GET    /{id}               # 任务详情
│   ├── POST   /{id}/cancel        # 取消任务
│   ├── POST   /{id}/retry         # 重试任务
│   └── GET    /{id}/logs          # 实时日志
│
├── /data              # 数据管理
│   ├── GET    /                   # 数据列表
│   ├── GET    /{id}               # 数据详情
│   ├── DELETE /                   # 批量删除
│   └── GET    /export             # 导出数据
│
├── /proxies           # 代理管理
│   ├── GET    /                   # 代理列表
│   ├── POST   /                   # 添加代理
│   ├── POST   /batch              # 批量导入
│   ├── PUT    /{id}               # 更新代理
│   ├── DELETE /{id}               # 删除代理
│   ├── POST   /{id}/check         # 检测单个
│   └── POST   /check-all          # 检测所有
│
├── /schedules         # 调度管理
│   ├── GET    /                   # 调度列表
│   ├── POST   /                   # 创建调度
│   ├── PUT    /{id}               # 更新调度
│   ├── DELETE /{id}               # 删除调度
│   └── POST   /{id}/toggle        # 启用/禁用
│
├── /workers           # 节点管理
│   └── GET    /                   # Worker 状态
│
├── /alerts            # 告警管理
│   ├── GET    /                   # 告警列表
│   ├── POST   /{id}/read          # 标记已读
│   └── GET    /settings           # 告警配置
│
└── /dashboard         # 仪表盘
    ├── GET    /stats              # 统计数据
    └── GET    /trends             # 趋势数据
```

## 后端目录结构

```
app/
├── routers/
│   └── admin/
│       ├── projects.py
│       ├── spiders.py
│       ├── tasks.py
│       ├── data.py
│       ├── proxies.py
│       ├── schedules.py
│       ├── workers.py
│       ├── alerts.py
│       └── dashboard.py
├── models/
│   ├── project.py
│   ├── spider.py
│   ├── task.py
│   ├── proxy.py
│   ├── schedule.py
│   ├── worker.py
│   └── alert.py
├── services/
│   ├── spider_service.py
│   ├── task_service.py
│   ├── proxy_service.py
│   ├── schedule_service.py
│   └── alert_service.py
├── tasks/
│   ├── spider_task.py
│   ├── proxy_check_task.py
│   └── alert_task.py
└── extensions/
    └── ext_mongodb.py
```

## 前端页面结构

```
admin/app/
├── (commonLayout)/
│   └── platform/
│       └── crawlhub/
│           ├── dashboard/         # 仪表盘
│           ├── projects/          # 项目管理
│           ├── spiders/           # 爬虫管理
│           │   ├── page.tsx       # 列表
│           │   ├── new/           # 新建
│           │   └── [id]/          # 详情/编辑
│           ├── tasks/             # 任务管理
│           ├── data/              # 数据管理
│           ├── proxies/           # 代理管理
│           ├── schedules/         # 调度管理
│           ├── workers/           # 节点监控
│           └── alerts/            # 告警中心
```

## 开发阶段规划

### Phase 1: 基础框架
- 项目初始化（从 fastapi-template）
- MongoDB 集成
- 基础数据模型（Project, Spider, Task）
- 项目/爬虫 CRUD API
- 前端基础页面框架

### Phase 2: 核心爬虫功能
- Docker 基础镜像构建
- 脚本模板（httpx, Scrapy, Playwright）
- Celery 任务执行逻辑
- 容器生命周期管理
- 结果收集写入 MongoDB
- 在线代码编辑器集成

### Phase 3: 代理与调度
- 代理池管理（CRUD + 批量导入）
- 代理健康检查
- 代理分配策略
- Cron 调度（Celery Beat）
- 调度管理界面

### Phase 4: 监控与告警
- Worker 注册与心跳
- 监控仪表盘
- 告警规则引擎
- 邮件/Webhook 通知
- 告警管理界面

### Phase 5: 数据管理
- 数据查看界面
- 数据筛选与分页
- 多格式导出（JSON/CSV/Excel）
- 数据批量删除

### Phase 6: 完善与优化
- 任务日志实时查看
- 脚本调试/测试运行
- 错误处理优化
- 性能优化
- 文档完善

## 项目初始化步骤

```bash
# 1. 克隆 fastapi-template 作为 CrawlHub 基础
git clone git@github.com:jeryfan/fastapi-template.git crawlhub
cd crawlhub

# 2. 移除用户端前端
rm -rf web/

# 3. 更新项目配置
#    - 修改项目名称为 CrawlHub
#    - 更新 docker-compose.yml 移除 web 服务
#    - 添加 MongoDB 服务配置

# 4. 初始化新的 Git 仓库
rm -rf .git
git init
git add .
git commit -m "feat: 初始化 CrawlHub 爬虫管理平台"
```
