from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Admin"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "YOUR_SECRET_KEY_HERE"  # 在生产环境中应该使用环境变量
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    BACKEND_CORS_ORIGINS: List[str] = []
    SERVER_HOST: str = "http://localhost:8000"  # 服务器主机地址，用于生成验证链接

    # 邮箱设置
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

    # 密码安全设置
    ENABLE_ACCOUNT_LOCKOUT: bool = False  # 是否启用账户锁定
    MAX_PASSWORD_RETRY: int = 5  # 最大密码重试次数
    PASSWORD_RETRY_LOCKOUT_MINUTES: int = 30  # 密码重试锁定时间（分钟）
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60  # 密码重置令牌有效期（分钟）
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 邮箱验证令牌有效期（分钟）

    # 数据库设置
    DATABASE_URL: str = "sqlite://./test.db"
    DATABASE_POOL_SIZE: int = 20  # 连接池大小
    DATABASE_POOL_RECYCLE: int = 300  # 连接回收时间（秒）

    # 日志设置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    LOG_FILE_PATH: str = "logs/app.log"
    LOG_ROTATION: str = "500 MB"

    # 文件上传设置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"]

    # API设置
    RATE_LIMIT_PER_MINUTE: int = 60
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()