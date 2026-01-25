# CrawlHub

通用爬虫管理平台，支持数据抓取、数据入库、数据可视化、数据检索等功能。

## 特性

- **Python 脚本沙箱**：支持在线编辑和上传爬虫脚本
- **Docker 容器隔离**：每个爬虫任务在独立容器中安全执行
- **多框架模板**：预置 httpx、Scrapy、Playwright 模板
- **内置代理池**：代理录入、健康检查、自动轮换
- **Cron 定时调度**：基于 Celery Beat 的定时任务
- **完整监控告警**：任务状态、节点健康、邮件/Webhook 通知
- **多格式数据导出**：JSON、CSV、Excel

## 技术栈

- **后端**：FastAPI + SQLAlchemy + Celery + Docker SDK
- **前端**：Next.js 15 + React 19 + Monaco Editor + ECharts
- **存储**：PostgreSQL + MongoDB + Redis
- **消息队列**：RabbitMQ

## 快速开始

```bash
# 安装后端依赖
cd app && uv sync

# 安装前端依赖
cd admin && pnpm install

# 启动开发环境
make dev-setup
```

## 文档

- [设计文档](docs/plans/2026-01-25-crawlhub-design.md)

## License

MIT
