from fastapi import APIRouter
from apps.users.routes import router as users_router
# 导入其他应用的路由...

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["users"])
# 包含其他应用的路由...