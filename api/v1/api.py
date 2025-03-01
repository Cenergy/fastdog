from fastapi import APIRouter
from apps.users.routes import router as users_router
from api.v1.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])