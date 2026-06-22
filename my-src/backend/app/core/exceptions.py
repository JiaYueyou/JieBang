"""业务异常与错误码。"""


class BusinessException(Exception):
    """可安全暴露给 API 调用方的业务异常。"""

    def __init__(self, *, status_code: int, code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class InvalidCredentialsError(BusinessException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code=40001,
            message="用户名或密码错误",
        )


class DuplicateUsernameError(BusinessException):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code=40002,
            message="用户名已存在",
        )


class AuthenticationError(BusinessException):
    def __init__(self, message: str = "Token 无效或已过期") -> None:
        super().__init__(
            status_code=401,
            code=40100,
            message=message,
        )


class ResourceNotFoundError(BusinessException):
    def __init__(self, message: str = "请求的资源不存在") -> None:
        super().__init__(
            status_code=404,
            code=40400,
            message=message,
        )


class InvalidParameterError(BusinessException):
    def __init__(self, message: str = "请求参数校验失败") -> None:
        super().__init__(
            status_code=422,
            code=40003,
            message=message,
        )
