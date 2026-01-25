from pydantic import Field
from pydantic_settings import BaseSettings


class OpenDALStorageConfig(BaseSettings):
    OPENDAL_SCHEME: str = Field(
        default="fs",
        description="OpenDAL scheme.",
    )
    OPENDAL_ROOT: str = Field(
        default="/www",
        description="Root path for filesystem storage in OpenDAL.",
    )
