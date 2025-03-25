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
    ConversionResponse
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
from .api import router as coordinate_api_router

router = APIRouter()

# 包含坐标转换API路由
router.include_router(coordinate_api_router, prefix="/api", tags=["coordinate"])

@router.post("/", response_model=ConverterInDB)
async def create_converter_api(
    converter: ConverterCreate,
    current_user: User = Depends(get_current_active_user)
) -> ConverterInDB:
    """创建转换器"""
    return await create_converter(converter)

@router.get("/{converter_id}", response_model=ConverterInDB)
async def get_converter_api(converter_id: int) -> ConverterInDB:
    """获取单个转换器"""
    converter = await get_converter(converter_id)
    if not converter:
        raise HTTPException(status_code=404, detail="Converter not found")
    return converter

@router.get("/", response_model=List[ConverterInDB])
async def get_converters_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[ConverterInDB]:
    """获取转换器列表"""
    return await get_converters(skip, limit, type, is_active, search)

@router.put("/{converter_id}", response_model=ConverterInDB)
async def update_converter_api(
    converter_id: int,
    converter: ConverterUpdate,
    current_user: User = Depends(get_current_active_user)
) -> ConverterInDB:
    """更新转换器"""
    updated_converter = await update_converter(converter_id, converter)
    if not updated_converter:
        raise HTTPException(status_code=404, detail="Converter not found")
    return updated_converter

@router.delete("/{converter_id}", response_model=bool)
async def delete_converter_api(
    converter_id: int,
    current_user: User = Depends(get_current_active_user)
) -> bool:
    """删除转换器"""
    deleted = await delete_converter(converter_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Converter not found")
    return True

@router.get("/templates/{converter_type}")
async def get_template_api(converter_type: ConverterType):
    """获取转换模板Excel文件
    
    Args:
        converter_type: 转换器类型
    
    Returns:
        FileResponse: Excel文件响应
    """
    try:
        # 生成模板文件
        template_path = generate_template_excel(converter_type)
        
        # 构建完整文件路径
        file_path = os.path.join(settings.STATIC_DIR, template_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Template file not found")
        
        # 返回文件响应
        return FileResponse(
            path=file_path,
            filename=f"{converter_type.value}_template.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate template: {str(e)}")

@router.post("/convert/")
async def convert_data_api(
    converter_type: ConverterType = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
) -> ConversionResponse:
    """处理转换请求
    
    Args:
        converter_type: 转换器类型
        file: 上传的Excel文件
    
    Returns:
        ConversionResponse: 转换响应
    """
    try:
        # 确保上传目录存在
        upload_dir = os.path.join(settings.STATIC_DIR, 'uploads', 'converters')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        file_name = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, file_name)
        
        # 保存上传的文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 处理转换
        result = await process_conversion(file_path, converter_type)
        
        # 如果转换成功且有结果文件，返回文件下载链接
        if result['success'] and result['file_url']:
            result_file_path = os.path.join(settings.STATIC_DIR, result['file_url'])
            return ConversionResponse(
                success=True,
                message="转换成功",
                file_url=f"/static/{result['file_url']}",
                data=result['data']
            )
        else:
            return ConversionResponse(
                success=False,
                message=result['message'],
                data=None
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")

@router.get("/download/{file_path:path}")
async def download_result_api(file_path: str):
    """下载转换结果文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        FileResponse: 文件响应
    """
    try:
        # 构建完整文件路径
        full_path = os.path.join(settings.STATIC_DIR, 'results', 'converters', file_path)
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Result file not found")
        
        # 返回文件响应
        return FileResponse(
            path=full_path,
            filename=os.path.basename(file_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

@router.get("/template/gps")
async def get_gps_template_api():
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

@router.post("/upload-coordinate-excel/")
async def upload_coordinate_excel(
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
        
        # 解析转换类型
        from_sys, to_sys = type.split("_to_")
        
        # 创建结果DataFrame，复制原始数据
        result_df = df.copy()
        
        # 添加转换后的列
        result_df["转换后经度"] = ""
        result_df["转换后纬度"] = ""
        
        # 遍历每一行进行坐标转换
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