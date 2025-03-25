from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
import os
import shutil
import io
from datetime import datetime
import pandas as pd
from utils.coordinate import convert_coordinates

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

router = APIRouter()


@router.get("/templates/gps")
async def download_gps_template():
    """获取GPS坐标模板Excel文件，包含序号、经度和纬度三列
    
    Returns:
        StreamingResponse: Excel文件响应
    """
    try:
        # 直接创建DataFrame
        df = pd.DataFrame({
            '序号': [1, 2, 3, 4, 5],
            '名称': ['北京天安门', '不能删除这列', '可以不填这列', '', ''],
            '经度': [116.3912, 116.4074, 116.4551, '', ''],  # 示例：北京部分地点的经度
            '纬度': [39.9076, 39.9042, 39.9177, '', '']      # 示例：北京部分地点的纬度
        })
        
        # 创建一个BytesIO对象，用于在内存中保存Excel文件
        output = io.BytesIO()
        
        # 使用ExcelWriter确保正确写入Excel数据
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        # 将指针移到开头
        output.seek(0)
        
        # 直接返回内存中的Excel文件
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=gps_template.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate GPS template: {str(e)}")

@router.post("/coordinates/convert-from-excel")
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
    # 检查文件类型
    if not file.filename.endswith((".xlsx", ".xls")):
        return JSONResponse(
            status_code=400,
            content={"error": "仅支持 Excel 文件 (.xlsx/.xls)"}
        )
    
    # 检查文件大小
    content = await file.read()
    if len(content) > settings.CONVERTERS_HANDLE_MAX_EXCEL_SIZE:
        return JSONResponse(
            status_code=400,
            content={"error": f"文件大小超过限制，最大允许{settings.CONVERTERS_HANDLE_MAX_EXCEL_SIZE / (1024 * 1024):.0f}MB"}
        )
    
    # 重置文件指针，以便后续读取
    file.file.seek(0)

    try:
        # 读取 Excel 数据
        df = pd.read_excel(file.file, engine="openpyxl")
        
        # 检查必要的列是否存在
        required_columns = ["经度", "纬度"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return JSONResponse(
                status_code=400,
                content={"error": f"Excel文件缺少必要的列: {', '.join(missing_columns)}"}
            )
        
        # 验证转换类型
        allowed_types = [
            "wgs84_to_gcj02", "wgs84_to_bd09", 
            "gcj02_to_wgs84", "gcj02_to_bd09", 
            "bd09_to_wgs84", "bd09_to_gcj02"
        ]
        
        if type not in allowed_types:
            return JSONResponse(
                status_code=400,
                content={"error": f"不支持的转换类型: {type}，支持的类型有: {', '.join(allowed_types)}"}
            )
            
        # 解析转换类型
        from_sys, to_sys = type.split("_to_")
        
        # 创建结果DataFrame，复制原始数据
        result_df = df.copy()
        
        # 添加转换后的列
        result_df["转换后经度"] = ""
        result_df["转换后纬度"] = ""
        
        # 定义坐标转换处理函数
        def process_coordinate(row_data):
            try:
                # 获取经纬度值
                index, row = row_data
                lng = float(row["经度"])
                lat = float(row["纬度"])
                
                # 进行坐标转换
                new_lng, new_lat = convert_coordinates(lng, lat, from_sys, to_sys)
                
                return index, new_lng, new_lat, True
            except (ValueError, TypeError):
                # 如果转换失败，返回空值
                return index, None, None, False
        
        # 判断是否需要启用线程池
        row_count = len(df)
        if row_count > settings.CONVERTERS_THREAD_POOL_THRESHOLD:
            # 使用线程池并行处理
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=settings.CONVERTERS_THREAD_POOL_WORKERS) as executor:
                # 提交所有任务到线程池
                futures = [executor.submit(process_coordinate, (index, row)) for index, row in df.iterrows()]
                
                # 获取结果并更新DataFrame
                for future in concurrent.futures.as_completed(futures):
                    index, new_lng, new_lat, success = future.result()
                    if success:
                        result_df.at[index, "转换后经度"] = new_lng
                        result_df.at[index, "转换后纬度"] = new_lat
        else:
            # 数据量较小，顺序处理
            for index, row in df.iterrows():
                try:
                    # 获取经纬度值
                    lng = float(row["经度"])
                    lat = float(row["纬度"])
                    
                    # 进行坐标转换
                    new_lng, new_lat = convert_coordinates(lng, lat, from_sys, to_sys)
                    
                    # 更新结果DataFrame
                    result_df.at[index, "转换后经度"] = new_lng
                    result_df.at[index, "转换后纬度"] = new_lat
                except (ValueError, TypeError):
                    # 如果转换失败，保留空值
                    continue
        
        # 创建一个BytesIO对象，用于在内存中保存Excel文件
        output = io.BytesIO()
        
        # 将DataFrame写入Excel
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            result_df.to_excel(writer, index=False)
        
        # 设置文件指针到开始位置
        output.seek(0)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        result_filename = f"coordinate_convert_{timestamp}.xlsx"
        
        # 返回Excel文件
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={result_filename}"}
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"坐标转换失败: {str(e)}"}
        )

@router.get("/coordinates/convert", response_model=CoordinateConversionResponse)
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
    # 创建请求对象并调用POST方法处理
    request = CoordinateConversionRequest(
        lng=lng,
        lat=lat,
        from_sys=from_sys,
        to_sys=to_sys
    )
    return await convert_coordinate(request)