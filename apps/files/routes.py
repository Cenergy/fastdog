from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File as FastAPIFile, Form, Body
from typing import List, Optional

from apps.files import crud
from apps.files.schemas import (
    FileCreate, FileUpdate, FileResponse,
    FileCategoryCreate, FileCategoryUpdate, FileCategoryResponse,
    FileUploadRequest, FileUploadResponse,
    FileBatchDeleteRequest, FileBatchUpdateRequest, FileBatchResponse,
    FileSearchRequest, FileSearchResponse,
    FileStatsResponse
)
from apps.files.models import FileFormat
from api.v1.deps import get_current_superuser
from apps.users.models import User

router = APIRouter()

# 文件分类接口
@router.get("/categories/", response_model=List[FileCategoryResponse])
async def read_file_categories(
    skip: int = 0,
    limit: int = 100,
    with_file_count: bool = Query(False, description="是否包含文件数量")
):
    """获取文件分类列表"""
    categories = await crud.get_file_categories(
        skip=skip,
        limit=limit,
        with_file_count=with_file_count
    )
    return categories

@router.post("/categories/", response_model=FileCategoryResponse)
async def create_file_category(category: FileCategoryCreate, current_user: User = Depends(get_current_superuser)):
    """创建文件分类"""
    return await crud.create_file_category(category)

@router.get("/categories/{category_id}", response_model=FileCategoryResponse)
async def read_file_category(category_id: int):
    """获取单个文件分类"""
    category = await crud.get_file_category(category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="文件分类不存在")
    return category

@router.put("/categories/{category_id}", response_model=FileCategoryResponse)
async def update_file_category(category_id: int, category: FileCategoryUpdate, current_user: User = Depends(get_current_superuser)):
    """更新文件分类"""
    updated_category = await crud.update_file_category(category_id, category)
    if updated_category is None:
        raise HTTPException(status_code=404, detail="文件分类不存在")
    return updated_category

@router.delete("/categories/{category_id}", response_model=dict)
async def delete_file_category(category_id: int, current_user: User = Depends(get_current_superuser)):
    """删除文件分类"""
    success = await crud.delete_file_category(category_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件分类不存在")
    return {"success": True}

# 文件接口
@router.get("/", response_model=List[FileResponse])
async def read_files(
    skip: int = 0,
    limit: int = 100,
    is_public: Optional[bool] = None,
    category_id: Optional[int] = None,
    file_format: Optional[FileFormat] = None,
    order_by: str = Query("created_at", description="排序字段"),
    order_desc: bool = Query(True, description="是否降序")
):
    """获取文件列表"""
    files = await crud.get_files(
        skip=skip,
        limit=limit,
        is_public=is_public,
        category_id=category_id,
        file_format=file_format,
        order_by=order_by,
        order_desc=order_desc
    )
    return files

@router.post("/", response_model=FileResponse)
async def create_file(file: FileCreate, current_user: User = Depends(get_current_superuser)):
    """创建文件"""
    return await crud.create_file(file)

@router.get("/{file_id}", response_model=FileResponse)
async def read_file(file_id: int):
    """获取单个文件"""
    file = await crud.get_file(file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    return file

@router.put("/{file_id}", response_model=FileResponse)
async def update_file(file_id: int, file: FileUpdate, current_user: User = Depends(get_current_superuser)):
    """更新文件"""
    updated_file = await crud.update_file(file_id, file)
    if updated_file is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    return updated_file

@router.delete("/{file_id}", response_model=dict)
async def delete_file(file_id: int, current_user: User = Depends(get_current_superuser)):
    """删除文件"""
    success = await crud.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"success": True}

# 文件上传接口
@router.post("/upload/", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    is_public: bool = Form(True),
    location: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    current_user: User = Depends(get_current_superuser)
):
    """上传文件"""
    try:
        # 创建文件记录
        file_data = FileCreate(
            title=title or file.filename,
            description=description,
            original_filename=file.filename,
            category_id=category_id,
            is_public=is_public,
            location=location,
            latitude=latitude,
            longitude=longitude
        )
        
        # 这里应该处理实际的文件上传逻辑
        # 由于文件上传涉及到文件系统操作，这里只是创建数据库记录
        # 实际的文件处理应该在admin.py中的save_model方法中完成
        created_file = await crud.create_file(file_data)
        
        return FileUploadResponse(
            success=True,
            message="文件上传成功",
            file=created_file
        )
    except Exception as e:
        return FileUploadResponse(
            success=False,
            message=f"文件上传失败: {str(e)}",
            errors=[str(e)]
        )

# 文件搜索接口
@router.post("/search/", response_model=FileSearchResponse)
async def search_files(search_request: FileSearchRequest):
    """搜索文件"""
    result = await crud.search_files(search_request)
    return FileSearchResponse(**result)

# 批量操作接口
@router.post("/batch/delete/", response_model=FileBatchResponse)
async def batch_delete_files(request: FileBatchDeleteRequest, current_user: User = Depends(get_current_superuser)):
    """批量删除文件"""
    result = await crud.batch_delete_files(request.file_ids)
    return FileBatchResponse(**result)

@router.post("/batch/update/", response_model=FileBatchResponse)
async def batch_update_files(request: FileBatchUpdateRequest, current_user: User = Depends(get_current_superuser)):
    """批量更新文件"""
    result = await crud.batch_update_files(request.file_ids, request.updates)
    return FileBatchResponse(**result)

# 地理位置相关接口
@router.get("/geo/", response_model=List[FileResponse])
async def read_files_by_coordinates(
    min_lat: float = Query(..., description="最小纬度"),
    max_lat: float = Query(..., description="最大纬度"),
    min_lng: float = Query(..., description="最小经度"),
    max_lng: float = Query(..., description="最大经度"),
    skip: int = 0,
    limit: int = 100,
    is_public: Optional[bool] = None
):
    """根据坐标范围获取文件"""
    files = await crud.get_files_by_coordinates(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lng=min_lng,
        max_lng=max_lng,
        skip=skip,
        limit=limit,
        is_public=is_public
    )
    return files

# 统计接口
@router.get("/stats/", response_model=FileStatsResponse)
async def get_file_stats():
    """获取文件统计信息"""
    return await crud.get_file_stats()

# 文件格式相关接口
@router.get("/formats/", response_model=List[dict])
async def get_file_formats():
    """获取支持的文件格式列表"""
    formats = []
    for format_enum in FileFormat:
        formats.append({
            "value": format_enum.value,
            "name": format_enum.name,
            "description": f"{format_enum.name} 格式"
        })
    return formats

# 文件类型统计接口
@router.get("/types/stats/", response_model=dict)
async def get_file_type_stats():
    """获取各文件类型的统计信息"""
    stats = await crud.get_file_stats()
    return {
        "image": stats.image_count,
        "video": stats.video_count,
        "audio": stats.audio_count,
        "document": stats.document_count,
        "archive": stats.archive_count,
        "other": stats.other_count
    }

# 文件数量统计接口
@router.get("/count/", response_model=dict)
async def count_files(
    is_public: Optional[bool] = None,
    category_id: Optional[int] = None,
    file_format: Optional[FileFormat] = None
):
    """统计文件数量"""
    count = await crud.count_files(
        is_public=is_public,
        category_id=category_id,
        file_format=file_format
    )
    return {"count": count}

# 分类数量统计接口
@router.get("/categories/count/", response_model=dict)
async def count_file_categories():
    """统计文件分类数量"""
    count = await crud.count_file_categories()
    return {"count": count}