from tortoise.queryset import Q
from tortoise.functions import Count, Sum
from typing import List, Optional, Dict, Any, Union
import os
from datetime import datetime

from apps.files.models import FileManager, FileCategory, FileFormat
from apps.files.schemas import (
    FileCreate, FileUpdate, FileCategoryCreate, FileCategoryUpdate,
    FileSearchRequest, FileStatsResponse
)


def generate_file_urls(file: FileManager) -> None:
    """为文件生成缩略图和预览图URL"""
    if file.original_url:
        # 基于原始文件生成缩略图和预览图URL
        original_path = file.original_url
        if original_path.startswith('/static/uploads/'):
            # 提取文件名（不含扩展名）
            filename = os.path.splitext(original_path)[0]
            # 生成缩略图URL (添加_thumbnail.jpg后缀)
            file.thumbnail_url = f"{filename}_thumbnail.jpg"
            # 生成预览图URL (添加_preview.webp后缀)
            file.preview_url = f"{filename}_preview.webp"
        else:
            # 如果不是标准上传路径，使用原文件作为缩略图和预览图
            file.thumbnail_url = original_path
            file.preview_url = original_path
    else:
        # 没有原始文件时使用默认图片
        file.thumbnail_url = "/static/default.png"
        file.preview_url = "/static/default.png"

# 文件分类 CRUD操作
async def get_file_category(category_id: int) -> Optional[FileCategory]:
    """获取单个文件分类"""
    return await FileCategory.get_or_none(id=category_id)

async def get_file_categories(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = True,
    with_file_count: bool = False,
) -> List[FileCategory]:
    """获取文件分类列表"""
    query = FileCategory.filter(is_active=is_active)
    
    # 添加文件数量统计
    if with_file_count:
        query = query.annotate(file_count=Count('files'))
    
    return await query.order_by('sort_order', '-created_at').offset(skip).limit(limit).all()

async def create_file_category(category_data: FileCategoryCreate) -> FileCategory:
    """创建文件分类"""
    category_dict = category_data.dict(exclude_unset=True)
    category = await FileCategory.create(**category_dict)
    return category

async def update_file_category(category_id: int, category_data: FileCategoryUpdate) -> Optional[FileCategory]:
    """更新文件分类"""
    category = await get_file_category(category_id)
    if not category:
        return None
    
    update_data = category_data.dict(exclude_unset=True, exclude_none=True)
    if update_data:
        await category.update_from_dict(update_data).save()
    
    return category

async def delete_file_category(category_id: int) -> bool:
    """删除文件分类"""
    category = await get_file_category(category_id)
    if not category:
        return False
    
    # 逻辑删除，将is_active设为False
    category.is_active = False
    await category.save(update_fields=["is_active"])
    return True

# 文件 CRUD操作
async def get_file(file_id: int) -> Optional[FileManager]:
    """获取单个文件"""
    file = await FileManager.get_or_none(id=file_id)
    if file:
        generate_file_urls(file)
    return file

async def get_files(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = True,
    is_public: Optional[bool] = None,
    category_id: Optional[int] = None,
    file_format: Optional[FileFormat] = None,
    order_by: str = "created_at",
    order_desc: bool = True,
) -> List[FileManager]:
    """获取文件列表"""
    query = FileManager.filter(is_active=is_active).prefetch_related('category')
    
    if is_public is not None:
        query = query.filter(is_public=is_public)
    
    if category_id is not None:
        query = query.filter(category_id=category_id)
    
    if file_format is not None:
        query = query.filter(file_format=file_format)
    
    # 排序
    order_field = f"-{order_by}" if order_desc else order_by
    query = query.order_by(order_field)
    
    files = await query.offset(skip).limit(limit).all()
    
    # 为每个文件生成URL
    for file in files:
        generate_file_urls(file)
    
    return files

async def create_file(file_data: FileCreate) -> FileManager:
    """创建文件"""
    file_dict = file_data.dict(exclude_unset=True)
    file = await FileManager.create(**file_dict)
    generate_file_urls(file)
    return file

async def update_file(file_id: int, file_data: FileUpdate) -> Optional[FileManager]:
    """更新文件"""
    file = await get_file(file_id)
    if not file:
        return None
    
    update_data = file_data.dict(exclude_unset=True, exclude_none=True)
    if update_data:
        await file.update_from_dict(update_data).save()
    
    generate_file_urls(file)
    return file

async def delete_file(file_id: int) -> bool:
    """删除文件"""
    file = await get_file(file_id)
    if not file:
        return False
    
    # 逻辑删除，将is_active设为False
    file.is_active = False
    await file.save(update_fields=["is_active"])
    return True

async def search_files(search_request: FileSearchRequest) -> Dict[str, Any]:
    """搜索文件"""
    query = FileManager.filter(is_active=True).prefetch_related('category')
    
    # 关键词搜索
    if search_request.keyword:
        keyword = search_request.keyword.strip()
        query = query.filter(
            Q(title__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(original_filename__icontains=keyword)
        )
    
    # 文件格式筛选
    if search_request.file_format:
        query = query.filter(file_format=search_request.file_format)
    
    # 分类筛选
    if search_request.category_id:
        query = query.filter(category_id=search_request.category_id)
    
    # 公开状态筛选
    if search_request.is_public is not None:
        query = query.filter(is_public=search_request.is_public)
    
    # 活跃状态筛选
    if search_request.is_active is not None:
        query = query.filter(is_active=search_request.is_active)
    
    # 日期范围筛选
    if search_request.date_from:
        query = query.filter(created_at__gte=search_request.date_from)
    
    if search_request.date_to:
        query = query.filter(created_at__lte=search_request.date_to)
    
    # 文件大小筛选
    if search_request.min_size:
        query = query.filter(file_size__gte=search_request.min_size)
    
    if search_request.max_size:
        query = query.filter(file_size__lte=search_request.max_size)
    
    # 位置信息筛选
    if search_request.has_location is not None:
        if search_request.has_location:
            query = query.filter(
                Q(latitude__isnull=False) & Q(longitude__isnull=False)
            )
        else:
            query = query.filter(
                Q(latitude__isnull=True) | Q(longitude__isnull=True)
            )
    
    # 获取总数
    total = await query.count()
    
    # 排序
    order_field = f"-{search_request.order_by}" if search_request.order_desc else search_request.order_by
    query = query.order_by(order_field)
    
    # 分页
    skip = (search_request.page - 1) * search_request.page_size
    files = await query.offset(skip).limit(search_request.page_size).all()
    
    # 为每个文件生成URL
    for file in files:
        generate_file_urls(file)
    
    # 计算分页信息
    total_pages = (total + search_request.page_size - 1) // search_request.page_size
    has_next = search_request.page < total_pages
    has_prev = search_request.page > 1
    
    return {
        "files": files,
        "total": total,
        "page": search_request.page,
        "page_size": search_request.page_size,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev,
    }

async def get_files_by_coordinates(
    min_lat: float,
    max_lat: float,
    min_lng: float,
    max_lng: float,
    skip: int = 0,
    limit: int = 100,
    is_active: bool = True,
    is_public: Optional[bool] = None,
) -> List[FileManager]:
    """根据坐标范围获取文件"""
    query = FileManager.filter(
        is_active=is_active,
        latitude__gte=min_lat,
        latitude__lte=max_lat,
        longitude__gte=min_lng,
        longitude__lte=max_lng,
        latitude__isnull=False,
        longitude__isnull=False
    ).prefetch_related('category')
    
    if is_public is not None:
        query = query.filter(is_public=is_public)
    
    files = await query.order_by('-created_at').offset(skip).limit(limit).all()
    
    # 为每个文件生成URL
    for file in files:
        generate_file_urls(file)
    
    return files

async def get_file_stats() -> FileStatsResponse:
    """获取文件统计信息"""
    # 基础统计
    total_files = await FileManager.filter(is_active=True).count()
    total_size_result = await FileManager.filter(is_active=True).aggregate(total_size=Sum('file_size'))
    total_size = total_size_result.get('total_size') or 0
    
    # 按文件格式统计
    image_formats = [
        FileFormat.JPG, FileFormat.JPEG, FileFormat.PNG, FileFormat.GIF,
        FileFormat.HEIC, FileFormat.WEBP, FileFormat.BMP, FileFormat.TIFF, FileFormat.SVG
    ]
    video_formats = [FileFormat.MP4, FileFormat.AVI, FileFormat.MOV, FileFormat.WMV, FileFormat.FLV, FileFormat.MKV, FileFormat.WEBM]
    audio_formats = [FileFormat.MP3, FileFormat.WAV, FileFormat.FLAC, FileFormat.AAC, FileFormat.OGG, FileFormat.M4A]
    document_formats = [FileFormat.PDF, FileFormat.DOC, FileFormat.DOCX, FileFormat.XLS, FileFormat.XLSX, FileFormat.PPT, FileFormat.PPTX, FileFormat.TXT, FileFormat.RTF]
    archive_formats = [FileFormat.ZIP, FileFormat.RAR, FileFormat.TAR, FileFormat.GZ, FileFormat.SEVENZ]
    
    image_count = await FileManager.filter(is_active=True, file_format__in=image_formats).count()
    video_count = await FileManager.filter(is_active=True, file_format__in=video_formats).count()
    audio_count = await FileManager.filter(is_active=True, file_format__in=audio_formats).count()
    document_count = await FileManager.filter(is_active=True, file_format__in=document_formats).count()
    archive_count = await FileManager.filter(is_active=True, file_format__in=archive_formats).count()
    other_count = total_files - (image_count + video_count + audio_count + document_count + archive_count)
    
    # 按公开状态统计
    public_count = await FileManager.filter(is_active=True, is_public=True).count()
    private_count = await FileManager.filter(is_active=True, is_public=False).count()
    
    # 按分类统计
    categories_stats = await FileCategory.filter(is_active=True).annotate(
        file_count=Count('files', _filter=Q(files__is_active=True))
    ).values('id', 'name', 'file_count')
    
    return FileStatsResponse(
        total_files=total_files,
        total_size=total_size,
        image_count=image_count,
        video_count=video_count,
        audio_count=audio_count,
        document_count=document_count,
        archive_count=archive_count,
        other_count=other_count,
        public_count=public_count,
        private_count=private_count,
        categories=list(categories_stats)
    )

async def batch_delete_files(file_ids: List[int]) -> Dict[str, Any]:
    """批量删除文件"""
    processed_count = 0
    failed_count = 0
    errors = []
    
    for file_id in file_ids:
        try:
            success = await delete_file(file_id)
            if success:
                processed_count += 1
            else:
                failed_count += 1
                errors.append(f"文件ID {file_id} 不存在")
        except Exception as e:
            failed_count += 1
            errors.append(f"删除文件ID {file_id} 失败: {str(e)}")
    
    return {
        "success": failed_count == 0,
        "message": f"成功处理 {processed_count} 个文件，失败 {failed_count} 个",
        "processed_count": processed_count,
        "failed_count": failed_count,
        "errors": errors if errors else None
    }

async def batch_update_files(file_ids: List[int], update_data: FileUpdate) -> Dict[str, Any]:
    """批量更新文件"""
    processed_count = 0
    failed_count = 0
    errors = []
    
    for file_id in file_ids:
        try:
            file = await update_file(file_id, update_data)
            if file:
                processed_count += 1
            else:
                failed_count += 1
                errors.append(f"文件ID {file_id} 不存在")
        except Exception as e:
            failed_count += 1
            errors.append(f"更新文件ID {file_id} 失败: {str(e)}")
    
    return {
        "success": failed_count == 0,
        "message": f"成功处理 {processed_count} 个文件，失败 {failed_count} 个",
        "processed_count": processed_count,
        "failed_count": failed_count,
        "errors": errors if errors else None
    }

async def count_files(
    is_active: bool = True,
    is_public: Optional[bool] = None,
    category_id: Optional[int] = None,
    file_format: Optional[FileFormat] = None,
) -> int:
    """统计文件数量"""
    query = FileManager.filter(is_active=is_active)
    
    if is_public is not None:
        query = query.filter(is_public=is_public)
    
    if category_id is not None:
        query = query.filter(category_id=category_id)
    
    if file_format is not None:
        query = query.filter(file_format=file_format)
    
    return await query.count()

async def count_file_categories(is_active: bool = True) -> int:
    """统计文件分类数量"""
    return await FileCategory.filter(is_active=is_active).count()