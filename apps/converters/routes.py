from fastapi import APIRouter
from .coords import router as coordinate_api_router

router = APIRouter()
# 包含坐标转换API路由
router.include_router(coordinate_api_router, tags=["坐标转换"])

