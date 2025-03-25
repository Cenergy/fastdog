from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from .models import ConverterType

class ConverterBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: ConverterType
    is_active: bool = True

class ConverterCreate(ConverterBase):
    template_path: Optional[str] = None

class ConverterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[ConverterType] = None
    template_path: Optional[str] = None
    is_active: Optional[bool] = None

class ConverterInDB(ConverterBase):
    id: int
    template_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConversionRequest(BaseModel):
    """转换请求模型"""
    converter_id: Optional[int] = None
    converter_type: Optional[ConverterType] = None
    data: Optional[Dict[str, Any]] = None
    
class ConversionResponse(BaseModel):
    """转换响应模型"""
    success: bool
    message: str
    file_url: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class CoordinateConversionRequest(BaseModel):
    """坐标转换请求模型"""
    lng: float = Field(..., description="经度")
    lat: float = Field(..., description="纬度")
    from_sys: str = Field(..., description="原始坐标系统，可选值：'wgs84', 'gcj02', 'bd09'")
    to_sys: str = Field(..., description="目标坐标系统，可选值：'wgs84', 'gcj02', 'bd09'")

class CoordinateConversionResponse(BaseModel):
    """坐标转换响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    data: Dict[str, Any] = Field(None, description="转换结果数据")