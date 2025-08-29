from tortoise import fields, models
from enum import Enum


class GeoCategory(models.Model):
    """分类Geo"""
    name = fields.CharField(max_length=255, description="分类名称")
    description = fields.TextField(description="分类描述", null=True)
    sort_order = fields.IntField(default=0, description="排序顺序")
    is_active = fields.BooleanField(default=True, description="是否可用")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    
    class Meta:
        table = "geo_categories"
        description = "地理分类"
    
    def __str__(self):
        return self.name

class GeoModel(models.Model):
    """地理位置3D模型管理
    
    用于管理在地图上显示的3D模型的地理位置信息，
    多个地理位置可以共用同一个3D模型。
    """
    
    # 基本信息
    id = fields.IntField(pk=True, description="主键ID")
    name = fields.CharField(max_length=255, description="地理模型名称")
    description = fields.TextField(description="地理模型描述", null=True)
    category = fields.ForeignKeyField('models.GeoCategory', related_name='geo_models', description="所属分类", null=True)
    
    # 关联的3D模型
    model_3d = fields.ForeignKeyField('models.Model3D', related_name='geo_instances', description="关联的3D模型",null=True)
    
    # 地理位置信息
    longitude = fields.DecimalField(max_digits=10, decimal_places=6, description="经度 (-180 到 180)", validators=[lambda x: -180 <= x <= 180])
    latitude = fields.DecimalField(max_digits=10, decimal_places=6, description="纬度 (-90 到 90)", validators=[lambda x: -90 <= x <= 90])
    altitude = fields.DecimalField(max_digits=10, decimal_places=3, description="海拔高度(米)", default=0,required=False, null=True)
    
    # 模型姿态信息
    pitch = fields.DecimalField(max_digits=6, decimal_places=3, description="俯仰角(度) -90到90", null=True)
    yaw = fields.DecimalField(max_digits=6, decimal_places=3, description="偏航角(度) 0到360", null=True)
    roll = fields.DecimalField(max_digits=6, decimal_places=3, description="翻滚角(度) -180到180", null=True)
    scale = fields.DecimalField(max_digits=6, decimal_places=3, description="统一缩放比例", default=1.0)
    
    # 缩放信息
    scale_x = fields.DecimalField(max_digits=6, decimal_places=3, description="X轴缩放比例", default=1.0)
    scale_y = fields.DecimalField(max_digits=6, decimal_places=3, description="Y轴缩放比例", default=1.0)
    scale_z = fields.DecimalField(max_digits=6, decimal_places=3, description="Z轴缩放比例", default=1.0)
    
    # 显示控制
    is_visible = fields.BooleanField(default=True, description="是否在地图上显示")
    is_interactive = fields.BooleanField(default=True, description="是否可交互(点击、选择等)")
    
    # 层级控制
    layer_name = fields.CharField(max_length=100, description="图层名称", null=True)
    z_index = fields.IntField(default=0, description="显示层级，数值越大越靠前",required=False, null=True)
    
    # 可见性控制
    min_zoom_level = fields.DecimalField(max_digits=4, decimal_places=2, description="最小可见缩放级别", null=True)
    max_zoom_level = fields.DecimalField(max_digits=4, decimal_places=2, description="最大可见缩放级别", null=True)
    
    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    
    # 状态标志
    is_active = fields.BooleanField(default=True, description="是否启用")
    
    class Meta:
        table = "geo_models"
        description = "地理位置3D模型表"
        indexes = [
            # 地理位置查询索引
            ("longitude", "latitude"),
            # 图层和可见性查询索引
            ("layer_name", "is_visible", "is_active"),
            # 缩放级别查询索引
            ("min_zoom_level", "max_zoom_level"),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.latitude}, {self.longitude})"