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
import magic
from datetime import datetime
from typing import List
from core.settings import settings
from fastadmin.api.helpers import is_valid_base64

PUBLIC_MODEL_PATH = settings.PUBLIC_MODEL_PATH
PRIVATE_MODEL_PATH = settings.PRIVATE_MODEL_PATH


def detect_file_type_from_data(data: bytes) -> str:
    """使用python-magic检测文件类型并返回合适的扩展名"""
    try:
        # 使用magic检测MIME类型
        mime_type = magic.from_buffer(data, mime=True)
        file_description = magic.from_buffer(data)
        
        # 图片文件类型映射
        if mime_type == "image/jpeg":
            return ".jpg"
        elif mime_type == "image/png":
            return ".png"
        elif mime_type == "image/gif":
            return ".gif"
        elif mime_type == "image/webp":
            return ".webp"
        
        # JSON格式检测
        elif mime_type == "application/json" or "JSON" in file_description:
            # 检查是否为GLTF JSON格式
            try:
                text_data = data.decode('utf-8')
                if '"asset"' in text_data and ('"scene' in text_data or '"nodes"' in text_data):
                    return ".gltf"
            except:
                pass
            return ".json"
        
        # 二进制文件检测
        elif mime_type == "application/octet-stream" or "data" in mime_type:
            # 检查GLB文件魔数
            if data.startswith(b'glTF'):
                return ".glb"
            # 检查FBX文件魔数
            elif data.startswith(b'Kaydara FBX Binary') or b'FBX' in data[:100]:
                return ".fbx"
            # 检查OBJ文件特征（通常以文本开头）
            elif b'v ' in data[:100] or b'f ' in data[:100] or b'vn ' in data[:100]:
                return ".obj"
            # 检查是否为fastdog格式（自定义二进制格式）
            elif b'FASTDOG' in data[:20]:
                return ".fastdog"
            else:
                return ".bin"
        
        # 文本格式检测
        elif "text" in mime_type:
            try:
                text_data = data.decode('utf-8')
                if '"asset"' in text_data and ('"scene' in text_data or '"nodes"' in text_data):
                    return ".gltf"
                elif any(line.strip().startswith(('v ', 'f ', 'vn ', 'vt ', 'o ', 'g ')) for line in text_data.split('\n')[:10]):
                    return ".obj"
            except:
                pass
            return ".txt"
        
        # 3D模型文件的MIME类型处理
        elif "gltf-binary" in mime_type.lower() or "model/gltf-binary" in mime_type.lower():
            return ".glb"
        elif "gltf" in mime_type.lower():
            return ".gltf"
        elif "glb" in mime_type.lower():
            return ".glb"
        elif "fbx" in mime_type.lower():
            return ".fbx"
        elif "obj" in mime_type.lower():
            return ".obj"
        else:
            return ".bin"
        
    except Exception as e:
        # 如果magic检测失败，回退到简单的文件头检测
        if data.startswith(b'glTF'):
            return ".glb"
        elif data.startswith(b'Kaydara FBX Binary') or b'FBX' in data[:100]:
            return ".fbx"
        # 图片文件的简单检测
        elif data.startswith(b'\xff\xd8\xff'):
            return ".jpg"
        elif data.startswith(b'\x89PNG\r\n\x1a\n'):
            return ".png"
        elif data.startswith(b'GIF8'):
            return ".gif"
        elif data.startswith(b'RIFF') and b'WEBP' in data[:12]:
            return ".webp"
        
        return ".bin"  # 最终默认值


def convert_model_to_binary(model_data: bytes, file_ext: str) -> bytes:
    """将各种3D模型格式转换为自定义二进制格式"""
    if file_ext == ".gltf":
        # GLTF文本格式
        gltf_json = json.loads(model_data.decode('utf-8'))
        return convert_gltf_to_binary(gltf_json)
    elif file_ext == ".glb":
        # GLB二进制格式 - 保留完整的GLB数据
        # 对于GLB文件，我们直接保存原始二进制数据，因为它已经是优化的二进制格式
        return convert_glb_to_fastdog_binary(model_data)
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
        return convert_gltf_to_binary(gltf_json)
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}")


def convert_glb_to_fastdog_binary(glb_data: bytes) -> bytes:
    """将GLB二进制数据转换为FastDog二进制格式"""
    # 创建二进制数据结构
    binary_data = io.BytesIO()
    
    # 写入文件头 (8字节魔数 + 4字节版本)
    binary_data.write(b'FASTDOG1')  # 魔数
    binary_data.write(struct.pack('<I', 2))  # 版本号2表示GLB格式
    
    # 压缩GLB数据 (使用较高的压缩级别，因为GLB已经是二进制格式)
    compressed_glb = zlib.compress(glb_data, level=9)
    
    # 写入压缩数据长度和数据
    binary_data.write(struct.pack('<I', len(compressed_glb)))
    binary_data.write(compressed_glb)
    
    # 写入原始数据长度（用于验证）
    binary_data.write(struct.pack('<I', len(glb_data)))
    
    return binary_data.getvalue()


def convert_gltf_to_binary(gltf_data: dict) -> bytes:
    """将GLTF数据转换为自定义二进制格式"""
    # 创建二进制数据结构
    binary_data = io.BytesIO()
    
    # 写入文件头 (8字节魔数 + 4字节版本)
    binary_data.write(b'FASTDOG1')  # 魔数
    binary_data.write(struct.pack('<I', 1))  # 版本号1表示GLTF格式
    
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
    verbose_name="模型分类"
    # An override to the verbose_name_plural from the model's inner Meta class.
    verbose_name_plural="模型分类"

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

      # An override to the verbose_name from the model's inner Meta class.
    verbose_name="模型管理"
    # An override to the verbose_name_plural from the model's inner Meta class.
    verbose_name_plural="模型管理"
    
    form_fields = {
        "name": CharField(max_length=255, description="模型名称"),
        "description": TextField(description="模型描述", required=False),
        "category": CharField(max_length=255, description="所属分类", required=False),
        "model_file_url": TextField(description="模型文件", required=False),
        "model_file_name": CharField(max_length=255, description="模型文件名", required=False),
        "binary_file_url": TextField(description="二进制文件", required=False),
        "binary_file_name": CharField(max_length=255, description="二进制文件名", required=False),
        "thumbnail_url": TextField(description="预览图", required=False),
        "thumbnail_file_name": CharField(max_length=255, description="预览图文件名", required=False)
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
    def _get_upload_directory(self, is_public: bool) -> str:
        """获取上传目录路径"""
        if is_public:
            return os.path.join(settings.STATIC_DIR, settings.PUBLIC_MODEL_PATH.lstrip('/'))
        else:
            return os.path.join(settings.STATIC_DIR, settings.PRIVATE_MODEL_PATH.lstrip('/'))
    
    def _generate_file_url(self, filename: str, is_public: bool) -> str:
        """生成文件URL"""
        if is_public:
            return f"/static{settings.PUBLIC_MODEL_PATH}{filename}"
        else:
            return f"/static{settings.PRIVATE_MODEL_PATH}{filename}"
    
    def _validate_file_type(self, field_name: str, file_ext: str) -> None:
        """验证文件类型"""
        if field_name == "thumbnail_url":
            if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                raise ValueError(f"缩略图不支持的格式: {file_ext}")
        elif field_name == "model_file_url":
            if file_ext not in [".gltf", ".glb", ".obj", ".fbx", ".fastdog"]:
                raise ValueError(f"模型文件不支持的格式: {file_ext}")
        elif field_name == "binary_file_url":
            if file_ext not in [".bin"]:
                raise ValueError(f"二进制文件不支持的格式: {file_ext}")
    
    def _save_file_to_disk(self, file_path: str, content: bytes) -> None:
        """保存文件到磁盘"""
        with open(file_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
    
    async def _get_or_generate_model_uuid(self, id: UUID | int | None) -> tuple[str, object | None]:
        """获取或生成模型UUID"""
        model_uuid = None
        existing_model = None
        if id:
            # 编辑现有模型，获取现有UUID
            existing_model = await self.model.get(id=id)
            model_uuid = existing_model.uuid
        else:
            # 新建模型，生成新UUID
            import uuid
            model_uuid = uuid.uuid4().hex
        return model_uuid, existing_model
    
    async def _move_files_for_public_status_change(self, existing_model, model_uuid: str, is_public: bool, file_fields: list, payload: dict) -> None:
        """当is_public状态变化时移动整个UUID文件夹"""
        import shutil
        
        upload_dir = self._get_upload_directory(is_public)
        old_upload_dir = self._get_upload_directory(existing_model.is_public)
        
        # 确保新目录存在
        os.makedirs(upload_dir, exist_ok=True)
        
        # 检查是否存在UUID文件夹
        old_uuid_folder = os.path.join(old_upload_dir, model_uuid)
        new_uuid_folder = os.path.join(upload_dir, model_uuid)
        
        if os.path.exists(old_uuid_folder):
            try:
                # 移动整个UUID文件夹
                if os.path.exists(new_uuid_folder):
                    # 如果目标文件夹已存在，先删除它
                    shutil.rmtree(new_uuid_folder)
                
                shutil.move(old_uuid_folder, new_uuid_folder)
                print(f"已移动UUID文件夹: {old_uuid_folder} -> {new_uuid_folder}")
                
                # 更新所有文件URL路径
                for field_name in file_fields:
                    current_url = getattr(existing_model, field_name)
                    if current_url and '/' in current_url:
                        # 提取相对路径（包含UUID文件夹）
                        url_parts = current_url.split('/')
                        if len(url_parts) >= 2:
                            relative_path = '/'.join(url_parts[-2:])  # UUID文件夹/文件名
                            payload[field_name] = self._generate_file_url(relative_path, is_public)
                            
            except Exception as e:
                print(f"移动UUID文件夹失败: {old_uuid_folder} -> {new_uuid_folder}, 错误: {e}")
                # 如果移动文件夹失败，回退到移动单个文件的逻辑
                await self._move_individual_files_fallback(existing_model, model_uuid, is_public, file_fields, payload, old_upload_dir, upload_dir)
        else:
            # 如果没有UUID文件夹，使用旧的单个文件移动逻辑（兼容性）
            await self._move_individual_files_fallback(existing_model, model_uuid, is_public, file_fields, payload, old_upload_dir, upload_dir)
    
    async def _move_individual_files_fallback(self, existing_model, model_uuid: str, is_public: bool, file_fields: list, payload: dict, old_upload_dir: str, upload_dir: str) -> None:
        """兼容性方法：移动单个文件（用于旧格式）"""
        import shutil
        
        # 移动现有文件并更新URL
        for field_name in file_fields:
            current_url = getattr(existing_model, field_name)
            if current_url:
                # 从URL中提取文件名
                filename = os.path.basename(current_url)
                old_file_path = os.path.join(old_upload_dir, filename)
                new_file_path = os.path.join(upload_dir, filename)
                
                # 如果旧文件存在，移动到新位置
                if os.path.exists(old_file_path):
                    try:
                        shutil.move(old_file_path, new_file_path)
                        # 更新URL路径
                        payload[field_name] = self._generate_file_url(filename, is_public)
                        print(f"已移动文件: {old_file_path} -> {new_file_path}")
                    except Exception as e:
                        print(f"移动文件失败: {old_file_path} -> {new_file_path}, 错误: {e}")
        
        # 移动.fastdog文件
        fastdog_filename = f"{model_uuid}.fastdog"
        old_fastdog_path = os.path.join(old_upload_dir, fastdog_filename)
        new_fastdog_path = os.path.join(upload_dir, fastdog_filename)
        
        if os.path.exists(old_fastdog_path):
            try:
                shutil.move(old_fastdog_path, new_fastdog_path)
                print(f"已移动.fastdog文件: {old_fastdog_path} -> {new_fastdog_path}")
            except Exception as e:
                print(f"移动.fastdog文件失败: {old_fastdog_path} -> {new_fastdog_path}, 错误: {e}")
    
    def _update_gltf_bin_references(self, gltf_content: bytes, model_uuid: str) -> bytes:
        """更新GLTF文件中的bin文件引用路径"""
        try:
            # 解析GLTF JSON内容
            gltf_text = gltf_content.decode('utf-8')
            gltf_data = json.loads(gltf_text)
            
            # 检查是否有buffers字段
            if 'buffers' in gltf_data:
                for buffer in gltf_data['buffers']:
                    if 'uri' in buffer:
                        # 获取原始bin文件名
                        original_uri = buffer['uri']
                        # 如果是相对路径的bin文件，更新为新的文件名
                        if original_uri.endswith('.bin') and not original_uri.startswith('http'):
                            # 更新为使用模型UUID的文件名
                            buffer['uri'] = f"{model_uuid}.bin"
            
            # 将更新后的JSON转换回字节
            updated_gltf_text = json.dumps(gltf_data, separators=(',', ':'))
            return updated_gltf_text.encode('utf-8')
            
        except Exception as e:
            # 如果解析失败，返回原始内容
            print(f"更新GLTF bin引用失败: {str(e)}")
            return gltf_content
    
    async def _process_upload_file(self, file: UploadFile, field_name: str, model_uuid: str, upload_dir: str, is_public: bool, payload: dict) -> None:
        """处理UploadFile文件上传"""
        try:
            # 创建UUID文件夹
            uuid_dir = os.path.join(upload_dir, model_uuid)
            os.makedirs(uuid_dir, exist_ok=True)
            
            # 获取原文件名和扩展名
            original_filename = file.filename
            file_ext = os.path.splitext(original_filename)[1].lower()
            
            # 验证文件格式
            self._validate_file_type(field_name, file_ext)
            
            # 确定保存的文件名
            if field_name == "model_file_url":
                # 主模型文件：优先使用model_file_name字段，否则使用原文件名，最后使用"model"
                if payload.get("model_file_name"):
                    save_filename = f"{payload['model_file_name']}{file_ext}"
                elif original_filename:
                    save_filename = original_filename
                else:
                    save_filename = f"model{file_ext}"
            elif field_name == "binary_file_url":
                # 二进制文件：优先使用binary_file_name字段，否则使用原文件名，最后使用"binary"
                if payload.get("binary_file_name"):
                    save_filename = f"{payload['binary_file_name']}{file_ext}"
                elif original_filename:
                    save_filename = original_filename
                else:
                    save_filename = f"binary{file_ext}"
            elif field_name == "thumbnail_url":
                # 预览图：优先使用原文件名，否则使用thumbnail_file_name字段，最后使用"thumbnail"
                if original_filename:
                    save_filename = original_filename
                elif payload.get("thumbnail_file_name"):
                    save_filename = payload["thumbnail_file_name"]
                else:
                    save_filename = f"thumbnail{file_ext}"
            else:
                save_filename = original_filename or f"file{file_ext}"
            
            # 构建完整文件路径
            file_path = os.path.join(uuid_dir, save_filename)
            
            # 读取文件内容
            content = await file.read()
            
            # 如果是GLTF文件，需要更新其中的bin文件引用
            if field_name == "model_file_url" and file_ext == ".gltf":
                content = self._update_gltf_bin_references(content, model_uuid)
            
            # 保存文件
            self._save_file_to_disk(file_path, content)
            
            # 如果是3D模型文件，生成压缩的二进制文件
            if field_name == "model_file_url" and file_ext in [".gltf", ".glb", ".obj", ".fbx"]:
                await self._generate_compressed_model(content, model_uuid, uuid_dir, file_ext, save_filename, payload)
            
            # 更新文件URL到payload（包含UUID文件夹路径）
            relative_path = f"{model_uuid}/{save_filename}"
            payload[field_name] = self._generate_file_url(relative_path, is_public)
            
            # 保存实际使用的文件名到对应的字段（不带扩展名）
            if field_name == "model_file_url":
                payload["model_file_name"] = os.path.splitext(save_filename)[0]
            elif field_name == "binary_file_url":
                payload["binary_file_name"] = os.path.splitext(save_filename)[0]
            elif field_name == "thumbnail_url":
                payload["thumbnail_file_name"] = os.path.splitext(save_filename)[0]
            
        except Exception as e:
             raise e
    
    async def _process_base64_thumbnail(self, file: str, model_uuid: str, upload_dir: str, is_public: bool, payload: dict, field_name: str) -> None:
        """处理缩略图的base64编码"""
        import base64
        import re
        
        # 确保上传目录存在
        os.makedirs(upload_dir, exist_ok=True)
        
        # 处理缩略图的base64编码
        base64_pattern = r'^data:image/(\w+);base64,(.+)$'
        match = re.match(base64_pattern, file)
        
        if match:
            base64_data = match.group(2)
            
            try:
                # 解码base64数据
                image_data = base64.b64decode(base64_data)
                
                # 使用python-magic检测文件类型
                file_ext = detect_file_type_from_data(image_data)
                
                # 验证缩略图格式
                if file_ext not in [".jpg", ".png", ".gif", ".webp"]:
                    raise ValueError(f"缩略图不支持的格式: {file_ext}")
                
                # 创建UUID文件夹
                uuid_dir = os.path.join(upload_dir, str(model_uuid))
                os.makedirs(uuid_dir, exist_ok=True)
                
                # 确定文件名（缩略图默认为thumbnail）
                filename = f"thumbnail{file_ext}"
                file_path = os.path.join(uuid_dir, filename)
                
                # 保存文件
                self._save_file_to_disk(file_path, image_data)
                
                # 更新文件URL到payload（包含UUID文件夹路径）
                relative_path = f"{str(model_uuid)}/{filename}"
                payload[field_name] = self._generate_file_url(relative_path, is_public)
                
            except Exception as e:
                raise ValueError(f"无效的base64图片数据: {str(e)}")
        else:
            raise ValueError("无效的base64图片格式")
    
    async def _process_base64_model_file(self, file: str, field_name: str, model_uuid: str, upload_dir: str, is_public: bool, payload: dict) -> None:
        """处理模型文件的base64编码"""
        import base64
        
        try:
            # 检查base64数据长度，避免过大文件
            if len(file) > 50 * 1024 * 1024:  # 50MB限制
                raise ValueError(f"文件过大({len(file)}字符)，建议不超过30MB，请使用文件上传方式")
            
            # 解析base64数据
            if file.startswith('data:'):
                # 处理带MIME类型的base64
                header, base64_data = file.split(',', 1)
            else:
                # 纯base64数据
                base64_data = file
            
            # 解码base64数据
            model_data = base64.b64decode(base64_data)
            
            # 使用python-magic检测文件类型
            file_ext = detect_file_type_from_data(model_data)
            
            # 验证文件格式
            if field_name == "model_file_url":
                if file_ext not in [".gltf", ".glb", ".obj", ".fbx", ".fastdog"]:
                    raise ValueError(f"模型文件不支持的格式: {file_ext}")
            elif field_name == "binary_file_url":
                if file_ext not in [".bin", ".glb", ".fastdog"]:
                    raise ValueError(f"二进制文件不支持的格式: {file_ext}")
            
            # 创建UUID文件夹
            uuid_dir = os.path.join(upload_dir, str(model_uuid))
            os.makedirs(uuid_dir, exist_ok=True)
            
            # 确定文件名，优先使用用户传入的文件名
            if field_name == "model_file_url":
                # 优先使用用户传入的model_file_name
                if payload.get("model_file_name"):
                    filename = f"{payload['model_file_name']}{file_ext}"
                else:
                    filename = f"model{file_ext}"
            elif field_name == "binary_file_url":
                # 优先使用用户传入的binary_file_name
                if payload.get("binary_file_name"):
                    filename = f"{payload['binary_file_name']}{file_ext}"
                else:
                    filename = f"binary{file_ext}"
            else:
                filename = f"{str(model_uuid)}{file_ext}"
            
            file_path = os.path.join(uuid_dir, filename)
            
            # 保存文件
            self._save_file_to_disk(file_path, model_data)
            
            # 如果是3D模型文件，生成压缩的二进制文件
            if field_name == "model_file_url" and file_ext in [".gltf", ".glb", ".obj", ".fbx"]:
                await self._generate_compressed_model(model_data, model_uuid, uuid_dir, file_ext, filename, payload)
            
            # 更新文件URL到payload（包含UUID文件夹路径）
            relative_path = f"{str(model_uuid)}/{filename}"
            payload[field_name] = self._generate_file_url(relative_path, is_public)
            
            # 保存文件名到对应的字段
            if field_name == "model_file_url":
                payload["model_file_name"] = os.path.splitext(filename)[0]  # 去掉扩展名
            elif field_name == "binary_file_url":
                payload["binary_file_name"] = os.path.splitext(filename)[0]  # 去掉扩展名
            
        except Exception as e:
            # 如果base64处理失败，移除该字段，避免将base64字符串保存到数据库
            payload.pop(field_name, None)
    
    async def _generate_compressed_model(self, model_data: bytes, model_uuid: str, upload_dir: str, file_ext: str, model_filename: str = None, payload: dict = None) -> None:
        """生成压缩的3D模型文件"""
        try:
            # 使用统一的转换函数处理各种格式，传入正确的文件扩展名
            compressed_data = convert_model_to_binary(model_data, file_ext)
            
            # 根据模型文件名生成fastdog文件名
            if model_filename:
                # 使用模型文件的名称（不含扩展名）+ .fastdog
                base_name = os.path.splitext(model_filename)[0]
                compressed_filename = f"{base_name}.fastdog"
            else:
                # 回退到默认名称
                compressed_filename = "binary.fastdog"
                base_name = "binary"
            
            compressed_file_path = os.path.join(upload_dir, compressed_filename)
            
            self._save_file_to_disk(compressed_file_path, compressed_data)
            
            # 压缩文件已保存，不更新binary_file_url字段
            # 压缩的fastdog文件仅用于内部处理，不保存到数据库字段中
            
        except Exception as e:
            # 记录错误但不中断主流程
            print(f"生成压缩模型文件失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    async def save_model(self, id: UUID | int | None, payload: dict) -> dict | None:
        """保存模型，处理文件上传和数据库操作"""
        try:
            # 获取或生成模型UUID
            model_uuid, existing_model = await self._get_or_generate_model_uuid(id)
            
            # 确保payload中不包含用户输入的uuid字段
            payload.pop('uuid', None)
            
            # 处理文件上传和移动
            await self._handle_file_operations(id, model_uuid, existing_model, payload)
            
            # 对于新建模型，将生成的UUID添加到payload中
            if not id:
                payload['uuid'] = model_uuid
            
            # 验证并清理文件URL字段
            self._validate_and_clean_file_urls(payload)
            
            # 保存模型到数据库
            result = await self._save_model_to_database(id, payload)
            
            return result
        except Exception as e:
            raise e
    
    async def _update_gltf_after_binary_upload(self, model_uuid: str, upload_dir: str, payload: dict) -> None:
        """在binary文件上传后更新对应的GLTF文件中的bin引用，并重新生成.fastdog文件"""
        try:
            # 检查是否有GLTF文件需要更新
            gltf_filename = f"{model_uuid}.gltf"
            gltf_path = os.path.join(upload_dir, gltf_filename)
            
            # 如果GLTF文件存在，更新其bin引用
            if os.path.exists(gltf_path):
                with open(gltf_path, 'rb') as f:
                    gltf_content = f.read()
                
                # 更新bin引用
                updated_content = self._update_gltf_bin_references(gltf_content, model_uuid)
                
                # 写回文件
                with open(gltf_path, 'wb') as f:
                    f.write(updated_content)
                
                print(f"已更新GLTF文件中的bin引用: {gltf_path}")
                
                # 重新生成.fastdog压缩文件，使用更新后的GLTF内容
                await self._generate_compressed_model(updated_content, model_uuid, upload_dir, ".gltf")
                print(f"已重新生成.fastdog压缩文件: {model_uuid}.fastdog")
                
        except Exception as e:
            print(f"更新GLTF文件bin引用或重新生成.fastdog文件失败: {str(e)}")
    
    async def _handle_file_operations(self, id: UUID | int | None, model_uuid: str, existing_model, payload: dict) -> None:
        """处理所有文件相关操作"""
        # 需要处理的文件字段
        file_fields = ["model_file_url", "binary_file_url", "thumbnail_url"]
        # 检查是否公开
        is_public = payload.get("is_public", False)
        upload_dir = self._get_upload_directory(is_public)
        
        # 如果是编辑现有模型且is_public状态发生变化，需要移动现有文件
        if existing_model and existing_model.is_public != is_public:
            await self._move_files_for_public_status_change(existing_model, model_uuid, is_public, file_fields, payload)
        
        # 处理文件名变更（编辑时重命名现有文件）
        if existing_model:
            await self._handle_filename_changes(existing_model, model_uuid, upload_dir, payload)
        
        # 处理文件上传
        binary_file_uploaded = False
        for field_name in file_fields:
            if field_name in payload and payload[field_name] is not None:
                file = payload[field_name]
                if isinstance(file, UploadFile):
                    await self._process_upload_file(file, field_name, model_uuid, upload_dir, is_public, payload)
                    # 记录是否上传了binary文件
                    if field_name == "binary_file_url":
                        binary_file_uploaded = True
                elif isinstance(file, str) and (is_valid_base64(file) or file.startswith('data:')):
                    if field_name == "thumbnail_url":
                        await self._process_base64_thumbnail(file, model_uuid, upload_dir, is_public, payload, field_name)
                    else:
                        await self._process_base64_model_file(file, field_name, model_uuid, upload_dir, is_public, payload)
                        # 记录是否上传了binary文件
                        if field_name == "binary_file_url":
                            binary_file_uploaded = True
        
        # 如果上传了binary文件，检查并更新对应的GLTF文件
        if binary_file_uploaded:
            await self._update_gltf_after_binary_upload(model_uuid, upload_dir, payload)
    
    def _validate_and_clean_file_urls(self, payload: dict) -> None:
        """验证文件URL字段长度，确保不超过数据库限制"""
        file_fields = ["model_file_url", "binary_file_url", "thumbnail_url"]
        for field_name in file_fields:
            if field_name in payload and payload[field_name]:
                url_value = payload[field_name]
                if isinstance(url_value, str) and len(url_value) > 2048:
                    payload.pop(field_name, None)
    
    async def _save_model_to_database(self, id: UUID | int | None, payload: dict) -> dict | None:
        """保存模型到数据库并验证结果"""
        # 保存模型
        result = await super().save_model(id, payload)
        
        # 验证保存结果
        if result:
            saved_model = await self.model.get(id=result["id"])
            
            # 如果文件URL和文件名没有正确保存，尝试直接更新
            file_fields = ["model_file_url", "binary_file_url", "thumbnail_url"]
            filename_fields = ["model_file_name", "binary_file_name", "thumbnail_file_name"]
            all_fields = file_fields + filename_fields
            
            update_needed = False
            for field_name in all_fields:
                if field_name in payload and payload[field_name] and getattr(saved_model, field_name) != payload[field_name]:
                    setattr(saved_model, field_name, payload[field_name])
                    update_needed = True
            
            if update_needed:
                await saved_model.save()
        
        return result
    
    async def _handle_filename_changes(self, existing_model, model_uuid: str, upload_dir: str, payload: dict) -> None:
        """处理编辑时的文件名变更，重命名磁盘上的现有文件"""
        try:
            uuid_dir = os.path.join(upload_dir, model_uuid)
            
            # 处理binary_file_name变更
            if "binary_file_name" in payload and payload["binary_file_name"]:
                new_binary_name = payload["binary_file_name"]
                
                # 检查是否有现有的binary文件URL
                if existing_model.binary_file_url:
                    # 从URL中提取当前文件名
                    current_file_path = self._get_file_path_from_url(existing_model.binary_file_url)
                    if current_file_path and os.path.exists(current_file_path):
                        current_filename = os.path.basename(current_file_path)
                        
                        # 如果文件名不同，进行重命名
                        if current_filename != new_binary_name:
                            # 确保新文件名有正确的扩展名
                            current_ext = os.path.splitext(current_filename)[1]
                            if not new_binary_name.endswith(current_ext):
                                new_binary_name += current_ext
                            
                            new_file_path = os.path.join(uuid_dir, new_binary_name)
                            
                            # 重命名文件
                            if not os.path.exists(new_file_path):  # 避免覆盖现有文件
                                os.rename(current_file_path, new_file_path)
                                print(f"重命名binary文件: {current_filename} -> {new_binary_name}")
                                
                                # 更新URL
                                is_public = payload.get("is_public", existing_model.is_public)
                                relative_path = f"{model_uuid}/{new_binary_name}"
                                payload["binary_file_url"] = self._generate_file_url(relative_path, is_public)
                                # 保存不带扩展名的文件名
                                payload["binary_file_name"] = os.path.splitext(new_binary_name)[0]
            
            # 处理model_file_name变更
            if "model_file_name" in payload and payload["model_file_name"]:
                new_model_name = payload["model_file_name"]
                
                # 检查是否有现有的model文件URL
                if existing_model.model_file_url:
                    # 从URL中提取当前文件名
                    current_file_path = self._get_file_path_from_url(existing_model.model_file_url)
                    if current_file_path and os.path.exists(current_file_path):
                        current_filename = os.path.basename(current_file_path)
                        
                        # 如果文件名不同，进行重命名
                        if current_filename != new_model_name:
                            # 确保新文件名有正确的扩展名
                            current_ext = os.path.splitext(current_filename)[1]
                            if not new_model_name.endswith(current_ext):
                                new_model_name += current_ext
                            
                            new_file_path = os.path.join(uuid_dir, new_model_name)
                            
                            # 重命名文件
                            if not os.path.exists(new_file_path):  # 避免覆盖现有文件
                                os.rename(current_file_path, new_file_path)
                                print(f"重命名model文件: {current_filename} -> {new_model_name}")
                                
                                # 更新URL
                                is_public = payload.get("is_public", existing_model.is_public)
                                relative_path = f"{model_uuid}/{new_model_name}"
                                payload["model_file_url"] = self._generate_file_url(relative_path, is_public)
                                # 保存不带扩展名的文件名
                                payload["model_file_name"] = os.path.splitext(new_model_name)[0]
            
            # 处理thumbnail_file_name变更
            if "thumbnail_file_name" in payload and payload["thumbnail_file_name"]:
                new_thumbnail_name = payload["thumbnail_file_name"]
                
                # 检查是否有现有的thumbnail文件URL
                if existing_model.thumbnail_url:
                    # 从URL中提取当前文件名
                    current_file_path = self._get_file_path_from_url(existing_model.thumbnail_url)
                    if current_file_path and os.path.exists(current_file_path):
                        current_filename = os.path.basename(current_file_path)
                        
                        # 如果文件名不同，进行重命名
                        if current_filename != new_thumbnail_name:
                            # 确保新文件名有正确的扩展名
                            current_ext = os.path.splitext(current_filename)[1]
                            if not new_thumbnail_name.endswith(current_ext):
                                new_thumbnail_name += current_ext
                            
                            new_file_path = os.path.join(uuid_dir, new_thumbnail_name)
                            
                            # 重命名文件
                            if not os.path.exists(new_file_path):  # 避免覆盖现有文件
                                os.rename(current_file_path, new_file_path)
                                print(f"重命名thumbnail文件: {current_filename} -> {new_thumbnail_name}")
                                
                                # 更新URL
                                is_public = payload.get("is_public", existing_model.is_public)
                                relative_path = f"{model_uuid}/{new_thumbnail_name}"
                                payload["thumbnail_url"] = self._generate_file_url(relative_path, is_public)
                                # 保存不带扩展名的文件名
                                payload["thumbnail_file_name"] = os.path.splitext(new_thumbnail_name)[0]
                                
        except Exception as e:
            print(f"处理文件名变更时出错: {str(e)}")
            # 不抛出异常，避免影响主流程
    
    async def delete_model(self, id: str) -> bool:
        """删除模型时同时删除相关文件"""
        try:
            # 获取模型信息
            model = await self.model.get(id=id)
            
            # 收集需要删除的文件路径
            files_to_delete = await self._collect_files_to_delete(model)
            
            # 删除文件
            self._delete_files_from_disk(files_to_delete)
            
            # 删除数据库记录
            return await super().delete_model(id)
            
        except Exception as e:
            raise e
    
    async def _collect_files_to_delete(self, model) -> list:
        """收集需要删除的文件路径 - 现在删除整个UUID文件夹"""
        folders_to_delete = []
        
        if model.uuid:
            # 检查public路径的UUID文件夹
            public_uuid_folder = os.path.join(settings.STATIC_DIR, settings.PUBLIC_MODEL_PATH.lstrip('/'), model.uuid)
            if os.path.exists(public_uuid_folder):
                folders_to_delete.append(("uuid_folder", public_uuid_folder))
            
            # 检查private路径的UUID文件夹
            private_uuid_folder = os.path.join(settings.STATIC_DIR, settings.PRIVATE_MODEL_PATH.lstrip('/'), model.uuid)
            if os.path.exists(private_uuid_folder):
                folders_to_delete.append(("uuid_folder", private_uuid_folder))
            
            # 兼容旧格式：检查是否有旧的单个文件需要删除
            old_files = self._collect_legacy_files(model)
            folders_to_delete.extend(old_files)
        
        return folders_to_delete
    
    def _collect_legacy_files(self, model) -> list:
        """收集旧格式的单个文件（兼容性）"""
        legacy_files = []
        
        # 收集模型相关文件
        legacy_files.extend(self._collect_model_files(model))
        
        # 收集fastdog文件
        legacy_files.extend(self._collect_fastdog_files(model))
        
        return legacy_files
    
    def _collect_model_files(self, model) -> list:
        """收集模型的主要文件路径"""
        files_to_delete = []
        file_fields = ["model_file_url", "binary_file_url", "thumbnail_url"]
        
        for field_name in file_fields:
            file_url = getattr(model, field_name, None)
            if file_url:
                file_path = self._get_file_path_from_url(file_url)
                if file_path and os.path.exists(file_path):
                    files_to_delete.append((field_name, file_path))
        
        return files_to_delete
    
    def _collect_fastdog_files(self, model) -> list:
        """收集fastdog压缩文件路径"""
        files_to_delete = []
        
        if model.uuid:
            fastdog_filename = f"{model.uuid}.fastdog"
            
            # 检查public路径
            public_fastdog_path = os.path.join(settings.STATIC_DIR, settings.PUBLIC_MODEL_PATH.lstrip('/'), fastdog_filename)
            if os.path.exists(public_fastdog_path):
                files_to_delete.append(("fastdog_file", public_fastdog_path))
            
            # 检查private路径
            private_fastdog_path = os.path.join(settings.STATIC_DIR, settings.PRIVATE_MODEL_PATH.lstrip('/'), fastdog_filename)
            if os.path.exists(private_fastdog_path):
                files_to_delete.append(("fastdog_file", private_fastdog_path))
        
        return files_to_delete
    
    def _get_file_path_from_url(self, file_url: str) -> str | None:
        """从文件URL获取实际文件路径"""
        # 处理public模型路径
        if file_url.startswith(f"/static{settings.PUBLIC_MODEL_PATH}"):
            filename = file_url.replace(f"/static{settings.PUBLIC_MODEL_PATH}", "")
            return os.path.join(settings.STATIC_DIR, settings.PUBLIC_MODEL_PATH.lstrip('/'), filename)
        
        # 处理private模型路径
        elif file_url.startswith(f"/static{settings.PRIVATE_MODEL_PATH}"):
            filename = file_url.replace(f"/static{settings.PRIVATE_MODEL_PATH}", "")
            return os.path.join(settings.STATIC_DIR, settings.PRIVATE_MODEL_PATH.lstrip('/'), filename)
        
        return None
    
    def _delete_files_from_disk(self, files_to_delete: list) -> None:
        """从磁盘删除文件和文件夹列表"""
        import shutil
        
        for item_type, path in files_to_delete:
            try:
                if item_type == "uuid_folder" and os.path.isdir(path):
                    # 删除整个UUID文件夹
                    shutil.rmtree(path)
                    print(f"已删除UUID文件夹: {path}")
                elif os.path.isfile(path):
                    # 删除单个文件（兼容旧格式）
                    os.remove(path)
                    print(f"已删除文件: {path}")
            except Exception as e:
                print(f"删除失败: {path}, 错误: {e}")
                # 文件删除失败不影响整体操作
                pass
