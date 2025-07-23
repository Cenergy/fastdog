from tortoise import fields, models
from enum import Enum
import uuid

def generate_uuid_hex():
    """生成无连字符的UUID字符串"""
    return uuid.uuid4().hex

class ResourceType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    IMAGE = "image"
    MODEL_3D = "model_3d"
    OTHER = "other"

class ModelFormat(str, Enum):
    GLTF = "gltf"
    GLB = "glb"
    OBJ = "obj"
    FBX = "fbx"
    FASTDOG = "fastdog"



class Model3DCategory(models.Model):
    """3D模型分类"""
    
    name = fields.CharField(max_length=255, description="分类名称")
    description = fields.TextField(description="分类描述", null=True)
    sort_order = fields.IntField(default=0, description="排序顺序")
    is_active = fields.BooleanField(default=True, description="是否可用")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    
    class Meta:
        table = "model_3d_categories"
        description = "3D模型分类表"
    
    def __str__(self):
        return self.name

class Resource(models.Model):
    """资源模型"""
    name = fields.CharField(max_length=255, description="资源名称")
    description = fields.TextField(description="资源描述", null=True)
    type = fields.CharEnumField(ResourceType, description="资源类型", default=ResourceType.OTHER)
    url = fields.CharField(max_length=1024, description="资源链接")
    image_url = fields.CharField(max_length=5 * 1024 * 1024, description="资源图片链接", null=True)
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    is_active = fields.BooleanField(default=True, description="是否可用")

    class Meta:
        table = "resources"
        description = "资源表"

    def __str__(self):
        return self.name


class Model3D(models.Model):
    """3D模型管理"""
    
    # 基本信息
    uuid = fields.CharField(max_length=32, default=generate_uuid_hex, description="模型唯一标识符", unique=True)
    name = fields.CharField(max_length=255, description="模型名称")
    description = fields.TextField(description="模型描述", null=True)

    
    # 关联字段
    category = fields.ForeignKeyField('models.Model3DCategory', related_name='models', description="所属分类", null=True)
    
    # 模型文件
    model_file_url = fields.CharField(max_length=1024, description="主模型文件URL", null=True)
    binary_file_url = fields.CharField(max_length=1024, description="二进制文件URL(用于GLB+BIN)", null=True)
    thumbnail_url = fields.CharField(max_length=1024, description="预览图URL", null=True)
    
    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    
    # 状态标志
    is_active = fields.BooleanField(default=True, description="是否可用")
    is_public = fields.BooleanField(default=True, description="是否公开")
    
    class Meta:
        table = "models_3d"
        description = "3D模型表"
    
    def __str__(self):
        return self.name