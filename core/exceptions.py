from fastapi import HTTPException, status

class CustomException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

class AuthenticationError(CustomException):
    def __init__(self, detail: str = "认证失败"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)

class PermissionDenied(CustomException):
    def __init__(self, detail: str = "权限不足"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)

class NotFoundError(CustomException):
    def __init__(self, detail: str = "资源不存在"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class ValidationError(CustomException):
    def __init__(self, detail: str = "数据验证失败"):
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

class DatabaseConnectionError(CustomException):
    def __init__(self, detail: str = "数据库连接失败"):
        super().__init__(detail=detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

class DatabaseOperationError(CustomException):
    def __init__(self, detail: str = "数据库操作失败"):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DatabaseTransactionError(CustomException):
    def __init__(self, detail: str = "数据库事务执行失败"):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DatabasePoolExhaustedError(CustomException):
    def __init__(self, detail: str = "数据库连接池已耗尽"):
        super().__init__(detail=detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)