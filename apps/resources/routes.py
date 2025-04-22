from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from .schemas import ResourceCreate, ResourceUpdate, ResourceInDB
from .crud import (
    create_resource,
    get_resource,
    get_resources,
    update_resource,
    delete_resource,
    count_resources
)
from api.v1.deps import get_current_active_user
from apps.users.models import User

router = APIRouter()

@router.post("/", response_model=ResourceInDB)
async def create_resource_api(
    resource: ResourceCreate,
    current_user: User = Depends(get_current_active_user)
) -> ResourceInDB:
    """创建资源"""
    return await create_resource(resource)

@router.get("/{resource_id}", response_model=ResourceInDB)
async def get_resource_api(resource_id: int) -> ResourceInDB:
    """获取单个资源"""
    resource = await get_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource

@router.get("/", response_model=List[ResourceInDB],operation_id="new_endpoint")
async def get_resources_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[ResourceInDB]:
    """获取资源列表"""
    return await get_resources(skip, limit, type, is_active, search)

@router.put("/{resource_id}", response_model=ResourceInDB)
async def update_resource_api(
    resource_id: int,
    resource: ResourceUpdate,
    current_user: User = Depends(get_current_active_user)
) -> ResourceInDB:
    """更新资源"""
    updated_resource = await update_resource(resource_id, resource)
    if not updated_resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return updated_resource

@router.delete("/{resource_id}")
async def delete_resource_api(
    resource_id: int,
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """删除资源"""
    success = await delete_resource(resource_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resource not found")
    return {"message": "Resource deleted successfully"}

@router.get("/count/total", response_model=int)
async def count_resources_api(
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """获取资源总数"""
    return await count_resources(type, is_active, search)