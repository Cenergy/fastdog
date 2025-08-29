from fastapi import APIRouter
from apps.users.routes import router as users_router
from api.v1.auth import router as auth_router
from apps.resources.routes import router as resources_router
from apps.converters.routes import router as converters_router
from apps.albums.routes import router as albums_router
from apps.geos.routes import router as geos_router

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["用户"])
api_router.include_router(auth_router, prefix="/auth", tags=["权限"])
api_router.include_router(resources_router, prefix="/resources", tags=["资源"])
api_router.include_router(converters_router, prefix="/converters", tags=["转换器"])
api_router.include_router(albums_router, prefix="/albums", tags=["相册"])
api_router.include_router(geos_router, prefix="/geos", tags=["地理空间"])