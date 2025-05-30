from functools import wraps
from typing import Optional, List, Callable, Any, Dict, Union
from fastapi import Request, Response, HTTPException, status
from datetime import datetime
import re
from core.settings import settings

def _version_to_tuple(version: str) -> tuple:
    """将版本字符串转换为可比较的元组
    
    Args:
        version: 版本字符串，如 "v1", "v2.1", "v3.0.1"
        
    Returns:
        版本元组，如 (1,), (2, 1), (3, 0, 1)
    """
    # 移除前缀 'v' 或 'V'
    if version.lower().startswith('v'):
        version = version[1:]
    
    # 分割版本号并转换为整数元组
    try:
        return tuple(int(x) for x in re.findall(r'\d+', version))
    except Exception:
        return (0,)  # 默认为最低版本

def _version_gte(version1: str, version2: str) -> bool:
    """检查version1是否大于等于version2
    
    Args:
        version1: 第一个版本字符串
        version2: 第二个版本字符串
        
    Returns:
        如果version1 >= version2返回True，否则返回False
    """
    return _version_to_tuple(version1) >= _version_to_tuple(version2)

def _version_lte(version1: str, version2: str) -> bool:
    """检查version1是否小于等于version2
    
    Args:
        version1: 第一个版本字符串
        version2: 第二个版本字符串
        
    Returns:
        如果version1 <= version2返回True，否则返回False
    """
    return _version_to_tuple(version1) <= _version_to_tuple(version2)

def api_version(
    version: str,
    deprecated: bool = False,
    deprecated_date: Optional[str] = None,
    deprecated_reason: Optional[str] = None,
    min_version: Optional[str] = None,
    max_version: Optional[str] = None,
    alternative_route: Optional[str] = None
):
    """API版本控制装饰器

    用于标记API端点的版本信息，并提供弃用警告机制。

    Args:
        version: API版本，例如 "v1", "v2"
        deprecated: 是否已弃用
        deprecated_date: 弃用日期，格式为 "YYYY-MM-DD"
        deprecated_reason: 弃用原因
        min_version: 最低支持版本
        max_version: 最高支持版本
        alternative_route: 替代路由

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 获取请求和响应对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request is None:
                for _, arg in kwargs.items():
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            # 检查客户端请求的API版本
            client_version = None
            if request:
                # 从请求头中获取版本信息
                if "X-API-Version" in request.headers:
                    client_version = request.headers["X-API-Version"]
                # 从URL参数中获取版本信息
                elif request.query_params.get("api_version"):
                    client_version = request.query_params.get("api_version")
                # 从请求路径中提取版本信息
                else:
                    version_match = re.search(r"/v\d+(?:\.\d+)*", str(request.url.path))
                    if version_match:
                        client_version = version_match.group()[1:]  # 移除前导斜杠
            
            # 版本兼容性检查
            if client_version:
                # 检查最低版本要求
                if min_version and not _version_gte(client_version, min_version):
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "detail": f"当前API需要最低版本 {min_version}，您的客户端版本 {client_version} 过低"
                        }
                    )
                
                # 检查最高版本限制
                if max_version and not _version_lte(client_version, max_version):
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "detail": f"当前API支持的最高版本为 {max_version}，您的客户端版本 {client_version} 过高，请降级或使用新的API"
                        }
                    )
            
            # 执行原始函数
            response = await func(*args, **kwargs)
            
            # 如果找不到请求对象，直接返回响应
            if request is None:
                return response
            
            # 如果响应不是Response对象，将其包装为Response
            if not isinstance(response, Response):
                from fastapi.responses import JSONResponse
                response = JSONResponse(content=response)
            
            # 添加版本信息到响应头
            response.headers["X-API-Version"] = version
            
            # 处理弃用警告
            if deprecated:
                response.headers["X-API-Deprecated"] = "true"
                
                if deprecated_date:
                    response.headers["X-API-Deprecated-Date"] = deprecated_date
                    
                    # 计算距离弃用日期的剩余天数
                    try:
                        today = datetime.now().date()
                        dep_date = datetime.strptime(deprecated_date, "%Y-%m-%d").date()
                        days_left = (dep_date - today).days
                        
                        if days_left > 0:
                            response.headers["X-API-Deprecated-Days-Left"] = str(days_left)
                    except Exception:
                        pass
                
                # 构建完整的警告消息后再进行一次性编码
                warning_msg = f"当前API端点已标记为弃用"
                if deprecated_date:
                    warning_msg += f"，将在 {deprecated_date} 停止服务"
                if deprecated_reason:
                    warning_msg += f"，原因：{deprecated_reason}"
                if alternative_route:
                    warning_msg += f"，请使用替代API：{alternative_route}"
                
                # 将完整的中文消息进行编码
                warning_msg = warning_msg.encode('utf-8').decode('latin1')
                
                response.headers["X-API-Warning"] = warning_msg
                
                # 如果距离弃用日期不足30天，添加更明显的警告
                if deprecated_date:
                    try:
                        today = datetime.now().date()
                        dep_date = datetime.strptime(deprecated_date, "%Y-%m-%d").date()
                        days_left = (dep_date - today).days
                        
                        if days_left <= 0:
                            # API已经过期
                            response.headers["X-API-Status"] = "expired"
                            response.headers["X-API-Critical-Warning"] = "Critical: This API has been deprecated and is no longer supported"
                        elif days_left <= 7:
                            # 最后一周警告
                            response.headers["X-API-Status"] = "critical"
                            response.headers["X-API-Critical-Warning"] = f"Critical: This API will be deprecated in {days_left} days. Please migrate immediately!"
                        elif days_left <= 30:
                            # 30天内警告
                            response.headers["X-API-Status"] = "warning"
                            response.headers["X-API-Critical-Warning"] = f"Warning: This API will be deprecated in {days_left} days"
                    except Exception:
                        pass
            
            # 处理版本范围限制
            if min_version:
                response.headers["X-API-Min-Version"] = min_version
            if max_version:
                response.headers["X-API-Max-Version"] = max_version
            
            return response
        
        # 添加版本信息到函数元数据
        setattr(wrapper, "api_version", version)
        setattr(wrapper, "api_deprecated", deprecated)
        if deprecated_date:
            setattr(wrapper, "api_deprecated_date", deprecated_date)
        if deprecated_reason:
            setattr(wrapper, "api_deprecated_reason", deprecated_reason)
        if alternative_route:
            setattr(wrapper, "api_alternative_route", alternative_route)
        
        return wrapper
    return decorator