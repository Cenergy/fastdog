from fastadmin import TortoiseModelAdmin, register, action, display, WidgetType
from tortoise.fields import CharField, TextField, JSONField
from ..models import Photo, PhotoFormat, Album
from fastapi import UploadFile
from uuid import UUID
from PIL import Image
import io
from core.config import settings
from .utils import process_image, save_image_file, process_base64_image, process_upload_file, get_image_dimensions, extract_exif_data, create_file_payload
from typing import Dict, Any
import os

@register(Photo)
class PhotoModelAdmin(TortoiseModelAdmin):
    """照片管理类
    
    处理照片的创建、编辑、删除等管理操作
    支持单张和多张照片的上传和处理
    包含缩略图和预览图的自动生成
    """
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
        """获取照片所属相册名称
        
        Args:
            obj: 照片对象
            
        Returns:
            相册名称，如果相册不存在则返回None
        """
        if obj.album:
            album = await Album.get_or_none(id=obj.album_id)
            if album:
                return album.name
        return "-"

    @display
    async def thumbnail_preview(self, obj) -> str:
        """生成缩略图预览HTML
        
        Args:
            obj: 照片对象
            
        Returns:
            缩略图HTML代码，如果没有图片则返回"-"
        """
        if obj.thumbnail_url:
            return f'<a href="{obj.preview_url or obj.original_url}" target="_blank"><img src="{obj.thumbnail_url}" height="50" /></a>'
        return "-"

    async def process_photo(self, file: UploadFile | str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理照片文件
        
        Args:
            file: 上传的文件对象或base64字符串
            payload: 请求的payload数据
            
        Returns:
            处理后的照片数据
            
        Raises:
            ValueError: 当文件格式不支持或处理失败时
        """
        upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos")
        os.makedirs(upload_dir, exist_ok=True)
        
        try:
            if isinstance(file, UploadFile):
                # 处理上传的文件
                file_ext, unique_filename = process_upload_file(file)
                file_path = os.path.join(upload_dir, unique_filename)
                content = await file.read()
                save_image_file(file_path, content)
                
                # 处理图片信息
                image = Image.open(io.BytesIO(content))
                dimensions = get_image_dimensions(image)
                exif_data = extract_exif_data(image)
                
                # 创建文件处理的payload
                result = create_file_payload(unique_filename, payload)
                
                # 生成缩略图和预览图
                image_result = process_image(image, unique_filename.split('.')[0], upload_dir, dimensions["width"], dimensions["height"], file_ext)
                result.update(image_result)
                
                # 添加EXIF数据
                result["exif_data"] = exif_data
                
                return result
                
            elif isinstance(file, str):
                # 处理base64编码的图片
                unique_filename, image_data, file_type = process_base64_image(file, upload_dir)
                file_path = os.path.join(upload_dir, f"{unique_filename}.{file_type}")
                save_image_file(file_path, image_data)
                
                # 处理图片信息
                image = Image.open(io.BytesIO(image_data))
                dimensions = get_image_dimensions(image)
                exif_data = extract_exif_data(image)
                
                # 创建文件处理的payload
                result = create_file_payload(f"{unique_filename}.{file_type}", payload)
                
                # 生成缩略图和预览图
                image_result = process_image(image, unique_filename, upload_dir, dimensions["width"], dimensions["height"], f".{file_type}")
                result.update(image_result)
                
                # 添加EXIF数据
                result["exif_data"] = exif_data
                
                return result
            else:
                raise ValueError("不支持的文件格式，仅支持文件上传或base64图片")
                
        except Exception as e:
            print(f"处理照片时出错: {str(e)}")
            if isinstance(e, ValueError):
                raise e
            raise ValueError(f"处理照片失败: {str(e)}")

    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        """保存照片模型
        
        Args:
            id: 照片ID
            payload: 请求的payload数据
            
        Returns:
            保存后的照片数据
        """
        try:
            if "original_url" in payload and payload["original_url"] is not None:
                files = payload["original_url"]
                if not isinstance(files, list):
                    files = [files]
                
                processed_files = []
                for file in files:
                    if file:
                        result = await self.process_photo(file, payload)
                        processed_files.append(result)
                
                if processed_files:
                    # 更新payload中的字段
                    first_file = processed_files[0]
                    payload.update({
                        "original_url": first_file["original_url"],
                        "thumbnail_url": first_file.get("thumbnail_url"),
                        "preview_url": first_file.get("preview_url"),
                        "exif_data": first_file.get("exif_data", {})
                    })
                    
                    # 如果有多个文件，创建额外的照片记录
                    if len(processed_files) > 1:
                        for file_data in processed_files[1:]:
                            new_payload = payload.copy()
                            new_payload.update({
                                "original_url": file_data["original_url"],
                                "thumbnail_url": file_data.get("thumbnail_url"),
                                "preview_url": file_data.get("preview_url"),
                                "exif_data": file_data.get("exif_data", {})
                            })
                            await super().save_model(None, new_payload)
            
            return await super().save_model(id, payload)
            
        except Exception as e:
            print(f"保存照片时出错: {str(e)}")
            raise e

    async def delete_model(self, id: str) -> bool:
        """删除照片及其关联的文件
        
        Args:
            id: 照片ID
            
        Returns:
            删除是否成功
        """
        try:
            # 获取照片对象
            photo = await self.model.get(id=id)
            
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
            
            # 删除照片记录
            return await super().delete_model(id)
            
        except Exception as e:
            print(f"删除照片及其文件时出错: {str(e)}")
            raise e