# app/services/crawlhub/spider_runner_service.py
import asyncio
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from models.crawlhub import ProjectSource, Spider, SpiderTask, SpiderTaskStatus
from services.base_service import BaseService

logger = logging.getLogger(__name__)


class SpiderRunnerService(BaseService):

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

    async def create_task(self, spider: Spider, trigger_type: str = "manual") -> SpiderTask:
        """创建爬虫任务"""
        task = SpiderTask(
            spider_id=spider.id,
            status=SpiderTaskStatus.PENDING,
            is_test=False,
            trigger_type=trigger_type,
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
                await self.prepare_from_deployment(spider, work_dir)

                cmd = self._build_command(spider, work_dir)

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

                stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
                stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""

                if process.returncode == 0:
                    task.status = SpiderTaskStatus.COMPLETED
                    await self._store_spider_data(task, stdout_str)
                else:
                    task.status = SpiderTaskStatus.FAILED
                    task.error_message = f"进程退出码: {process.returncode}"
                    if stderr_str:
                        task.error_message += f"\n{stderr_str[:2000]}"

                await self._store_task_log(task, stdout_str, stderr_str)

        except Exception as e:
            task.status = SpiderTaskStatus.FAILED
            task.error_message = str(e)
        finally:
            task.finished_at = datetime.utcnow()
            await self.db.commit()

    async def prepare_project_files(self, spider: Spider, work_dir: Path) -> None:
        """准备项目文件到工作目录（测试运行用）

        代码来源优先级:
        1. 如果有 Coder Workspace 且正在运行 -> 从 Workspace 拉取
        2. 如果有 script_content -> 写入 main.py
        3. 否则抛出错误
        """
        if spider.coder_workspace_id:
            try:
                await self._pull_from_workspace(spider, work_dir)
                return
            except Exception as e:
                logger.warning(
                    f"Failed to pull from workspace, falling back to script_content: {e}"
                )

        if spider.script_content:
            main_file = work_dir / "main.py"
            main_file.write_text(spider.script_content)
            return

        raise ValueError("爬虫没有可执行的代码（无工作区且无 script_content）")

    async def _pull_from_workspace(self, spider: Spider, work_dir: Path) -> None:
        """从 Workspace 拉取项目文件"""
        import re
        from services.crawlhub.coder_workspace_service import CoderWorkspaceService
        from services.crawlhub.filebrowser_service import FileBrowserService

        ws_service = CoderWorkspaceService(self.db)
        try:
            workspace = await ws_service.ensure_workspace_running(spider)
            await ws_service.wait_for_workspace_ready(spider.coder_workspace_id, timeout=60)
        finally:
            await ws_service.close()

        fb_service = FileBrowserService()
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", spider.name)
        project_path = f"/workspace/{safe_name}"

        files = await fb_service.download_project(workspace, project_path)
        if not files:
            raise ValueError(f"工作区项目目录为空: {project_path}")

        for rel_path, content in files.items():
            target = work_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    async def prepare_from_deployment(self, spider: Spider, work_dir: Path) -> None:
        """从部署快照准备项目文件（生产执行用）

        优先级:
        1. 有 active_deployment_id -> 从 GridFS 下载快照
        2. 有 script_content -> 写入 main.py
        3. 否则抛出错误
        """
        if spider.active_deployment_id:
            from services.crawlhub.deployment_service import DeploymentService

            deployment = await DeploymentService(self.db).get_deployment(
                spider.active_deployment_id
            )
            if deployment:
                archive = await DeploymentService.download_archive(deployment.file_archive_id)
                await DeploymentService.extract_archive(archive, work_dir)
                return

        if spider.script_content:
            main_file = work_dir / "main.py"
            main_file.write_text(spider.script_content)
            return

        raise ValueError("爬虫没有可执行的代码（无部署快照且无 script_content）")

    def _build_command(self, spider: Spider, work_dir: Path) -> list[str]:
        """构建执行命令"""
        if spider.source == ProjectSource.SCRAPY:
            return ["scrapy", "crawl", spider.name]

        # 检查入口点配置
        entry_point = spider.entry_point or "main:run"
        module, _, func_name = entry_point.partition(":")
        if not func_name:
            func_name = "run"

        return ["python", "-c", f"""
import sys, json
sys.path.insert(0, '{work_dir}')
from {module} import {func_name}
result = {func_name}({{}})
if result is not None:
    print(json.dumps(result, ensure_ascii=False, default=str))
"""]

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

        stdout_lines = []
        stderr_lines = []

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                work_dir = Path(temp_dir)

                # 准备文件
                await self.prepare_project_files(spider, work_dir)

                yield {"event": "status", "data": {"status": "preparing", "message": "准备执行环境..."}}

                cmd = self._build_command(spider, work_dir)

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
                        decoded_line = line.decode("utf-8", errors="replace").rstrip()
                        if event_type == "stdout":
                            stdout_lines.append(decoded_line)
                        else:
                            stderr_lines.append(decoded_line)
                        yield {
                            "event": event_type,
                            "data": {
                                "line": decoded_line,
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

            # 持久化日志到 MongoDB
            await self._store_task_log(
                task,
                "\n".join(stdout_lines),
                "\n".join(stderr_lines),
            )

            # 存储测试数据
            if task.status == SpiderTaskStatus.COMPLETED:
                await self._store_spider_data(task, "\n".join(stdout_lines))

            duration = (task.finished_at - task.started_at).total_seconds() if task.started_at else 0
            yield {
                "event": "status",
                "data": {
                    "status": task.status.value,
                    "duration": duration,
                }
            }

    async def _store_spider_data(self, task: SpiderTask, stdout: str) -> None:
        """将爬取结果存入 MongoDB spider_data"""
        from extensions.ext_mongodb import mongodb_client

        if not mongodb_client.is_enabled():
            return

        try:
            output = stdout.strip()
            if not output:
                return

            data = json.loads(output)
            collection = mongodb_client.get_collection("spider_data")

            if isinstance(data, list):
                docs = [{
                    "task_id": str(task.id),
                    "spider_id": str(task.spider_id),
                    "data": item,
                    "is_test": task.is_test,
                    "created_at": datetime.utcnow(),
                } for item in data]
                if docs:
                    await collection.insert_many(docs)
                    task.total_count = len(docs)
                    task.success_count = len(docs)
            elif isinstance(data, dict):
                await collection.insert_one({
                    "task_id": str(task.id),
                    "spider_id": str(task.spider_id),
                    "data": data,
                    "is_test": task.is_test,
                    "created_at": datetime.utcnow(),
                })
                task.total_count = 1
                task.success_count = 1
        except json.JSONDecodeError:
            pass  # stdout 不是 JSON，跳过
        except Exception as e:
            logger.warning(f"Failed to store spider data for task {task.id}: {e}")

    async def _store_task_log(self, task: SpiderTask, stdout: str, stderr: str) -> None:
        """存储任务日志到 MongoDB"""
        from services.crawlhub.log_service import LogService

        log_service = LogService()
        await log_service.store_log(
            task_id=task.id,
            spider_id=task.spider_id,
            stdout=stdout,
            stderr=stderr,
        )
