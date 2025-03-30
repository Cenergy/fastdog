from fastadmin import TortoiseModelAdmin, register, action, display, WidgetType
from tortoise.fields import CharField, TextField
from ..models import Album, Photo
from fastapi import UploadFile
from uuid import UUID
from PIL import Image
import io
import re
import base64
from core.config import settings
from .utils import process_image, save_image_file, process_base64_image, process_upload_file, get_image_dimensions
import os

@register(Album)
class AlbumModelAdmin(TortoiseModelAdmin):
    """相册管理类
    
    处理相册的创建、编辑、删除等管理操作
    支持封面图片的上传和处理
    删除相册及其关联的所有图片文件
    """
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
        """获取相册中的照片数量
        
        Args:
            obj: 相册对象
            
        Returns:
            照片数量
        """
        return await Photo.filter(album_id=obj.id).count()
    
    def is_valid_base64(self, base64_str: str) -> bool:
        """验证字符串是否为有效的base64图片格式
        
        Args:
            base64_str: 待验证的base64字符串
            
        Returns:
            是否为有效的base64图片格式
        """
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
        """处理封面图片
        
        Args:
            file: 上传的文件对象或base64字符串
            
        Returns:
            处理后的图片URL
            
        Raises:
            ValueError: 当文件格式不支持或处理失败时
        """
        upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "albums")
        os.makedirs(upload_dir, exist_ok=True)
        
        try:
            if isinstance(file, UploadFile):
                # 处理上传的文件
                file_ext, unique_filename = process_upload_file(file)
                file_path = os.path.join(upload_dir, unique_filename)
                content = await file.read()
                save_image_file(file_path, content)
                return f"/static/uploads/albums/{unique_filename}"
                
            elif isinstance(file, str):
                if not self.is_valid_base64(file):
                    raise ValueError("无效的base64图片格式或不支持的图片类型")
                    
                # 处理base64编码的图片
                unique_filename, image_data, file_type = process_base64_image(file, upload_dir)
                file_path = os.path.join(upload_dir, f"{unique_filename}.{file_type}")
                save_image_file(file_path, image_data)
                
                # 处理图片信息
                image = Image.open(io.BytesIO(image_data))
                dimensions = get_image_dimensions(image)
                
                # 设置原始图片URL
                original_url = f"/static/uploads/albums/{unique_filename}.{file_type}"
                
                # 生成缩略图和预览图
                result = process_image(image, unique_filename, upload_dir, dimensions["width"], dimensions["height"], f".{file_type}")
                # 确保result中包含original_url
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
                # 处理封面图片并确保正确赋值给payload
                image_url = await self.process_cover_image(file)
                payload["cover_image"] = image_url
                print(f"处理后的封面图片URL: {image_url}")
            
            # 确保cover_image字段被正确设置
            if "cover_image" in payload and payload["cover_image"] and isinstance(payload["cover_image"], str):
                print(f"保存前的cover_image: {payload['cover_image']}")
            
            result = await super().save_model(id, payload)
            
            # 验证保存结果
            if result and "id" in result:
                saved_album = await self.model.get(id=result["id"])
                print(f"保存后的album.cover_image: {saved_album.cover_image}")
                
                # 如果cover_image没有正确保存，尝试直接更新
                if "cover_image" in payload and payload["cover_image"] and saved_album.cover_image != payload["cover_image"]:
                    saved_album.cover_image = payload["cover_image"]
                    await saved_album.save()
                    print(f"更新后的album.cover_image: {saved_album.cover_image}")
            
            return result
        except Exception as e:
            print(f"保存相册时出错: {str(e)}")
            raise e
        
    async def delete_model(self, id: str) -> bool:
        """删除相册及其关联的所有图片文件
        
        Args:
            id: 相册ID
            
        Returns:
            删除是否成功
        """
        try:
            # 获取相册对象
            album = await self.model.get(id=id)
            
            # 删除封面图片及其预览图和缩略图
            if album.cover_image and album.cover_image.startswith('/static/uploads/'):
                # 删除原图
                cover_path = os.path.join(settings.STATIC_DIR, album.cover_image.replace('/static/', ''))
                if os.path.exists(cover_path):
                    os.remove(cover_path)
                
                # 构造并删除预览图
                preview_path = cover_path.replace('/uploads/', '/uploads/preview/')
                if os.path.exists(preview_path):
                    os.remove(preview_path)
                
                # 构造并删除缩略图
                thumbnail_path = cover_path.replace('/uploads/', '/uploads/thumbnail/')
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
            
            # 获取相册下的所有照片
            photos = await Photo.filter(album_id=id)
            
            # 删除每张照片的文件
            for photo in photos:
                # 删除原图
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
                
                # 删除缩略图
                if photo.thumbnail_url and photo.thumbnail_url.startswith('/static/uploads/'):
                    thumbnail_path = os.path.join(settings.STATIC_DIR, photo.thumbnail_url.replace('/static/', ''))
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                
                # 删除预览图
                if photo.preview_url and photo.preview_url.startswith('/static/uploads/'):
                    preview_path = os.path.join(settings.STATIC_DIR, photo.preview_url.replace('/static/', ''))
                    if os.path.exists(preview_path):
                        os.remove(preview_path)
            
            # 删除相册记录（这会级联删除所有关联的照片记录）
            return await super().delete_model(id)
            
        except Exception as e:
            print(f"删除相册及其图片文件时出错: {str(e)}")
            raise e

    async def to_dict(self, **kwargs) -> dict:
        """自定义字典转换方法

        重写以确保original_url字段在序列化时使用thumbnail_url的值（如果存在）

        Returns:
            处理后的对象数据字典
        """
        # 先获取原始数据字典
        data = await super().to_dict(**kwargs)
        print(f"to_dict 原始数据字典: {data}")
        return data