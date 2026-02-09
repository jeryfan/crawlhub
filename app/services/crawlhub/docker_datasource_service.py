import asyncio
import logging
import secrets
import string

from models.crawlhub.datasource import DataSource, DataSourceMode, DataSourceStatus, DataSourceType

logger = logging.getLogger(__name__)


class DockerDataSourceManager:
    """Docker 容器管理服务（托管数据源）"""

    DEFAULT_IMAGES = {
        DataSourceType.POSTGRESQL: "postgres:16-alpine",
        DataSourceType.MYSQL: "mysql:8.0",
        DataSourceType.MONGODB: "mongo:7",
    }

    DEFAULT_PORTS = {
        DataSourceType.POSTGRESQL: 5432,
        DataSourceType.MYSQL: 3306,
        DataSourceType.MONGODB: 27017,
    }

    @staticmethod
    def _generate_password(length: int = 16) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def _get_docker_client():
        import docker
        return docker.from_env()

    async def create_container(self, datasource: DataSource) -> dict:
        """创建 Docker 容器"""
        ds_type = datasource.type
        image = datasource.docker_image or self.DEFAULT_IMAGES.get(ds_type)
        if not image:
            raise ValueError(f"不支持的数据源类型: {ds_type}")

        password = self._generate_password()
        container_name = f"crawlhub-ds-{str(datasource.id)[:8]}"
        internal_port = self.DEFAULT_PORTS[ds_type]

        env_vars = {}
        username = "crawlhub"
        database = "crawlhub_data"

        if ds_type == DataSourceType.POSTGRESQL:
            env_vars = {
                "POSTGRES_USER": username,
                "POSTGRES_PASSWORD": password,
                "POSTGRES_DB": database,
            }
        elif ds_type == DataSourceType.MYSQL:
            env_vars = {
                "MYSQL_ROOT_PASSWORD": password,
                "MYSQL_USER": username,
                "MYSQL_PASSWORD": password,
                "MYSQL_DATABASE": database,
            }
        elif ds_type == DataSourceType.MONGODB:
            env_vars = {
                "MONGO_INITDB_ROOT_USERNAME": username,
                "MONGO_INITDB_ROOT_PASSWORD": password,
                "MONGO_INITDB_DATABASE": database,
            }

        def _create():
            client = self._get_docker_client()
            # 尝试获取 app 所在的网络
            network_name = "crawlhub_default"
            try:
                client.networks.get(network_name)
            except Exception:
                network_name = None

            container = client.containers.run(
                image,
                name=container_name,
                detach=True,
                environment=env_vars,
                ports={f"{internal_port}/tcp": None},  # 随机端口映射
                restart_policy={"Name": "unless-stopped"},
                network=network_name,
            )
            container.reload()

            # 获取映射端口
            port_bindings = container.attrs["NetworkSettings"]["Ports"]
            mapped_port = None
            key = f"{internal_port}/tcp"
            if key in port_bindings and port_bindings[key]:
                mapped_port = int(port_bindings[key][0]["HostPort"])

            return {
                "container_id": container.id,
                "container_name": container_name,
                "host": container_name,  # Docker 内部网络可通过容器名访问
                "port": internal_port,
                "mapped_port": mapped_port,
                "username": username,
                "password": password,
                "database": database,
            }

        return await asyncio.to_thread(_create)

    async def start_container(self, container_id: str) -> None:
        def _start():
            client = self._get_docker_client()
            container = client.containers.get(container_id)
            container.start()
        await asyncio.to_thread(_start)

    async def stop_container(self, container_id: str) -> None:
        def _stop():
            client = self._get_docker_client()
            container = client.containers.get(container_id)
            container.stop(timeout=10)
        await asyncio.to_thread(_stop)

    async def remove_container(self, container_id: str, remove_volume: bool = False) -> None:
        def _remove():
            client = self._get_docker_client()
            container = client.containers.get(container_id)
            container.remove(force=True, v=remove_volume)
        await asyncio.to_thread(_remove)

    async def get_container_status(self, container_id: str) -> str:
        def _status():
            client = self._get_docker_client()
            try:
                container = client.containers.get(container_id)
                return container.status  # running, exited, etc.
            except Exception:
                return "not_found"
        return await asyncio.to_thread(_status)
