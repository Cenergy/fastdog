from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
import os
import shutil
import io
from datetime import datetime
import pandas as pd
import concurrent.futures
from utils.coordinate import convert_coordinates
from core.config import settings


def download_gps_template() -> StreamingResponse:
    """获取GPS坐标模板Excel文件，包含序号、名称、经度和纬度四列
    
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


async def convert_coordinates_from_excel(file: UploadFile, type: str) -> StreamingResponse:
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


async def convert_coordinate(request: Dict[str, Any]) -> Dict[str, Any]:
    """坐标转换API
    
    将单个坐标从一个坐标系统转换到另一个坐标系统
    
    Args:
        request: 包含lng, lat, from_sys, to_sys的字典
        
    Returns:
        Dict[str, Any]: 坐标转换响应
    """
    try:
        # 验证坐标系统
        allowed_systems = ["wgs84", "gcj02", "bd09"]
        from_sys = request["from_sys"].lower()
        to_sys = request["to_sys"].lower()
        
        if from_sys not in allowed_systems or to_sys not in allowed_systems:
            return {
                "success": False,
                "message": f"不支持的坐标系统，支持的系统有: {', '.join(allowed_systems)}",
                "data": None
            }
        
        # 获取经纬度
        lng = float(request["lng"])
        lat = float(request["lat"])
        
        # 进行坐标转换
        new_lng, new_lat = convert_coordinates(lng, lat, from_sys, to_sys)
        
        # 返回结果
        return {
            "success": True,
            "message": "坐标转换成功",
            "data": {
                "lng": new_lng,
                "lat": new_lat,
                "from_sys": from_sys,
                "to_sys": to_sys
            }
        }
    except ValueError as e:
        return {
            "success": False,
            "message": str(e),
            "data": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"坐标转换失败: {str(e)}",
            "data": None
        }