from fastapi.exceptions import HTTPException
from enums.response_code import ResponseCode


class BaseHTTPException(HTTPException):
    error_code: int = ResponseCode.FAIL
    data: dict | None = None

    def __init__(
        self,
        status_code: int,
        message: str | None = None,
        error_code: int | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.error_code = error_code if error_code is not None else self.__class__.error_code
        if self.error_code is None:
            self.error_code = status_code

        self.data = {
            "code": self.error_code,
            "msg": self.detail,
            "data": None,
        }
