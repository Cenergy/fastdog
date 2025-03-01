"""API依赖项

这个模块包含了API路由中使用的各种依赖项，如认证、权限检查等。
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from core.config import settings
from core.security import verify_password
from apps.users.crud import get_user
from apps.users.models import User_Pydantic

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token",
    auto_error=True,
    description="使用邮箱作为用户名，输入密码进行登录"
)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[User_Pydantic]:
    """获取当前用户

    Args:
        token: JWT token

    Returns:
        User_Pydantic: 用户信息

    Raises:
        HTTPException: 认证失败时抛出
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValidationError):
        raise credentials_exception
    
    try:
        user = await get_user(int(user_id))
        if user is None:
            raise credentials_exception
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )

async def get_current_active_user(current_user: User_Pydantic = Depends(get_current_user)) -> User_Pydantic:
    """获取当前活跃用户

    Args:
        current_user: 当前用户

    Returns:
        User_Pydantic: 用户信息

    Raises:
        HTTPException: 用户未激活时抛出
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user

async def get_current_superuser(current_user: User_Pydantic = Depends(get_current_user)) -> User_Pydantic:
    """获取当前超级用户

    Args:
        current_user: 当前用户

    Returns:
        User_Pydantic: 用户信息

    Raises:
        HTTPException: 用户不是超级用户或管理员时抛出
    """
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级用户或管理员权限"
        )
    return current_user