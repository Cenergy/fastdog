# -*- coding: utf-8 -*-
"""
统一配置文件
整合了项目的所有配置信息，包括基础应用配置、数据库配置、邮件配置、
安全配置、日志配置、文件上传配置、API配置、管理员配置、AI服务配置和系统常量等。
"""

from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
import os
from urllib.parse import urlparse
from loguru import logger


class Settings(BaseSettings):
    """统一配置类"""
    
    # ==================== 基础应用配置 ====================
    PROJECT_NAME: str = "Fast Go Go"
    API_V1_STR: str = "/api/v1"
    STATIC_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    SECRET_KEY: str = "YOUR_SECRET_KEY_HERE"  # 在生产环境中应该使用环境变量
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    BACKEND_CORS_ORIGINS: List[str] = []
    SERVER_HOST: str = "http://localhost:8000"  # 服务器主机地址，用于生成验证链接

    # ==================== 数据库配置 ====================
    DATABASE_URL: str = "sqlite://./data/test.db"
    DATABASE_POOL_SIZE: int = 20  # 连接池大小
    DATABASE_POOL_RECYCLE: int = 300  # 连接回收时间（秒）
    
    # 不同数据库类型的连接池配置
    DB_POOL_CONFIGS: Dict[str, Dict[str, Any]] = {
        'sqlite': {
            "max_size": 50,  # 增加最大连接数
            "min_size": 10,  # 增加最小连接数
            "max_inactive_connection_lifetime": 180,  # 减少非活动连接的生命周期
            "connection_timeout": 30,  # 减少连接超时时间
            "retry_limit": 2,  # 减少重试次数
            "retry_interval": 0.5  # 减少重试间隔
        },
        'postgres': {
            "max_size": 50,
            "min_size": 10,
            "max_inactive_connection_lifetime": 300,
            "connection_timeout": 60,
            "retry_limit": 3,
            "retry_interval": 1
        },
        'mysql': {
            "max_size": 50,
            "min_size": 10,
            "max_inactive_connection_lifetime": 300,
            "connection_timeout": 60,
            "retry_limit": 3,
            "retry_interval": 1,
            "pool_recycle": 300
        }
    }

    # ==================== 邮件配置 ====================
    SMTP_TLS: bool = True  # 使用TLS
    SMTP_PORT: Optional[int] = 465  # 新浪邮箱SMTP SSL端口
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    EMAIL_RETRY_COUNT: int = 3  # 邮件发送失败重试次数
    EMAIL_RETRY_INTERVAL: int = 5  # 重试间隔（秒）
    EMAIL_CONNECTION_CONFIG: dict = {
        "MAIL_USERNAME": None,  # 使用环境变量SMTP_USER
        "MAIL_PASSWORD": None,  # 使用环境变量SMTP_PASSWORD
        "MAIL_FROM": None,     # 使用环境变量EMAILS_FROM_EMAIL
        "MAIL_PORT": None,     # 使用环境变量SMTP_PORT
        "MAIL_SERVER": None,   # 使用环境变量SMTP_HOST
        "MAIL_FROM_NAME": None,# 使用环境变量EMAILS_FROM_NAME
        "MAIL_STARTTLS": False,  # 不使用STARTTLS
        "MAIL_SSL_TLS": True,   # 使用SSL连接
        "USE_CREDENTIALS": True,
        "VALIDATE_CERTS": False,  # 禁用SSL证书验证
        "TIMEOUT": 5  # 设置超时时间为5秒
    }

    # ==================== 安全配置 ====================
    # 密码安全设置
    ENABLE_ACCOUNT_LOCKOUT: bool = False  # 是否启用账户锁定
    MAX_PASSWORD_RETRY: int = 5  # 最大密码重试次数
    PASSWORD_RETRY_LOCKOUT_MINUTES: int = 30  # 密码重试锁定时间（分钟）
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60  # 密码重置令牌有效期（分钟）
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 邮箱验证令牌有效期（分钟）

    # ==================== 日志配置 ====================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    LOG_FILE_PATH: str = "logs/app.log"
    LOG_ROTATION: str = "100 MB"  # 减小轮转大小，避免Windows权限问题

    # ==================== 文件上传配置 ====================
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"]
    CONVERTERS_HANDLE_MAX_EXCEL_SIZE: int = 5 * 1024 * 1024  # 5MB
    
    # 图片处理配置
    SAVE_ORIGINAL_PHOTOS: bool = False  # 是否保存原始图片文件，默认不保存
    
    # 坐标转换线程池设置
    CONVERTERS_THREAD_POOL_THRESHOLD: int = 1000  # 启用线程池的数据行数阈值
    CONVERTERS_THREAD_POOL_WORKERS: int = 4  # 线程池工作线程数

    # ==================== API配置 ====================
    RATE_LIMIT_PER_MINUTE: int = 60
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100
    API_TIMEOUT: int = 30  # API超时时间（秒）

    # ==================== 管理员配置 ====================
    ADMIN_USER_MODEL: str = "User"
    ADMIN_USER_MODEL_USERNAME_FIELD: str = "username"
    ADMIN_SECRET_KEY: str = "your_secret_key"
    ADMIN_DISABLE_CROP_IMAGE: bool = False
    
    # 默认管理员账户设置
    DEFAULT_ADMIN_EMAIL: str = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    DEFAULT_ADMIN_USERNAME: str = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    
    # ==================== AI服务配置 ====================
    DASHSCOPE_API_KEY: Optional[str] = None  # 通义万相API密钥
    HUGGINGFACE_API_KEY: Optional[str] = None  # HuggingFace API密钥

    # ==================== 系统常量 ====================
    # 用户相关常量
    USER_STATUS_ACTIVE: str = "active"
    USER_STATUS_INACTIVE: str = "inactive"
    USER_STATUS_DELETED: str = "deleted"

    # 权限相关常量
    ROLE_ADMIN: str = "admin"
    ROLE_USER: str = "user"
    ROLE_GUEST: str = "guest"

    # 缓存相关常量
    CACHE_TTL_SHORT: int = 300  # 5分钟
    CACHE_TTL_MEDIUM: int = 1800  # 30分钟
    CACHE_TTL_LONG: int = 86400  # 24小时

    def __init__(self):
        super().__init__()
        # 从环境变量更新邮件配置
        if self.SMTP_USER:
            self.EMAIL_CONNECTION_CONFIG["MAIL_USERNAME"] = self.SMTP_USER
        if self.SMTP_PASSWORD:
            self.EMAIL_CONNECTION_CONFIG["MAIL_PASSWORD"] = self.SMTP_PASSWORD
        if self.EMAILS_FROM_EMAIL:
            self.EMAIL_CONNECTION_CONFIG["MAIL_FROM"] = self.EMAILS_FROM_EMAIL
        if self.SMTP_PORT:
            self.EMAIL_CONNECTION_CONFIG["MAIL_PORT"] = self.SMTP_PORT
        if self.SMTP_HOST:
            self.EMAIL_CONNECTION_CONFIG["MAIL_SERVER"] = self.SMTP_HOST
        if self.EMAILS_FROM_NAME:
            self.EMAIL_CONNECTION_CONFIG["MAIL_FROM_NAME"] = self.EMAILS_FROM_NAME

    def get_db_type(self, db_url: str = None) -> str:
        """获取数据库类型"""
        if db_url is None:
            db_url = self.DATABASE_URL
        parsed = urlparse(db_url)
        return parsed.scheme.split('+')[0]

    def get_db_pool_config(self, db_type: str = None) -> Dict[str, Any]:
        """获取数据库连接池配置"""
        if db_type is None:
            db_type = self.get_db_type()
        
        if db_type not in self.DB_POOL_CONFIGS:
            logger.warning(f"未找到数据库类型 {db_type} 的连接池配置，将使用默认配置")
            db_type = 'sqlite'
        
        return self.DB_POOL_CONFIGS[db_type]

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"  # 忽略未定义的环境变量，避免ValidationError


# 创建全局配置实例
settings = Settings()