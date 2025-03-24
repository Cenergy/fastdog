from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
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