from fastapi import APIRouter
from apps.users.routes import router as users_router
from api.v1.auth import router as auth_router
from apps.resources.routes import router as resources_router
from apps.converters.routes import router as converters_router

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(resources_router, prefix="/resources", tags=["resources"])
api_router.include_router(converters_router, prefix="/converters", tags=["converters"])