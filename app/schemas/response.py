from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from enums.response_code import ResponseCode

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = ResponseCode.SUCCESS
    msg: str = "success"
    data: T | None = None

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    code: int = ResponseCode.SUCCESS
    msg: str = "success"
