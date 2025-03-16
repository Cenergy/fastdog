from fastadmin import TortoiseModelAdmin, register
from uuid import UUID
from tortoise.fields import CharField
from .models import Resource
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from core.config import settings
from fastadmin.api.helpers import is_valid_base64
from fastadmin import TortoiseInlineModelAdmin, TortoiseModelAdmin, WidgetType, action, display


@register(Resource)
class ResourceModelAdmin(TortoiseModelAdmin):
    model = Resource
    icon = "file"
    display_name = "资源管理"
    list_display = ["id", "name", "type", "url", "image_url", "is_active", "created_at"]
    list_display_links = ["id", "name"]
    list_filter = ["type", "is_active", "created_at"]
    search_fields = ["name", "description"]
    list_per_page = 15
    ordering = ["-created_at"]
    
    form_fields = {
        "name": CharField(max_length=255, description="资源名称"),
        "description": CharField(max_length=1024, description="资源描述", required=False),
        "type": CharField(max_length=50, description="资源类型"),
        "url": CharField(max_length=1024, description="资源链接", required=False),
        "image_url": CharField(max_length=1024, description="资源图片链接", required=False)
    }
    formfield_overrides = {  # noqa: RUF012
        "image_url": (WidgetType.Upload, {"required": True, "upload_action_name": "upload"})  
    }
    
    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        # 处理上传的图片文件
        try:
            if "image_url" in payload and payload["image_url"] is not None:
                file = payload["image_url"]
                if isinstance(file, UploadFile):
                    # 确保上传目录存在
                    upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "resources")
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # 生成唯一文件名
                    file_ext = os.path.splitext(file.filename)[1]
                    unique_filename = f"{UUID(str(id)).hex if id else UUID(str(payload.get('id'))).hex}{file_ext}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    
                    # 读取文件内容
                    content = await file.read()
                    
                    # 保存文件
                    with open(file_path, "wb") as f:
                        f.write(content)
                    
                    # 更新图片URL到payload
                    payload["image_url"] = f"/static/uploads/resources/{unique_filename}"
                elif isinstance(file, str) and is_valid_base64(file):
                    # 处理base64编码的图片
                    import base64
                    from uuid import uuid4
                    
                    # 确保上传目录存在
                    upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "resources")
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # 生成唯一文件名
                    unique_filename = f"{uuid4().hex}.png"
                    file_path = os.path.join(upload_dir, unique_filename)
                    
                    # 解码base64并保存文件
                    # 移除data:image/png;base64前缀
                    if ';base64,' in file:
                        file = file.split(';base64,')[1]
                    image_data = base64.b64decode(file)
                    with open(file_path, "wb") as f:
                        f.write(image_data)
                    
                    # 更新图片URL到payload
                    payload["image_url"] = f"/static/uploads/resources/{unique_filename}"
            
            return await super().save_model(id, payload)
        except Exception as e:
            print(f"Error saving resource: {str(e)}")
            raise e
