from typing import List, Optional
from tortoise.expressions import Q
from .models import Resource, Model3D, Model3DCategory
from .schemas import (
    ResourceCreate, ResourceUpdate,
    Model3DCategoryCreate, Model3DCategoryUpdate,
    Model3DCreate, Model3DUpdate
)

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


# Model3D CRUD operations
async def create_model3d(model_data: Model3DCreate) -> Model3D:
    """创建3D模型"""
    model_dict = model_data.model_dump()
    # 处理分类关联
    category_id = model_dict.pop('category_id', None)
    model = await Model3D.create(**model_dict)
    
    if category_id:
        category = await get_model3d_category(category_id)
        if category:
            model.category = category
            await model.save()
    
    return model

async def get_model3d(model_id: int) -> Optional[Model3D]:
    """根据ID获取3D模型"""
    return await Model3D.get_or_none(id=model_id).prefetch_related('category')

async def get_model3d_by_uuid(uuid: str) -> Optional[Model3D]:
    """根据UUID获取3D模型"""
    return await Model3D.get_or_none(uuid=uuid).prefetch_related('category')

async def get_model3ds(
    skip: int = 0,
    limit: int = 10,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_public: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Model3D]:
    """获取3D模型列表"""
    query = Model3D.all().prefetch_related('category')
    
    if category_id:
        query = query.filter(category_id=category_id)
    if is_active is not None:
        query = query.filter(is_active=is_active)
    if is_public is not None:
        query = query.filter(is_public=is_public)
    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    models = await query.offset(skip).limit(limit).order_by('-created_at')
    return models

async def update_model3d(model_id: int, model_data: Model3DUpdate) -> Optional[Model3D]:
    """更新3D模型"""
    model = await get_model3d(model_id)
    if not model:
        return None
        
    update_dict = model_data.model_dump(exclude_unset=True)
    # 处理分类关联
    category_id = update_dict.pop('category_id', None)
    
    await model.update_from_dict(update_dict).save()
    
    if category_id is not None:
        if category_id:
            category = await get_model3d_category(category_id)
            if category:
                model.category = category
        else:
            model.category = None
        await model.save()
    
    return model

async def delete_model3d(model_id: int) -> bool:
    """删除3D模型"""
    model = await get_model3d(model_id)
    if not model:
        return False
        
    await model.delete()
    return True

async def count_model3ds(
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_public: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """获取3D模型总数"""
    query = Model3D.all()
    
    if category_id:
        query = query.filter(category_id=category_id)
    if is_active is not None:
        query = query.filter(is_active=is_active)
    if is_public is not None:
        query = query.filter(is_public=is_public)
    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    return await query.count()


# Model3DCategory CRUD operations
async def create_model3d_category(category_data: Model3DCategoryCreate) -> Model3DCategory:
    """创建3D模型分类"""
    category = await Model3DCategory.create(**category_data.model_dump())
    return category

async def get_model3d_category(category_id: int) -> Optional[Model3DCategory]:
    """根据ID获取3D模型分类"""
    return await Model3DCategory.get_or_none(id=category_id)

async def get_model3d_categories(
    skip: int = 0,
    limit: int = 10,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Model3DCategory]:
    """获取3D模型分类列表"""
    query = Model3DCategory.all()
    
    if is_active is not None:
        query = query.filter(is_active=is_active)
    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    categories = await query.offset(skip).limit(limit).order_by('sort_order', '-created_at')
    return categories

async def update_model3d_category(category_id: int, category_data: Model3DCategoryUpdate) -> Optional[Model3DCategory]:
    """更新3D模型分类"""
    category = await get_model3d_category(category_id)
    if not category:
        return None
        
    update_data = category_data.model_dump(exclude_unset=True)
    await category.update_from_dict(update_data).save()
    return category

async def delete_model3d_category(category_id: int) -> bool:
    """删除3D模型分类"""
    category = await get_model3d_category(category_id)
    if not category:
        return False
        
    await category.delete()
    return True

async def count_model3d_categories(
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """获取3D模型分类总数"""
    query = Model3DCategory.all()
    
    if is_active is not None:
        query = query.filter(is_active=is_active)
    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    return await query.count()