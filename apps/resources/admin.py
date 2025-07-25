from .models import Resource, ResourceType, Model3D, ModelFormat, Model3DCategory
from fastadmin import TortoiseModelAdmin, register, action, display, TortoiseInlineModelAdmin, WidgetType
from tortoise.fields import CharField,TextField
from fastapi.responses import JSONResponse
from fastapi import UploadFile
from uuid import UUID
import os
import base64
import hashlib
import json
import struct
import zlib
import io
from datetime import datetime
from typing import List
from core.settings import settings
from fastadmin.api.helpers import is_valid_base64


def parse_glb_to_gltf(glb_data: bytes) -> dict:
    """解析GLB二进制文件为GLTF JSON数据"""
    if len(glb_data) < 12:
        raise ValueError("GLB文件太小，无法解析")
    
    # 读取GLB文件头
    magic = glb_data[:4]
    if magic != b'glTF':
        raise ValueError("不是有效的GLB文件")
    
    version = struct.unpack('<I', glb_data[4:8])[0]
    if version != 2:
        raise ValueError(f"不支持的GLB版本: {version}")
    
    length = struct.unpack('<I', glb_data[8:12])[0]
    
    # 读取JSON chunk
    offset = 12
    json_chunk_length = struct.unpack('<I', glb_data[offset:offset+4])[0]
    json_chunk_type = glb_data[offset+4:offset+8]
    
    if json_chunk_type != b'JSON':
        raise ValueError("GLB文件格式错误：缺少JSON chunk")
    
    json_data = glb_data[offset+8:offset+8+json_chunk_length]
    gltf_json = json.loads(json_data.decode('utf-8'))
    
    return gltf_json


def convert_model_to_binary(model_data: bytes, file_ext: str) -> bytes:
    """将各种3D模型格式转换为自定义二进制格式"""
    if file_ext == ".gltf":
        # GLTF文本格式
        gltf_json = json.loads(model_data.decode('utf-8'))
    elif file_ext == ".glb":
        # GLB二进制格式
        gltf_json = parse_glb_to_gltf(model_data)
    elif file_ext in [".obj", ".fbx"]:
        # 对于OBJ和FBX格式，创建一个简化的GLTF结构
        # 这里只是保存原始数据，实际项目中可能需要更复杂的转换
        gltf_json = {
            "asset": {"version": "2.0", "generator": "FastDog Converter"},
            "extensionsUsed": ["FASTDOG_ORIGINAL_FORMAT"],
            "extensions": {
                "FASTDOG_ORIGINAL_FORMAT": {
                    "format": file_ext,
                    "data": base64.b64encode(model_data).decode('utf-8')
                }
            }
        }
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}")
    
    return convert_gltf_to_binary(gltf_json)


def convert_gltf_to_binary(gltf_data: dict) -> bytes:
    """将GLTF数据转换为自定义二进制格式"""
    # 创建二进制数据结构
    binary_data = io.BytesIO()
    
    # 写入文件头 (8字节魔数 + 4字节版本)
    binary_data.write(b'FASTDOG1')  # 魔数
    binary_data.write(struct.pack('<I', 1))  # 版本号
    
    # 序列化JSON数据
    json_str = json.dumps(gltf_data, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    
    # 压缩JSON数据 (优化压缩级别以平衡速度和压缩比)
    compressed_json = zlib.compress(json_bytes, level=6)
    
    # 写入压缩数据长度和数据
    binary_data.write(struct.pack('<I', len(compressed_json)))
    binary_data.write(compressed_json)
    
    # 写入原始数据长度（用于验证）
    binary_data.write(struct.pack('<I', len(json_bytes)))
    
    return binary_data.getvalue()


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
        "image_url": CharField(max_length=5 * 1024 * 1024, description="资源图片链接", required=False)
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
                            raise ValueError("无效的base64图片数据")
                    else:
                        raise ValueError("无效的base64图片格式")
                    
                    # 更新图片URL到payload
                    payload["image_url"] = f"/static/uploads/resources/{unique_filename}"
            
            # 保存资源
            result = await super().save_model(id, payload)
            
            # 验证保存结果
            if result:
                saved_resource = await self.model.get(id=result["id"])
                
                # 如果image_url没有正确保存，尝试直接更新
                if "image_url" in payload and payload["image_url"] and saved_resource.image_url != payload["image_url"]:
                    saved_resource.image_url = payload["image_url"]
                    await saved_resource.save()
            
            return result
        except Exception as e:
            raise e


@register(Model3DCategory)
class Model3DCategoryAdmin(TortoiseModelAdmin):
    model = Model3DCategory
    icon = "folder"
    display_name = "3D模型分类"
    list_display = ["id", "name", "sort_order", "is_active", "created_at"]
    list_display_links = ["id", "name"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    list_per_page = 15
    ordering = ["sort_order", "-created_at"]
    
    form_fields = {
        "name": CharField(max_length=255, description="分类名称"),
        "description": CharField(max_length=1024, description="分类描述", required=False),
        "sort_order": CharField(max_length=10, description="排序顺序", required=False)
    }

@register(Model3D)
class Model3DAdmin(TortoiseModelAdmin):
    model = Model3D
    icon = "cube"
    display_name = "3D模型管理"
    list_display = ["id", "name", "category", "is_public", "created_at"]
    list_display_links = ["id", "name"]
    list_filter = ["category", "is_public", "created_at"]
    search_fields = ["name", "description"]
    list_per_page = 15
    ordering = ["-created_at"]
    readonly_fields = ["uuid"]  # 设置UUID为只读字段，查看时显示但不可编辑
    
    form_fields = {
        "name": CharField(max_length=255, description="模型名称"),
        "description": TextField(description="模型描述", required=False),
        "category": CharField(max_length=255, description="所属分类", required=False),
        "model_file_url": TextField(description="模型文件", required=False),
        "binary_file_url": TextField(description="二进制文件", required=False),
        "thumbnail_url": TextField(description="预览图", required=False)
    }
    formfield_overrides = {  # noqa: RUF012
          "model_file_url": (WidgetType.Upload, {
            "required": False,
            "upload_action_name": "upload",
            "accept": ".glb,.gltf,.obj,.fbx,.fastdog",
            "multiple": False,
            "showUploadList": True,
            "maxCount": 1,
            "maxFileSize": 50 * 1024 * 1024,  # 50MB
        }),
        "binary_file_url": (WidgetType.Upload, {
            "required": False,
            "upload_action_name": "upload",
            "accept": ".bin,.fastdog",
            "multiple": False,
            "showUploadList": True,
            "maxCount": 1,
            "maxFileSize": 50 * 1024 * 1024,  # 50MB
        }),
        "thumbnail_url": (WidgetType.Upload, {
            "required": False,
            "upload_action_name": "upload",
            "accept": ".jpg,.jpeg,.png,.gif,.webp",
            "multiple": False,
            "showUploadList": True,
            "listType": "picture",
            "maxCount": 1,
            "maxFileSize": 10 * 1024 * 1024,  # 10MB
        }) 
    }
    
    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        # 处理上传的模型文件
        try:
            # 获取或生成模型UUID
            model_uuid = None
            if id:
                # 编辑现有模型，获取现有UUID
                existing_model = await self.model.get(id=id)
                model_uuid = existing_model.uuid
            else:
                # 新建模型，生成新UUID
                import uuid
                model_uuid = uuid.uuid4().hex
            
            # 确保payload中不包含用户输入的uuid字段
            payload.pop('uuid', None)
            
            # 需要处理的文件字段
            file_fields = ["model_file_url", "binary_file_url", "thumbnail_url"]
            
            for field_name in file_fields:
                if field_name in payload and payload[field_name] is not None:
                    file = payload[field_name]
                    if isinstance(file, UploadFile):
                        try:
                            # 确保上传目录存在
                            upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "models")
                            os.makedirs(upload_dir, exist_ok=True)
                            
                            # 获取文件扩展名并转换为小写
                            file_ext = os.path.splitext(file.filename)[1].lower()
                            
                            # 根据字段类型验证文件格式
                            if field_name == "thumbnail_url":
                                if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                                    raise ValueError(f"缩略图不支持的格式: {file_ext}")
                            elif field_name == "model_file_url":
                                if file_ext not in [".gltf", ".glb", ".obj", ".fbx", ".fastdog"]:
                                    raise ValueError(f"模型文件不支持的格式: {file_ext}")
                            elif field_name == "binary_file_url":
                                if file_ext not in [".bin"]:
                                    raise ValueError(f"二进制文件不支持的格式: {file_ext}")
                            
                            # 使用模型UUID生成文件名
                            unique_filename = f"{str(model_uuid)}{file_ext}"
                            file_path = os.path.join(upload_dir, unique_filename)
                            
                            # 读取文件内容
                            content = await file.read()
                            
                            # 保存文件
                            with open(file_path, "wb") as f:
                                f.write(content)
                                f.flush()
                                os.fsync(f.fileno())
                            
                            # 更新文件URL到payload
                            payload[field_name] = f"/static/uploads/models/{unique_filename}"
                            
                        except Exception as e:
                            raise e
                    elif isinstance(file, str) and (is_valid_base64(file) or file.startswith('data:')):
                        import base64
                        import re
                        
                        # 确保上传目录存在
                        upload_dir = os.path.join(settings.STATIC_DIR, "uploads", "models")
                        os.makedirs(upload_dir, exist_ok=True)
                        
                        if field_name == "thumbnail_url":
                            # 处理缩略图的base64编码
                            base64_pattern = r'^data:image/(\w+);base64,(.+)$'
                            match = re.match(base64_pattern, file)
                            
                            if match:
                                file_type = match.group(1)
                                base64_data = match.group(2)
                                
                                # 检查文件类型
                                if file_type not in ['jpeg', 'jpg', 'png', 'gif', 'webp']:
                                    raise ValueError(f"缩略图不支持的格式: {file_type}")
                                    
                                # 使用模型UUID生成文件名
                                unique_filename = f"{str(model_uuid)}.{file_type}"
                                file_path = os.path.join(upload_dir, unique_filename)
                                
                                try:
                                    # 解码base64并保存文件
                                    image_data = base64.b64decode(base64_data)
                                    with open(file_path, "wb") as f:
                                        f.write(image_data)
                                        f.flush()
                                        os.fsync(f.fileno())
                                    
                                    # 更新文件URL到payload
                                    payload[field_name] = f"/static/uploads/models/{unique_filename}"
                                    
                                except Exception as e:
                                    raise ValueError("无效的base64图片数据")
                            else:
                                raise ValueError("无效的base64图片格式")
                        else:
                            # 处理模型文件的base64编码
                            try:
                                # 检查base64数据长度，避免过大文件
                                if len(file) > 50 * 1024 * 1024:  # 50MB限制
                                    raise ValueError(f"文件过大({len(file)}字符)，建议不超过30MB，请使用文件上传方式")
                                
                                # 尝试解析base64数据
                                if file.startswith('data:'):
                                    # 处理带MIME类型的base64
                                    header, base64_data = file.split(',', 1)
                                    # 从header中提取文件扩展名
                                    if 'gltf' in header.lower():
                                        file_ext = '.gltf'
                                    elif 'glb' in header.lower():
                                        file_ext = '.glb'
                                    elif 'obj' in header.lower():
                                        file_ext = '.obj'
                                    elif 'fbx' in header.lower():
                                        file_ext = '.fbx'
                                    elif 'application/json' in header.lower():
                                        # JSON格式，可能是gltf
                                        file_ext = '.gltf'
                                    elif 'octet-stream' in header.lower():
                                        # 对于 octet-stream，尝试从文件内容判断类型
                                        try:
                                            # 解码一小部分数据来检测文件类型
                                            sample_data = base64.b64decode(base64_data[:200])  # 取前200个字符解码
                                            
                                            # 检查 GLB 文件魔数 (glTF)
                                            if sample_data.startswith(b'glTF'):
                                                file_ext = '.glb'
                                            else:
                                                # 尝试解码为文本检查是否为 gltf JSON
                                                try:
                                                    sample_text = sample_data.decode('utf-8')
                                                    # 更严格的 gltf JSON 检测
                                                    if (sample_text.strip().startswith('{') and 
                                                        ('"asset"' in sample_text or '"scene' in sample_text or '"nodes"' in sample_text)):
                                                        file_ext = '.gltf'
                                                    else:
                                                        file_ext = '.bin'
                                                except UnicodeDecodeError:
                                                    file_ext = '.bin'  # 无法解码为文本，是二进制文件
                                        except:
                                            file_ext = '.bin'  # 解码失败，默认为二进制文件
                                    else:
                                        file_ext = '.bin'  # 默认为二进制文件
                                else:
                                    # 纯base64数据，默认为二进制文件
                                    base64_data = file
                                    file_ext = '.bin'
                                
                                # 验证base64文件格式
                                if field_name == "model_file_url":
                                    if file_ext not in [".gltf", ".glb", ".obj", ".fbx", ".fastdog"]:
                                        raise ValueError(f"模型文件不支持的格式: {file_ext}")
                                elif field_name == "binary_file_url":
                                    if file_ext not in [".bin", ".glb"]:
                                        raise ValueError(f"二进制文件不支持的格式: {file_ext}")
                                
                                # 使用模型UUID生成文件名
                                unique_filename = f"{str(model_uuid)}{file_ext}"
                                file_path = os.path.join(upload_dir, unique_filename)
                                
                                # 解码base64并保存文件
                                model_data = base64.b64decode(base64_data)
                                with open(file_path, "wb") as f:
                                    f.write(model_data)
                                    f.flush()
                                    os.fsync(f.fileno())
                                
                                # 如果是3D模型文件，同时生成压缩的二进制文件
                                if field_name == "model_file_url" and file_ext in [".gltf", ".glb", ".obj", ".fbx"]:
                                    try:
                                        # 使用统一的转换函数处理各种格式
                                        compressed_data = convert_model_to_binary(model_data, file_ext)
                                        
                                        # 保存压缩文件
                                        compressed_filename = f"{str(model_uuid)}.fastdog"
                                        compressed_file_path = os.path.join(upload_dir, compressed_filename)
                                        
                                        with open(compressed_file_path, "wb") as cf:
                                            cf.write(compressed_data)
                                            cf.flush()
                                            os.fsync(cf.fileno())
                                        
                                        # 更新binary_file_url到payload
                                        payload['binary_file_url'] = f"/static/uploads/models/{compressed_filename}"
                                        
                                    except Exception as e:
                                        pass  # 生成压缩二进制文件失败，继续处理
                                
                                # 更新文件URL到payload
                                payload[field_name] = f"/static/uploads/models/{unique_filename}"
                                
                            except Exception as e:
                                # 如果base64处理失败，移除该字段，避免将base64字符串保存到数据库
                                payload.pop(field_name, None)
                                continue    
            # 对于新建模型，将生成的UUID添加到payload中
            if not id:
                payload['uuid'] = model_uuid
            
            # 验证文件URL字段长度，确保不超过数据库限制
            file_fields = ["model_file_url", "binary_file_url", "thumbnail_url"]
            for field_name in file_fields:
                if field_name in payload and payload[field_name]:
                    url_value = payload[field_name]
                    if isinstance(url_value, str) and len(url_value) > 2048:
                        payload.pop(field_name, None)
            
            # 保存模型
            result = await super().save_model(id, payload)
            
            # 验证保存结果
            if result:
                saved_model = await self.model.get(id=result["id"])
                
                # 如果文件URL没有正确保存，尝试直接更新
                update_needed = False
                for field_name in file_fields:
                    if field_name in payload and payload[field_name] and getattr(saved_model, field_name) != payload[field_name]:
                        setattr(saved_model, field_name, payload[field_name])
                        update_needed = True
                
                if update_needed:
                    await saved_model.save()
            
            return result
        except Exception as e:
            raise e
    
    async def delete_model(self, id: str) -> bool:
        """删除模型时同时删除相关文件"""
        try:
            # 先获取模型信息，获取文件路径
            model = await self.model.get(id=id)
            
            # 收集需要删除的文件路径
            files_to_delete = []
            file_fields = ["model_file_url", "binary_file_url", "thumbnail_url"]
            
            for field_name in file_fields:
                file_url = getattr(model, field_name, None)
                if file_url and file_url.startswith("/static/uploads/models/"):
                    # 从URL转换为实际文件路径
                    filename = file_url.replace("/static/uploads/models/", "")
                    file_path = os.path.join(settings.STATIC_DIR, "uploads", "models", filename)
                    if os.path.exists(file_path):
                        files_to_delete.append((field_name, file_path))
            
            # 先删除文件，再删除数据库记录
            for field_name, file_path in files_to_delete:
                try:
                    os.remove(file_path)
                except Exception as e:
                    # 文件删除失败不影响整体操作
                    pass
            
            # 删除数据库记录
            return await super().delete_model(id)
            
        except Exception as e:
            raise e
