from pydantic import BaseModel, Field, field_validator, field_serializer
from typing import Optional
from datetime import datetime
from decimal import Decimal
from apps.resources.schemas import Model3DInDB


class GeoCategoryBase(BaseModel):
    name: str = Field(..., description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    sort_order: int = Field(0, description="排序顺序")
    is_active: bool = Field(True, description="是否可用")


class GeoCategoryCreate(GeoCategoryBase):
    pass


class GeoCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    is_active: Optional[bool] = Field(None, description="是否可用")


class GeoCategoryInDB(GeoCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GeoModelBase(BaseModel):
    name: str = Field(..., description="地理模型名称")
    description: Optional[str] = Field(None, description="地理模型描述")
    longitude: Decimal = Field(..., description="经度 (-180 到 180)")
    latitude: Decimal = Field(..., description="纬度 (-90 到 90)")
    altitude: Optional[Decimal] = Field(None, description="海拔高度(米)")
    pitch: Optional[Decimal] = Field(None, description="俯仰角(度) -90到90")
    yaw: Optional[Decimal] = Field(None, description="偏航角(度) 0到360")
    roll: Optional[Decimal] = Field(None, description="翻滚角(度) -180到180")
    scale: Decimal = Field(1.0, description="统一缩放比例")
    scale_x: Decimal = Field(1.0, description="X轴缩放比例")
    scale_y: Decimal = Field(1.0, description="Y轴缩放比例")
    scale_z: Decimal = Field(1.0, description="Z轴缩放比例")
    is_visible: bool = Field(True, description="是否在地图上显示")
    is_interactive: bool = Field(True, description="是否可交互(点击、选择等)")
    layer_name: Optional[str] = Field(None, description="图层名称")
    z_index: int = Field(0, description="显示层级，数值越大越靠前")
    min_zoom_level: Optional[Decimal] = Field(None, description="最小可见缩放级别")
    max_zoom_level: Optional[Decimal] = Field(None, description="最大可见缩放级别")
    is_active: bool = Field(True, description="是否启用")

    @field_validator('longitude')
    def validate_longitude(cls, v):
        if v < -180 or v > 180:
            raise ValueError('经度必须在-180到180之间')
        return v

    @field_validator('latitude')
    def validate_latitude(cls, v):
        if v < -90 or v > 90:
            raise ValueError('纬度必须在-90到90之间')
        return v

    @field_validator('pitch')
    def validate_pitch(cls, v):
        if v is not None and (v < -90 or v > 90):
            raise ValueError('俯仰角必须在-90到90之间')
        return v

    @field_validator('yaw')
    def validate_yaw(cls, v):
        if v is not None and (v < 0 or v > 360):
            raise ValueError('偏航角必须在0到360之间')
        return v

    @field_validator('roll')
    def validate_roll(cls, v):
        if v is not None and (v < -180 or v > 180):
            raise ValueError('翻滚角必须在-180到180之间')
        return v


class GeoModelCreate(GeoModelBase):
    category_id: Optional[int] = Field(None, description="所属分类ID")
    model_3d_id: Optional[int] = Field(None, description="关联的3D模型ID")


class GeoModelUpdate(BaseModel):
    name: Optional[str] = Field(None, description="地理模型名称")
    description: Optional[str] = Field(None, description="地理模型描述")
    category_id: Optional[int] = Field(None, description="所属分类ID")
    model_3d_id: Optional[int] = Field(None, description="关联的3D模型ID")
    longitude: Optional[Decimal] = Field(None, description="经度 (-180 到 180)")
    latitude: Optional[Decimal] = Field(None, description="纬度 (-90 到 90)")
    altitude: Optional[Decimal] = Field(None, description="海拔高度(米)")
    pitch: Optional[Decimal] = Field(None, description="俯仰角(度) -90到90")
    yaw: Optional[Decimal] = Field(None, description="偏航角(度) 0到360")
    roll: Optional[Decimal] = Field(None, description="翻滚角(度) -180到180")
    scale: Optional[Decimal] = Field(None, description="统一缩放比例")
    scale_x: Optional[Decimal] = Field(None, description="X轴缩放比例")
    scale_y: Optional[Decimal] = Field(None, description="Y轴缩放比例")
    scale_z: Optional[Decimal] = Field(None, description="Z轴缩放比例")
    is_visible: Optional[bool] = Field(None, description="是否在地图上显示")
    is_interactive: Optional[bool] = Field(None, description="是否可交互(点击、选择等)")
    layer_name: Optional[str] = Field(None, description="图层名称")
    z_index: Optional[int] = Field(None, description="显示层级，数值越大越靠前")
    min_zoom_level: Optional[Decimal] = Field(None, description="最小可见缩放级别")
    max_zoom_level: Optional[Decimal] = Field(None, description="最大可见缩放级别")
    is_active: Optional[bool] = Field(None, description="是否启用")

    @field_validator('longitude')
    def validate_longitude(cls, v):
        if v is not None and (v < -180 or v > 180):
            raise ValueError('经度必须在-180到180之间')
        return v

    @field_validator('latitude')
    def validate_latitude(cls, v):
        if v is not None and (v < -90 or v > 90):
            raise ValueError('纬度必须在-90到90之间')
        return v

    @field_validator('pitch')
    def validate_pitch(cls, v):
        if v is not None and (v < -90 or v > 90):
            raise ValueError('俯仰角必须在-90到90之间')
        return v

    @field_validator('yaw')
    def validate_yaw(cls, v):
        if v is not None and (v < 0 or v > 360):
            raise ValueError('偏航角必须在0到360之间')
        return v

    @field_validator('roll')
    def validate_roll(cls, v):
        if v is not None and (v < -180 or v > 180):
            raise ValueError('翻滚角必须在-180到180之间')
        return v


class GeoModelInDB(GeoModelBase):
    id: int
    category_id: Optional[int] = None
    model_3d_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer('longitude', 'latitude', 'altitude', 'pitch', 'yaw', 'roll', 'scale', 'scale_x', 'scale_y', 'scale_z', 'min_zoom_level', 'max_zoom_level')
    def serialize_decimal(self, value: Optional[Decimal]) -> Optional[str]:
        if value is None:
            return None
        return f"{value:.6f}".rstrip('0').rstrip('.')

    class Config:
        from_attributes = True


# 地理查询相关的Schema
class GeoQueryParams(BaseModel):
    """地理查询参数"""
    min_longitude: Optional[Decimal] = Field(None, description="最小经度")
    max_longitude: Optional[Decimal] = Field(None, description="最大经度")
    min_latitude: Optional[Decimal] = Field(None, description="最小纬度")
    max_latitude: Optional[Decimal] = Field(None, description="最大纬度")
    layer_name: Optional[str] = Field(None, description="图层名称")
    is_visible: Optional[bool] = Field(None, description="是否可见")
    is_active: Optional[bool] = Field(None, description="是否启用")
    zoom_level: Optional[Decimal] = Field(None, description="当前缩放级别")


class GeoModelWithRelations(GeoModelInDB):
    """包含关联数据的地理模型"""
    model_3d: Optional[Model3DInDB] = None

    class Config:
        from_attributes = True