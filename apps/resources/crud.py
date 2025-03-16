from typing import List, Optional
from tortoise.expressions import Q
from .models import Resource
from .schemas import ResourceCreate, ResourceUpdate

async def create_resource(resource_data: ResourceCreate) -> Resource:
    """创建资源"""
    resource = await Resource.create(**resource_data.model_dump())
    return resource

async def get_resource(resource_id: int) -> Optional[Resource]:
    """根据ID获取资源"""
    return await Resource.get_or_none(id=resource_id)

async def get_resources(
    skip: int = 0,
    limit: int = 10,
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Resource]:
    """获取资源列表"""
    query = Resource.all()
    
    if type:
        query = query.filter(type=type)
    if is_active is not None:
        query = query.filter(is_active=is_active)
    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    resources = await query.offset(skip).limit(limit).order_by('-created_at')
    return resources

async def update_resource(resource_id: int, resource_data: ResourceUpdate) -> Optional[Resource]:
    """更新资源"""
    resource = await get_resource(resource_id)
    if not resource:
        return None
        
    update_data = resource_data.model_dump(exclude_unset=True)
    await resource.update_from_dict(update_data).save()
    return resource

async def delete_resource(resource_id: int) -> bool:
    """删除资源"""
    resource = await get_resource(resource_id)
    if not resource:
        return False
        
    await resource.delete()
    return True

async def count_resources(
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """获取资源总数"""
    query = Resource.all()
    
    if type:
        query = query.filter(type=type)
    if is_active is not None:
        query = query.filter(is_active=is_active)
    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    return await query.count()