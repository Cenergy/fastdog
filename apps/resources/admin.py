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
                    try:
                        # 确保上传目录存在
                        upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "resources")
                        os.makedirs(upload_dir, exist_ok=True)
                        
                        # 获取文件扩展名并转换为小写
                        file_ext = os.path.splitext(file.filename)[1].lower()
                        if file_ext not in [".jpg", ".jpeg", ".png", ".gif"]:
                            raise ValueError(f"不支持的图片格式: {file_ext}")
                        
                        # 生成唯一文件名
                        unique_filename = f"{UUID(str(id)).hex if id else UUID(str(payload.get('id'))).hex}{file_ext}"
                        file_path = os.path.join(upload_dir, unique_filename)
                        
                        # 读取文件内容
                        content = await file.read()
                        
                        # 保存文件
                        with open(file_path, "wb") as f:
                            f.write(content)
                            f.flush()
                            os.fsync(f.fileno())
                        
                        # 更新图片URL到payload
                        payload["image_url"] = f"/static/uploads/resources/{unique_filename}"
                    except Exception as e:
                        print(f"保存上传文件时出错: {str(e)}")
                        raise e
                elif isinstance(file, str) and is_valid_base64(file):
                    # 处理base64编码的图片
                    import base64
                    import re
                    from uuid import uuid4
                    
                    # 确保上传目录存在
                    upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "resources")
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # 解析base64数据和文件类型
                    base64_pattern = r'^data:image/(\w+);base64,(.+)$'
                    match = re.match(base64_pattern, file)
                    
                    if match:
                        file_type = match.group(1)
                        base64_data = match.group(2)
                        
                        # 检查文件类型
                        if file_type not in ['jpeg', 'jpg', 'png', 'gif']:
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
                        except Exception as e:
                            print(f"保存base64图片时出错: {str(e)}")
                            raise ValueError("无效的base64图片数据")
                    else:
                        raise ValueError("无效的base64图片格式")
                    
                    # 更新图片URL到payload
                    payload["image_url"] = f"/static/uploads/resources/{unique_filename}"
            
            # 确保image_url字段被正确设置
            if "image_url" in payload and payload["image_url"] and payload["image_url"].startswith("/static/"):
                print(f"Image URL before save: {payload['image_url']}")
                
            # 保存资源
            result = await super().save_model(id, payload)
            
            # 验证保存结果
            if result:
                saved_resource = await self.model.get(id=result["id"])
                print(f"Saved resource image_url: {saved_resource.image_url}")
                
                # 如果image_url没有正确保存，尝试直接更新
                if "image_url" in payload and payload["image_url"] and saved_resource.image_url != payload["image_url"]:
                    saved_resource.image_url = payload["image_url"]
                    await saved_resource.save()
                    print(f"Updated resource image_url: {saved_resource.image_url}")
            
            return result
        except Exception as e:
            print(f"Error saving resource: {str(e)}")
            raise e
