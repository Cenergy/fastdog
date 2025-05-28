from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# 相册分类模型
class CategoryBase(BaseModel):
    """分类基础模型"""
    name: str = Field(..., description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    is_active: bool = Field(True, description="是否可用")
    sort_order: int = Field(0, description="排序顺序")

class CategoryCreate(CategoryBase):
    """创建分类模型"""
    pass

class CategoryUpdate(BaseModel):
    """更新分类模型"""
    name: Optional[str] = Field(None, description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    is_active: Optional[bool] = Field(None, description="是否可用")
    sort_order: Optional[int] = Field(None, description="排序顺序")

class CategoryResponse(CategoryBase):
    """分类响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    album_count: Optional[int] = Field(0, description="相册数量")

    class Config:
        from_attributes = True

# 相册模型
class AlbumBase(BaseModel):
    """相册基础模型"""
    name: str = Field(..., description="相册名称")
    description: Optional[str] = Field(None, description="相册描述")
    cover_image: Optional[str] = Field(None, description="封面图片URL")
    is_public: bool = Field(True, description="是否公开")
    is_active: bool = Field(True, description="是否可用")
    sort_order: int = Field(0, description="排序顺序")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")
    category_id: Optional[int] = Field(None, description="所属分类ID")

class AlbumCreate(AlbumBase):
    """创建相册模型"""
    pass

class AlbumUpdate(BaseModel):
    """更新相册模型"""
    name: Optional[str] = Field(None, description="相册名称")
    description: Optional[str] = Field(None, description="相册描述")
    cover_image: Optional[str] = Field(None, description="封面图片URL")
    is_public: Optional[bool] = Field(None, description="是否公开")
    is_active: Optional[bool] = Field(None, description="是否可用")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")
    category_id: Optional[int] = Field(None, description="所属分类ID")

class AlbumResponse(AlbumBase):
    """相册响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    photo_count: Optional[int] = Field(0, description="照片数量")
    category: Optional[CategoryResponse] = Field(None, description="所属分类")

    class Config:
        from_attributes = True

# 照片模型
class PhotoBase(BaseModel):
    """照片基础模型"""
    title: Optional[str] = Field(None, description="照片标题")
    description: Optional[str] = Field(None, description="照片描述")
    album_id: int = Field(..., description="所属相册ID")
    sort_order: int = Field(0, description="排序顺序")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")

class PhotoCreate(PhotoBase):
    """创建照片模型"""
    pass

class PhotoUpdate(BaseModel):
    """更新照片模型"""
    title: Optional[str] = Field(None, description="照片标题")
    description: Optional[str] = Field(None, description="照片描述")
    album_id: Optional[int] = Field(None, description="所属相册ID")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")

class PhotoResponse(PhotoBase):
    """照片响应模型"""
    id: int
    original_url: List[str]= Field([], description="原始图片URL列表")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    preview_url: Optional[str] = Field(None, description="预览图URL")
    file_format: str = Field("other", description="文件格式")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    taken_at: Optional[datetime] = Field(None, description="拍摄时间")
    location: Optional[str] = Field(None, description="拍摄地点")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True