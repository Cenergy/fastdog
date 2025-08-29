from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from decimal import Decimal
from .schemas import (
    GeoCategoryCreate, GeoCategoryUpdate, GeoCategoryInDB,
    GeoModelCreate, GeoModelUpdate, GeoModelInDB, GeoModelWithRelations,
    GeoQueryParams
)
from .crud import (
    # GeoCategory CRUD
    create_geo_category,
    get_geo_category,
    get_geo_categories,
    update_geo_category,
    delete_geo_category,
    count_geo_categories,
    # GeoModel CRUD
    create_geo_model,
    get_geo_model,
    get_geo_models,
    get_geo_models_by_bounds,
    get_geo_models_by_layer,
    update_geo_model,
    delete_geo_model,
    count_geo_models,
    # 地理查询
    search_geo_models_by_params,
    get_layers,
    update_model_visibility,
    batch_update_layer_visibility
)
from api.v1.deps import get_current_active_user
from apps.users.models import User

router = APIRouter()

# ==================== GeoCategory 接口 ====================

@router.post("/categories/", response_model=GeoCategoryInDB)
async def create_category_api(
    category: GeoCategoryCreate,
    current_user: User = Depends(get_current_active_user)
) -> GeoCategoryInDB:
    """创建地理分类"""
    return await create_geo_category(category)


@router.get("/categories/{category_id}", response_model=GeoCategoryInDB)
async def get_category_api(category_id: int) -> GeoCategoryInDB:
    """获取单个地理分类"""
    category = await get_geo_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("/categories/", response_model=List[GeoCategoryInDB])
async def get_categories_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[GeoCategoryInDB]:
    """获取地理分类列表"""
    return await get_geo_categories(skip, limit, is_active, search)


@router.put("/categories/{category_id}", response_model=GeoCategoryInDB)
async def update_category_api(
    category_id: int,
    category: GeoCategoryUpdate,
    current_user: User = Depends(get_current_active_user)
) -> GeoCategoryInDB:
    """更新地理分类"""
    updated_category = await update_geo_category(category_id, category)
    if not updated_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return updated_category


@router.delete("/categories/{category_id}")
async def delete_category_api(
    category_id: int,
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """删除地理分类"""
    success = await delete_geo_category(category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted successfully"}


@router.get("/categories/count/total", response_model=int)
async def count_categories_api(
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """获取地理分类总数"""
    return await count_geo_categories(is_active, search)


# ==================== GeoModel 接口 ====================

@router.post("/models/", response_model=GeoModelInDB)
async def create_model_api(
    model: GeoModelCreate,
    current_user: User = Depends(get_current_active_user)
) -> GeoModelInDB:
    """创建地理模型"""
    return await create_geo_model(model)


@router.get("/models/{model_id}", response_model=GeoModelWithRelations)
async def get_model_api(model_id: int) -> GeoModelWithRelations:
    """获取单个地理模型"""
    model = await get_geo_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.get("/models/", response_model=List[GeoModelWithRelations])
async def get_models_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category_id: Optional[int] = None,
    model_3d_id: Optional[int] = None,
    is_visible: Optional[bool] = None,
    is_active: Optional[bool] = None,
    layer_name: Optional[str] = None,
    search: Optional[str] = None
) -> List[GeoModelWithRelations]:
    """获取地理模型列表"""
    return await get_geo_models(
        skip, limit, category_id, model_3d_id, 
        is_visible, is_active, layer_name, search
    )


@router.get("/models/bounds/search", response_model=List[GeoModelWithRelations])
async def get_models_by_bounds_api(
    min_longitude: Decimal = Query(..., description="最小经度"),
    max_longitude: Decimal = Query(..., description="最大经度"),
    min_latitude: Decimal = Query(..., description="最小纬度"),
    max_latitude: Decimal = Query(..., description="最大纬度"),
    zoom_level: Optional[Decimal] = Query(None, description="缩放级别"),
    layer_name: Optional[str] = Query(None, description="图层名称"),
    is_visible: bool = Query(True, description="是否可见"),
    is_active: bool = Query(True, description="是否启用")
) -> List[GeoModelWithRelations]:
    """根据地理边界获取模型列表"""
    return await get_geo_models_by_bounds(
        min_longitude, max_longitude, min_latitude, max_latitude,
        zoom_level, layer_name, is_visible, is_active
    )


@router.get("/models/layers/{layer_name}", response_model=List[GeoModelWithRelations])
async def get_models_by_layer_api(layer_name: str) -> List[GeoModelWithRelations]:
    """根据图层名称获取模型列表"""
    return await get_geo_models_by_layer(layer_name)


@router.put("/models/{model_id}", response_model=GeoModelWithRelations)
async def update_model_api(
    model_id: int,
    model: GeoModelUpdate,
    current_user: User = Depends(get_current_active_user)
) -> GeoModelWithRelations:
    """更新地理模型"""
    updated_model = await update_geo_model(model_id, model)
    if not updated_model:
        raise HTTPException(status_code=404, detail="Model not found")
    return updated_model


@router.delete("/models/{model_id}")
async def delete_model_api(
    model_id: int,
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """删除地理模型"""
    success = await delete_geo_model(model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model deleted successfully"}


@router.get("/models/count/total", response_model=int)
async def count_models_api(
    category_id: Optional[int] = None,
    model_3d_id: Optional[int] = None,
    is_visible: Optional[bool] = None,
    is_active: Optional[bool] = None,
    layer_name: Optional[str] = None,
    search: Optional[str] = None
) -> int:
    """获取地理模型总数"""
    return await count_geo_models(
        category_id, model_3d_id, is_visible, 
        is_active, layer_name, search
    )


# ==================== 地理查询接口 ====================

@router.post("/search", response_model=List[GeoModelWithRelations])
async def search_models_api(query_params: GeoQueryParams) -> List[GeoModelWithRelations]:
    """根据查询参数搜索地理模型"""
    return await search_geo_models_by_params(query_params)


@router.get("/layers", response_model=List[str])
async def get_layers_api() -> List[str]:
    """获取所有图层名称"""
    return await get_layers()


@router.patch("/models/{model_id}/visibility")
async def update_model_visibility_api(
    model_id: int,
    is_visible: bool = Query(..., description="是否可见"),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """更新模型可见性"""
    success = await update_model_visibility(model_id, is_visible)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": f"Model visibility updated to {is_visible}"}


@router.patch("/layers/{layer_name}/visibility")
async def update_layer_visibility_api(
    layer_name: str,
    is_visible: bool = Query(..., description="是否可见"),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """批量更新图层可见性"""
    count = await batch_update_layer_visibility(layer_name, is_visible)
    return {
        "message": f"Updated {count} models in layer '{layer_name}' to visible={is_visible}",
        "updated_count": count
    }


# ==================== 统计接口 ====================

@router.get("/stats/summary")
async def get_stats_summary() -> dict:
    """获取统计摘要"""
    total_categories = await count_geo_categories(is_active=True)
    total_models = await count_geo_models(is_active=True)
    visible_models = await count_geo_models(is_active=True, is_visible=True)
    layers = await get_layers()
    
    return {
        "total_categories": total_categories,
        "total_models": total_models,
        "visible_models": visible_models,
        "total_layers": len(layers),
        "layers": layers
    }


@router.get("/stats/layers")
async def get_layer_stats() -> List[dict]:
    """获取图层统计信息"""
    layers = await get_layers()
    stats = []
    
    for layer in layers:
        total = await count_geo_models(layer_name=layer, is_active=True)
        visible = await count_geo_models(layer_name=layer, is_active=True, is_visible=True)
        stats.append({
            "layer_name": layer,
            "total_models": total,
            "visible_models": visible,
            "visibility_rate": round(visible / total * 100, 2) if total > 0 else 0
        })
    
    return stats


# ==================== 批量操作接口 ====================

@router.post("/models/batch/create", response_model=List[GeoModelInDB])
async def batch_create_models_api(
    models: List[GeoModelCreate],
    current_user: User = Depends(get_current_active_user)
) -> List[GeoModelInDB]:
    """批量创建地理模型"""
    if len(models) > 100:
        raise HTTPException(status_code=400, detail="Batch size cannot exceed 100")
    
    created_models = []
    for model_data in models:
        try:
            model = await create_geo_model(model_data)
            created_models.append(model)
        except Exception as e:
            # 如果某个模型创建失败，继续创建其他模型
            continue
    
    return created_models


@router.delete("/models/batch/delete")
async def batch_delete_models_api(
    model_ids: List[int] = Query(..., description="要删除的模型ID列表"),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """批量删除地理模型"""
    if len(model_ids) > 100:
        raise HTTPException(status_code=400, detail="Batch size cannot exceed 100")
    
    deleted_count = 0
    for model_id in model_ids:
        success = await delete_geo_model(model_id)
        if success:
            deleted_count += 1
    
    return {
        "message": f"Deleted {deleted_count} out of {len(model_ids)} models",
        "deleted_count": deleted_count,
        "total_requested": len(model_ids)
    }