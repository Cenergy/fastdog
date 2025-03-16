from tortoise import fields, models
from enum import Enum

class ResourceType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    IMAGE = "image"
    OTHER = "other"

class Resource(models.Model):
    """资源模型"""
    name = fields.CharField(max_length=255, description="资源名称")
    description = fields.TextField(description="资源描述", null=True)
    type = fields.CharEnumField(ResourceType, description="资源类型", default=ResourceType.OTHER)
    url = fields.CharField(max_length=1024, description="资源链接")
    image_url = fields.CharField(max_length=1024, description="资源图片链接", null=True)
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    is_active = fields.BooleanField(default=True, description="是否可用")

    class Meta:
        table = "resources"
        description = "资源表"

    def __str__(self):
        return self.name