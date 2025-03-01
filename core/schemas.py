"""共用的Pydantic模型

这个模块包含了项目中共用的Pydantic模型定义。
"""

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

# 用于泛型的类型变量
T = TypeVar('T')

class ResponseBase(BaseModel):
    """基础响应模型"""
    code: int = 200
    message: str = "Success"

class Response(ResponseBase, Generic[T]):
    """通用响应模型"""
    data: Optional[T] = None

class PageInfo(BaseModel):
    """分页信息"""
    page: int
    size: int
    total: int

class PageResponse(Response[T]):
    """分页响应模型"""
    page_info: Optional[PageInfo] = None