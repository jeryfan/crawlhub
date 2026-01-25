from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from configs import app_config
import logging
from schemas.response import ApiResponse
from enums.response_code import ResponseCode

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理请求数据验证失败的异常
    """
    # 从异常中提取简化的错误信息
    simplified_errors = [
        {
            "loc": ".".join(map(str, error["loc"])),
            "msg": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            code=ResponseCode.UNPROCESSABLE_ENTITY,
            msg="请求参数验证失败",
            data={"details": simplified_errors},
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    处理 HTTP 异常
    """
    code = exc.status_code

    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(code=code, msg=exc.detail, data=None).model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    捕获所有未被处理的异常
    """
    # 记录详细的异常信息到日志
    logger.exception(f"Unhandled exception on {request.method} {request.url}: {exc}")

    # 生产环境不泄露敏感异常信息
    msg = "服务器开小差了,请稍后再试"
    error_detail = None

    if app_config.DEBUG:
        # DEBUG 模式返回异常类型和消息,但不包含堆栈信息
        error_detail = {"type": type(exc).__name__, "message": str(exc)}

    return JSONResponse(
        status_code=500,
        content=ApiResponse(code=ResponseCode.FAIL, msg=msg, data=error_detail).model_dump(),
    )


def set_up(app: FastAPI):
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
