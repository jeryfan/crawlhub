import logging

from sqlalchemy import func, select

from models.crawlhub import Spider, ScriptType, ProjectSource
from schemas.crawlhub import SpiderCreate, SpiderUpdate
from services.base_service import BaseService

from .coder_workspace_service import CoderWorkspaceService

logger = logging.getLogger(__name__)


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

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

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

    async def create(self, data: SpiderCreate, create_workspace: bool = True) -> Spider:
        """创建爬虫

        Args:
            data: 爬虫创建数据
            create_workspace: 是否自动创建 Coder 工作区
        """
        spider = Spider(**data.model_dump())
        self.db.add(spider)
        await self.db.commit()
        await self.db.refresh(spider)

        # 为所有类型的爬虫创建 Coder 工作区
        if create_workspace:
            try:
                workspace_service = CoderWorkspaceService(self.db)
                # 使用 spider 的 source 字段，如果是 scrapy 类型且 source 为 empty，则自动设为 scrapy
                source = data.source.value if data.source else "empty"
                if source == "empty" and data.script_type == ScriptType.SCRAPY:
                    source = "scrapy"
                git_repo = data.git_repo if data.source == ProjectSource.GIT else None
                await workspace_service.create_workspace_for_spider(
                    spider, source=source, git_repo=git_repo
                )
                await workspace_service.close()
                # 刷新 spider 以获取更新后的 workspace 字段
                await self.db.refresh(spider)
            except Exception as e:
                # 工作区创建失败不影响爬虫创建
                logger.warning(f"Failed to create workspace for spider {spider.id}: {e}")

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

        # 删除关联的 Coder 工作区
        if spider.coder_workspace_id:
            try:
                workspace_service = CoderWorkspaceService(self.db)
                await workspace_service.delete_workspace(spider)
                await workspace_service.close()
            except Exception as e:
                # 工作区删除失败不影响爬虫删除
                logger.warning(f"Failed to delete workspace for spider {spider_id}: {e}")

        await self.db.delete(spider)
        await self.db.commit()
        return True

    def get_templates(self) -> dict[str, str]:
        """获取脚本模板"""
        return {
            "httpx": '''import httpx
from bs4 import BeautifulSoup

def run(config):
    results = []
    client = httpx.Client(proxy=config.get("proxy"))

    for url in config["urls"]:
        resp = client.get(url, headers=config.get("headers", {}))
        soup = BeautifulSoup(resp.text, "lxml")
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
        yield {
            "url": response.url,
            "title": response.css("title::text").get(),
        }
''',
            "playwright": '''from playwright.sync_api import sync_playwright

def run(config):
    results = []

    with sync_playwright() as p:
        browser_args = {}
        if config.get("proxy"):
            browser_args["proxy"] = {"server": config["proxy"]}

        browser = p.chromium.launch(**browser_args)
        page = browser.new_page()

        for url in config["urls"]:
            page.goto(url)
            data = {"title": page.title()}
            results.append({"url": url, "data": data})

        browser.close()

    return results
''',
        }
