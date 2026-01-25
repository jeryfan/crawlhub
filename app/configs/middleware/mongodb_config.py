from pydantic import Field, PositiveInt, computed_field
from pydantic_settings import BaseSettings


class MongoDBConfig(BaseSettings):
    """MongoDB configuration."""

    MONGODB_ENABLED: bool = Field(
        description="Enable MongoDB.",
        default=False,
    )

    MONGODB_HOST: str = Field(
        description="MongoDB server hostname.",
        default="mongodb",
    )

    MONGODB_PORT: PositiveInt = Field(
        description="MongoDB server port.",
        default=27017,
    )

    MONGODB_USERNAME: str = Field(
        description="MongoDB authentication username.",
        default="",
    )

    MONGODB_PASSWORD: str = Field(
        description="MongoDB authentication password.",
        default="",
    )

    MONGODB_DATABASE: str = Field(
        description="MongoDB database name.",
        default="fastapi",
    )

    @computed_field
    @property
    def MONGODB_URI(self) -> str:
        """Build MongoDB connection URI from individual settings."""
        if self.MONGODB_USERNAME and self.MONGODB_PASSWORD:
            return (
                f"mongodb://{self.MONGODB_USERNAME}:{self.MONGODB_PASSWORD}"
                f"@{self.MONGODB_HOST}:{self.MONGODB_PORT}"
                f"/{self.MONGODB_DATABASE}?authSource=admin"
            )
        return f"mongodb://{self.MONGODB_HOST}:{self.MONGODB_PORT}/{self.MONGODB_DATABASE}"
