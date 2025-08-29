from typing import List, Optional
from tortoise.expressions import Q
from decimal import Decimal
from .models import GeoCategory, GeoModel
from .schemas import (
    GeoCategoryCreate, GeoCategoryUpdate,
    GeoModelCreate, GeoModelUpdate,
    GeoQueryParams
)


# GeoCategory CRUD operations
async def create_geo_category(category_data: GeoCategoryCreate) -> GeoCategory:
    """创建地理分类"""
    category = await GeoCategory.create(**category_data.model_dump())
    return category


async def get_geo_category(category_id: int) -> Optional[GeoCategory]:
    """根据ID获取地理分类"""
    return await GeoCategory.get_or_none(id=category_id)


async def get_geo_categories(
    skip: int = 0,
    limit: int = 10,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[GeoCategory]:
    """获取地理分类列表"""
    query = GeoCategory.all()
    
    if is_active is not None:
        query = query.filter(is_active=is_active)
    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    categories = await query.offset(skip).limit(limit).order_by('sort_order', '-created_at')
    return categories


async def update_geo_category(category_id: int, category_data: GeoCategoryUpdate) -> Optional[GeoCategory]:
    """更新地理分类"""
    category = await get_geo_category(category_id)
    if not category:
        return None
        
    update_data = category_data.model_dump(exclude_unset=True)
    await category.update_from_dict(update_data).save()
    return category


async def delete_geo_category(category_id: int) -> bool:
    """删除地理分类"""
    category = await get_geo_category(category_id)
    if not category:
        return False
        
    await category.delete()
    return True


async def count_geo_categories(
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """获取地理分类总数"""
    query = GeoCategory.all()
    
    if is_active is not None:
        query = query.filter(is_active=is_active)
    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    return await query.count()


# GeoModel CRUD operations
async def create_geo_model(model_data: GeoModelCreate) -> GeoModel:
    """创建地理模型"""
    model_dict = model_data.model_dump()
    # 处理关联字段
    category_id = model_dict.pop('category_id', None)
    model_3d_id = model_dict.pop('model_3d_id', None)
    
    model = await GeoModel.create(**model_dict)
    
    # 设置关联
    if category_id:
        category = await get_geo_category(category_id)
        if category:
            model.category = category
            await model.save()
    
    if model_3d_id:
        # 这里需要导入Model3D模型
        from apps.resources.models import Model3D
        model_3d = await Model3D.get_or_none(id=model_3d_id)
        if model_3d:
            model.model_3d = model_3d
            await model.save()
    
    return model


async def get_geo_model(model_id: int) -> Optional[GeoModel]:
    """根据ID获取地理模型"""
    return await GeoModel.get_or_none(id=model_id).prefetch_related('model_3d')


async def get_geo_models(
    skip: int = 0,
    limit: int = 10,
    category_id: Optional[int] = None,
    model_3d_id: Optional[int] = None,
    is_visible: Optional[bool] = None,
    is_active: Optional[bool] = None,
    layer_name: Optional[str] = None,
    search: Optional[str] = None
) -> List[GeoModel]:
    """获取地理模型列表"""
    query = GeoModel.all().prefetch_related('model_3d')
    
    if category_id:
        query = query.filter(category_id=category_id)
    if model_3d_id:
        query = query.filter(model_3d_id=model_3d_id)
    if is_visible is not None:
        query = query.filter(is_visible=is_visible)
    if is_active is not None:
        query = query.filter(is_active=is_active)
    if layer_name:
        query = query.filter(layer_name=layer_name)
    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    models = await query.offset(skip).limit(limit).order_by('z_index', '-created_at')
    return models


async def get_geo_models_by_bounds(
    min_longitude: Decimal,
    max_longitude: Decimal,
    min_latitude: Decimal,
    max_latitude: Decimal,
    zoom_level: Optional[Decimal] = None,
    layer_name: Optional[str] = None,
    is_visible: bool = True,
    is_active: bool = True
) -> List[GeoModel]:
    """根据地理边界获取模型列表"""
    query = GeoModel.filter(
        longitude__gte=min_longitude,
        longitude__lte=max_longitude,
        latitude__gte=min_latitude,
        latitude__lte=max_latitude,
        is_visible=is_visible,
        is_active=is_active
    ).prefetch_related('model_3d')
    
    if layer_name:
        query = query.filter(layer_name=layer_name)
    
    # 根据缩放级别过滤
    if zoom_level is not None:
        query = query.filter(
            Q(min_zoom_level__isnull=True) | Q(min_zoom_level__lte=zoom_level),
            Q(max_zoom_level__isnull=True) | Q(max_zoom_level__gte=zoom_level)
        )
    
    models = await query.order_by('z_index', '-created_at')
    return models


async def get_geo_models_by_layer(layer_name: str) -> List[GeoModel]:
    """根据图层名称获取模型列表"""
    return await GeoModel.filter(
        layer_name=layer_name,
        is_active=True
    ).prefetch_related('model_3d').order_by('z_index')


async def update_geo_model(model_id: int, model_data: GeoModelUpdate) -> Optional[GeoModel]:
    """更新地理模型"""
    model = await get_geo_model(model_id)
    if not model:
        return None
        
    update_dict = model_data.model_dump(exclude_unset=True)
    # 处理关联字段
    category_id = update_dict.pop('category_id', None)
    model_3d_id = update_dict.pop('model_3d_id', None)
    
    await model.update_from_dict(update_dict).save()
    
    # 更新关联
    if category_id is not None:
        if category_id:
            category = await get_geo_category(category_id)
            if category:
                model.category = category
        else:
            model.category = None
        await model.save()
    
    if model_3d_id is not None:
        if model_3d_id:
            from apps.resources.models import Model3D
            model_3d = await Model3D.get_or_none(id=model_3d_id)
            if model_3d:
                model.model_3d = model_3d
        else:
            model.model_3d = None
        await model.save()
    
    return model


async def delete_geo_model(model_id: int) -> bool:
    """删除地理模型"""
    model = await get_geo_model(model_id)
    if not model:
        return False
        
    await model.delete()
    return True


async def count_geo_models(
    category_id: Optional[int] = None,
    model_3d_id: Optional[int] = None,
    is_visible: Optional[bool] = None,
    is_active: Optional[bool] = None,
    layer_name: Optional[str] = None,
    search: Optional[str] = None
) -> int:
    """获取地理模型总数"""
    query = GeoModel.all()
    
    if category_id:
        query = query.filter(category_id=category_id)
    if model_3d_id:
        query = query.filter(model_3d_id=model_3d_id)
    if is_visible is not None:
        query = query.filter(is_visible=is_visible)
    if is_active is not None:
        query = query.filter(is_active=is_active)
    if layer_name:
        query = query.filter(layer_name=layer_name)
    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    return await query.count()


# 地理查询相关函数
async def search_geo_models_by_params(query_params: GeoQueryParams) -> List[GeoModel]:
    """根据查询参数搜索地理模型"""
    query = GeoModel.filter(is_active=True).prefetch_related('model_3d')
    
    # 地理边界过滤
    if query_params.min_longitude is not None:
        query = query.filter(longitude__gte=query_params.min_longitude)
    if query_params.max_longitude is not None:
        query = query.filter(longitude__lte=query_params.max_longitude)
    if query_params.min_latitude is not None:
        query = query.filter(latitude__gte=query_params.min_latitude)
    if query_params.max_latitude is not None:
        query = query.filter(latitude__lte=query_params.max_latitude)
    
    # 其他过滤条件
    if query_params.layer_name:
        query = query.filter(layer_name=query_params.layer_name)
    if query_params.is_visible is not None:
        query = query.filter(is_visible=query_params.is_visible)
    if query_params.is_active is not None:
        query = query.filter(is_active=query_params.is_active)
    
    # 缩放级别过滤
    if query_params.zoom_level is not None:
        query = query.filter(
            Q(min_zoom_level__isnull=True) | Q(min_zoom_level__lte=query_params.zoom_level),
            Q(max_zoom_level__isnull=True) | Q(max_zoom_level__gte=query_params.zoom_level)
        )
    
    models = await query.order_by('z_index', '-created_at')
    return models


async def get_layers() -> List[str]:
    """获取所有图层名称"""
    result = await GeoModel.filter(
        layer_name__isnull=False,
        is_active=True
    ).distinct().values_list('layer_name', flat=True)
    return list(result)


async def update_model_visibility(model_id: int, is_visible: bool) -> bool:
    """更新模型可见性"""
    model = await GeoModel.get_or_none(id=model_id)
    if not model:
        return False
    
    model.is_visible = is_visible
    await model.save()
    return True


async def batch_update_layer_visibility(layer_name: str, is_visible: bool) -> int:
    """批量更新图层可见性"""
    count = await GeoModel.filter(layer_name=layer_name).update(is_visible=is_visible)
    return count