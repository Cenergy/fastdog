from fastadmin import TortoiseModelAdmin, register, action, display, WidgetType
from tortoise.fields import CharField, TextField
from .models import Album, Photo, PhotoFormat
from fastapi import UploadFile
from uuid import UUID, uuid4
import os
import re
import base64
from PIL import Image, UnidentifiedImageError
import io
from core.config import settings
from fastadmin.api.helpers import is_valid_base64


@register(Album)
class AlbumModelAdmin(TortoiseModelAdmin):
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
    async def photo_count(self, obj):
        return await Photo.filter(album_id=obj.id).count()
    
    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        # 处理上传的封面图片
        try:
            if "cover_image" in payload and payload["cover_image"] is not None:
                file = payload["cover_image"]
                if isinstance(file, UploadFile):
                    # 确保上传目录存在
                    upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "albums")
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # 获取文件扩展名并转换为小写
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                        raise ValueError(f"不支持的图片格式: {file_ext}")
                    
                    # 生成唯一文件名
                    unique_filename = f"{uuid4().hex}{file_ext}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    
                    # 读取文件内容
                    content = await file.read()
                    
                    # 保存文件
                    with open(file_path, "wb") as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())
                    
                    # 更新封面图片URL到payload
                    payload["cover_image"] = f"/static/uploads/albums/{unique_filename}"
                elif isinstance(file, str) and is_valid_base64(file):
                    # 处理base64编码的图片
                    # 确保上传目录存在
                    upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "albums")
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # 解析base64数据和文件类型
                    base64_pattern = r'^data:image/(\w+);base64,(.+)$'
                    match = re.match(base64_pattern, file)
                    
                    if match:
                        file_type = match.group(1)
                        base64_data = match.group(2)
                        
                        # 检查文件类型
                        if file_type not in ['jpeg', 'jpg', 'png', 'gif', 'webp']:
                            raise ValueError(f"不支持的图片格式: {file_type}")
                            
                        # 生成唯一文件名
                        unique_filename = f"{uuid4().hex}.{file_type}"
                        file_path = os.path.join(upload_dir, unique_filename)
                        
                        try:
                            # 解码base64并保存文件
                            image_data = base64.b64decode(base64_data)
                            with open(file_path, "wb") as f:
                                f.write(image_data)
                                f.flush()
                                os.fsync(f.fileno())
                                
                            # 更新图片URL到payload
                            payload["original_url"] = f"/static/uploads/photos/{unique_filename}"
                            payload["original_filename"] = f"base64_image.{file_type}"
                            
                            # 设置文件格式
                            try:
                                format_enum = PhotoFormat(file_type.lower())
                                payload["file_format"] = format_enum
                            except ValueError:
                                payload["file_format"] = PhotoFormat.OTHER
                            
                            # 获取图片信息并生成缩略图和预览图
                            try:
                                # 打开图片
                                image = Image.open(io.BytesIO(image_data))
                                
                                # 获取图片尺寸
                                width, height = image.size
                                payload["width"] = width
                                payload["height"] = height
                                payload["file_size"] = len(image_data)
                                
                                # 生成缩略图 (200px宽)
                                thumbnail_size = (200, int(200 * height / width))
                                thumbnail = image.copy()
                                thumbnail.thumbnail(thumbnail_size, Image.LANCZOS)
                                
                                # 保存缩略图
                                thumbnail_filename = f"{unique_id}_thumbnail.jpg"
                                thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
                                thumbnail.convert("RGB").save(thumbnail_path, "JPEG", quality=85)
                                payload["thumbnail_url"] = f"/static/uploads/photos/thumbnails/{thumbnail_filename}"
                                
                                # 生成预览图 (1000px宽)
                                if width > 1000:
                                    preview_size = (1000, int(1000 * height / width))
                                    preview = image.copy()
                                    preview.thumbnail(preview_size, Image.LANCZOS)
                                    
                                    # 保存预览图
                                    preview_filename = f"{unique_id}_preview.jpg"
                                    preview_path = os.path.join(previews_dir, preview_filename)
                                    preview.convert("RGB").save(preview_path, "JPEG", quality=90)
                                    payload["preview_url"] = f"/static/uploads/photos/previews/{preview_filename}"
                                else:
                                    # 如果原图小于预览图尺寸，则使用原图作为预览图
                                    payload["preview_url"] = payload["original_url"]
                                    
                            except Exception as e:
                                print(f"处理base64图片时出错: {str(e)}")
                        except Exception as e:
                            print(f"解码base64图片时出错: {str(e)}")
                            raise ValueError("无效的base64图片数据")
                    else:
                        raise ValueError("无效的base64图片格式")
            
            # 保存照片
            result = await super().save_model(id, payload)
            return result
        except Exception as e:
            print(f"保存照片时出错: {str(e)}")
            raise e


@register(Photo)
class PhotoModelAdmin(TortoiseModelAdmin):
    model = Photo
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
        "album": CharField(max_length=255, description="所属相册"),
        "original_url": CharField(max_length=1024, description="原始图片"),
        "is_active": WidgetType.Checkbox,
        "sort_order": WidgetType.InputNumber,
        "location": CharField(max_length=255, description="拍摄地点", required=False)
    }
    formfield_overrides = {
        "original_url": (WidgetType.Upload, {"required": True, "upload_action_name": "upload"})
    }
    
    @display
    async def album_name(self, obj):
        if obj.album:
            album = await Album.get_or_none(id=obj.album_id)
            if album:
                return album.name
        return "-"

    @display
    async def thumbnail_preview(self, obj):
        if obj.thumbnail_url:
            return f'<img src="{obj.thumbnail_url}" height="50" />'
        elif obj.original_url:
            return f'<img src="{obj.original_url}" height="50" />'
        return "-"
    
    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        # 处理上传的图片文件
        try:
            if "original_url" in payload and payload["original_url"] is not None:
                file = payload["original_url"]
                if isinstance(file, UploadFile):
                    # 确保上传目录存在
                    upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos")
                    thumbnails_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos", "thumbnails")
                    previews_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos", "previews")
                    
                    os.makedirs(upload_dir, exist_ok=True)
                    os.makedirs(thumbnails_dir, exist_ok=True)
                    os.makedirs(previews_dir, exist_ok=True)
                    
                    # 获取文件扩展名并转换为小写
                    original_filename = file.filename
                    file_ext = os.path.splitext(original_filename)[1].lower()
                    
                    # 检查文件格式
                    supported_formats = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"]
                    if file_ext not in supported_formats:
                        raise ValueError(f"不支持的图片格式: {file_ext}")
                    
                    # 设置文件格式
                    file_format = file_ext[1:].upper()  # 去掉点号并转为大写
                    if file_format == "JPEG":
                        file_format = "JPG"
                    
                    # 生成唯一文件名
                    unique_id = uuid4().hex
                    unique_filename = f"{unique_id}{file_ext}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    
                    # 读取文件内容
                    content = await file.read()
                    
                    # 保存原始文件
                    with open(file_path, "wb") as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())
                    
                    # 更新图片URL到payload
                    payload["original_url"] = f"/static/uploads/photos/{unique_filename}"
                    payload["original_filename"] = original_filename
                    
                    # 设置文件格式
                    try:
                        format_enum = PhotoFormat(file_ext[1:].lower())
                        payload["file_format"] = format_enum
                    except ValueError:
                        payload["file_format"] = PhotoFormat.OTHER
                    
                    # 获取图片信息并生成缩略图和预览图
                    try:
                        # 打开图片
                        image = Image.open(io.BytesIO(content))
                        
                        # 获取图片尺寸
                        width, height = image.size
                        payload["width"] = width
                        payload["height"] = height
                        payload["file_size"] = len(content)
                        
                        # 生成缩略图 (200px宽)
                        thumbnail_size = (200, int(200 * height / width))
                        thumbnail = image.copy()
                        thumbnail.thumbnail(thumbnail_size, Image.LANCZOS)
                        
                        # 保存缩略图
                        thumbnail_filename = f"{unique_id}_thumbnail.jpg"
                        thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
                        thumbnail.convert("RGB").save(thumbnail_path, "JPEG", quality=85)
                        payload["thumbnail_url"] = f"/static/uploads/photos/thumbnails/{thumbnail_filename}"
                        
                        # 生成预览图 (1000px宽)
                        if width > 1000:
                            preview_size = (1000, int(1000 * height / width))
                            preview = image.copy()
                            preview.thumbnail(preview_size, Image.LANCZOS)
                            
                            # 保存预览图
                            preview_filename = f"{unique_id}_preview.jpg"
                            preview_path = os.path.join(previews_dir, preview_filename)
                            preview.convert("RGB").save(preview_path, "JPEG", quality=90)
                            payload["preview_url"] = f"/static/uploads/photos/previews/{preview_filename}"
                        else:
                            # 如果原图小于预览图尺寸，则使用原图作为预览图
                            payload["preview_url"] = payload["original_url"]
                            
                    except UnidentifiedImageError:
                        print(f"无法识别图片格式: {original_filename}")
                    except Exception as e:
                        print(f"处理图片时出错: {str(e)}")
                
                elif isinstance(file, str) and is_valid_base64(file):
                    # 处理base64编码的图片
                    # 确保上传目录存在
                    upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos")
                    thumbnails_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos", "thumbnails")
                    previews_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos", "previews")
                    
                    os.makedirs(upload_dir, exist_ok=True)
                    os.makedirs(thumbnails_dir, exist_ok=True)
                    os.makedirs(previews_dir, exist_ok=True)
                    
                    # 解析base64数据和文件类型
                    base64_pattern = r'^data:image/(\w+);base64,(.+)$'
                    match = re.match(base64_pattern, file)
                    
                    if match:
                        file_type = match.group(1)
                        base64_data = match.group(2)
                        
                        # 检查文件类型
                        if file_type not in ['jpeg', 'jpg', 'png', 'gif', 'webp']:
                            raise ValueError(f"不支持的图片格式: {file_type}")
                        
                        # 生成唯一文件名和ID
                        unique_id = uuid4().hex
                        unique_filename = f"{unique_id}.{file_type}"
                        file_path = os.path.join(upload_dir, unique_filename)
                        
                        try:
                            # 解码base64并保存文件
                            image_data = base64.b64decode(base64_data)
                            with open(file_path, "wb") as f:
                                f.write(image_data)
                                f.flush()
                                os.fsync(f.fileno())
                                
                            # 更新图片URL到payload
                            payload["original_url"] = f"/static/uploads/photos/{unique_filename}"
                            payload["original_filename"] = f"base64_image.{file_type}"
                            
                            # 设置文件格式
                            try:
                                format_enum = PhotoFormat(file_type.lower())
                                payload["file_format"] = format_enum
                            except ValueError:
                                payload["file_format"] = PhotoFormat.OTHER
                            
                            # 获取图片信息并生成缩略图和预览图
                            try:
                                # 打开图片
                                image = Image.open(io.BytesIO(image_data))
                                
                                # 获取图片尺寸
                                width, height = image.size
                                payload["width"] = width
                                payload["height"] = height
                                payload["file_size"] = len(image_data)
                                
                                # 生成缩略图 (200px宽)
                                thumbnail_size = (200, int(200 * height / width))
                                thumbnail = image.copy()
                                thumbnail.thumbnail(thumbnail_size, Image.LANCZOS)
                                
                                # 保存缩略图
                                thumbnail_filename = f"{unique_id}_thumbnail.jpg"
                                thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
                                thumbnail.convert("RGB").save(thumbnail_path, "JPEG", quality=85)
                                payload["thumbnail_url"] = f"/static/uploads/photos/thumbnails/{thumbnail_filename}"
                                
                                # 生成预览图 (1000px宽)
                                if width > 1000:
                                    preview_size = (1000, int(1000 * height / width))
                                    preview = image.copy()
                                    preview.thumbnail(preview_size, Image.LANCZOS)
                                    
                                    # 保存预览图
                                    preview_filename = f"{unique_id}_preview.jpg"
                                    preview_path = os.path.join(previews_dir, preview_filename)
                                    preview.convert("RGB").save(preview_path, "JPEG", quality=90)
                                    payload["preview_url"] = f"/static/uploads/photos/previews/{preview_filename}"
                                else:
                                    # 如果原图小于预览图尺寸，则使用原图作为预览图
                                    payload["preview_url"] = payload["original_url"]
                                    
                            except Exception as e:
                                print(f"处理base64图片时出错: {str(e)}")
                        except Exception as e:
                            print(f"解码base64图片时出错: {str(e)}")
                            raise ValueError("无效的base64图片数据")
                    else:
                        raise ValueError("无效的base64图片格式")
            
            # 保存照片
            result = await super().save_model(id, payload)
            return result
        except Exception as e:
            print(f"保存照片时出错: {str(e)}")
            raise e