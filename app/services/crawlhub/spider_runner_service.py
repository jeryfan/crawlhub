# app/services/crawlhub/spider_runner_service.py
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub import ProjectType, Spider, SpiderTask, SpiderTaskStatus


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
        """准备项目文件到工作目录

        Note: 文件管理现在由 Coder 工作区处理，此方法仅用于单文件项目的 script_content。
        对于多文件项目，请使用 Coder 工作区进行开发和测试。
        """
        # 对于单文件项目，使用 script_content
        if spider.project_type == ProjectType.SINGLE_FILE and spider.script_content:
            main_file = work_dir / "main.py"
            main_file.write_text(spider.script_content)

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
