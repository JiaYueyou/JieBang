"""FastAPI 全局异常处理。"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import BusinessException
from app.schemas.common import ApiResponse

logger = logging.getLogger(__name__)


def _error_response(*, status_code: int, code: int, message: str) -> JSONResponse:
    body = ApiResponse[None](code=code, message=message).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=body)


async def business_exception_handler(
    _request: Request,
    exc: BusinessException,
) -> JSONResponse:
    return _error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
    )


async def validation_exception_handler(
    _request: Request,
    _exc: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        status_code=422,
        code=40003,
        message="请求参数校验失败",
    )


async def http_exception_handler(
    _request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    if exc.status_code == 404:
        return _error_response(
            status_code=404,
            code=40400,
            message="请求的资源不存在",
        )

    message = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
    return _error_response(
        status_code=exc.status_code,
        code=exc.status_code * 100,
        message=message,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "Unhandled exception while processing %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return _error_response(
        status_code=500,
        code=50000,
        message="服务器内部错误",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册统一异常处理器。"""
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
