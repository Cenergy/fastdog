from fastadmin import TortoiseModelAdmin, register, action, display, WidgetType
from tortoise.fields import CharField, TextField, JSONField
from .models import FileManager, FileCategory, FileFormat
from fastapi import UploadFile
from uuid import UUID, uuid4
import os
import re
import base64
from PIL import Image, ImageOps, UnidentifiedImageError
import io
from core.settings import settings
from fastadmin.api.helpers import is_valid_base64
from typing import Optional, Dict, Any, List, Tuple
import mimetypes
import magic



@register(FileCategory)
class FileCategoryModelAdmin(TortoiseModelAdmin):
    """文件分类管理"""
    model = FileCategory
    icon = "folder"
    verbose_name = "文件分类"
    verbose_name_plural = "文件分类管理"
    list_display = ["id", "name", "description", "is_active", "sort_order", "created_at"]
    list_display_links = ["id", "name"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    list_per_page = 15
    ordering = ["sort_order", "-created_at"]
    
    form_fields = {
        "name": CharField(max_length=255, description="分类名称"),
        "description": TextField(description="分类描述", required=False),
        "sort_order": WidgetType.InputNumber,
        "is_active": WidgetType.Checkbox,
    }


@register(FileManager)
class FileModelAdmin(TortoiseModelAdmin):
    """文件管理类"""
    model = FileManager
    icon = "file"
    verbose_name = "文件"
    verbose_name_plural = "文件管理"
    list_display = ["id", "title", "original_url", "category", "is_public", "is_active", "created_at"]
    list_display_links = ["id", "title"]
    list_filter = ["is_public", "is_active", "category", "created_at"]
    search_fields = ["title", "description"]
    list_per_page = 15
    ordering = ["-created_at"]
    
    form_fields = {
        "title": CharField(max_length=255, description="文件标题", required=False),
        "description": TextField(description="文件描述", required=False),
        "original_url": WidgetType.Upload,
        "category": WidgetType.Select,
        "is_public": WidgetType.Checkbox,
        "is_active": WidgetType.Checkbox,
    }
    
    @property
    def formfield_overrides(self):
        """文件上传字段配置"""
        return {
            "original_url": (WidgetType.Upload, {
                "required": False,
                "upload_action_name": "upload",
                "accept": "*/*",  # 接受所有文件类型
                "multiple": False,
                "showUploadList": True,
                "maxCount": 1,
                "maxFileSize": 100 * 1024 * 1024,  # 100MB
                "listType": "text"
            })
        }
    
    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        """处理文件上传和保存"""
        try:
            # 处理文件上传
            if "original_url" in payload and payload["original_url"] is not None:
                file = payload["original_url"]
                if isinstance(file, UploadFile):
                    try:
                        # 确保上传目录存在 - 修改为files目录以匹配用户要求的格式
                        upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "files")
                        os.makedirs(upload_dir, exist_ok=True)
                        
                        # 获取文件扩展名并保留原始扩展名
                        file_ext = os.path.splitext(file.filename)[1].lower()
                        
                        # 如果没有扩展名或扩展名不明确，尝试通过文件内容检测
                        if not file_ext or file_ext == ".bin":
                            # 读取文件内容进行检测
                            content = await file.read()
                            
                            # 检测GLB文件（以"glTF"开头的二进制文件）
                            if content.startswith(b'glTF'):
                                file_ext = ".glb"
                            # 检测GLTF文件（JSON格式）
                            elif content.startswith(b'{') and b'"asset"' in content[:1000]:
                                file_ext = ".gltf"
                            # 其他文件类型检测可以在这里添加
                            else:
                                # 如果仍然无法确定，保持原扩展名或使用.bin
                                file_ext = file_ext or ".bin"
                        else:
                            # 读取文件内容
                            content = await file.read()
                        
                        # 生成唯一文件名，保留原始扩展名
                        unique_filename = f"{uuid4().hex}{file_ext}"
                        file_path = os.path.join(upload_dir, unique_filename)
                        
                        # 保存文件
                        with open(file_path, "wb") as f:
                            f.write(content)
                            f.flush()
                            os.fsync(f.fileno())
                        
                        # 更新文件URL - 修改为files路径
                        payload["original_url"] = f"/static/uploads/files/{unique_filename}"
                        
                        # 如果没有提供title，使用原始文件名
                        if not payload.get("title"):
                            payload["title"] = os.path.splitext(file.filename)[0]
                            
                    except Exception as e:
                        raise ValueError(f"文件上传失败: {str(e)}")
                        
                elif isinstance(file, str) and file.startswith("data:"):
                    # 处理base64编码的文件
                    try:
                        # 解析base64数据
                        header, base64_data = file.split(",", 1)
                        
                        # 从header中提取文件类型
                        mime_type = header.split(";")[0].split(":")[1]
                        
                        # 根据MIME类型确定文件扩展名
                        mime_to_ext = {
                            "image/jpeg": ".jpeg",
                            "image/jpg": ".jpeg", 
                            "image/png": ".png",
                            "image/gif": ".gif",
                            "image/webp": ".webp",
                            "application/pdf": ".pdf",
                            "text/plain": ".txt",
                            "application/msword": ".doc",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
                            # 3D模型文件
                            "model/gltf-binary": ".glb",
                            "model/gltf+json": ".gltf",
                            "application/octet-stream": ".glb",  # GLB文件有时会被识别为这个MIME类型
                            # 音频文件
                            "audio/mpeg": ".mp3",
                            "audio/wav": ".wav",
                            "audio/ogg": ".ogg",
                            # 视频文件
                            "video/mp4": ".mp4",
                            "video/avi": ".avi",
                            "video/mov": ".mov",
                            # 压缩文件
                            "application/zip": ".zip",
                            "application/x-rar-compressed": ".rar",
                            "application/x-7z-compressed": ".7z",
                        }
                        file_ext = mime_to_ext.get(mime_type, ".bin")
                        
                        # 确保上传目录存在 - 修改为files目录
                        upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "files")
                        os.makedirs(upload_dir, exist_ok=True)
                        
                        # 生成唯一文件名，保留扩展名
                        unique_filename = f"{uuid4().hex}{file_ext}"
                        file_path = os.path.join(upload_dir, unique_filename)
                        
                        # 解码并保存文件
                        file_data = base64.b64decode(base64_data)
                        with open(file_path, "wb") as f:
                            f.write(file_data)
                            f.flush()
                            os.fsync(f.fileno())
                        
                        # 更新文件URL - 修改为files路径
                        payload["original_url"] = f"/static/uploads/files/{unique_filename}"
                    except Exception as e:
                        raise ValueError(f"无效的base64文件数据: {str(e)}")
                else:
                    raise ValueError("无效的base64文件格式")
            
            # 调用父类的save_model方法保存到数据库
            result = await super().save_model(id, payload)
            
            # 验证保存结果，确保original_url正确保存
            if result and "original_url" in payload and payload["original_url"]:
                saved_file = await self.model.get(id=result["id"])
                
                # 如果original_url没有正确保存，尝试直接更新
                if saved_file.original_url != payload["original_url"]:
                    saved_file.original_url = payload["original_url"]
                    await saved_file.save()
            
            return result
            
        except Exception as e:
            raise e
    
    async def delete_model(self, id: UUID | int) -> bool:
        """删除文件记录时同时删除物理文件"""
        try:
            # 先获取文件记录
            file_record = await self.model.get(id=id)
            
            # 如果有文件URL，删除物理文件
            if file_record.original_url:
                # 构建完整的文件路径
                # original_url格式: "/static/uploads/files/filename.ext"
                file_path = os.path.join(settings.STATIC_DIR, file_record.original_url.lstrip("/static/"))
                
                # 检查文件是否存在并删除
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"已删除物理文件: {file_path}")
                    except OSError as e:
                        print(f"删除物理文件失败: {file_path}, 错误: {str(e)}")
                        # 即使物理文件删除失败，也继续删除数据库记录
                else:
                    print(f"物理文件不存在: {file_path}")
            
            # 调用父类方法删除数据库记录
            result = await super().delete_model(id)
            return result
            
        except Exception as e:
            print(f"删除文件记录失败: {str(e)}")
            raise e
    