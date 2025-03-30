from fastadmin import TortoiseModelAdmin, register, action, display, WidgetType
from tortoise.fields import CharField, TextField, JSONField
from ..models import Album, Photo, PhotoFormat
from fastapi import UploadFile
from uuid import UUID, uuid4
from uuid import UUID
import os
import re
import base64
from PIL import Image, UnidentifiedImageError
import io
from core.config import settings
from fastadmin.api.helpers import is_valid_base64
from typing import Optional, Dict, Any, List, Tuple

def process_image(image: Image.Image, unique_id: str, upload_dir: str, width: int, height: int,file_ext:str='.png') -> Dict[str, Any]:
    """处理图片，生成缩略图和预览图
    
    Args:
        image: PIL Image对象
        unique_id: 唯一标识符
        upload_dir: 上传目录路径
        width: 原图宽度
        height: 原图高度
        
    Returns:
        包含图片处理结果的字典，包括缩略图和预览图URL
    """
    # 初始化结果字典，设置原始图片URL
    result = {}
    # 注意：这里不设置original_url，应该由调用方提供
    
    # 生成缩略图 (200px宽)
    thumbnail_size = (200, int(200 * height / width))
    thumbnail = image.copy()
    thumbnail.thumbnail(thumbnail_size, Image.LANCZOS)
    
    # 保存缩略图
    thumbnail_filename = f"{unique_id}_thumbnail.jpg"
    thumbnail_path = os.path.join(upload_dir, thumbnail_filename)
    thumbnail.convert("RGB").save(thumbnail_path, "JPEG", quality=85)
    result["thumbnail_url"] = f"/static/uploads/albums/{thumbnail_filename}"
    
    # 生成预览图 (1000px宽)
    if width > 1000:
        preview_size = (1000, int(1000 * height / width))
        preview = image.copy()
        preview.thumbnail(preview_size, Image.LANCZOS)
        
        # 保存预览图
        preview_filename = f"{unique_id}_preview.jpg"
        preview_path = os.path.join(upload_dir, preview_filename)
        preview.convert("RGB").save(preview_path, "JPEG", quality=90)
        result["preview_url"] = f"/static/uploads/albums/{preview_filename}"
    else:
        # 如果原图小于预览图尺寸，则使用原图作为预览图
        # 确保original_url已经被设置
        unique_filename = unique_id+file_ext
        if "original_url" not in result:
            # 如果没有设置original_url，使用一个默认值
            result["original_url"] = f"/static/uploads/albums/{unique_filename}"
        result["preview_url"] = result["original_url"]
    
    return result


def ensure_upload_dirs() -> Tuple[str, str, str]:
    """确保上传目录存在
    
    Returns:
        包含上传目录、缩略图目录和预览图目录路径的元组
    """
    upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos")
    thumbnails_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos", "thumbnails")
    previews_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos", "previews")
    
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(thumbnails_dir, exist_ok=True)
    os.makedirs(previews_dir, exist_ok=True)
    
    return upload_dir, thumbnails_dir, previews_dir


def save_image_file(file_path: str, content: bytes) -> None:
    """保存图片文件到指定路径
    
    Args:
        file_path: 文件保存路径
        content: 文件内容
    """
    with open(file_path, "wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())


def create_file_payload(unique_filename: str, payload: Dict[str, Any], file_type: str = "photos") -> Dict[str, Any]:
    """创建文件处理的payload
    
    Args:
        unique_filename: 唯一文件名
        payload: 原始payload
        file_type: 文件类型，默认为photos
        
    Returns:
        处理后的payload字典
    """
    return {
        "original_url": f"/static/uploads/{file_type}/{unique_filename}",
        "album": payload.get("album"),
        "title": payload.get("title") or "未命名照片",
        "description": payload.get("description"),
        "is_active": payload.get("is_active", True),
        "sort_order": payload.get("sort_order", 0),
        "exif_data": {}  # 默认空字典
    }


def process_base64_image(base64_str: str, upload_dir: str) -> Tuple[str, bytes, str]:
    """处理base64编码的图片
    
    Args:
        base64_str: base64编码的图片字符串
        upload_dir: 上传目录路径
        
    Returns:
        包含文件名、图片数据和文件类型的元组
    
    Raises:
        ValueError: 当base64数据格式无效或图片格式不支持时
    """
    base64_pattern = r'^data:image/(\w+);base64,(.+)$'
    match = re.match(base64_pattern, base64_str)
    
    if not match:
        raise ValueError("无效的base64图片数据")
    
    file_type = match.group(1)
    base64_data = match.group(2)
    
    if file_type not in ['jpeg', 'jpg', 'png', 'gif', 'webp', 'heic']:
        raise ValueError(f"不支持的图片格式: {file_type}")
    
    unique_filename = f"{uuid4().hex}"
    image_data = base64.b64decode(base64_data)
    
    return unique_filename, image_data,file_type


def process_upload_file(file: UploadFile) -> Tuple[str, str]:
    """处理上传的文件
    
    Args:
        file: FastAPI的UploadFile对象
        
    Returns:
        包含文件扩展名和唯一文件名的元组
    
    Raises:
        ValueError: 当文件格式不支持时
    """
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        raise ValueError(f"不支持的图片格式: {file_ext}")
    
    unique_filename = f"{uuid4().hex}{file_ext}"
    return file_ext, unique_filename


def extract_exif_data(image: Image.Image) -> Dict[str, Any]:
    """从图片中提取EXIF数据
    
    Args:
        image: PIL Image对象
        
    Returns:
        包含EXIF数据的字典
    """
    exif_data = {}
    try:
        if hasattr(image, '_getexif') and image._getexif() is not None:
            exif = image._getexif()
            exif_data = {str(k): str(v) for k, v in exif.items()}
            
            # 提取拍摄时间
            if 36867 in exif:  # DateTimeOriginal
                from datetime import datetime
                taken_at = datetime.strptime(exif[36867], "%Y:%m:%d %H:%M:%S")
                exif_data["taken_at"] = taken_at.isoformat()
    except Exception as e:
        print(f"提取EXIF数据时出错: {str(e)}")
    
    return exif_data


def get_image_dimensions(image: Image.Image) -> Dict[str, int]:
    """获取图片尺寸信息
    
    Args:
        image: PIL Image对象
        
    Returns:
        包含图片宽度和高度的字典
    """
    width, height = image.size
    return {
        "width": width,
        "height": height
    }