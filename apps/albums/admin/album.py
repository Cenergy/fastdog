from fastadmin import TortoiseModelAdmin, register, action, display, WidgetType
from tortoise.fields import CharField, TextField
from ..models import Album, Photo
from fastapi import UploadFile
from uuid import UUID, uuid4
import os
import re
import base64
from PIL import Image
import io
from core.config import settings
from fastadmin.api.helpers import is_valid_base64


def process_image(image: Image.Image, unique_id: str, upload_dir: str, width: int, height: int, file_ext: str = '.png') -> dict:
    """处理图片，生成缩略图和预览图"""
    result = {}
    
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
        
        preview_filename = f"{unique_id}_preview.jpg"
        preview_path = os.path.join(upload_dir, preview_filename)
        preview.convert("RGB").save(preview_path, "JPEG", quality=90)
        result["preview_url"] = f"/static/uploads/albums/{preview_filename}"
    else:
        unique_filename = unique_id + file_ext
        if "original_url" not in result:
            result["original_url"] = f"/static/uploads/albums/{unique_filename}"
        result["preview_url"] = result["original_url"]
    
    return result


def process_base64_image(base64_str: str, upload_dir: str) -> tuple:
    """处理base64编码的图片"""
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
    
    return unique_filename, image_data, file_type


def save_image_file(file_path: str, content: bytes) -> None:
    """保存图片文件到指定路径"""
    with open(file_path, "wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())


@register(Album)
class AlbumModelAdmin(TortoiseModelAdmin):
    """相册管理类"""
    model = Album
    icon = "image"
    display_name = "相册管理"
    list_display = ["id", "name", "is_public", "is_active", "created_at", "photo_count"]
    list_display_links = ["id", "name"]
    list_filter = ["is_public", "is_active", "created_at"]
    search_fields = ["name", "description"]
    list_per_page = 15
    ordering = ["-created_at"]
    
    form_fields = {
        "name": CharField(max_length=255, description="相册名称"),
        "description": TextField(description="相册描述", required=False),
        "is_public": WidgetType.Checkbox,
        "is_active": WidgetType.Checkbox,
        "cover_image": CharField(max_length=1024, description="封面图片", required=False),
        "sort_order": WidgetType.InputNumber
    }
    formfield_overrides = {
        "cover_image": (WidgetType.Upload, {"required": False, "upload_action_name": "upload"})
    }
    
    @display
    async def photo_count(self, obj) -> int:
        """获取相册中的照片数量"""
        return await Photo.filter(album_id=obj.id).count()
    
    def is_valid_base64(self, base64_str: str) -> bool:
        """验证字符串是否为有效的base64图片格式"""
        if not isinstance(base64_str, str):
            return False
            
        base64_pattern = r'^data:image/(\w+);base64,(.+)$'
        match = re.match(base64_pattern, base64_str)
        
        if not match:
            return False
            
        file_type = match.group(1).lower()
        if file_type not in ['jpeg', 'jpg', 'png', 'gif', 'webp', 'heic']:
            return False
            
        try:
            base64_data = match.group(2)
            base64.b64decode(base64_data)
            return True
        except Exception:
            return False

    async def process_cover_image(self, file: UploadFile | str) -> str:
        """处理封面图片"""
        upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "albums")
        os.makedirs(upload_dir, exist_ok=True)
        
        try:
            if isinstance(file, UploadFile):
                # 处理上传的文件
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext not in [".jpg", ".jpeg", ".png", ".gif"]:
                    raise ValueError(f"不支持的图片格式: {file_ext}")
                
                unique_filename = f"{uuid4().hex}{file_ext}"
                file_path = os.path.join(upload_dir, unique_filename)
                content = await file.read()
                save_image_file(file_path, content)
                return f"/static/uploads/albums/{unique_filename}"
                
            elif isinstance(file, str):
                if not self.is_valid_base64(file):
                    raise ValueError("无效的base64图片格式或不支持的图片类型")
                    
                unique_filename, image_data, file_type = process_base64_image(file, upload_dir)
                file_path = os.path.join(upload_dir, f"{unique_filename}.{file_type}")
                save_image_file(file_path, image_data)
                
                image = Image.open(io.BytesIO(image_data))
                width, height = image.size
                
                original_url = f"/static/uploads/albums/{unique_filename}.{file_type}"
                
                result = process_image(image, unique_filename, upload_dir, width, height, f".{file_type}")
                result["original_url"] = original_url
                return original_url
            else:
                raise ValueError("不支持的文件格式，仅支持文件上传或base64图片")
                
        except Exception as e:
            print(f"处理封面图片时出错: {str(e)}")
            if isinstance(e, ValueError):
                raise e
            raise ValueError(f"处理封面图片失败: {str(e)}")

    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        try:
            if "cover_image" in payload and payload["cover_image"] is not None:
                file = payload["cover_image"]
                image_url = await self.process_cover_image(file)
                payload["cover_image"] = image_url
                print(f"处理后的封面图片URL: {image_url}")
            
            if "cover_image" in payload and payload["cover_image"] and isinstance(payload["cover_image"], str):
                print(f"保存前的cover_image: {payload['cover_image']}")
            
            result = await super().save_model(id, payload)
            
            if result and "id" in result:
                saved_album = await self.model.get(id=result["id"])
                print(f"保存后的album.cover_image: {saved_album.cover_image}")
                
                if "cover_image" in payload and payload["cover_image"] and saved_album.cover_image != payload["cover_image"]:
                    saved_album.cover_image = payload["cover_image"]
                    await saved_album.save()
                    print(f"更新后的album.cover_image: {saved_album.cover_image}")
            
            return result
        except Exception as e:
            print(f"保存相册时出错: {str(e)}")
            raise e
        
    async def delete_model(self, id: str) -> bool:
        """删除相册及其关联的所有图片文件"""
        try:
            album = await self.model.get(id=id)
            
            if album.cover_image and album.cover_image.startswith('/static/uploads/'):
                cover_path = os.path.join(settings.STATIC_DIR, album.cover_image.replace('/static/', ''))
                if os.path.exists(cover_path):
                    os.remove(cover_path)
                
                preview_path = cover_path.replace('/uploads/', '/uploads/preview/')
                if os.path.exists(preview_path):
                    os.remove(preview_path)
                
                thumbnail_path = cover_path.replace('/uploads/', '/uploads/thumbnail/')
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
            
            photos = await Photo.filter(album_id=id)
            
            for photo in photos:
                if isinstance(photo.original_url, list):
                    for url in photo.original_url:
                        if url.startswith('/static/uploads/'):
                            file_path = os.path.join(settings.STATIC_DIR, url.replace('/static/', ''))
                            if os.path.exists(file_path):
                                os.remove(file_path)
                elif isinstance(photo.original_url, str) and photo.original_url.startswith('/static/uploads/'):
                    file_path = os.path.join(settings.STATIC_DIR, photo.original_url.replace('/static/', ''))
                    if os.path.exists(file_path):
                        os.remove(file_path)
                
                if photo.thumbnail_url and photo.thumbnail_url.startswith('/static/uploads/'):
                    thumbnail_path = os.path.join(settings.STATIC_DIR, photo.thumbnail_url.replace('/static/', ''))
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                
                if photo.preview_url and photo.preview_url.startswith('/static/uploads/'):
                    preview_path = os.path.join(settings.STATIC_DIR, photo.preview_url.replace('/static/', ''))
                    if os.path.exists(preview_path):
                        os.remove(preview_path)
            
            return await super().delete_model(id)
            
        except Exception as e:
            print(f"删除相册及其图片文件时出错: {str(e)}")
            raise e

    async def to_dict(self, **kwargs) -> dict:
        """自定义字典转换方法"""
        data = await super().to_dict(**kwargs)
        print(f"to_dict 原始数据字典: {data}")
        return data