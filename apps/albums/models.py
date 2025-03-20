from tortoise import fields, models
from enum import Enum
from uuid import uuid4
import os

class PhotoFormat(str, Enum):
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    HEIC = "heic"
    WEBP = "webp"
    OTHER = "other"

class Album(models.Model):
    """相册模型"""
    name = fields.CharField(max_length=255, description="相册名称")
    description = fields.TextField(description="相册描述", null=True)
    cover_image = fields.CharField(max_length=1024, description="封面图片URL", null=True)
    is_public = fields.BooleanField(default=True, description="是否公开")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    is_active = fields.BooleanField(default=True, description="是否可用")
    sort_order = fields.IntField(default=0, description="排序顺序")
    
    # 关联字段
    photos: fields.ReverseRelation["Photo"]
    
    class Meta:
        table = "albums"
        description = "相册表"
    
    def __str__(self):
        return self.name

class Photo(models.Model):
    """照片模型"""
    title = fields.CharField(max_length=255, description="照片标题", null=True)
    description = fields.TextField(description="照片描述", null=True)
    original_filename = fields.CharField(max_length=255, description="原始文件名", null=True)
    file_format = fields.CharEnumField(PhotoFormat, description="文件格式", default=PhotoFormat.OTHER)
    file_size = fields.IntField(description="文件大小(字节)", null=True)
    width = fields.IntField(description="图片宽度", null=True)
    height = fields.IntField(description="图片高度", null=True)
    
    # 图片路径
    original_url = fields.CharField(max_length=1024, description="原始图片URL", null=False, default="/static/default.png")
    thumbnail_url = fields.CharField(max_length=1024, description="缩略图URL", null=True)
    preview_url = fields.CharField(max_length=1024, description="预览图URL", null=True)
    
    # 元数据
    taken_at = fields.DatetimeField(description="拍摄时间", null=True)
    location = fields.CharField(max_length=255, description="拍摄地点", null=True)
    exif_data = fields.JSONField(description="EXIF数据", null=True, default={})
    
    # 状态字段
    is_active = fields.BooleanField(default=True, description="是否可用")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    sort_order = fields.IntField(default=0, description="排序顺序")
    
    # 关联字段
    album = fields.ForeignKeyField('models.Album', related_name='photos', description="所属相册")
    
    class Meta:
        table = "photos"
        description = "照片表"
    
    def __str__(self):
        return self.title or f"Photo {self.id}"