"""
统一异常类 —— 业务异常基类及各类具体异常。
"""
from fastapi import Request
from fastapi.responses import JSONResponse


class BusinessException(Exception):
    """业务异常基类，所有自定义异常继承此类"""
    def __init__(self, status_code: int, code: int, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


class AuthenticationError(BusinessException):
    """认证失败（401）"""
    def __init__(self, message: str = "认证失败"):
        super().__init__(401, 40100, message)


class InvalidCredentialsError(BusinessException):
    """用户名或密码错误（401）"""
    def __init__(self, message: str = "用户名或密码错误"):
        super().__init__(401, 40001, message)


class DuplicateUsernameError(BusinessException):
    """用户名已存在（409）"""
    def __init__(self, message: str = "用户名已被注册"):
        super().__init__(409, 40002, message)


class ResourceNotFoundError(BusinessException):
    """资源不存在（404）"""
    def __init__(self, message: str = "资源不存在"):
        super().__init__(404, 40400, message)


class InvalidParameterError(BusinessException):
    """参数校验失败（422）"""
    def __init__(self, message: str = "参数错误"):
        super().__init__(422, 40003, message)


def register_exception_handlers(app):
    """注册全局异常处理器，统一返回 ApiResponse 格式"""

    @app.exception_handler(BusinessException)
    async def business_handler(request: Request, exc: BusinessException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"code": 50000, "message": f"服务器内部错误: {str(exc)}", "data": None},
        )
