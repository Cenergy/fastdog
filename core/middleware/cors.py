from fastapi.middleware.cors import CORSMiddleware
from core.config import settings

def setup_cors_middleware(app):
    """配置 CORS 中间件"""
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    return app