# app/services/crawlhub/spider_runner_service.py
import asyncio
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from models.crawlhub import ProjectSource, Spider, SpiderTask, SpiderTaskStatus
from services.base_service import BaseService

logger = logging.getLogger(__name__)

SDK_SOURCE_PATH = Path(__file__).parent.parent.parent / "libs" / "crawlhub_sdk" / "crawlhub.py"


class SpiderRunnerService(BaseService):

    @staticmethod
    def _make_preexec_fn(memory_limit_mb: int | None = None):
        """Create preexec_fn for subprocess resource limits"""
        def preexec():
            import resource
            if memory_limit_mb:
                limit_bytes = memory_limit_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
        return preexec if memory_limit_mb else None

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

    def _get_spider_env(self, spider: Spider, task: SpiderTask) -> dict:
        """构建爬虫进程的环境变量"""
        env = os.environ.copy()
        env["CRAWLHUB_TASK_ID"] = str(task.id)
        env["CRAWLHUB_SPIDER_ID"] = str(spider.id)
        env["CRAWLHUB_API_URL"] = os.getenv(
            "CRAWLHUB_INTERNAL_API_URL", "http://localhost:8000/platform/api"
        )

        # 代理注入
        if spider.proxy_enabled:
            proxy_url = self._get_proxy_url(spider)
            if proxy_url:
                env["CRAWLHUB_PROXY_URL"] = proxy_url
                env["HTTP_PROXY"] = proxy_url
                env["HTTPS_PROXY"] = proxy_url

        # 限速
        if spider.rate_limit_rps:
            env["CRAWLHUB_RATE_LIMIT"] = str(spider.rate_limit_rps)

        # 最大采集条数
        if spider.max_items:
            env["CRAWLHUB_MAX_ITEMS"] = str(spider.max_items)

        # Scrapy 特殊环境变量
        if spider.source == ProjectSource.SCRAPY:
            if spider.rate_limit_rps:
                env["SCRAPY_DOWNLOAD_DELAY"] = str(1.0 / spider.rate_limit_rps)
            if spider.autothrottle_enabled:
                env["SCRAPY_AUTOTHROTTLE_ENABLED"] = "True"

        # 自定义环境变量
        if spider.env_vars:
            try:
                custom_vars = json.loads(spider.env_vars)
                if isinstance(custom_vars, dict):
                    env.update({k: str(v) for k, v in custom_vars.items()})
            except json.JSONDecodeError:
                pass

        # 数据源连接信息注入（同步方法中不做 DB 查询，由调用方注入）
        return env

    async def _inject_datasource_env(self, spider: Spider, env: dict) -> None:
        """注入数据源连接信息到环境变量"""
        from sqlalchemy import select
        from models.crawlhub import DataSource, DataSourceStatus, SpiderDataSource

        result = await self.db.execute(
            select(SpiderDataSource, DataSource)
            .join(DataSource, SpiderDataSource.datasource_id == DataSource.id)
            .where(
                SpiderDataSource.spider_id == str(spider.id),
                SpiderDataSource.is_enabled.is_(True),
                DataSource.status == DataSourceStatus.ACTIVE,
            )
        )
        rows = result.all()
        if not rows:
            return

        ds_list = []
        for assoc, ds in rows:
            ds_list.append({
                "id": str(ds.id),
                "name": ds.name,
                "type": ds.type.value,
                "host": ds.host,
                "port": ds.port,
                "username": ds.username,
                "password": ds.password,
                "database": ds.database,
            })
        env["CRAWLHUB_DATASOURCES"] = json.dumps(ds_list, ensure_ascii=False)

    def _get_proxy_url(self, spider: Spider) -> str | None:
        """从代理池获取一个可用代理 URL"""
        # This is a sync helper; for actual use in async context,
        # proxy will be fetched asynchronously in run_spider_sync
        return None  # Placeholder; actual logic is in _get_proxy_url_async

    async def _get_proxy_url_async(self, spider: Spider) -> str | None:
        """从代理池异步获取一个可用代理"""
        from sqlalchemy import select
        from models.crawlhub.proxy import Proxy, ProxyStatus

        result = await self.db.execute(
            select(Proxy)
            .where(Proxy.status == ProxyStatus.ACTIVE)
            .order_by(Proxy.success_rate.desc())
            .limit(1)
        )
        proxy = result.scalar_one_or_none()
        if not proxy:
            return None

        auth = ""
        if proxy.username and proxy.password:
            auth = f"{proxy.username}:{proxy.password}@"
        return f"{proxy.protocol}://{auth}{proxy.host}:{proxy.port}"

    def _embed_sdk(self, work_dir: Path) -> None:
        """复制 SDK 到工作目录，使爬虫可以 from crawlhub import ..."""
        target = work_dir / "crawlhub.py"
        if SDK_SOURCE_PATH.exists():
            shutil.copy2(str(SDK_SOURCE_PATH), str(target))

    async def _install_requirements(self, spider: Spider, work_dir: Path, env: dict) -> None:
        """安装 per-spider 依赖"""
        if not spider.requirements_txt or not spider.requirements_txt.strip():
            return

        req_file = work_dir / "requirements.txt"
        req_file.write_text(spider.requirements_txt)

        deps_dir = work_dir / ".deps"
        deps_dir.mkdir(exist_ok=True)

        process = await asyncio.create_subprocess_exec(
            "pip", "install", "--target", str(deps_dir),
            "-r", str(req_file), "--quiet",
            cwd=str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(process.communicate(), timeout=120)
        except asyncio.TimeoutError:
            process.kill()
            logger.warning(f"pip install timeout for spider {spider.id}")
            return

        # Add deps to PYTHONPATH
        python_path = env.get("PYTHONPATH", "")
        if python_path:
            env["PYTHONPATH"] = f"{deps_dir}:{python_path}"
        else:
            env["PYTHONPATH"] = str(deps_dir)

    def _classify_error(self, error_msg: str, stderr: str) -> str:
        """根据错误内容自动分类"""
        combined = f"{error_msg} {stderr}".lower()
        if any(k in combined for k in ["timeout", "connectionerror", "dns", "refused", "connectionreset", "networkerror"]):
            return "network"
        if any(k in combined for k in ["httpstatuserror", "403", "429", "captcha", "unauthorized", "forbidden"]):
            return "auth"
        if any(k in combined for k in ["keyerror", "indexerror", "attributeerror", "parseerror", "jsondecodeerror", "valueerror"]):
            return "parse"
        return "system"

    async def run_spider_sync(self, spider: Spider, task: SpiderTask) -> None:
        """同步执行爬虫（用于 Celery worker 调用，不走 SSE）"""
        task.status = SpiderTaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        await self.db.commit()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                work_dir = Path(temp_dir)
                await self.prepare_from_deployment(spider, work_dir)

                # 嵌入 SDK
                self._embed_sdk(work_dir)

                # 设置输出目录
                output_dir = work_dir / "output"
                output_dir.mkdir(exist_ok=True)

                # 构建环境变量
                env = self._get_spider_env(spider, task)
                env["CRAWLHUB_OUTPUT_DIR"] = str(output_dir)

                # 代理注入（异步获取）
                if spider.proxy_enabled:
                    proxy_url = await self._get_proxy_url_async(spider)
                    if proxy_url:
                        env["CRAWLHUB_PROXY_URL"] = proxy_url
                        env["HTTP_PROXY"] = proxy_url
                        env["HTTPS_PROXY"] = proxy_url

                # 数据源连接信息注入
                await self._inject_datasource_env(spider, env)

                # 安装依赖
                await self._install_requirements(spider, work_dir, env)

                cmd = self._build_command(spider, work_dir)

                preexec = self._make_preexec_fn(spider.memory_limit_mb)
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=str(work_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                    preexec_fn=preexec,
                )

                timeout = spider.timeout_seconds or 300
                deadline = asyncio.get_event_loop().time() + timeout

                # Start reading streams concurrently
                async def read_stream(stream):
                    chunks = []
                    while True:
                        chunk = await stream.read(8192)
                        if not chunk:
                            break
                        chunks.append(chunk)
                    return b"".join(chunks)

                stdout_task = asyncio.create_task(read_stream(process.stdout))
                stderr_task = asyncio.create_task(read_stream(process.stderr))

                # Poll for completion or cancellation
                while process.returncode is None:
                    try:
                        await asyncio.wait_for(asyncio.shield(process.wait()), timeout=5.0)
                    except asyncio.TimeoutError:
                        pass

                    if process.returncode is not None:
                        break

                    # Check timeout
                    if asyncio.get_event_loop().time() > deadline:
                        process.kill()
                        await process.wait()
                        task.status = SpiderTaskStatus.FAILED
                        task.error_message = f"执行超时 (最大 {timeout} 秒)"
                        task.error_category = "system"
                        return

                    # Check cancellation
                    await self.db.refresh(task)
                    if task.status == SpiderTaskStatus.CANCELLED:
                        process.terminate()
                        await asyncio.sleep(2)
                        if process.returncode is None:
                            process.kill()
                        await process.wait()
                        task.error_message = "任务被用户取消"
                        return

                stdout_data = await stdout_task
                stderr_data = await stderr_task
                stdout_str = stdout_data.decode("utf-8", errors="replace")
                stderr_str = stderr_data.decode("utf-8", errors="replace")

                if process.returncode == 0:
                    await self._store_spider_data(task, stdout_str)
                    # 收集文件输出
                    await self._collect_file_output(task, output_dir)
                    # 状态必须在 _store_spider_data 之后设置，
                    # 因为该方法内部 refresh(task) 会从 DB 重载覆盖内存值
                    task.status = SpiderTaskStatus.COMPLETED
                else:
                    task.status = SpiderTaskStatus.FAILED
                    task.error_message = f"进程退出码: {process.returncode}"
                    if stderr_str:
                        task.error_message += f"\n{stderr_str[:2000]}"
                    task.error_category = self._classify_error(
                        task.error_message, stderr_str
                    )

                await self._store_task_log(task, stdout_str, stderr_str)

        except Exception as e:
            task.status = SpiderTaskStatus.FAILED
            task.error_message = str(e)
            task.error_category = "system"
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
        """构建执行命令（支持 async 函数自动检测）"""
        if spider.source == ProjectSource.SCRAPY:
            return ["scrapy", "crawl", spider.name]

        entry_point = spider.entry_point

        # 没有设置入口点时，直接执行 main.py
        if not entry_point:
            return ["python", str(work_dir / "main.py")]

        module, _, func_name = entry_point.partition(":")

        # 只指定了模块名（如 "main"），没有函数名
        if not func_name:
            return ["python", str(work_dir / f"{module}.py")]

        # 指定了模块和函数（如 "main:run"）
        return ["python", "-c", f"""
import sys, json, asyncio, inspect
sys.path.insert(0, '{work_dir}')
from {module} import {func_name}
result = {func_name}({{}})
if inspect.isawaitable(result):
    result = asyncio.run(result)
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

                # 嵌入 SDK
                self._embed_sdk(work_dir)

                # 设置输出目录
                output_dir = work_dir / "output"
                output_dir.mkdir(exist_ok=True)

                # 构建环境变量
                env = self._get_spider_env(spider, task)
                env["CRAWLHUB_OUTPUT_DIR"] = str(output_dir)

                # 数据源连接信息注入
                await self._inject_datasource_env(spider, env)

                # 安装依赖
                await self._install_requirements(spider, work_dir, env)

                yield {"event": "status", "data": {"status": "preparing", "message": "准备执行环境..."}}

                cmd = self._build_command(spider, work_dir)

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=str(work_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )

                timeout = spider.timeout_seconds or 300

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
                        "data": {"message": f"执行超时 (最大 {timeout} 秒)"}
                    }
                    task.status = SpiderTaskStatus.FAILED
                    task.error_message = "执行超时"
                    task.error_category = "system"
                else:
                    if process.returncode == 0:
                        task.status = SpiderTaskStatus.COMPLETED
                    else:
                        task.status = SpiderTaskStatus.FAILED
                        task.error_message = f"进程退出码: {process.returncode}"
                        stderr_str = "\n".join(stderr_lines)
                        task.error_category = self._classify_error(
                            task.error_message, stderr_str
                        )

        except Exception as e:
            task.status = SpiderTaskStatus.FAILED
            task.error_message = str(e)
            task.error_category = "system"
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
        """将爬取结果存入 MongoDB spider_data

        优先级:
        1. task.total_count > 0（SDK 已上报）→ 跳过 stdout 解析
        2. 解析 stdout 最后一行为 JSON（忽略之前的 print）
        3. 单行 stdout 整体解析（旧行为兼容）
        """
        from extensions.ext_mongodb import mongodb_client

        if not mongodb_client.is_enabled():
            return

        # 如果 SDK 已上报数据，跳过 stdout 解析
        await self.db.refresh(task)
        if task.total_count > 0:
            return

        try:
            output = stdout.strip()
            if not output:
                return

            # 优先尝试解析最后一行（兼容有 print 输出的情况）
            data = None
            lines = output.split("\n")
            if len(lines) > 1:
                last_line = lines[-1].strip()
                try:
                    data = json.loads(last_line)
                except json.JSONDecodeError:
                    pass

            # 回退到整体解析
            if data is None:
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

    async def _collect_file_output(self, task: SpiderTask, output_dir: Path) -> None:
        """收集文件输出（JSON/JSONL/CSV）到 MongoDB"""
        from extensions.ext_mongodb import mongodb_client

        if not mongodb_client.is_enabled():
            return
        if not output_dir.exists():
            return

        collection = mongodb_client.get_collection("spider_data")
        total_inserted = 0

        for file_path in output_dir.iterdir():
            if not file_path.is_file():
                continue

            try:
                items = []
                suffix = file_path.suffix.lower()

                if suffix == ".json":
                    content = file_path.read_text(encoding="utf-8")
                    data = json.loads(content)
                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict):
                        items = [data]

                elif suffix == ".jsonl":
                    for line in file_path.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line:
                            items.append(json.loads(line))

                elif suffix == ".csv":
                    import csv
                    with open(file_path, newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        items = list(reader)

                if items:
                    docs = [{
                        "task_id": str(task.id),
                        "spider_id": str(task.spider_id),
                        "data": item,
                        "is_test": task.is_test,
                        "created_at": datetime.utcnow(),
                    } for item in items]
                    await collection.insert_many(docs)
                    total_inserted += len(docs)

            except Exception as e:
                logger.warning(f"Failed to collect file output {file_path}: {e}")

        if total_inserted > 0:
            task.total_count = (task.total_count or 0) + total_inserted
            task.success_count = (task.success_count or 0) + total_inserted

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
