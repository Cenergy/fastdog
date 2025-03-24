from tortoise.exceptions import DoesNotExist, IntegrityError
from fastapi import HTTPException
from typing import List, Optional, Dict, Any
import os
import pandas as pd
from datetime import datetime
from .models import Converter, ConverterType
from .schemas import ConverterCreate, ConverterUpdate
from core.config import settings

async def create_converter(converter: ConverterCreate) -> Converter:
    """创建转换器

    Args:
        converter: 转换器创建模型

    Returns:
        Converter: 创建的转换器对象
    """
    try:
        converter_obj = await Converter.create(**converter.dict(exclude_unset=True))
        return converter_obj
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"创建转换器失败: {str(e)}")

async def get_converter(converter_id: int) -> Optional[Converter]:
    """获取单个转换器

    Args:
        converter_id: 转换器ID

    Returns:
        Optional[Converter]: 转换器对象，如果未找到则返回None
    """
    try:
        return await Converter.get(id=converter_id)
    except DoesNotExist:
        return None

async def get_converters(
    skip: int = 0,
    limit: int = 10,
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Converter]:
    """获取转换器列表

    Args:
        skip: 跳过记录数
        limit: 返回记录数
        type: 转换器类型
        is_active: 是否可用
        search: 搜索关键词

    Returns:
        List[Converter]: 转换器列表
    """
    query = Converter.all()
    
    if type:
        query = query.filter(type=type)
    
    if is_active is not None:
        query = query.filter(is_active=is_active)
    
    if search:
        query = query.filter(
            Converter.name.contains(search) | 
            Converter.description.contains(search)
        )
    
    return await query.offset(skip).limit(limit).all()

async def count_converters(
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """获取转换器数量

    Args:
        type: 转换器类型
        is_active: 是否可用
        search: 搜索关键词

    Returns:
        int: 转换器数量
    """
    query = Converter.all()
    
    if type:
        query = query.filter(type=type)
    
    if is_active is not None:
        query = query.filter(is_active=is_active)
    
    if search:
        query = query.filter(
            Converter.name.contains(search) | 
            Converter.description.contains(search)
        )
    
    return await query.count()

async def update_converter(converter_id: int, converter: ConverterUpdate) -> Optional[Converter]:
    """更新转换器

    Args:
        converter_id: 转换器ID
        converter: 转换器更新模型

    Returns:
        Optional[Converter]: 更新后的转换器对象，如果未找到则返回None
    """
    converter_obj = await get_converter(converter_id)
    if not converter_obj:
        return None
    
    update_data = converter.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(converter_obj, field, value)
    
    await converter_obj.save()
    return converter_obj

async def delete_converter(converter_id: int) -> bool:
    """删除转换器

    Args:
        converter_id: 转换器ID

    Returns:
        bool: 是否删除成功
    """
    converter_obj = await get_converter(converter_id)
    if not converter_obj:
        return False
    
    await converter_obj.delete()
    return True

def generate_template_excel(converter_type: ConverterType) -> str:
    """生成转换模板Excel文件

    Args:
        converter_type: 转换器类型

    Returns:
        str: 生成的Excel文件路径
    """
    # 确保目录存在
    template_dir = os.path.join(settings.STATIC_DIR, 'templates', 'converters')
    os.makedirs(template_dir, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    file_name = f"{converter_type.value}_template_{timestamp}.xlsx"
    file_path = os.path.join(template_dir, file_name)
    
    # 创建DataFrame并保存为Excel
    if converter_type == ConverterType.COORDINATE:
        # 坐标转换模板
        df = pd.DataFrame({
            '原始X坐标': ['', '', ''],
            '原始Y坐标': ['', '', ''],
            '原始坐标系统': ['WGS84', 'GCJ02', 'BD09'],
            '目标坐标系统': ['WGS84', 'GCJ02', 'BD09']
        })
    elif converter_type == ConverterType.FORMAT:
        # 格式转换模板
        df = pd.DataFrame({
            '原始数据': ['', '', ''],
            '原始格式': ['JSON', 'XML', 'CSV'],
            '目标格式': ['JSON', 'XML', 'CSV']
        })
    elif converter_type == ConverterType.UNIT:
        # 单位转换模板
        df = pd.DataFrame({
            '原始数值': ['', '', ''],
            '原始单位': ['米', '千米', '英里'],
            '目标单位': ['米', '千米', '英里']
        })
    else:
        # 其他类型的通用模板
        df = pd.DataFrame({
            '原始数据': ['', '', ''],
            '转换类型': ['', '', '']
        })
    
    # 保存Excel文件
    df.to_excel(file_path, index=False)
    
    # 返回相对于静态目录的路径
    return os.path.join('templates', 'converters', file_name)

def generate_gps_template_excel() -> str:
    """生成GPS坐标模板Excel文件，包含序号、经度和纬度三列

    Returns:
        str: 生成的Excel文件路径
    """
    # 确保目录存在
    template_dir = os.path.join(settings.STATIC_DIR, 'templates', 'converters')
    os.makedirs(template_dir, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    file_name = f"gps_template_{timestamp}.xlsx"
    file_path = os.path.join(template_dir, file_name)
    
    # 创建DataFrame并保存为Excel
    df = pd.DataFrame({
        '序号': [1, 2, 3, 4, 5],
        '经度': [116.3912, 116.4074, 116.4551, '', ''],  # 示例：北京部分地点的经度
        '纬度': [39.9076, 39.9042, 39.9177, '', '']      # 示例：北京部分地点的纬度
    })
    
    # 保存Excel文件
    df.to_excel(file_path, index=False)
    
    # 返回相对于静态目录的路径
    return os.path.join('templates', 'converters', file_name)

async def process_conversion(file_path: str, converter_type: ConverterType) -> Dict[str, Any]:
    """处理转换请求

    Args:
        file_path: 上传的Excel文件路径
        converter_type: 转换器类型

    Returns:
        Dict[str, Any]: 转换结果
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(file_path)
        
        # 根据转换器类型进行不同的处理
        if converter_type == ConverterType.COORDINATE:
            # 坐标转换处理
            result_df = process_coordinate_conversion(df)
        elif converter_type == ConverterType.FORMAT:
            # 格式转换处理
            result_df = process_format_conversion(df)
        elif converter_type == ConverterType.UNIT:
            # 单位转换处理
            result_df = process_unit_conversion(df)
        else:
            # 其他类型的通用处理
            result_df = df.copy()
            result_df['转换结果'] = '未实现的转换类型'
        
        # 生成结果文件
        result_dir = os.path.join(settings.STATIC_DIR, 'results', 'converters')
        os.makedirs(result_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        result_file_name = f"{converter_type.value}_result_{timestamp}.xlsx"
        result_file_path = os.path.join(result_dir, result_file_name)
        
        # 保存结果Excel文件
        result_df.to_excel(result_file_path, index=False)
        
        # 返回结果
        return {
            'success': True,
            'message': '转换成功',
            'file_url': os.path.join('results', 'converters', result_file_name),
            'data': result_df.to_dict(orient='records')
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'转换失败: {str(e)}',
            'file_url': None,
            'data': None
        }

def process_coordinate_conversion(df: pd.DataFrame) -> pd.DataFrame:
    """处理坐标转换

    Args:
        df: 输入数据DataFrame

    Returns:
        pd.DataFrame: 转换后的DataFrame
    """
    from utils.coordinate import convert_coordinates
    
    result_df = df.copy()
    
    # 添加结果列
    result_df['转换后X坐标'] = ''
    result_df['转换后Y坐标'] = ''
    
    # 实现坐标转换逻辑
    for index, row in result_df.iterrows():
        try:
            # 获取原始坐标和坐标系统
            x = float(row['原始X坐标'])
            y = float(row['原始Y坐标'])
            from_sys = row['原始坐标系统']
            to_sys = row['目标坐标系统']
            
            # 如果源坐标系和目标坐标系相同，则不需要转换
            if from_sys == to_sys:
                result_df.at[index, '转换后X坐标'] = x
                result_df.at[index, '转换后Y坐标'] = y
                continue
            
            # 使用坐标转换工具进行转换
            try:
                # 调用坐标转换函数
                lng, lat = convert_coordinates(x, y, from_sys, to_sys)
                result_df.at[index, '转换后X坐标'] = lng
                result_df.at[index, '转换后Y坐标'] = lat
            except ValueError as e:
                # 处理不支持的转换类型错误
                result_df.at[index, '转换后X坐标'] = f'不支持的转换: {str(e)}'
                result_df.at[index, '转换后Y坐标'] = f'不支持的转换: {str(e)}'
        except Exception as e:
            result_df.at[index, '转换后X坐标'] = f'错误: {str(e)}'
            result_df.at[index, '转换后Y坐标'] = f'错误: {str(e)}'
    
    return result_df

def process_format_conversion(df: pd.DataFrame) -> pd.DataFrame:
    """处理格式转换

    Args:
        df: 输入数据DataFrame

    Returns:
        pd.DataFrame: 转换后的DataFrame
    """
    result_df = df.copy()
    
    # 添加结果列
    result_df['转换结果'] = ''
    
    # 实现格式转换逻辑
    for index, row in result_df.iterrows():
        try:
            # 获取原始数据和格式
            data = row['原始数据']
            from_format = row['原始格式']
            to_format = row['目标格式']
            
            # 如果源格式和目标格式相同，则不需要转换
            if from_format == to_format:
                result_df.at[index, '转换结果'] = data
                continue
            
            # 这里应该实现实际的格式转换逻辑
            # 示例转换（仅作演示）
            result_df.at[index, '转换结果'] = f'已将{data}从{from_format}转换为{to_format}'
        except Exception as e:
            result_df.at[index, '转换结果'] = f'错误: {str(e)}'
    
    return result_df

def process_unit_conversion(df: pd.DataFrame) -> pd.DataFrame:
    """处理单位转换

    Args:
        df: 输入数据DataFrame

    Returns:
        pd.DataFrame: 转换后的DataFrame
    """
    result_df = df.copy()
    
    # 添加结果列
    result_df['转换结果'] = ''
    
    # 实现单位转换逻辑
    for index, row in result_df.iterrows():
        try:
            # 获取原始数值和单位
            value = float(row['原始数值'])
            from_unit = row['原始单位']
            to_unit = row['目标单位']
            
            # 如果源单位和目标单位相同，则不需要转换
            if from_unit == to_unit:
                result_df.at[index, '转换结果'] = value
                continue
            
            # 这里实现单位转换逻辑
            # 长度单位转换示例
            # 转换为米作为中间单位
            value_in_meters = 0
            if from_unit == '米':
                value_in_meters = value
            elif from_unit == '千米':
                value_in_meters = value * 1000
            elif from_unit == '英里':
                value_in_meters = value * 1609.34
            
            # 从米转换为目标单位
            result = 0
            if to_unit == '米':
                result = value_in_meters
            elif to_unit == '千米':
                result = value_in_meters / 1000
            elif to_unit == '英里':
                result = value_in_meters / 1609.34
            
            result_df.at[index, '转换结果'] = round(result, 6)
        except Exception as e:
            result_df.at[index, '转换结果'] = f'错误: {str(e)}'
    
    return result_df