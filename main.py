from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.settings import settings
from core.database import init_db, close_db
from core.logging import setup_logging
from api.v1.api import api_router
from core.middleware.cors import setup_cors_middleware
from core.middleware.error_handler import setup_exception_handlers
from core.middleware.rate_limit import RateLimitMiddleware
from core.admin import setup_admin
from core.static import setup_static_files
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html

# 初始化日志系统
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    await init_db()
    # 启动任务调度器
    from apps.tasks.scheduler import scheduler
    await scheduler.start()
    
    yield
    
    # 关闭事件
    await close_db()
    # 关闭任务调度器
    from apps.tasks.scheduler import scheduler
    await scheduler.shutdown()

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=None,  # 禁用默认的docs路由，我们将自定义它
    lifespan=lifespan
)

import os
from dotenv import load_dotenv
 
# 加载.env文件，默认在当前目录下查找.env文件
load_dotenv()
 

# 配置中间件
app = setup_cors_middleware(app)
app = setup_exception_handlers(app)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)

# 配置静态文件
app = setup_static_files(app)

# 确保Swagger UI资源目录存在
os.makedirs(os.path.join(settings.STATIC_DIR, "swagger-ui"), exist_ok=True)

# 自定义Swagger UI路由，使用本地资源
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{settings.PROJECT_NAME} - Swagger UI",
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
    )

# 设置FastAdmin后台管理
app = setup_admin(app)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

@app.get("/health")
async def health_check():
    from core.database_config import check_db_health, DatabaseMetrics
    db_health = await check_db_health()
    metrics = DatabaseMetrics().get_metrics()
    return {
        "status": "healthy" if db_health else "unhealthy",
        "version": "1.0.0",
        "database": {
            "status": "connected" if db_health else "disconnected",
            "metrics": metrics
        }
    }


from fastapi_mcp import FastApiMCP

mcp = FastApiMCP(
    app,
    name="My API MCP",
    description="My API description",
)

# Mount the MCP server directly to your FastAPI app
mcp.mount()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_excludes=["logs/*",".git/*","static/*"]
    )
