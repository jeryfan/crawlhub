from pydantic import Field
from pydantic_settings import SettingsConfigDict

from configs.common import CommonConfig
from configs.deploy import DeploymentConfig
from configs.feature import FeatureConfig
from configs.middleware import MiddlewareConfig
from configs.packaging import PackagingInfo
from configs.payment import PaymentConfig


class AppConfig(
    MiddlewareConfig, CommonConfig, FeatureConfig, PackagingInfo, DeploymentConfig, PaymentConfig
):
    PROJECT_NAME: str = Field(default="fastapi")

    model_config = SettingsConfigDict(
        # read from dotenv format config file
        env_file=".env",
        env_file_encoding="utf-8",
        # ignore extra attributes
        extra="ignore",
    )


app_config: AppConfig = AppConfig()

__all__ = ["app_config"]
