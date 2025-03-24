"""坐标系统转换工具

提供WGS84、GCJ02和BD09三种坐标系统之间的相互转换功能。

WGS84：GPS坐标系，国际通用坐标系
GCJ02：国测局坐标系，火星坐标系，中国国内使用的经过加密的坐标系
BD09：百度坐标系，在GCJ02基础上再次加密
"""

import math
from typing import Tuple, Dict, Any

# 地球半径
EARTH_RADIUS = 6378245.0
# 偏心率
EE = 0.00669342162296594323

def _transform_lat(x: float, y: float) -> float:
    """GCJ02坐标转换算法中纬度转换"""
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def _transform_lng(x: float, y: float) -> float:
    """GCJ02坐标转换算法中经度转换"""
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

def _out_of_china(lng: float, lat: float) -> bool:
    """判断坐标是否在中国境外"""
    return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)

def wgs84_to_gcj02(lng: float, lat: float) -> Tuple[float, float]:
    """WGS84坐标系转GCJ02坐标系
    
    Args:
        lng: WGS84坐标系下的经度
        lat: WGS84坐标系下的纬度
        
    Returns:
        Tuple[float, float]: GCJ02坐标系下的经度和纬度
    """
    if _out_of_china(lng, lat):
        return lng, lat
        
    d_lat = _transform_lat(lng - 105.0, lat - 35.0)
    d_lng = _transform_lng(lng - 105.0, lat - 35.0)
    
    rad_lat = lat / 180.0 * math.pi
    magic = math.sin(rad_lat)
    magic = 1 - EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    
    d_lat = (d_lat * 180.0) / ((EARTH_RADIUS * (1 - EE)) / (magic * sqrt_magic) * math.pi)
    d_lng = (d_lng * 180.0) / (EARTH_RADIUS / sqrt_magic * math.cos(rad_lat) * math.pi)
    
    return lng + d_lng, lat + d_lat

def gcj02_to_wgs84(lng: float, lat: float) -> Tuple[float, float]:
    """GCJ02坐标系转WGS84坐标系
    
    Args:
        lng: GCJ02坐标系下的经度
        lat: GCJ02坐标系下的纬度
        
    Returns:
        Tuple[float, float]: WGS84坐标系下的经度和纬度
    """
    if _out_of_china(lng, lat):
        return lng, lat
        
    d_lat = _transform_lat(lng - 105.0, lat - 35.0)
    d_lng = _transform_lng(lng - 105.0, lat - 35.0)
    
    rad_lat = lat / 180.0 * math.pi
    magic = math.sin(rad_lat)
    magic = 1 - EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    
    d_lat = (d_lat * 180.0) / ((EARTH_RADIUS * (1 - EE)) / (magic * sqrt_magic) * math.pi)
    d_lng = (d_lng * 180.0) / (EARTH_RADIUS / sqrt_magic * math.cos(rad_lat) * math.pi)
    
    return lng - d_lng, lat - d_lat

def gcj02_to_bd09(lng: float, lat: float) -> Tuple[float, float]:
    """GCJ02坐标系转BD09坐标系
    
    Args:
        lng: GCJ02坐标系下的经度
        lat: GCJ02坐标系下的纬度
        
    Returns:
        Tuple[float, float]: BD09坐标系下的经度和纬度
    """
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * math.pi * 3000.0 / 180.0)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * math.pi * 3000.0 / 180.0)
    
    bd_lng = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    
    return bd_lng, bd_lat

def bd09_to_gcj02(lng: float, lat: float) -> Tuple[float, float]:
    """BD09坐标系转GCJ02坐标系
    
    Args:
        lng: BD09坐标系下的经度
        lat: BD09坐标系下的纬度
        
    Returns:
        Tuple[float, float]: GCJ02坐标系下的经度和纬度
    """
    x = lng - 0.0065
    y = lat - 0.006
    
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * math.pi * 3000.0 / 180.0)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * math.pi * 3000.0 / 180.0)
    
    gcj_lng = z * math.cos(theta)
    gcj_lat = z * math.sin(theta)
    
    return gcj_lng, gcj_lat

def wgs84_to_bd09(lng: float, lat: float) -> Tuple[float, float]:
    """WGS84坐标系转BD09坐标系
    
    Args:
        lng: WGS84坐标系下的经度
        lat: WGS84坐标系下的纬度
        
    Returns:
        Tuple[float, float]: BD09坐标系下的经度和纬度
    """
    gcj_lng, gcj_lat = wgs84_to_gcj02(lng, lat)
    return gcj02_to_bd09(gcj_lng, gcj_lat)

def bd09_to_wgs84(lng: float, lat: float) -> Tuple[float, float]:
    """BD09坐标系转WGS84坐标系
    
    Args:
        lng: BD09坐标系下的经度
        lat: BD09坐标系下的纬度
        
    Returns:
        Tuple[float, float]: WGS84坐标系下的经度和纬度
    """
    gcj_lng, gcj_lat = bd09_to_gcj02(lng, lat)
    return gcj02_to_wgs84(gcj_lng, gcj_lat)

def convert_coordinates(lng: float, lat: float, from_sys: str, to_sys: str) -> Tuple[float, float]:
    """坐标系统转换函数
    
    Args:
        lng: 原始经度
        lat: 原始纬度
        from_sys: 原始坐标系统，可选值：'wgs84', 'gcj02', 'bd09'
        to_sys: 目标坐标系统，可选值：'wgs84', 'gcj02', 'bd09'
        
    Returns:
        Tuple[float, float]: 转换后的经度和纬度
    """
    # 统一转为小写
    from_sys = from_sys.lower()
    to_sys = to_sys.lower()
    
    # 如果源坐标系和目标坐标系相同，则不需要转换
    if from_sys == to_sys:
        return lng, lat
    
    # WGS84 -> GCJ02
    if from_sys == 'wgs84' and to_sys == 'gcj02':
        return wgs84_to_gcj02(lng, lat)
    
    # WGS84 -> BD09
    if from_sys == 'wgs84' and to_sys == 'bd09':
        return wgs84_to_bd09(lng, lat)
    
    # GCJ02 -> WGS84
    if from_sys == 'gcj02' and to_sys == 'wgs84':
        return gcj02_to_wgs84(lng, lat)
    
    # GCJ02 -> BD09
    if from_sys == 'gcj02' and to_sys == 'bd09':
        return gcj02_to_bd09(lng, lat)
    
    # BD09 -> WGS84
    if from_sys == 'bd09' and to_sys == 'wgs84':
        return bd09_to_wgs84(lng, lat)
    
    # BD09 -> GCJ02
    if from_sys == 'bd09' and to_sys == 'gcj02':
        return bd09_to_gcj02(lng, lat)
    
    # 不支持的转换
    raise ValueError(f"不支持从{from_sys}转换到{to_sys}的坐标系统转换")