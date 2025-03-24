from tortoise import fields, models
from enum import Enum

class ConverterType(str, Enum):
    """转换器类型枚举"""
    COORDINATE = "coordinate"  # 坐标转换
    FORMAT = "format"          # 格式转换
    UNIT = "unit"              # 单位转换
    OTHER = "other"            # 其他类型
    
    # 坐标系统类型
    WGS84 = "wgs84"            # GPS坐标系
    GCJ02 = "gcj02"            # 国测局坐标系/火星坐标系
    BD09 = "bd09"              # 百度坐标系

class Converter(models.Model):
    """转换器模型"""
    name = fields.CharField(max_length=255, description="转换器名称")
    description = fields.TextField(description="转换器描述", null=True)
    type = fields.CharEnumField(ConverterType, description="转换器类型", default=ConverterType.OTHER)
    template_path = fields.CharField(max_length=1024, description="模板文件路径", null=True)
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    is_active = fields.BooleanField(default=True, description="是否可用")

    class Meta:
        table = "converters"
        description = "转换器表"

    def __str__(self):
        return self.name