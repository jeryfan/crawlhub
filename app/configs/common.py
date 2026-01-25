from pydantic import Field, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings


class CommonConfig(BaseSettings):
    PASSWORD_REGEX: str = Field(
        description="Regular expression for validating passwords",
        default=r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$",
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: PositiveInt = Field(
        description="Expiration time for access tokens in minutes",
        default=60,
    )

    REFRESH_TOKEN_EXPIRE_DAYS: PositiveFloat = Field(
        description="Expiration time for refresh tokens in days",
        default=30,
    )

    # CDN Configuration (optional)
    CDN_DOMAIN: str = Field(default="", description="CDN 域名（用于加速文件访问）")

    # CORS Configuration
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001",
        description="Comma-separated list of allowed CORS origins",
    )

    MAX_FILE_SIZE: PositiveInt = Field(
        default=50 * 1024 * 1024,
        description="Maximum file upload size in bytes",
    )
