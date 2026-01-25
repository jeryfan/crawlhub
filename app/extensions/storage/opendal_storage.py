import os
from pathlib import Path
from typing import AsyncGenerator

import opendal  # type: ignore[import]
from dotenv import dotenv_values

from configs import app_config
from extensions.storage.base_storage import BaseStorage
import logging


logger = logging.getLogger(__name__)


def _get_opendal_kwargs(*, scheme: str, env_file_path: str = ".env", prefix: str = "OPENDAL_"):
    kwargs = {}
    config_prefix = prefix + scheme.upper() + "_"
    for key, value in os.environ.items():
        if key.startswith(config_prefix):
            kwargs[key[len(config_prefix) :].lower()] = value

    file_env_vars: dict = dotenv_values(env_file_path) or {}
    for key, value in file_env_vars.items():
        if (
            key.startswith(config_prefix)
            and key[len(config_prefix) :].lower() not in kwargs
            and value
        ):
            kwargs[key[len(config_prefix) :].lower()] = value

    return kwargs


class AsyncOpenDALStorage(BaseStorage):
    def __init__(self, scheme: str, **kwargs):
        kwargs = kwargs or _get_opendal_kwargs(scheme=scheme)

        if scheme == "fs":
            root = kwargs.get("root", app_config.OPENDAL_ROOT)
            Path(root).mkdir(parents=True, exist_ok=True)

        self.op = opendal.AsyncOperator(scheme=scheme, **kwargs)  # type: ignore
        logger.debug("opendal operator created with scheme %s", scheme)
        retry_layer = opendal.layers.RetryLayer(max_times=3, factor=2.0, jitter=True)
        self.op = self.op.layer(retry_layer)
        logger.debug("added retry layer to opendal operator")

    async def save(self, filename: str, data: bytes):
        await self.op.write(path=filename, bs=data)
        logger.debug("file %s saved", filename)

    async def load_once(self, filename: str) -> bytes:
        if not await self.exists(filename):
            raise FileNotFoundError("File not found")

        content: bytes = await self.op.read(path=filename)
        logger.debug("file %s loaded", filename)
        return content

    def load_stream(self, filename: str) -> AsyncGenerator:
        async def _stream():
            if not await self.exists(filename):
                raise FileNotFoundError("File not found")

            batch_size = 4096
            file = await self.op.open(path=filename, mode="rb")
            while chunk := await file.read(batch_size):
                yield chunk
            logger.debug("file %s loaded as stream", filename)

        return _stream()

    async def download(self, filename: str, target_filepath: str):
        if not await self.exists(filename):
            raise FileNotFoundError("File not found")

        with Path(target_filepath).open("wb") as f:
            f.write(await self.op.read(path=filename))
        logger.debug("file %s downloaded to %s", filename, target_filepath)

    async def exists(self, filename: str) -> bool:
        res: bool = await self.op.exists(path=filename)
        return res

    async def delete(self, filename: str):
        if await self.exists(filename):
            await self.op.delete(path=filename)
            logger.debug("file %s deleted", filename)
            return
        logger.debug("file %s not found, skip delete", filename)

    async def list(self, path: str, files: bool = True, directories: bool = False) -> list[str]:
        if not await self.exists(path):
            raise FileNotFoundError("Path not found")

        all_files = await self.op.list(path=path)
        if files and directories:
            logger.debug("files and directories on %s scanned", path)
            return [f.path async for f in all_files]
        if files:
            logger.debug("files on %s scanned", path)
            return [f.path async for f in all_files if not f.path.endswith("/")]
        elif directories:
            logger.debug("directories on %s scanned", path)
            return [f.path async for f in all_files if f.path.endswith("/")]
        else:
            raise ValueError("At least one of files or directories must be True")
