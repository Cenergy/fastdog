from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
import os
import shutil
from datetime import datetime
from . import services

from .schemas import (
    ConverterCreate, 
    ConverterUpdate, 
    ConverterInDB, 
    ConversionRequest,
    ConversionResponse,
    CoordinateConversionRequest,
    CoordinateConversionResponse
)
from .models import ConverterType
from .crud import (
    create_converter,
    get_converter,
    get_converters,
    update_converter,
    delete_converter,
    count_converters,
    generate_template_excel,
    generate_gps_template_excel,
    process_conversion
)
from api.v1.deps import get_current_active_user
from apps.users.models import User
from core.config import settings

router = APIRouter(prefix="/coords")




@router.get("/templates/gps")
async def download_gps_template():
    """获取GPS坐标模板Excel文件，包含序号、名称、经度和纬度四列
    
    Returns:
        StreamingResponse: Excel文件响应
    """
    return services.download_gps_template()

@router.post("/convert_from_excel")
async def convert_coordinates_from_excel(
    file: UploadFile = File(...),
    type: str = Form("gcj02_to_wgs84")
):
    """识别上传的Excel文件，根据经度和纬度实现转换，并返回转换后的excel文件，根据类型实现不同的坐标转换
    
    Args:
        file: 上传的Excel文件
        type: 转换类型，可选值："wgs84_to_gcj02"、"gcj02_to_wgs84"、"wgs84_to_bd09"、"bd09_to_wgs84"、"gcj02_to_bd09"、"bd09_to_gcj02", 默认值为"gcj02_to_wgs84"
    
    Returns:
        StreamingResponse: Excel文件响应
    """
    return await services.convert_coordinates_from_excel(file, type)

@router.get("/convert", response_model=CoordinateConversionResponse)
async def convert_single_coordinate_get(
    lng: float = Query(..., description="经度"),
    lat: float = Query(..., description="纬度"),
    from_sys: str = Query(..., description="原始坐标系统，可选值：'wgs84', 'gcj02', 'bd09'"),
    to_sys: str = Query(..., description="目标坐标系统，可选值：'wgs84', 'gcj02', 'bd09'")
) -> CoordinateConversionResponse:
    """坐标转换API (GET方法)
    
    将单个坐标从一个坐标系统转换到另一个坐标系统
    
    Args:
        lng: 经度
        lat: 纬度
        from_sys: 原始坐标系统
        to_sys: 目标坐标系统
        
    Returns:
        CoordinateConversionResponse: 坐标转换响应
    """
    # 创建请求字典并调用服务处理
    request = {
        "lng": lng,
        "lat": lat,
        "from_sys": from_sys,
        "to_sys": to_sys
    }
    return await services.convert_coordinate(request)