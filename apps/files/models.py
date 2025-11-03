from tortoise import fields, models
from enum import Enum
from uuid import uuid4
import os
import mimetypes


class FileFormat(str, Enum):
    """文件格式枚举"""
    # 图片格式
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    HEIC = "heic"
    WEBP = "webp"
    BMP = "bmp"
    TIFF = "tiff"
    SVG = "svg"
    
    # 文档格式
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    XLS = "xls"
    XLSX = "xlsx"
    PPT = "ppt"
    PPTX = "pptx"
    TXT = "txt"
    RTF = "rtf"
    
    # 音频格式
    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    AAC = "aac"
    OGG = "ogg"
    M4A = "m4a"
    
    # 视频格式
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    WMV = "wmv"
    FLV = "flv"
    MKV = "mkv"
    WEBM = "webm"
    
    # 压缩格式
    ZIP = "zip"
    RAR = "rar"
    TAR = "tar"
    GZ = "gz"
    SEVEN_Z = "7z"
    
    # 其他格式
    OTHER = "other"


class FileCategory(models.Model):
    """文件分类模型"""
    name = fields.CharField(max_length=255, description="分类名称")
    description = fields.TextField(description="分类描述", null=True)
    sort_order = fields.IntField(default=0, description="排序顺序")
    is_active = fields.BooleanField(default=True, description="是否可用")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    
    # 关联字段
    files: fields.ReverseRelation["File"]
    
    class Meta:
        table = "file_categories"
        description = "文件分类表"
    
    def __str__(self):
        return self.name


class FileManager(models.Model):
    """文件模型"""
    title = fields.CharField(max_length=255, description="文件标题", null=True)
    description = fields.TextField(description="文件描述", null=True)
    # 文件URL
    original_url = fields.CharField(max_length=1024, description="原始文件URL", null=True)
    
    # 状态字段
    is_active = fields.BooleanField(default=True, description="是否可用")
    is_public = fields.BooleanField(default=True, description="是否公开")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    
    # 关联字段
    category = fields.ForeignKeyField('models.FileCategory', related_name='files', description="所属分类", null=True)
    
    class Meta:
        table = "files"
        description = "文件表"