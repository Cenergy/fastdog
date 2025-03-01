from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from core.database import init_db, close_db
from core.logging import setup_logging
from api.v1.api import api_router
from core.middleware.cors import setup_cors_middleware
from core.middleware.error_handler import setup_exception_handlers
from core.middleware.rate_limit import RateLimitMiddleware

# 初始化日志系统
logger = setup_logging()

app = FastAPI(title=settings.PROJECT_NAME)

# 配置中间件
app = setup_cors_middleware(app)
app = setup_exception_handlers(app)
app.add_middleware(RateLimitMiddleware)

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": "connected"
    }


