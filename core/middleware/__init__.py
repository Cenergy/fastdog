# -*- coding: utf-8 -*-
"""
中间件模块
包含所有与中间件相关的功能，包括CORS、错误处理、限流、安全认证、异常定义和装饰器等。
"""

# 导入中间件设置函数
from .cors import setup_cors_middleware
from .error_handler import (
    validation_exception_handler,
    not_found_exception_handler,
    custom_exception_handler,
    general_exception_handler,
    setup_exception_handlers
)
from .rate_limit import RateLimitMiddleware

# 导入安全相关功能
from .security import (
    create_access_token,
    verify_password,
    get_password_hash,
    decode_token,
    create_verification_token
)

# 导入异常类
from .exceptions import (
    CustomException,
    AuthenticationError,
    PermissionDenied,
    NotFoundError,
    ValidationError,
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseTransactionError,
    DatabasePoolExhaustedError
)

# 导入装饰器
from .decorators import api_version

__all__ = [
    # 中间件设置
    'setup_cors_middleware',
    'setup_exception_handlers',
    'RateLimitMiddleware',
    
    # 异常处理器
    'validation_exception_handler',
    'not_found_exception_handler', 
    'custom_exception_handler',
    'general_exception_handler',
    
    # 安全功能
    'create_access_token',
    'verify_password',
    'get_password_hash',
    'decode_token',
    'create_verification_token',
    
    # 异常类
    'CustomException',
    'AuthenticationError',
    'PermissionDenied',
    'NotFoundError',
    'ValidationError',
    'DatabaseConnectionError',
    'DatabaseOperationError',
    'DatabaseTransactionError',
    'DatabasePoolExhaustedError',
    
    # 装饰器
    'api_version'
]