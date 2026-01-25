from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from constants import HIDDEN_VALUE


class APIBasedExtensionPayload(BaseModel):
    name: str = Field(description="Extension name")
    api_endpoint: str = Field(description="API endpoint URL")
    api_key: str = Field(description="API key for authentication")


class APIBasedExtensionResponse(BaseModel):
    """Response model for API-based extension."""

    id: str
    tenant_id: str
    name: str
    api_endpoint: str
    api_key: str = HIDDEN_VALUE
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CodeBasedExtensionQuery(BaseModel):
    module: str


class CodeBasedExtensionResponse(BaseModel):
    """Response model for code-based extension."""

    module: str
    data: dict
