import asyncio
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from core.settings import settings
from datetime import datetime
from core.security import create_access_token, verify_password, get_password_hash, create_verification_token
from apps.users.crud import get_user_by_username_or_email, create_user, update_user, get_user_by_verification_token
from apps.users.models import User_Pydantic, UserCreate
from jose import jwt, JWTError
from utils.email import send_verification_email
import time
from loguru import logger

router = APIRouter()

@router.post("/login/access-token", response_model=dict, description="使用用户名或邮箱进行登录")
async def login_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """获取访问令牌"""
    user = await get_user_by_username_or_email(form_data.username)  # 使用用户名或邮箱登录
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查账户是否被锁定（仅在启用账户锁定功能时）
    if settings.ENABLE_ACCOUNT_LOCKOUT and user.password_retry_lockout_until and user.password_retry_lockout_until > datetime.utcnow():
        remaining_minutes = int((user.password_retry_lockout_until - datetime.utcnow()).total_seconds() / 60)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"账户已被锁定，请在{remaining_minutes}分钟后重试"
        )
    
    # 验证密码
    if not verify_password(form_data.password, user.hashed_password):
        if settings.ENABLE_ACCOUNT_LOCKOUT:
            # 更新密码重试次数
            user_data = {"password_retry_count": user.password_retry_count + 1}
            if user_data["password_retry_count"] >= settings.MAX_PASSWORD_RETRY:
                user_data["password_retry_lockout_until"] = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RETRY_LOCKOUT_MINUTES)
            await update_user(user.id, user_data)
            detail_msg = f"用户名或密码错误（剩余尝试次数：{settings.MAX_PASSWORD_RETRY - user_data['password_retry_count']}）"
        else:
            detail_msg = "用户名或密码错误"
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查邮箱是否已验证
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先验证您的邮箱"
        )
    
    # 重置密码重试次数
    if user.password_retry_count > 0:
        await update_user(user.id, {"password_retry_count": 0, "password_retry_lockout_until": None})
    
    # 生成访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={"sub": str(user.id), "type": "access"},
        expires_delta=access_token_expires
    )
    refresh_token = create_access_token(
        data={"sub": str(user.id), "type": "refresh"},
        expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/register", response_model=User_Pydantic)
async def register(user: UserCreate):
    start_time = time.time()
    """注册新用户"""
    # 检查邮箱是否已被注册
    db_user = await get_user_by_username_or_email(user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 创建新用户
    verification_token = create_verification_token()
    user_dict = user.model_dump()
    password = user_dict.pop('password')  # 从字典中移除密码
    user_dict['hashed_password'] = get_password_hash(password)  # 添加哈希后的密码
    user_dict["email_verification_token"] = verification_token
    user_dict["email_verified"] = False
    
    # 创建用户
    new_user = await create_user(user_dict,is_admin_creation=False)
    
    # 异步发送验证邮件
    asyncio.create_task(send_verification_email(user.email, verification_token))
    
    end_time = time.time()
    logger.info(f"注册接口总耗时: {end_time - start_time:.2f}秒")
    return new_user

@router.get("/verify-email/{token}")
async def verify_email(token: str):
    """验证邮箱"""
    user = await get_user_by_verification_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的验证链接"
        )
    
    await update_user(user.id, {
        "email_verified": True,
        "email_verification_token": None
    })
    
    return {"message": "邮箱验证成功"}

@router.post("/refresh-token", response_model=dict)
async def refresh_token(refresh_token: str):
    """刷新访问令牌"""
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的刷新令牌"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的刷新令牌"
            )
        
        # 生成新的访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id, "type": "access"},
            expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的刷新令牌"
        )