from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Body
from typing import List, Optional

from apps.albums import crud
from apps.albums.schemas import (
    AlbumCreate, AlbumUpdate, AlbumResponse,
    PhotoCreate, PhotoUpdate, PhotoResponse,
    CategoryCreate, CategoryUpdate, CategoryResponse
)
from api.v1.deps import get_current_superuser
from apps.users.models import User

router = APIRouter()

# 分类接口
@router.get("/categories/", response_model=List[CategoryResponse])
async def read_categories(
    skip: int = 0,
    limit: int = 100,
    with_album_count: bool = Query(False, description="是否包含相册数量")
):
    """获取分类列表"""
    categories = await crud.get_categories(
        skip=skip,
        limit=limit,
        with_album_count=with_album_count
    )
    return categories

@router.post("/categories/", response_model=CategoryResponse)
async def create_category(category: CategoryCreate, current_user: User = Depends(get_current_superuser)):
    """创建分类"""
    return await crud.create_category(category)

@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def read_category(category_id: int):
    """获取单个分类"""
    category = await crud.get_category(category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在")
    return category

@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: int, category: CategoryUpdate, current_user: User = Depends(get_current_superuser)):
    """更新分类"""
    updated_category = await crud.update_category(category_id, category)
    if updated_category is None:
        raise HTTPException(status_code=404, detail="分类不存在")
    return updated_category

@router.delete("/categories/{category_id}", response_model=dict)
async def delete_category(category_id: int, current_user: User = Depends(get_current_superuser)):
    """删除分类"""
    success = await crud.delete_category(category_id)
    if not success:
        raise HTTPException(status_code=404, detail="分类不存在")
    return {"success": True}

# 相册接口
@router.get("/", response_model=List[AlbumResponse])
async def read_albums(
    skip: int = 0,
    limit: int = 100,
    is_public: Optional[bool] = None,
    category_id: Optional[int] = None,
    with_photo_count: bool = Query(False, description="是否包含照片数量")
):
    """获取相册列表"""
    albums = await crud.get_albums(
        skip=skip,
        limit=limit,
        is_public=is_public,
        category_id=category_id,
        with_photo_count=with_photo_count
    )
    return albums

@router.post("/", response_model=AlbumResponse)
async def create_album(album: AlbumCreate, current_user: User = Depends(get_current_superuser)):
    """创建相册"""
    return await crud.create_album(album)

@router.get("/{album_id}", response_model=AlbumResponse)
async def read_album(album_id: int):
    """获取单个相册"""
    album = await crud.get_album(album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="相册不存在")
    return album

@router.put("/{album_id}", response_model=AlbumResponse)
async def update_album(album_id: int, album: AlbumUpdate, current_user: User = Depends(get_current_superuser)):
    """更新相册"""
    updated_album = await crud.update_album(album_id, album)
    if updated_album is None:
        raise HTTPException(status_code=404, detail="相册不存在")
    return updated_album

@router.delete("/{album_id}", response_model=dict)
async def delete_album(album_id: int, current_user: User = Depends(get_current_superuser)):
    """删除相册"""
    success = await crud.delete_album(album_id)
    if not success:
        raise HTTPException(status_code=404, detail="相册不存在")
    return {"success": True}

# 照片接口
@router.get("/photos/", response_model=List[PhotoResponse])
async def read_photos(
    skip: int = 0,
    limit: int = 100,
    album_id: Optional[int] = None
):
    """获取照片列表"""
    photos = await crud.get_photos(
        skip=skip,
        limit=limit,
        album_id=album_id
    )
    return photos

@router.post("/photos/", response_model=PhotoResponse)
async def create_photo(photo: PhotoCreate, current_user: User = Depends(get_current_superuser)):
    """创建照片"""
    return await crud.create_photo(photo)

@router.get("/photos/{photo_id}", response_model=PhotoResponse)
async def read_photo(photo_id: int):
    """获取单个照片"""
    photo = await crud.get_photo(photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="照片不存在")
    return photo

@router.put("/photos/{photo_id}", response_model=PhotoResponse)
async def update_photo(photo_id: int, photo: PhotoUpdate, current_user: User = Depends(get_current_superuser)):
    """更新照片"""
    updated_photo = await crud.update_photo(photo_id, photo)
    if updated_photo is None:
        raise HTTPException(status_code=404, detail="照片不存在")
    return updated_photo

@router.delete("/photos/{photo_id}", response_model=dict)
async def delete_photo(photo_id: int, current_user: User = Depends(get_current_superuser)):
    """删除照片"""
    success = await crud.delete_photo(photo_id)
    if not success:
        raise HTTPException(status_code=404, detail="照片不存在")
    return {"success": True}

# 地理位置相关接口
@router.get("/geo/photos/", response_model=List[PhotoResponse])
async def read_photos_by_coordinates(
    min_lat: float = Query(..., description="最小纬度"),
    max_lat: float = Query(..., description="最大纬度"),
    min_lng: float = Query(..., description="最小经度"),
    max_lng: float = Query(..., description="最大经度"),
    skip: int = 0,
    limit: int = 100
):
    """根据经纬度范围获取照片"""
    photos = await crud.get_photos_by_coordinates(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lng=min_lng,
        max_lng=max_lng,
        skip=skip,
        limit=limit
    )
    return photos

@router.get("/geo/albums/", response_model=List[AlbumResponse])
async def read_albums_by_coordinates(
    min_lat: float = Query(..., description="最小纬度"),
    max_lat: float = Query(..., description="最大纬度"),
    min_lng: float = Query(..., description="最小经度"),
    max_lng: float = Query(..., description="最大经度"),
    skip: int = 0,
    limit: int = 100,
    is_public: Optional[bool] = None
):
    """根据经纬度范围获取相册"""
    albums = await crud.get_albums_by_coordinates(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lng=min_lng,
        max_lng=max_lng,
        skip=skip,
        limit=limit,
        is_public=is_public
    )
    return albums