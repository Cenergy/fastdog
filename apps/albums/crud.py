from tortoise.expressions import Q
from tortoise.functions import Count
from typing import List, Optional, Dict, Any, Union

from apps.albums.models import Album, Photo, AlbumCategory
from apps.albums.schemas import AlbumCreate, AlbumUpdate, PhotoCreate, PhotoUpdate, CategoryCreate, CategoryUpdate

# 分类 CRUD操作
async def get_category(category_id: int) -> Optional[AlbumCategory]:
    """获取单个分类"""
    return await AlbumCategory.get_or_none(id=category_id)

async def get_categories(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = True,
    with_album_count: bool = False,
) -> List[AlbumCategory]:
    """获取分类列表"""
    query = AlbumCategory.filter(is_active=is_active)
    
    # 添加相册数量统计
    if with_album_count:
        query = query.annotate(album_count=Count('albums'))
    
    return await query.order_by('sort_order', '-created_at').offset(skip).limit(limit).all()

async def create_category(category_data: CategoryCreate) -> AlbumCategory:
    """创建分类"""
    category_dict = category_data.dict(exclude_unset=True)
    category = await AlbumCategory.create(**category_dict)
    return category

async def update_category(category_id: int, category_data: CategoryUpdate) -> Optional[AlbumCategory]:
    """更新分类"""
    category = await get_category(category_id)
    if not category:
        return None
    
    update_data = category_data.dict(exclude_unset=True, exclude_none=True)
    if update_data:
        await category.update_from_dict(update_data).save()
    
    return category

async def delete_category(category_id: int) -> bool:
    """删除分类"""
    category = await get_category(category_id)
    if not category:
        return False
    
    # 逻辑删除，将is_active设为False
    category.is_active = False
    await category.save(update_fields=["is_active"])
    return True

# Album CRUD操作
async def get_album(album_id: int) -> Optional[Album]:
    """获取单个相册"""
    return await Album.get_or_none(id=album_id)

async def get_albums(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = True,
    is_public: Optional[bool] = None,
    category_id: Optional[int] = None,
    with_photo_count: bool = False,
) -> List[Album]:
    """获取相册列表"""
    query = Album.filter(is_active=is_active).prefetch_related('category')
    
    if is_public is not None:
        query = query.filter(is_public=is_public)
    
    if category_id is not None:
        query = query.filter(category_id=category_id)
    
    # 添加照片数量统计
    if with_photo_count:
        query = query.annotate(photo_count=Count('photos'))
    
    return await query.order_by('-created_at').offset(skip).limit(limit).all()

async def create_album(album_data: AlbumCreate) -> Album:
    """创建相册"""
    album_dict = album_data.dict(exclude_unset=True)
    album = await Album.create(**album_dict)
    return album

async def update_album(album_id: int, album_data: AlbumUpdate) -> Optional[Album]:
    """更新相册"""
    album = await get_album(album_id)
    if not album:
        return None
    
    update_data = album_data.dict(exclude_unset=True, exclude_none=True)
    if update_data:
        await album.update_from_dict(update_data).save()
    
    return album

async def delete_album(album_id: int) -> bool:
    """删除相册"""
    album = await get_album(album_id)
    if not album:
        return False
    
    # 逻辑删除，将is_active设为False
    album.is_active = False
    await album.save(update_fields=["is_active"])
    return True

# Photo CRUD操作
async def get_photo(photo_id: int) -> Optional[Photo]:
    """获取单个照片"""
    return await Photo.get_or_none(id=photo_id)

async def get_photos(
    skip: int = 0,
    limit: int = 100,
    album_id: Optional[int] = None,
    is_active: bool = True,
) -> List[Photo]:
    """获取照片列表"""
    query = Photo.filter(is_active=is_active)
    
    if album_id is not None:
        query = query.filter(album_id=album_id)
    
    return await query.order_by('sort_order', '-created_at').offset(skip).limit(limit).all()

async def create_photo(photo_data: PhotoCreate) -> Photo:
    """创建照片"""
    photo_dict = photo_data.dict(exclude_unset=True)
    photo = await Photo.create(**photo_dict)
    return photo

async def update_photo(photo_id: int, photo_data: PhotoUpdate) -> Optional[Photo]:
    """更新照片"""
    photo = await get_photo(photo_id)
    if not photo:
        return None
    
    update_data = photo_data.dict(exclude_unset=True, exclude_none=True)
    if update_data:
        await photo.update_from_dict(update_data).save()
    
    return photo

async def delete_photo(photo_id: int) -> bool:
    """删除照片"""
    photo = await get_photo(photo_id)
    if not photo:
        return False
    
    # 逻辑删除，将is_active设为False
    photo.is_active = False
    await photo.save(update_fields=["is_active"])
    return True

async def get_photos_by_coordinates(
    min_lat: float,
    max_lat: float,
    min_lng: float,
    max_lng: float,
    skip: int = 0,
    limit: int = 100,
    is_active: bool = True,
) -> List[Photo]:
    """根据经纬度范围获取照片"""
    query = Photo.filter(
        Q(is_active=is_active) &
        Q(latitude__gte=min_lat) &
        Q(latitude__lte=max_lat) &
        Q(longitude__gte=min_lng) &
        Q(longitude__lte=max_lng)
    )
    
    return await query.order_by('-created_at').offset(skip).limit(limit).all()

async def get_albums_by_coordinates(
    min_lat: float,
    max_lat: float,
    min_lng: float,
    max_lng: float,
    skip: int = 0,
    limit: int = 100,
    is_active: bool = True,
    is_public: Optional[bool] = None,
) -> List[Album]:
    """根据经纬度范围获取相册"""
    query = Album.filter(
        Q(is_active=is_active) &
        Q(latitude__gte=min_lat) &
        Q(latitude__lte=max_lat) &
        Q(longitude__gte=min_lng) &
        Q(longitude__lte=max_lng)
    )
    
    if is_public is not None:
        query = query.filter(is_public=is_public)
    
    return await query.order_by('-created_at').offset(skip).limit(limit).all()