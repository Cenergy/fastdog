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

class AlbumCategory(models.Model):
    """相册分类模型"""
    name = fields.CharField(max_length=255, description="分类名称")
    description = fields.TextField(description="分类描述", null=True)
    sort_order = fields.IntField(default=0, description="排序顺序")
    is_active = fields.BooleanField(default=True, description="是否可用")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    
    class Meta:
        table = "album_categories"
        description = "相册分类表"
    
    def __str__(self):
        return self.name

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
    latitude = fields.FloatField(null=True, description="纬度")
    longitude = fields.FloatField(null=True, description="经度")
    taken_at = fields.DatetimeField(null=True, description="拍摄时间")
    location = fields.CharField(max_length=255, null=True, description="拍摄地点")
    
    # 关联字段
    photos: fields.ReverseRelation["Photo"]
    category = fields.ForeignKeyField('models.AlbumCategory', related_name='albums', description="所属分类", null=True)
    
    class Meta:
        table = "albums"
        description = "相册表"
    
    def __str__(self):
        return self.name
        
    async def save(self, *args, **kwargs):
        """重写save方法以从关联照片的EXIF数据读取经纬度"""
        # 先调用父类save方法确保模型已保存
        await super().save(*args, **kwargs)
        
        # 只有在模型有ID且需要经纬度时才查询关联照片
        if self.id and (not self.latitude or not self.longitude):
            try:
                # 遍历关联照片尝试获取GPS信息
                for photo in await self.photos.all():
                    # 从照片文件动态提取GPS信息
                    if photo.latitude and photo.longitude:
                        self.latitude = photo.latitude
                        self.longitude = photo.longitude
                        # 更新经纬度后需要再次保存
                        await super().save(update_fields=["latitude", "longitude"])
                        break
            except Exception as e:
                # 捕获并记录异常，但不中断保存流程
                print(f"从照片读取经纬度时出错: {e}")

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
    original_url = fields.JSONField(description="原始图片URL列表", null=False, default=[])
    thumbnail_url = fields.CharField(max_length=1024, description="缩略图URL", null=True)
    preview_url = fields.CharField(max_length=1024, description="预览图URL", null=True)
    
    # 元数据
    taken_at = fields.DatetimeField(description="拍摄时间", null=True)
    location = fields.CharField(max_length=255, description="拍摄地点", null=True)
    
    # 状态字段
    is_active = fields.BooleanField(default=True, description="是否可用")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    sort_order = fields.IntField(default=0, description="排序顺序")
    latitude = fields.FloatField(null=True, description="纬度")
    longitude = fields.FloatField(null=True, description="经度")
    
    # 关联字段
    album = fields.ForeignKeyField('models.Album', related_name='photos', description="所属相册")
    
    class Meta:
        table = "photos"
        description = "照片表"
    
    def __str__(self):
        return self.title or f"Photo {self.id}"
        
    async def to_dict(self, **kwargs):
        """自定义字典转换方法
        
        重写以确保original_url字段在序列化时使用thumbnail_url的值（如果存在）
        
        Returns:
            处理后的对象数据字典
        """
        # 先获取原始数据字典
        data = await super().to_dict(**kwargs)
        
        # 如果有缩略图但original_url为空或默认值，使用缩略图
        # if self.thumbnail_url and (
        #     not self.original_url or 
        #     self.original_url == [] or
        #     self.original_url == ["/static/default.png"] or 
        #     self.original_url == "/static/default.png"
        # ):
        #     data["original_url"] = [self.thumbnail_url]
            
        #     # 同时更新模型字段值
        #     self.original_url = [self.thumbnail_url]
        #     await self.save(update_fields=["original_url"])
            
        return data
        
    async def save(self, *args, **kwargs):
        """保存照片模型"""
        await super().save(*args, **kwargs)