from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Admin"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "YOUR_SECRET_KEY_HERE"  # 在生产环境中应该使用环境变量
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    BACKEND_CORS_ORIGINS: List[str] = []

    # 数据库设置
    DATABASE_URL: str = "sqlite://./test.db"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()