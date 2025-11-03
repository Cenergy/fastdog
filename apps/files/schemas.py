from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import FileManager, FileCategory, FileFormat

# 文件分类模型
class FileCategoryBase(BaseModel):
    """文件分类基础模型"""
    name: str = Field(..., description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    is_active: bool = Field(True, description="是否可用")
    sort_order: int = Field(0, description="排序顺序")

class FileCategoryCreate(FileCategoryBase):
    """创建文件分类模型"""
    pass

class FileCategoryUpdate(BaseModel):
    """更新文件分类模型"""
    name: Optional[str] = Field(None, description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    is_active: Optional[bool] = Field(None, description="是否可用")
    sort_order: Optional[int] = Field(None, description="排序顺序")

class FileCategoryResponse(FileCategoryBase):
    """文件分类响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    file_count: Optional[int] = Field(0, description="文件数量")

    class Config:
        from_attributes = True

# 文件模型
class FileBase(BaseModel):
    """文件基础模型"""
    title: Optional[str] = Field(None, description="文件标题")
    description: Optional[str] = Field(None, description="文件描述")
    original_filename: Optional[str] = Field(None, description="原始文件名")
    file_format: Optional[FileFormat] = Field(None, description="文件格式")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    is_public: bool = Field(True, description="是否公开")
    is_active: bool = Field(True, description="是否可用")
    sort_order: int = Field(0, description="排序顺序")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")
    location: Optional[str] = Field(None, description="位置信息")
    taken_at: Optional[datetime] = Field(None, description="创建/拍摄时间")
    category_id: Optional[int] = Field(None, description="所属分类ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="文件元数据")

class FileCreate(FileBase):
    """创建文件模型"""
    pass

class FileUpdate(BaseModel):
    """更新文件模型"""
    title: Optional[str] = Field(None, description="文件标题")
    description: Optional[str] = Field(None, description="文件描述")
    original_filename: Optional[str] = Field(None, description="原始文件名")
    file_format: Optional[FileFormat] = Field(None, description="文件格式")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    is_public: Optional[bool] = Field(None, description="是否公开")
    is_active: Optional[bool] = Field(None, description="是否可用")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")
    location: Optional[str] = Field(None, description="位置信息")
    taken_at: Optional[datetime] = Field(None, description="创建/拍摄时间")
    category_id: Optional[int] = Field(None, description="所属分类ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="文件元数据")

class FileResponse(FileBase):
    """文件响应模型"""
    id: int
    original_url: Optional[str] = Field(None, description="原始文件URL")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    preview_url: Optional[str] = Field(None, description="预览图URL")
    created_at: datetime
    updated_at: datetime
    category: Optional[FileCategoryResponse] = Field(None, description="所属分类")
    
    # 文件类型判断属性
    is_image: bool = Field(False, description="是否为图片")
    is_video: bool = Field(False, description="是否为视频")
    is_audio: bool = Field(False, description="是否为音频")
    is_document: bool = Field(False, description="是否为文档")
    is_archive: bool = Field(False, description="是否为压缩包")

    class Config:
        from_attributes = True

# 文件上传模型
class FileUploadRequest(BaseModel):
    """文件上传请求模型"""
    title: Optional[str] = Field(None, description="文件标题")
    description: Optional[str] = Field(None, description="文件描述")
    category_id: Optional[int] = Field(None, description="所属分类ID")
    is_public: bool = Field(True, description="是否公开")
    location: Optional[str] = Field(None, description="位置信息")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")

class FileUploadResponse(BaseModel):
    """文件上传响应模型"""
    success: bool = Field(..., description="上传是否成功")
    message: str = Field(..., description="响应消息")
    file: Optional[FileResponse] = Field(None, description="上传的文件信息")
    errors: Optional[List[str]] = Field(None, description="错误信息列表")

# 批量操作模型
class FileBatchDeleteRequest(BaseModel):
    """批量删除文件请求模型"""
    file_ids: List[int] = Field(..., description="要删除的文件ID列表")

class FileBatchUpdateRequest(BaseModel):
    """批量更新文件请求模型"""
    file_ids: List[int] = Field(..., description="要更新的文件ID列表")
    updates: FileUpdate = Field(..., description="更新的字段")

class FileBatchResponse(BaseModel):
    """批量操作响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    processed_count: int = Field(0, description="处理的文件数量")
    failed_count: int = Field(0, description="失败的文件数量")
    errors: Optional[List[str]] = Field(None, description="错误信息列表")

# 文件搜索模型
class FileSearchRequest(BaseModel):
    """文件搜索请求模型"""
    keyword: Optional[str] = Field(None, description="搜索关键词")
    file_format: Optional[FileFormat] = Field(None, description="文件格式筛选")
    category_id: Optional[int] = Field(None, description="分类筛选")
    is_public: Optional[bool] = Field(None, description="公开状态筛选")
    is_active: Optional[bool] = Field(None, description="活跃状态筛选")
    date_from: Optional[datetime] = Field(None, description="开始日期")
    date_to: Optional[datetime] = Field(None, description="结束日期")
    min_size: Optional[int] = Field(None, description="最小文件大小(字节)")
    max_size: Optional[int] = Field(None, description="最大文件大小(字节)")
    has_location: Optional[bool] = Field(None, description="是否有位置信息")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    order_by: str = Field("created_at", description="排序字段")
    order_desc: bool = Field(True, description="是否降序")

class FileSearchResponse(BaseModel):
    """文件搜索响应模型"""
    files: List[FileResponse] = Field(..., description="文件列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")

# 文件统计模型
class FileStatsResponse(BaseModel):
    """文件统计响应模型"""
    total_files: int = Field(0, description="总文件数")
    total_size: int = Field(0, description="总文件大小(字节)")
    image_count: int = Field(0, description="图片数量")
    video_count: int = Field(0, description="视频数量")
    audio_count: int = Field(0, description="音频数量")
    document_count: int = Field(0, description="文档数量")
    archive_count: int = Field(0, description="压缩包数量")
    other_count: int = Field(0, description="其他文件数量")
    public_count: int = Field(0, description="公开文件数量")
    private_count: int = Field(0, description="私有文件数量")
    categories: List[Dict[str, Any]] = Field([], description="分类统计")