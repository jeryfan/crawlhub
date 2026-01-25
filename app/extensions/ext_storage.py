import logging
from collections.abc import Callable, AsyncGenerator
from typing import Literal, Union, overload
from configs import app_config
from fastapi import FastAPI
from extensions.storage.base_storage import BaseStorage
from extensions.storage.storage_type import StorageType

logger = logging.getLogger(__name__)


class Storage:
    def init_app(self):
        storage_factory = self.get_storage_factory(app_config.STORAGE_TYPE)
        self.storage_runner = storage_factory()

    @staticmethod
    def get_storage_factory(storage_type: str) -> Callable[[], BaseStorage]:
        match storage_type:
            case StorageType.OPENDAL:
                from extensions.storage.opendal_storage import AsyncOpenDALStorage

                return lambda: AsyncOpenDALStorage(app_config.OPENDAL_SCHEME)
            case StorageType.LOCAL:
                from extensions.storage.opendal_storage import AsyncOpenDALStorage

                return lambda: AsyncOpenDALStorage(scheme="fs", root=app_config.STORAGE_LOCAL_PATH)

            case _:
                raise ValueError(f"unsupported storage type {storage_type}")

    async def save(self, filename: str, data: bytes):
        await self.storage_runner.save(filename, data)

    @overload
    async def load(self, filename: str, /, *, stream: Literal[False] = False) -> bytes: ...

    @overload
    async def load(self, filename: str, /, *, stream: Literal[True]) -> AsyncGenerator: ...

    async def load(self, filename: str, /, *, stream: bool = False) -> Union[bytes, AsyncGenerator]:
        if stream:
            return self.load_stream(filename)
        else:
            return await self.load_once(filename)

    async def load_once(self, filename: str) -> bytes:
        return await self.storage_runner.load_once(filename)

    def load_stream(self, filename: str) -> AsyncGenerator:
        return self.storage_runner.load_stream(filename)

    async def download(self, filename, target_filepath):
        await self.storage_runner.download(filename, target_filepath)

    async def exists(self, filename):
        return await self.storage_runner.exists(filename)

    async def delete(self, filename: str):
        return await self.storage_runner.delete(filename)

    async def list(self, path: str, files: bool = True, directories: bool = False) -> list[str]:
        return await self.storage_runner.list(path, files=files, directories=directories)


storage = Storage()


def init_app(app: FastAPI):
    storage.init_app()
    app.state.storage = storage
