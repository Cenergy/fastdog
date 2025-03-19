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

@register(Photo)
class PhotoModelAdmin(TortoiseModelAdmin):
    model = Photo
    icon = "camera"
    display_name = "照片管理"
    list_display = ["id", "title", "album", "is_active", "created_at"]
    list_display_links = ["id", "title"]
    list_filter = ["is_active", "created_at", "album"]
    search_fields = ["title", "description"]
    list_per_page = 15
    ordering = ["-created_at"]
    
    form_fields = {
        "title": CharField(max_length=255, description="照片标题", required=False),
        "description": TextField(description="照片描述", required=False),
        "original_url": CharField(max_length=1024, description="原始图片", required=True),
        "is_active": WidgetType.Checkbox,
        "sort_order": WidgetType.InputNumber,
        "album": WidgetType.Select
    }
    formfield_overrides = {
        "original_url": (WidgetType.Upload, {"required": True, "upload_action_name": "upload"})
    }
    
    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        try:
            if "original_url" in payload and payload["original_url"] is not None:
                file = payload["original_url"]
                if isinstance(file, UploadFile):
                    # 确保上传目录存在
                    upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos")
                    os.makedirs(upload_dir, exist_ok=True)
                    os.makedirs(os.path.join(upload_dir, "thumbnails"), exist_ok=True)
                    os.makedirs(os.path.join(upload_dir, "previews"), exist_ok=True)
                    
                    # 获取文件扩展名并转换为小写
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                        raise ValueError(f"不支持的图片格式: {file_ext}")
                    
                    # 保存原始文件名
                    payload["original_filename"] = file.filename
                    
                    # 生成唯一文件名
                    unique_filename = f"{uuid4().hex}{file_ext}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    
                    # 读取文件内容
                    content = await file.read()
                    
                    # 保存原始文件
                    with open(file_path, "wb") as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())
                    
                    # 更新原始图片URL
                    payload["original_url"] = f"/static/uploads/photos/{unique_filename}"
                    
                    # 设置文件格式
                    file_format = file_ext.lstrip(".").lower()
                    try:
                        format_enum = PhotoFormat(file_format)
                        payload["file_format"] = format_enum
                    except ValueError:
                        payload["file_format"] = PhotoFormat.OTHER
                    
                    # 获取图片信息并生成缩略图和预览图
                    try:
                        # 打开图片
                        image = Image.open(io.BytesIO(content))
                        
                        # 获取图片尺寸和大小
                        width, height = image.size
                        payload["width"] = width
                        payload["height"] = height
                        payload["file_size"] = len(content)
                        
                        # 获取EXIF数据
                        try:
                            exif = image._getexif()
                            if exif:
                                payload["exif_data"] = {str(k): str(v) for k, v in exif.items()}
                                # 提取拍摄时间
                                if 36867 in exif:  # 36867 是 DateTimeOriginal 的标签
                                    from datetime import datetime
                                    payload["taken_at"] = datetime.strptime(exif[36867], "%Y:%m:%d %H:%M:%S")
                        except Exception as e:
                            print(f"读取EXIF数据时出错: {str(e)}")
                        
                        # 生成缩略图 (200px宽)
                        thumbnail_size = (200, int(200 * height / width))
                        thumbnail = image.copy()
                        thumbnail.thumbnail(thumbnail_size, Image.LANCZOS)
                        
                        # 保存缩略图
                        thumbnail_filename = f"{unique_filename}_thumbnail.jpg"
                        thumbnail_path = os.path.join(upload_dir, "thumbnails", thumbnail_filename)
                        thumbnail.convert("RGB").save(thumbnail_path, "JPEG", quality=85)
                        payload["thumbnail_url"] = f"/static/uploads/photos/thumbnails/{thumbnail_filename}"
                        
                        # 生成预览图 (1000px宽)
                        if width > 1000:
                            preview_size = (1000, int(1000 * height / width))
                            preview = image.copy()
                            preview.thumbnail(preview_size, Image.LANCZOS)
                            
                            # 保存预览图
                            preview_filename = f"{unique_filename}_preview.jpg"
                            preview_path = os.path.join(upload_dir, "previews", preview_filename)
                            preview.convert("RGB").save(preview_path, "JPEG", quality=90)
                            payload["preview_url"] = f"/static/uploads/photos/previews/{preview_filename}"
                        else:
                            # 如果原图小于预览图尺寸，则使用原图作为预览图
                            payload["preview_url"] = payload["original_url"]
                            
                    except Exception as e:
                        print(f"处理图片时出错: {str(e)}")
                        raise e
                        
                elif isinstance(file, str) and is_valid_base64(file):
                    # 处理base64编码的图片
                    # 确保上传目录存在
                    upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos")
                    os.makedirs(upload_dir, exist_ok=True)
                    os.makedirs(os.path.join(upload_dir, "thumbnails"), exist_ok=True)
                    os.makedirs(os.path.join(upload_dir, "previews"), exist_ok=True)
                    
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
                            
                            # 更新原始图片URL
                            payload["original_url"] = f"/static/uploads/photos/{unique_filename}"
                            
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
                                
                                # 获取图片尺寸和大小
                                width, height = image.size
                                payload["width"] = width
                                payload["height"] = height
                                payload["file_size"] = len(image_data)
                                
                                # 获取EXIF数据
                                try:
                                    exif = image._getexif()
                                    if exif:
                                        payload["exif_data"] = {str(k): str(v) for k, v in exif.items()}
                                        # 提取拍摄时间
                                        if 36867 in exif:  # 36867 是 DateTimeOriginal 的标签
                                            from datetime import datetime
                                            payload["taken_at"] = datetime.strptime(exif[36867], "%Y:%m:%d %H:%M:%S")
                                except Exception as e:
                                    print(f"读取EXIF数据时出错: {str(e)}")
                                
                                # 生成缩略图 (200px宽)
                                thumbnail_size = (200, int(200 * height / width))
                                thumbnail = image.copy()
                                thumbnail.thumbnail(thumbnail_size, Image.LANCZOS)
                                
                                # 保存缩略图
                                thumbnail_filename = f"{unique_filename}_thumbnail.jpg"
                                thumbnail_path = os.path.join(upload_dir, "thumbnails", thumbnail_filename)
                                thumbnail.convert("RGB").save(thumbnail_path, "JPEG", quality=85)
                                payload["thumbnail_url"] = f"/static/uploads/photos/thumbnails/{thumbnail_filename}"
                                
                                # 生成预览图 (1000px宽)
                                if width > 1000:
                                    preview_size = (1000, int(1000 * height / width))
                                    preview = image.copy()
                                    preview.thumbnail(preview_size, Image.LANCZOS)
                                    
                                    # 保存预览图
                                    preview_filename = f"{unique_filename}_preview.jpg"
                                    preview_path = os.path.join(upload_dir, "previews", preview_filename)
                                    preview.convert("RGB").save(preview_path, "JPEG", quality=90)
                                    payload["preview_url"] = f"/static/uploads/photos/previews/{preview_filename}"
                                else:
                                    # 如果原图小于预览图尺寸，则使用原图作为预览图
                                    payload["preview_url"] = payload["original_url"]
                                    
                            except Exception as e:
                                print(f"处理base64图片时出错: {str(e)}")
                                raise e
                        except Exception as e:
                            print(f"保存base64图片时出错: {str(e)}")
                            raise ValueError("无效的base64图片数据")
                    else:
                        raise ValueError("无效的base64图片格式")
            
            # 保存照片记录
            result = await super().save_model(id, payload)
            return result
        except Exception as e:
            print(f"保存照片时出错: {str(e)}")
            raise e
    
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
                            payload["cover_image"] = f"/static/uploads/albums/{unique_filename}"
                            
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
                                thumbnail_filename = f"{unique_filename}_thumbnail.jpg"
                                thumbnail_path = os.path.join(upload_dir, thumbnail_filename)
                                thumbnail.convert("RGB").save(thumbnail_path, "JPEG", quality=85)
                                
                                # 生成预览图 (1000px宽)
                                if width > 1000:
                                    preview_size = (1000, int(1000 * height / width))
                                    preview = image.copy()
                                    preview.thumbnail(preview_size, Image.LANCZOS)
                                    
                                    # 保存预览图
                                    preview_filename = f"{unique_filename}_preview.jpg"
                                    preview_path = os.path.join(upload_dir, preview_filename)
                                    preview.convert("RGB").save(preview_path, "JPEG", quality=90)
                                    
                                else:
                                    # 如果原图小于预览图尺寸，则使用原图作为预览图
                                    preview_filename = unique_filename
                                    payload["thumbnail_url"] = f"/static/uploads/photos/thumbnails/{thumbnail_filename}"
                                    payload["preview_url"] = f"/static/uploads/photos/previews/{preview_filename}"
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
        "original_url": (WidgetType.Upload, {"required": True, "upload_action_name": "upload", "multiple": True})
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
                files = payload["original_url"]
                if not isinstance(files, list):
                    files = [files]
                
                processed_files = []
                for file in files:
                    if isinstance(file, str) and file.startswith('data:image/'):
                        # 处理base64编码的图片
                        base64_pattern = r'^data:image/([a-zA-Z]+);base64,(.+)$'
                        match = re.match(base64_pattern, file)
                        
                        if not match:
                            raise ValueError("无效的base64图片数据")
                        
                        file_type = match.group(1).lower()
                        base64_data = match.group(2)
                        
                        # 检查文件格式
                        supported_formats = ["jpg", "jpeg", "png", "gif", "webp", "heic"]
                        if file_type not in supported_formats:
                            raise ValueError(f"不支持的图片格式: {file_type}")
                        
                        # 生成唯一文件名
                        unique_id = uuid4().hex
                        file_ext = f".{file_type}"
                        unique_filename = f"{unique_id}{file_ext}"
                        
                        # 确保上传目录存在
                        upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos")
                        thumbnails_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos", "thumbnails")
                        previews_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos", "previews")
                        
                        os.makedirs(upload_dir, exist_ok=True)
                        os.makedirs(thumbnails_dir, exist_ok=True)
                        os.makedirs(previews_dir, exist_ok=True)
                        
                        # 解码并保存文件
                        try:
                            content = base64.b64decode(base64_data)
                            file_path = os.path.join(upload_dir, unique_filename)
                            
                            with open(file_path, "wb") as f:
                                f.write(content)
                                f.flush()
                                os.fsync(f.fileno())
                            
                            # 更新图片URL到payload
                            file_payload = {
                                "original_url": f"/static/uploads/photos/{unique_filename}",
                                "album": payload.get("album"),
                                "title": payload.get("title") or "未命名照片",
                                "description": payload.get("description"),
                                "is_active": payload.get("is_active", True),
                                "sort_order": payload.get("sort_order", 0)
                            }
                            
                            # 设置文件格式
                            try:
                                format_enum = PhotoFormat(file_type)
                                file_payload["file_format"] = format_enum
                            except ValueError:
                                file_payload["file_format"] = PhotoFormat.OTHER
                            
                            # 获取图片信息并生成缩略图和预览图
                            image = Image.open(io.BytesIO(content))
                            width, height = image.size
                            file_payload["width"] = width
                            file_payload["height"] = height
                            file_payload["file_size"] = len(content)
                            
                            # 生成缩略图 (200px宽)
                            thumbnail_size = (200, int(200 * height / width))
                            thumbnail = image.copy()
                            thumbnail.thumbnail(thumbnail_size, Image.LANCZOS)
                            
                            # 保存缩略图
                            thumbnail_filename = f"{unique_id}_thumbnail.jpg"
                            thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
                            thumbnail.convert("RGB").save(thumbnail_path, "JPEG", quality=85)
                            file_payload["thumbnail_url"] = f"/static/uploads/photos/thumbnails/{thumbnail_filename}"
                            
                            # 生成预览图 (1000px宽)
                            if width > 1000:
                                preview_size = (1000, int(1000 * height / width))
                                preview = image.copy()
                                preview.thumbnail(preview_size, Image.LANCZOS)
                                
                                # 保存预览图
                                preview_filename = f"{unique_id}_preview.jpg"
                                preview_path = os.path.join(previews_dir, preview_filename)
                                preview.convert("RGB").save(preview_path, "JPEG", quality=90)
                                file_payload["preview_url"] = f"/static/uploads/photos/previews/{preview_filename}"
                            else:
                                # 如果原图小于预览图尺寸，则使用原图作为预览图
                                file_payload["preview_url"] = file_payload["original_url"]
                            
                            processed_files.append(file_payload)
                            
                        except Exception as e:
                            print(f"处理base64图片时出错: {str(e)}")
                            raise e
                            
                    elif isinstance(file, UploadFile):
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
                        
                        # 保存文件
                        with open(file_path, "wb") as f:
                            f.write(content)
                            f.flush()
                            os.fsync(f.fileno())
                        
                        # 更新图片URL到payload
                        file_payload = {
                            "original_url": f"/static/uploads/photos/{unique_filename}",
                            "original_filename": original_filename,
                            "album": payload.get("album"),
                            "title": payload.get("title") or "未命名照片",
                            "description": payload.get("description"),
                            "is_active": payload.get("is_active", True),
                            "sort_order": payload.get("sort_order", 0)
                        }
                        
                        # 设置文件格式
                        try:
                            format_enum = PhotoFormat(file_ext[1:].lower())
                            file_payload["file_format"] = format_enum
                        except ValueError as e:
                            print(f"设置文件格式时出错: {str(e)}")
                            file_payload["file_format"] = PhotoFormat.OTHER
                        
                        
                        # 获取图片信息并生成缩略图和预览图
                        try:
                            # 打开图片
                            image = Image.open(io.BytesIO(content))
                            # 获取图片尺寸
                            width, height = image.size
                            file_payload["width"] = width
                            file_payload["height"] = height
                            file_payload["file_size"] = len(content)
                            
                            # 提取EXIF数据
                            try:
                                exif = image._getexif()
                                if exif:
                                    file_payload["exif_data"] = {str(k): str(v) for k, v in exif.items()}
                                    # 提取拍摄时间
                                    if 36867 in exif:  # DateTimeOriginal
                                        from datetime import datetime
                                        taken_at = datetime.strptime(exif[36867], "%Y:%m:%d %H:%M:%S")
                                        file_payload["taken_at"] = taken_at
                            except Exception as e:
                                print(f"提取EXIF数据时出错: {str(e)}")
                            
                            # 生成缩略图 (200px宽)
                            thumbnail_size = (200, int(200 * height / width))
                            thumbnail = image.copy()
                            thumbnail.thumbnail(thumbnail_size, Image.LANCZOS)
                            
                            # 保存缩略图
                            thumbnail_filename = f"{unique_id}_thumbnail.jpg"
                            thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
                            thumbnail.convert("RGB").save(thumbnail_path, "JPEG", quality=85)
                            file_payload["thumbnail_url"] = f"/static/uploads/photos/thumbnails/{thumbnail_filename}"
                            
                            # 生成预览图 (1000px宽)
                            if width > 1000:
                                preview_size = (1000, int(1000 * height / width))
                                preview = image.copy()
                                preview.thumbnail(preview_size, Image.LANCZOS)
                                
                                # 保存预览图
                                preview_filename = f"{unique_id}_preview.jpg"
                                preview_path = os.path.join(previews_dir, preview_filename)
                                preview.convert("RGB").save(preview_path, "JPEG", quality=90)
                                file_payload["preview_url"] = f"/static/uploads/photos/previews/{preview_filename}"
                            else:
                                # 如果原图小于预览图尺寸，则使用原图作为预览图
                                file_payload["preview_url"] = file_payload["original_url"]
                        except UnidentifiedImageError:
                            print(f"无法识别图片格式: {original_filename}")
                            continue
                        except Exception as e:
                            print(f"处理图片时出错: {str(e)}")
                            continue
                        
                        processed_files.append(file_payload)
                
                # 如果是多文件上传，创建多个照片记录
                if len(processed_files) > 1:
                    results = []
                    for file_payload in processed_files:
                        try:
                            # 确保必需字段存在
                            if not file_payload.get("original_url"):
                                raise ValueError("缺少必需字段：original_url")
                            if not file_payload.get("album"):
                                raise ValueError("缺少必需字段：album")
                            
                            result = await super().save_model(None, file_payload)
                            if result:
                                results.append(result)
                        except Exception as e:
                            print(f"保存照片记录时出错: {str(e)}")
                    return results[0] if results else None
                elif len(processed_files) == 1:
                    # 单文件上传，更新原始payload
                    file_payload = processed_files[0]
                    # 确保必需字段存在
                    if not file_payload.get("original_url"):
                        raise ValueError("缺少必需字段：original_url")
                    if not file_payload.get("album"):
                        raise ValueError("缺少必需字段：album")
                    
                    # 更新payload前确保original_url字段存在
                    if "original_url" not in payload:
                        payload["original_url"] = file_payload["original_url"]
                    payload.update(file_payload)
            
            # 在保存前确保original_url字段有值
            if not payload.get("original_url"):
                raise ValueError("original_url字段不能为空")
            
            # 保存照片
            result = await super().save_model(id, payload)
            return result
        except Exception as e:
            print(f"保存照片时出错: {str(e)}")
            raise e