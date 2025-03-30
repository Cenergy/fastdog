from fastadmin import TortoiseModelAdmin, register, action, display, WidgetType
from tortoise.fields import CharField, TextField, JSONField
from ..models import Album, Photo, PhotoFormat
from uuid import UUID, uuid4
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image
import os
import io
import base64
from fastapi import UploadFile
from core.config import settings
from fastadmin.api.helpers import is_valid_base64
class PhotoUtils:
    """照片处理工具类"""
    
    @staticmethod
    def process_image(image: Image.Image, unique_id: str, upload_dir: str, width: int, height: int, file_ext: str = '.png') -> dict:
        """处理图片，生成缩略图和预览图"""
        result = {}
        
        # 生成缩略图
        thumbnail = image.copy()
        thumbnail.thumbnail((width, height))
        thumbnail_filename = f"thumbnail_{unique_id}{file_ext}"
        thumbnail_path = os.path.join(upload_dir, thumbnail_filename)
        thumbnail.save(thumbnail_path)
        result["thumbnail_url"] = f"/static/uploads/photos/{thumbnail_filename}"
        
        # 生成预览图
        preview = image.copy()
        preview.thumbnail((800, 800))
        preview_filename = f"preview_{unique_id}{file_ext}"
        preview_path = os.path.join(upload_dir, preview_filename)
        preview.save(preview_path)
        result["preview_url"] = f"/static/uploads/photos/{preview_filename}"
        
        # 保存原图
        unique_filename = f"original_{unique_id}{file_ext}"
        original_path = os.path.join(upload_dir, unique_filename)
        image.save(original_path)
        result["original_url"] = f"/static/uploads/photos/{unique_filename}"
        
        return result
    
    @staticmethod
    def process_base64_image(base64_str: str, upload_dir: str) -> tuple:
        """处理base64格式的图片数据"""
        # 移除base64前缀
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
            
        # 解码base64数据
        image_data = base64.b64decode(base64_str)
        
        # 生成唯一文件名
        unique_id = str(uuid4())
        
        # 确定文件类型
        image = Image.open(io.BytesIO(image_data))
        file_type = image.format.lower()
        
        return unique_id, image_data, file_type
    
    @staticmethod
    async def process_photo_file(file: UploadFile | str) -> Dict[str, Any]:
        """处理上传的照片文件"""
        upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos")
        os.makedirs(upload_dir, exist_ok=True)
        
        width, height = 200, 200  # 缩略图尺寸
        
        # 处理UploadFile类型
        if isinstance(file, UploadFile):
            content = await file.read()
            image = Image.open(io.BytesIO(content))
            file_type = image.format.lower()
            unique_id = str(uuid4())
            
            return PhotoUtils.process_image(image, unique_id, upload_dir, width, height, f".{file_type}")
        
        # 处理base64字符串
        elif isinstance(file, str) and is_valid_base64(file):
            unique_id, image_data, file_type = PhotoUtils.process_base64_image(file, upload_dir)
            image = Image.open(io.BytesIO(image_data))
            
            return PhotoUtils.process_image(image, unique_id, upload_dir, width, height, f".{file_type}")
        
        return {}


class CustomModelAdmin(TortoiseModelAdmin):
    """自定义ModelAdmin基类，用于在不修改源码的情况下重写BaseModelAdmin方法"""
    
    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        """This method is used to save orm/db model object.

        :params id: an id of object.
        :params payload: a payload from request.
        :return: A saved object or None.
        """
        fields = self.get_model_fields_with_widget_types(with_m2m=False, with_upload=False)
        m2m_fields = self.get_model_fields_with_widget_types(with_m2m=True)
        upload_fields = self.get_model_fields_with_widget_types(with_upload=True)

        fields_payload = {
            field.column_name: self.deserialize_value(field, payload[field.name])
            for field in fields
            if field.name in payload
        }
        obj = await self.orm_save_obj(id, fields_payload)
        if not obj:
            return None

        for upload_field in upload_fields:
            if upload_field.name in payload:
                field_value = payload[upload_field.name]
                if isinstance(field_value, list):
                    continue
                elif isinstance(field_value, str):
                    # 处理图片上传
                    photo_info = await PhotoUtils.process_photo_file(field_value)
                    if photo_info:
                        for key, value in photo_info.items():
                            setattr(obj, key, value)
                        await obj.save()

        for m2m_field in m2m_fields:
            if m2m_field.name in payload:
                await self.orm_save_m2m_ids(obj, m2m_field.column_name, payload[m2m_field.name])

        return await self.serialize_obj(obj)


@register(Photo)
class PhotoModelAdmin(CustomModelAdmin):
    """照片管理类"""
    model = Photo
    order = 3
    icon = "camera"
    display_name = "照片管理"
    list_display = ["id", "title", "album_name", "file_format", "thumbnail_preview", "is_active", "created_at"]
    list_display_links = ["id", "title"]
    list_filter = ["file_format", "is_active", "created_at", "album"]
    search_fields = ["title", "description", "original_filename"]
    list_per_page = 15
    ordering = ["-created_at"]
    
    form_fields = {
        "title": CharField(max_length=255, description="照片标题", required=False),
        "description": TextField(description="照片描述", required=False),
        "album": CharField(max_length=255, description="所属相册", required=True),
        "original_url": JSONField(description="原始图片", required=True, default=[]),
        "is_active": WidgetType.Checkbox,
        "sort_order": WidgetType.InputNumber,
        "location": CharField(max_length=255, description="拍摄地点", required=False)
    }
    formfield_overrides = {
        "original_url": (WidgetType.Upload, {"required": True, "upload_action_name": "upload", "multiple": True})
    }
    
    @display
    async def album_name(self, obj) -> str:
        """获取照片所属相册名称"""
        if obj.album:
            album = await Album.get_or_none(id=obj.album_id)
            if album:
                return album.name
        return "-"

    @display
    async def thumbnail_preview(self, obj) -> str:
        """生成缩略图预览HTML"""
        if obj.thumbnail_url:
            return f'<img src="{obj.thumbnail_url}" style="max-width: 100px; max-height: 100px;" />'
        return "-"
        
    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        """保存照片模型
        
        处理照片上传和保存的逻辑，包括：
        1. 处理单张或多张图片上传
        2. 生成缩略图和预览图
        3. 保存照片元数据
        
        Args:
            id: 照片ID，新建时为None
            payload: 请求数据
            
        Returns:
            保存后的照片数据或None
        """
        try:
            if "original_url" in payload:
                files = payload["original_url"]
                if not isinstance(files, list):
                    files = [files]
                
                # 处理所有上传的图片
                processed_files = []
                for file in files:
                    if file:
                        photo_info = await PhotoUtils.process_photo_file(file)
                        if photo_info:
                            processed_files.append(photo_info)
                
                # 更新payload中的图片URL
                if processed_files:
                    payload["original_url"] = [info["original_url"] for info in processed_files]
                    payload["thumbnail_url"] = processed_files[0]["thumbnail_url"]
                    payload["preview_url"] = processed_files[0]["preview_url"]
                    
                    # 如果是多张图片，将其他图片的信息保存到formats字段
                    if len(processed_files) > 1:
                        formats = []
                        for info in processed_files[1:]:
                            format_data = {
                                "original_url": info["original_url"],
                                "thumbnail_url": info["thumbnail_url"],
                                "preview_url": info["preview_url"]
                            }
                            formats.append(format_data)
                        payload["formats"] = formats
            
            # 调用父类的save_model方法保存数据
            result = await super().save_model(id, payload)
            
            # 验证保存结果
            if result and "id" in result:
                saved_photo = await self.model.get(id=result["id"])
                if "original_url" in payload and isinstance(payload["original_url"], list):
                    saved_photo.original_url = payload["original_url"]
                    await saved_photo.save()
            
            return result
            
        except Exception as e:
            print(f"保存照片时出错: {str(e)}")
            raise e