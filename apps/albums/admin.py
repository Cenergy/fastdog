from fastadmin import TortoiseModelAdmin, register, action, display, WidgetType
from tortoise.fields import CharField, TextField, JSONField
from .models import Album, Photo, PhotoFormat
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
                # 处理可能是列表的情况
                field_value = payload[upload_field.name]
                if isinstance(field_value, list):
                    # 如果是列表，跳过base64验证，由具体的ModelAdmin处理
                    continue
                elif isinstance(field_value, str) and is_valid_base64(field_value):
                    await self.orm_save_upload_field(obj, upload_field.column_name, payload[upload_field.name])

        for m2m_field in m2m_fields:
            if m2m_field.name in payload:
                await self.orm_save_m2m_ids(obj, m2m_field.column_name, payload[m2m_field.name])

        return await self.serialize_obj(obj)


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

@register(Photo)
class PhotoModelAdmin(CustomModelAdmin):
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
            return f'<img src="{obj.thumbnail_url}" height="50" />'
        elif obj.original_url:
            return f'<img src="{obj.original_url}" height="50" />'
        return "-"
    
    def process_photo_image(self, image: Image.Image, unique_id: str, upload_dir: str, thumbnails_dir: str, previews_dir: str, width: int, height: int, file_ext: str = '.jpg') -> dict:
        """处理图片，生成缩略图和预览图
        
        Args:
            image: PIL Image对象
            unique_id: 唯一标识符
            upload_dir: 上传目录路径
            thumbnails_dir: 缩略图目录路径
            previews_dir: 预览图目录路径
            width: 图片宽度
            height: 图片高度
            file_ext: 文件扩展名，默认为.jpg
            
        Returns:
            包含图片处理结果的字典，包括缩略图和预览图URL
        """
        result = {}
        
        # 生成缩略图 (200px宽)
        thumbnail_size = (200, int(200 * height / width))
        thumbnail = image.copy()
        thumbnail.thumbnail(thumbnail_size, Image.LANCZOS)
        
        # 保存缩略图
        thumbnail_filename = f"{unique_id}_thumbnail.jpg"
        thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
        thumbnail.convert("RGB").save(thumbnail_path, "JPEG", quality=85)
        result["thumbnail_url"] = f"/static/uploads/photos/thumbnails/{thumbnail_filename}"
        
        # 生成预览图 (1000px宽)
        if width > 1000:
            preview_size = (1000, int(1000 * height / width))
            preview = image.copy()
            preview.thumbnail(preview_size, Image.LANCZOS)
            
            # 保存预览图
            preview_filename = f"{unique_id}_preview.jpg"
            preview_path = os.path.join(previews_dir, preview_filename)
            preview.convert("RGB").save(preview_path, "JPEG", quality=90)
            result["preview_url"] = f"/static/uploads/photos/previews/{preview_filename}"
        else:
            # 如果原图小于预览图尺寸，则使用原图作为预览图
            # 使用与原始文件相同的扩展名
            result["preview_url"] = f"/static/uploads/photos/{unique_id}{file_ext}"
        
        return result

    def update_photo_metadata(self, payload: dict, file_type: str, content: bytes, unique_id: str) -> dict:
        """更新照片元数据
        
        Args:
            payload: 原始payload数据
            file_type: 文件类型
            content: 文件内容
            unique_id: 唯一标识符
            
        Returns:
            更新后的payload字典
        """
        file_payload = {
            "original_url": [f"/static/uploads/photos/{unique_id}.{file_type}"],
            "album": payload.get("album"),
            "title": payload.get("title") or "未命名照片",
            "description": payload.get("description"),
            "is_active": payload.get("is_active", True),
            "sort_order": payload.get("sort_order", 0),
            "exif_data": {},
            "file_size": len(content)
        }
        
        # 设置文件格式
        try:
            format_enum = PhotoFormat(file_type)
            file_payload["file_format"] = format_enum
        except ValueError:
            file_payload["file_format"] = PhotoFormat.OTHER
            
        return file_payload

    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        """保存照片模型
        
        这个方法处理照片的保存操作，包括两种情况：
        1. 首次保存（id为None）：创建新的照片记录
        2. 修改保存（id存在）：更新现有照片记录
        
        Args:
            id: 照片ID，首次保存时为None
            payload: 包含照片数据的字典
            
        Returns:
            保存后的照片数据字典
        """
        try:
            # 先验证album字段
            if not payload.get("album"):
                raise ValueError("所属相册不能为空")

            # 处理现有记录的修改（id存在）
            if id:
                existing = await Photo.get_or_none(id=id)
                if existing and existing.thumbnail_url:
                    # 如果原图URL为空或是默认值，使用现有的缩略图URL
                    if not payload.get("original_url") or payload.get("original_url") == [] or payload.get("original_url") == ["/static/default.png"]:
                        payload["original_url"] = [existing.thumbnail_url]
                        print(f"修改保存：使用现有缩略图作为原图URL: {existing.thumbnail_url}")

            # 首次保存时的默认值处理
            if "original_url" not in payload or payload["original_url"] is None:
                payload["original_url"] = ["/static/default.png"]
                print("首次保存：设置默认原图URL")
            
            # 初始化默认值
            if "exif_data" not in payload or payload["exif_data"] is None:
                payload["exif_data"] = {}
                print("初始化：设置默认EXIF数据")
            
            # 处理缩略图和原图URL的关系
            if "thumbnail_url" in payload and payload["thumbnail_url"] and (
                not payload["original_url"] or 
                payload["original_url"] == ["/static/default.png"] or 
                payload["original_url"] == "/static/default.png"):
                # 如果有缩略图但原图为空或默认值，使用缩略图作为原图
                payload["original_url"] = [payload["thumbnail_url"]]
                print("图片处理：使用缩略图作为原图URL")
            
            # 标准化original_url格式
            if isinstance(payload["original_url"], str):
                payload["original_url"] = [payload["original_url"]]
                print("格式化：将原图URL转换为列表格式")
                
            # 处理图片文件
            if "original_url" in payload and payload["original_url"] is not None:
                # 标准化文件列表
                files = payload["original_url"]
                if not isinstance(files, list):
                    files = [files]
                    print("格式化：将文件转换为列表格式")
                
                # 如果是多张图片上传，每张图片创建一个新的记录
                if len(files) > 1 and not id:
                    results = []
                    for file in files:
                        # 为每张图片创建新的payload
                        single_payload = payload.copy()
                        single_payload["original_url"] = file
                        # 递归调用save_model处理单张图片
                        result = await self.save_model(None, single_payload)
                        if result:
                            results.append(result)
                    return results[0] if results else None
                
                processed_files = []
                for file in files:
                    # 处理base64编码的图片
                    if isinstance(file, str) and file.startswith('data:image/'):
                        # 处理base64编码的图片
                        print("开始处理base64编码的图片")
                        base64_pattern = r'^data:image/(\w+);base64,(.+)$'
                        match = re.match(base64_pattern, file)
                        
                        if not match:
                            raise ValueError("无效的base64图片数据：数据格式不正确")
                        
                        # 提取并验证图片格式
                        file_type = match.group(1).lower()
                        base64_data = match.group(2)
                        
                        # 检查文件格式是否支持
                        supported_formats = ["jpg", "jpeg", "png", "gif", "webp", "heic"]
                        if file_type not in supported_formats:
                            raise ValueError(f"不支持的图片格式 {file_type}，仅支持：{', '.join(supported_formats)}")
                        
                        # 生成唯一标识符和文件名
                        unique_id = uuid4().hex
                        file_ext = f".{file_type}"
                        unique_filename = f"{unique_id}{file_ext}"
                        print(f"生成唯一文件名：{unique_filename}")
                        
                        # 确保上传目录存在
                        upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos")
                        thumbnails_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos", "thumbnails")
                        previews_dir = os.path.join(settings.STATIC_DIR, "uploads", "photos", "previews")
                        
                        os.makedirs(upload_dir, exist_ok=True)
                        os.makedirs(thumbnails_dir, exist_ok=True)
                        os.makedirs(previews_dir, exist_ok=True)
                        
                        # 解码并保存base64图片
                        try:
                            print("开始解码和保存base64图片")
                            content = base64.b64decode(base64_data)
                            file_path = os.path.join(upload_dir, unique_filename)
                            
                            # 保存原始图片文件
                            save_image_file(file_path, content)
                            print(f"原始图片已保存到：{file_path}")
                            
                            # 创建并更新图片元数据
                            file_payload = self.update_photo_metadata(payload, file_type, content, unique_id)
                            print("已更新图片元数据")
                            
                            # 获取图片信息
                            print("开始处理图片信息")
                            image = Image.open(io.BytesIO(content))
                            width, height = image.size
                            
                            # 处理图片格式
                            try:
                                format_enum = PhotoFormat(file_type)
                                file_payload["file_format"] = format_enum
                                print(f"设置图片格式：{format_enum}")
                            except ValueError:
                                file_payload["file_format"] = PhotoFormat.OTHER
                                print("使用默认图片格式：OTHER")
                            
                            # 更新图片尺寸信息
                            file_payload["width"] = width
                            file_payload["height"] = height
                            file_payload["file_size"] = len(content)
                            print(f"图片尺寸：{width}x{height}, 文件大小：{len(content)}字节")
                            
                            # 处理图片并生成缩略图和预览图
                            # 传递文件扩展名参数，确保预览图URL使用正确的扩展名
                            result = self.process_photo_image(image, unique_id, upload_dir, thumbnails_dir, previews_dir, width, height, f".{file_type}")
                            file_payload.update(result)
                            print("已生成缩略图和预览图")
                            
                            # 确保所有必需的URL都已设置
                            if not file_payload.get("preview_url"):
                                file_payload["preview_url"] = file_payload["original_url"][0]
                                print("使用原图作为预览图")
                            
                            # 更新关联的payload
                            # 如果原图是默认地址或不存在，但有缩略图，使用缩略图作为原图
                            if ("original_url" not in file_payload or 
                                not file_payload["original_url"] or
                                (isinstance(file_payload["original_url"], list) and (not file_payload["original_url"] or file_payload["original_url"] == ["/static/default.png"])) or
                                file_payload["original_url"] == "/static/default.png") and "thumbnail_url" in file_payload and file_payload["thumbnail_url"]:
                                file_payload["original_url"] = [file_payload["thumbnail_url"]]
                            
                            if not file_payload.get("album"):
                                raise ValueError("缺少必需字段：album")
                            
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
                            "original_url": [f"/static/uploads/photos/{unique_filename}"],
                            "original_filename": original_filename,
                            "album": payload.get("album"),
                            "title": payload.get("title") or "未命名照片",
                            "description": payload.get("description"),
                            "is_active": payload.get("is_active", True),
                            "sort_order": payload.get("sort_order", 0),
                            "exif_data": {}  # 添加一个默认空字典
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
                                # 确保exif_data至少是空JSON
                                file_payload["exif_data"] = {}
                            
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
                                if isinstance(file_payload["original_url"], list) and file_payload["original_url"]:
                                    file_payload["preview_url"] = file_payload["original_url"][0]
                                else:
                                    file_payload["preview_url"] = f"/static/uploads/photos/{unique_filename}"
                            
                            # 更新关联的payload
                            # 如果原图是默认地址或不存在，但有缩略图，使用缩略图作为原图
                            if ("original_url" not in file_payload or 
                                not file_payload["original_url"] or
                                (isinstance(file_payload["original_url"], list) and (not file_payload["original_url"] or file_payload["original_url"] == ["/static/default.png"])) or
                                file_payload["original_url"] == "/static/default.png") and "thumbnail_url" in file_payload and file_payload["thumbnail_url"]:
                                file_payload["original_url"] = [file_payload["thumbnail_url"]]
                            
                            if not file_payload.get("album"):
                                raise ValueError("缺少必需字段：album")
                            
                            processed_files.append(file_payload)
                        except UnidentifiedImageError:
                            print(f"无法识别图片格式: {original_filename}")
                            raise ValueError(f"无法识别图片格式: {original_filename}")
                        except Exception as e:
                            print(f"处理图片时出错: {str(e)}")
                            raise ValueError(f"处理图片时出错: {str(e)}")
                    elif isinstance(file, str) and (file.startswith('/static/uploads/') or file == '/static/default.png'):
                        # 如果是已有图片的URL或默认图片，确保保留并验证它
                        file_payload = {
                            "original_url": [file],
                            "album": payload.get("album"),
                            "title": payload.get("title") or "未命名照片",
                            "description": payload.get("description"),
                            "is_active": payload.get("is_active", True),
                            "sort_order": payload.get("sort_order", 0),
                            "exif_data": {}  # 添加一个默认空字典
                        }
                        processed_files.append(file_payload)
                    else:
                        raise ValueError(f"不支持的文件格式或无效文件: {file}")
                
                # 如果是多文件上传，创建多个照片记录
                if len(processed_files) > 1:
                    results = []
                    for file_payload in processed_files:
                        try:
                            # 确保必需字段存在
                            if not file_payload.get("original_url"):
                                if "thumbnail_url" in file_payload and file_payload["thumbnail_url"]:
                                    file_payload["original_url"] = [file_payload["thumbnail_url"]]
                                else:
                                    file_payload["original_url"] = ["/static/default.png"]  # 使用默认值
                            elif (isinstance(file_payload["original_url"], str) and file_payload["original_url"] == "/static/default.png") or \
                                 (isinstance(file_payload["original_url"], list) and (not file_payload["original_url"] or file_payload["original_url"] == ["/static/default.png"])):
                                if "thumbnail_url" in file_payload and file_payload["thumbnail_url"]:
                                    file_payload["original_url"] = [file_payload["thumbnail_url"]]
                            
                            if not file_payload.get("album"):
                                raise ValueError("缺少必需字段：album")
                            
                            # 确保exif_data是一个字典，而不是None
                            if "exif_data" not in file_payload or file_payload["exif_data"] is None:
                                file_payload["exif_data"] = {}
                            
                            print(f"保存照片: {file_payload}")
                            result = await super().save_model(None, file_payload)
                            if result:
                                results.append(result)
                        except Exception as e:
                            print(f"保存照片记录时出错: {str(e)}")
                            raise e
                    return results[0] if results else None
                elif len(processed_files) == 1:
                    # 单文件上传，更新原始payload
                    file_payload = processed_files[0]
                    # 确保必需字段存在
                    if not file_payload.get("original_url"):
                        if "thumbnail_url" in file_payload and file_payload["thumbnail_url"]:
                            file_payload["original_url"] = [file_payload["thumbnail_url"]]
                        else:
                            file_payload["original_url"] = ["/static/default.png"]  # 使用默认值
                    elif (isinstance(file_payload["original_url"], str) and file_payload["original_url"] == "/static/default.png") or \
                         (isinstance(file_payload["original_url"], list) and (not file_payload["original_url"] or file_payload["original_url"] == ["/static/default.png"])):
                        if "thumbnail_url" in file_payload and file_payload["thumbnail_url"]:
                            file_payload["original_url"] = [file_payload["thumbnail_url"]]
                    
                    if not file_payload.get("album"):
                        raise ValueError("缺少必需字段：album")
                    
                    # 确保exif_data是一个字典，而不是None
                    if "exif_data" not in file_payload or file_payload["exif_data"] is None:
                        file_payload["exif_data"] = {}
                    
                    # 更新payload前确保original_url字段存在
                    # 确保original_url是列表类型，因为模型中定义为JSONField
                    if "original_url" in file_payload and isinstance(file_payload["original_url"], str):
                        file_payload["original_url"] = [file_payload["original_url"]]
                    payload.update(file_payload)
            elif isinstance(payload.get("original_url"), str) and payload["original_url"].startswith('/static/uploads/'):
                # 如果是已有图片的URL，确保不为空
                pass
            else:
                # 使用默认值
                payload["original_url"] = ["/static/default.png"]
            
            # 保存前再次确保important字段有值
            if not payload.get("original_url"):
                # 如果有缩略图但没有原图，使用缩略图作为原图
                if "thumbnail_url" in payload and payload["thumbnail_url"]:
                    payload["original_url"] = [payload["thumbnail_url"]]
                else:
                    payload["original_url"] = ["/static/default.png"]  # 使用默认值
            elif payload.get("original_url") == "/static/default.png" and "thumbnail_url" in payload and payload["thumbnail_url"]:
                # 如果原图是默认地址但有缩略图，使用缩略图作为原图
                payload["original_url"] = [payload["thumbnail_url"]]
            
            if not payload.get("album"):
                raise ValueError("所属相册不能为空")
                
            # 确保exif_data是一个字典，而不是None
            if "exif_data" not in payload or payload["exif_data"] is None:
                payload["exif_data"] = {}
            
            # 确保键值对完整合法
            for key, value in list(payload.items()):
                if value is None and key != 'description' and key != 'title' and key != 'location' and key != 'taken_at':
                    if key == 'original_url':
                        payload[key] = ["/static/default.png"]
                    elif key == 'exif_data':
                        payload[key] = {}
            
            print(f"即将保存数据: {payload}")
            
            # 保存照片
            try:
                result = await super().save_model(id, payload)
                
                # 保存后验证并修复 - 确保 original_url 真的被保存到数据库
                if result and "id" in result:
                    saved_photo = await self.model.get(id=result["id"])
                    print(f"保存后的photo.original_url: {saved_photo.original_url}, photo.thumbnail_url: {saved_photo.thumbnail_url}")
                    
                    # 如果保存后 original_url 为空或默认值，但有 thumbnail_url，直接更新数据库
                    if saved_photo.thumbnail_url and (
                        not saved_photo.original_url or
                        saved_photo.original_url == [] or
                        saved_photo.original_url == ["/static/default.png"] or
                        saved_photo.original_url == "/static/default.png"
                    ):
                        saved_photo.original_url = [saved_photo.thumbnail_url]
                        await saved_photo.save()
                        print(f"保存后修复: 更新了 photo.original_url 为 {saved_photo.original_url}")
                        
                        # 再次检查更新是否成功
                        check_photo = await self.model.get(id=result["id"])
                        print(f"再次检查: photo.original_url = {check_photo.original_url}")
                        
                        # 如果数据库更新失败，尝试强制更新
                        if not check_photo.original_url or check_photo.original_url == []:
                            # 使用原始SQL尝试更新
                            from tortoise.expressions import RawSQL
                            await self.model.filter(id=result["id"]).update(original_url=RawSQL(f"'[\"{saved_photo.thumbnail_url}\"]'"))
                            print(f"使用RawSQL更新original_url: {saved_photo.thumbnail_url}")
                            
                            # 最后检查
                            final_check = await self.model.get(id=result["id"])
                            print(f"最终检查: photo.original_url = {final_check.original_url}")
                
                return result
            except Exception as e:
                print(f"保存照片记录时出错: {str(e)}")
                raise e
        except Exception as e:
            print(f"保存照片时出错: {str(e)}")
            raise e