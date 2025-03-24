from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from .models import ConverterType
from utils.coordinate import convert_coordinates

router = APIRouter()

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

class BatchCoordinateConversionRequest(BaseModel):
    """批量坐标转换请求模型"""
    coordinates: List[Dict[str, float]] = Field(..., description="坐标列表，每个坐标包含lng和lat字段")
    from_sys: str = Field(..., description="原始坐标系统，可选值：'wgs84', 'gcj02', 'bd09'")
    to_sys: str = Field(..., description="目标坐标系统，可选值：'wgs84', 'gcj02', 'bd09'")

@router.post("/coordinate/convert", response_model=CoordinateConversionResponse)
async def convert_coordinate(
    request: CoordinateConversionRequest
) -> CoordinateConversionResponse:
    """坐标转换API
    
    将单个坐标从一个坐标系统转换到另一个坐标系统
    
    Args:
        request: 坐标转换请求
        
    Returns:
        CoordinateConversionResponse: 坐标转换响应
    """
    try:
        # 调用坐标转换函数
        lng, lat = convert_coordinates(
            request.lng, 
            request.lat, 
            request.from_sys, 
            request.to_sys
        )
        
        # 返回转换结果
        return CoordinateConversionResponse(
            success=True,
            message="转换成功",
            data={
                "lng": lng,
                "lat": lat,
                "from_sys": request.from_sys,
                "to_sys": request.to_sys
            }
        )
    except ValueError as e:
        # 处理不支持的转换类型错误
        return CoordinateConversionResponse(
            success=False,
            message=str(e),
            data=None
        )
    except Exception as e:
        # 处理其他错误
        raise HTTPException(status_code=500, detail=f"坐标转换失败: {str(e)}")

@router.post("/coordinate/batch-convert", response_model=CoordinateConversionResponse)
async def batch_convert_coordinate(
    request: BatchCoordinateConversionRequest
) -> CoordinateConversionResponse:
    """批量坐标转换API
    
    将多个坐标从一个坐标系统批量转换到另一个坐标系统
    
    Args:
        request: 批量坐标转换请求
        
    Returns:
        CoordinateConversionResponse: 坐标转换响应
    """
    try:
        # 批量转换坐标
        result = []
        for coord in request.coordinates:
            lng, lat = convert_coordinates(
                coord["lng"], 
                coord["lat"], 
                request.from_sys, 
                request.to_sys
            )
            result.append({
                "original_lng": coord["lng"],
                "original_lat": coord["lat"],
                "converted_lng": lng,
                "converted_lat": lat
            })
        
        # 返回转换结果
        return CoordinateConversionResponse(
            success=True,
            message=f"成功转换{len(result)}个坐标",
            data={
                "coordinates": result,
                "from_sys": request.from_sys,
                "to_sys": request.to_sys,
                "count": len(result)
            }
        )
    except ValueError as e:
        # 处理不支持的转换类型错误
        return CoordinateConversionResponse(
            success=False,
            message=str(e),
            data=None
        )
    except Exception as e:
        # 处理其他错误
        raise HTTPException(status_code=500, detail=f"批量坐标转换失败: {str(e)}")

@router.get("/coordinate/convert", response_model=CoordinateConversionResponse)
async def convert_coordinate_get(
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
    # 创建请求对象并调用POST方法处理
    request = CoordinateConversionRequest(
        lng=lng,
        lat=lat,
        from_sys=from_sys,
        to_sys=to_sys
    )
    return await convert_coordinate(request)