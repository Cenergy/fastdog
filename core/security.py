from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from core.config import settings
import secrets

from loguru import logger
import time

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=1,      # 降低时间成本
    argon2__memory_cost=64*1024,  # 64MB内存使用
    argon2__parallelism=4,    # 并行度
    argon2__hash_len=32       # 哈希长度
)  # 使用Argon2id算法以提高性能

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    start_time = time.time()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    end_time = time.time()
    logger.debug(f"令牌生成耗时: {end_time - start_time:.4f}秒")
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    start_time = time.time()
    result = pwd_context.verify(plain_password, hashed_password)
    end_time = time.time()
    logger.debug(f"密码验证耗时: {end_time - start_time:.4f}秒")
    return result

def get_password_hash(password: str) -> str:
    start_time = time.time()
    hashed_password = pwd_context.hash(password)
    end_time = time.time()
    logger.info(f"密码哈希计算耗时: {end_time - start_time:.4f}秒")
    return hashed_password

def decode_token(token: str) -> Optional[dict]:
    start_time = time.time()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        end_time = time.time()
        logger.debug(f"令牌解码耗时: {end_time - start_time:.4f}秒")
        return payload
    except JWTError:
        end_time = time.time()
        logger.warning(f"令牌解码失败，耗时: {end_time - start_time:.4f}秒")
        return None

def create_verification_token() -> str:
    """生成邮箱验证令牌"""
    return secrets.token_urlsafe(32)

def create_password_reset_token() -> str:
    """生成密码重置令牌"""
    return secrets.token_urlsafe(32)

def verify_token_expiration(token_expires: datetime) -> bool:
    """验证令牌是否过期"""
    return datetime.utcnow() < token_expires