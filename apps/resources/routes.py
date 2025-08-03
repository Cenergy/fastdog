from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from .schemas import (
    ResourceCreate, ResourceUpdate, ResourceInDB,
    Model3DCategoryCreate, Model3DCategoryUpdate, Model3DCategoryInDB,
    Model3DCreate, Model3DUpdate, Model3DInDB
)
from .crud import (
    create_resource,
    get_resource,
    get_resources,
    update_resource,
    delete_resource,
    count_resources,
    # Model3DCategory CRUD
    create_model3d_category,
    get_model3d_category,
    get_model3d_categories,
    update_model3d_category,
    delete_model3d_category,
    count_model3d_categories,
    # Model3D CRUD
    create_model3d,
    get_model3d,
    get_model3d_by_uuid,
    get_model3ds,
    update_model3d,
    delete_model3d,
    count_model3ds
)
from api.v1.deps import get_current_active_user
from apps.users.models import User
from fastapi.responses import StreamingResponse
import os
import json
import struct
import zlib
import io
import hashlib
from functools import lru_cache
from fastapi import Header, HTTPException
from core.settings import settings
from datetime import datetime

router = APIRouter()

@router.post("/", response_model=ResourceInDB)
async def create_resource_api(
    resource: ResourceCreate,
    current_user: User = Depends(get_current_active_user)
) -> ResourceInDB:
    """创建资源"""
    return await create_resource(resource)

@router.get("/{resource_id}", response_model=ResourceInDB)
async def get_resource_api(resource_id: int) -> ResourceInDB:
    """获取单个资源"""
    resource = await get_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource

@router.get("/", response_model=List[ResourceInDB],operation_id="new_endpoint")
async def get_resources_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[ResourceInDB]:
    """获取资源列表"""
    return await get_resources(skip, limit, type, is_active, search)

@router.put("/{resource_id}", response_model=ResourceInDB)
async def update_resource_api(
    resource_id: int,
    resource: ResourceUpdate,
    current_user: User = Depends(get_current_active_user)
) -> ResourceInDB:
    """更新资源"""
    updated_resource = await update_resource(resource_id, resource)
    if not updated_resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return updated_resource

@router.delete("/{resource_id}")
async def delete_resource_api(
    resource_id: int,
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """删除资源"""
    success = await delete_resource(resource_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resource not found")
    return {"message": "Resource deleted successfully"}

@router.get("/count/total", response_model=int)
async def count_resources_api(
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """获取资源总数"""
    return await count_resources(type, is_active, search)


@router.get("/models/{filename}")
async def stream_model(filename: str, range: str = Header(None)):
    file_path = os.path.join(settings.STATIC_DIR, "models", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    file_size = os.path.getsize(file_path)
    
    if range:
        start, end = range.replace("bytes=", "").split("-")
        start = int(start)
        end = min(file_size - 1, int(end) if end else file_size - 1)
    else:
        start, end = 0, file_size - 1
    
    def file_iterator():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk_size = min(1024 * 1024, remaining)  # 1MB chunks
                data = f.read(chunk_size)
                if not data:
                    break
                remaining -= len(data)
                yield data
    
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
    }
    return StreamingResponse(file_iterator(), status_code=206 if range else 200, headers=headers, media_type="application/octet-stream")


@router.get("/models/{filename}/info")
async def get_model_info(filename: str):
    """获取模型基本信息"""
    file_path = os.path.join(settings.STATIC_DIR, "models", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    
    file_size = os.path.getsize(file_path)
    
    # 解析GLTF文件获取基本信息
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            gltf_data = json.load(f)
        
        # 提取模型信息
        info = {
            "name": filename,
            "size": file_size,
            "format": "gltf",
            "nodes": len(gltf_data.get("nodes", [])),
            "meshes": len(gltf_data.get("meshes", [])),
            "materials": len(gltf_data.get("materials", [])),
            "textures": len(gltf_data.get("textures", [])),
            "animations": len(gltf_data.get("animations", [])),
            "scenes": len(gltf_data.get("scenes", [])),
            "compression_available": True,
            "estimated_compressed_size": file_size // 3  # 估算压缩后大小
        }
        
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse model file: {str(e)}")


def get_cache_key(file_path: str) -> str:
    """基于文件路径和修改时间生成缓存键"""
    try:
        stat = os.stat(file_path)
        cache_data = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    except OSError:
        # 如果文件不存在或无法访问，返回基于路径的哈希
        return hashlib.md5(file_path.encode()).hexdigest()


# 缓存统计
cache_stats = {
    "hits": 0,
    "misses": 0,
    "total_requests": 0
}

@lru_cache(maxsize=50)
def cached_convert_gltf_to_binary(file_path: str, cache_key: str) -> bytes:
    """带缓存的模型文件到二进制转换函数"""
    try:
        # 获取文件扩展名
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 读取文件数据
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # 导入转换函数
        from .admin import convert_model_to_binary
        
        # 使用admin中的转换函数处理不同格式
        return convert_model_to_binary(file_data, file_ext)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load or convert model file: {str(e)}")


def convert_gltf_to_binary(gltf_data: dict) -> bytes:
    """将GLTF数据转换为自定义二进制格式"""
    # 创建二进制数据结构
    binary_data = io.BytesIO()
    
    # 写入文件头 (8字节魔数 + 4字节版本)
    binary_data.write(b'FASTDOG1')  # 魔数
    binary_data.write(struct.pack('<I', 1))  # 版本号
    
    # 序列化JSON数据
    json_str = json.dumps(gltf_data, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    
    # 压缩JSON数据 (优化压缩级别以平衡速度和压缩比)
    compressed_json = zlib.compress(json_bytes, level=6)
    
    # 写入压缩数据长度和数据
    binary_data.write(struct.pack('<I', len(compressed_json)))
    binary_data.write(compressed_json)
    
    # 写入原始数据长度（用于验证）
    binary_data.write(struct.pack('<I', len(json_bytes)))
    
    return binary_data.getvalue()


@router.get("/models/{filename}/binary")
async def stream_model_binary(filename: str, range: str = Header(None)):
    """以自定义二进制格式流式传输模型"""
    file_path = os.path.join(settings.STATIC_DIR, "models", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    
    try:
        # 生成缓存键
        cache_key = get_cache_key(file_path)
        
        # 更新缓存统计
        cache_stats["total_requests"] += 1
        cache_info = cached_convert_gltf_to_binary.cache_info()
        
        # 使用缓存转换GLTF文件
        binary_data = cached_convert_gltf_to_binary(file_path, cache_key)
        file_size = len(binary_data)
        
        # 检查是否为缓存命中
        new_cache_info = cached_convert_gltf_to_binary.cache_info()
        if new_cache_info.hits > cache_info.hits:
            cache_stats["hits"] += 1
            cache_status = "HIT"
        else:
            cache_stats["misses"] += 1
            cache_status = "MISS"
        
        # 处理Range请求
        if range:
            start, end = range.replace("bytes=", "").split("-")
            start = int(start)
            end = min(file_size - 1, int(end) if end else file_size - 1)
        else:
            start, end = 0, file_size - 1
        
        def binary_iterator():
            data_stream = io.BytesIO(binary_data)
            data_stream.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                # 优化块大小以减少系统调用
                chunk_size = min(4 * 1024 * 1024, remaining)  # 4MB chunks
                chunk = data_stream.read(chunk_size)
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
        
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "X-Original-Size": str(os.path.getsize(file_path)),
            "X-Compression-Ratio": f"{file_size / os.path.getsize(file_path):.2f}",
            "X-Format": "fastdog-binary-v1",
            "X-Cache-Key": cache_key,
            "X-Cache-Status": cache_status,
            "X-Cache-Hit-Rate": f"{(cache_stats['hits'] / cache_stats['total_requests'] * 100):.1f}%" if cache_stats['total_requests'] > 0 else "0.0%",
            "Cache-Control": "public, max-age=3600",  # 1小时缓存
            "ETag": f'"{cache_key}"'
        }
        
        return StreamingResponse(
            binary_iterator(), 
            status_code=206 if range else 200, 
            headers=headers, 
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert model: {str(e)}")


@router.get("/models/{filename}/manifest")
async def get_model_manifest(filename: str):
    """获取模型清单信息，用于分片加载"""
    file_path = os.path.join(settings.STATIC_DIR, "models", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            gltf_data = json.load(f)
        
        # 分析模型结构，生成分片清单
        manifest = {
            "model_name": filename,
            "total_size": os.path.getsize(file_path),
            "format": "gltf",
            "parts": [],
            "lod_levels": ["preview", "low", "medium", "high"],
            "compression": {
                "available": True,
                "format": "fastdog-binary-v1",
                "estimated_ratio": 0.3
            },
            "streaming": {
                "chunk_size": 1024 * 1024,  # 1MB
                "supports_range": True
            }
        }
        
        # 分析网格数据
        if "meshes" in gltf_data:
            for i, mesh in enumerate(gltf_data["meshes"]):
                part = {
                    "name": f"mesh_{i}",
                    "type": "geometry",
                    "primitives": len(mesh.get("primitives", [])),
                    "estimated_size": len(json.dumps(mesh)) * 0.8  # 估算大小
                }
                manifest["parts"].append(part)
        
        # 分析材质数据
        if "materials" in gltf_data:
            for i, material in enumerate(gltf_data["materials"]):
                part = {
                    "name": f"material_{i}",
                    "type": "material",
                    "estimated_size": len(json.dumps(material))
                }
                manifest["parts"].append(part)
        
        # 分析纹理数据
        if "textures" in gltf_data:
            for i, texture in enumerate(gltf_data["textures"]):
                part = {
                    "name": f"texture_{i}",
                    "type": "texture",
                    "estimated_size": 1024 * 1024  # 假设1MB纹理
                }
                manifest["parts"].append(part)
        
        return manifest
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate manifest: {str(e)}")


@router.get("/models/{filename}/blob")
async def get_model_blob(filename: str, current_user: User = Depends(get_current_active_user)):
    """以blob格式返回模型二进制数据"""
    file_path = os.path.join(settings.STATIC_DIR, "models", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    
    try:
        # 获取文件扩展名
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 读取文件数据
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # 导入转换函数
        from .admin import convert_model_to_binary
        
        # 转换为二进制格式
        binary_data = convert_model_to_binary(file_data, file_ext)
        
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Disposition": f"attachment; filename={filename}.bin",
            "X-Original-Size": str(os.path.getsize(file_path)),
            "X-Compressed-Size": str(len(binary_data)),
            "X-Compression-Ratio": f"{len(binary_data) / os.path.getsize(file_path):.2f}",
            "X-Format": "fastdog-binary-v1",
            "Access-Control-Expose-Headers": "X-Original-Size,X-Compressed-Size,X-Compression-Ratio,X-Format"
        }
        
        return StreamingResponse(
            io.BytesIO(binary_data),
            media_type="application/octet-stream",
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert model to blob: {str(e)}")


@router.get("/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息"""
    cache_info = cached_convert_gltf_to_binary.cache_info()
    return {
        "cache_info": {
            "hits": cache_info.hits,
            "misses": cache_info.misses,
            "maxsize": cache_info.maxsize,
            "currsize": cache_info.currsize
        },
        "custom_stats": cache_stats,
        "hit_rate": f"{(cache_stats['hits'] / cache_stats['total_requests'] * 100):.2f}%" if cache_stats['total_requests'] > 0 else "0.00%",
        "memory_efficiency": f"{(cache_info.currsize / cache_info.maxsize * 100):.1f}%" if cache_info.maxsize > 0 else "0.0%"
    }


@router.post("/cache/clear")
async def clear_cache(current_user: User = Depends(get_current_active_user)):
    """清理缓存（需要认证）"""
    # 清理LRU缓存
    cached_convert_gltf_to_binary.cache_clear()
    
    # 重置统计
    cache_stats["hits"] = 0
    cache_stats["misses"] = 0
    cache_stats["total_requests"] = 0
    
    return {
        "message": "Cache cleared successfully",
        "cleared_by": current_user.username if hasattr(current_user, 'username') else "unknown"
    }


# Model3DCategory API endpoints
@router.post("/categories/", response_model=Model3DCategoryInDB)
async def create_model3d_category_api(
    category: Model3DCategoryCreate,
    current_user: User = Depends(get_current_active_user)
) -> Model3DCategoryInDB:
    """创建3D模型分类"""
    db_category = await create_model3d_category(category)
    return Model3DCategoryInDB.model_validate(db_category)

@router.get("/categories/{category_id}", response_model=Model3DCategoryInDB)
async def get_model3d_category_api(category_id: int) -> Model3DCategoryInDB:
    """根据ID获取3D模型分类"""
    category = await get_model3d_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return Model3DCategoryInDB.model_validate(category)

@router.get("/categories/", response_model=List[Model3DCategoryInDB])
async def get_model3d_categories_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Model3DCategoryInDB]:
    """获取3D模型分类列表"""
    categories = await get_model3d_categories(
        skip=skip, limit=limit, is_active=is_active, search=search
    )
    return [Model3DCategoryInDB.model_validate(category) for category in categories]

@router.put("/categories/{category_id}", response_model=Model3DCategoryInDB)
async def update_model3d_category_api(
    category_id: int,
    category: Model3DCategoryUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Model3DCategoryInDB:
    """更新3D模型分类"""
    db_category = await update_model3d_category(category_id, category)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return Model3DCategoryInDB.model_validate(db_category)

@router.delete("/categories/{category_id}")
async def delete_model3d_category_api(
    category_id: int,
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """删除3D模型分类"""
    success = await delete_model3d_category(category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted successfully"}

@router.get("/categories/count/total", response_model=int)
async def count_model3d_categories_api(
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """获取3D模型分类总数"""
    return await count_model3d_categories(is_active=is_active, search=search)


# Model3D API endpoints
@router.post("/models3d/", response_model=Model3DInDB)
async def create_model3d_api(
    model: Model3DCreate,
    current_user: User = Depends(get_current_active_user)
) -> Model3DInDB:
    """创建3D模型"""
    db_model = await create_model3d(model)
    return Model3DInDB.model_validate(db_model)

@router.get("/models3d/{model_id}", response_model=Model3DInDB)
async def get_model3d_api(model_id: int) -> Model3DInDB:
    """根据ID获取3D模型"""
    model = await get_model3d(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return Model3DInDB.model_validate(model)

@router.get("/models3d/uuid/{uuid}", response_model=Model3DInDB)
async def get_model3d_by_uuid_api(uuid: str) -> Model3DInDB:
    """根据UUID获取3D模型"""
    model = await get_model3d_by_uuid(uuid)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return Model3DInDB.model_validate(model)

@router.get("/models3d/", response_model=List[Model3DInDB])
async def get_model3ds_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_public: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Model3DInDB]:
    """获取3D模型列表"""
    models = await get_model3ds(
        skip=skip, limit=limit, category_id=category_id,
        is_active=is_active, is_public=is_public, search=search
    )
    return [Model3DInDB.model_validate(model) for model in models]

@router.put("/models3d/{model_id}", response_model=Model3DInDB)
async def update_model3d_api(
    model_id: int,
    model: Model3DUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Model3DInDB:
    """更新3D模型"""
    db_model = await update_model3d(model_id, model)
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    return Model3DInDB.model_validate(db_model)

@router.delete("/models3d/{model_id}")
async def delete_model3d_api(
    model_id: int,
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """删除3D模型"""
    success = await delete_model3d(model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model deleted successfully"}

@router.get("/models3d/count/total", response_model=int)
async def count_model3ds_api(
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_public: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """获取3D模型总数"""
    return await count_model3ds(
        category_id=category_id, is_active=is_active,
        is_public=is_public, search=search
    )


@router.get("/models/uuid/{uuid}")
async def stream_model_by_uuid(uuid: str, range: str = Header(None)):
    """根据模型UUID以自定义二进制格式流式传输模型"""
    # 首先从数据库获取模型信息
    model = await get_model3d_by_uuid(uuid)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # 检查模型是否有文件URL
    if not model.model_file_url:
        raise HTTPException(status_code=404, detail="Model file not found")
    
    # 从URL中提取文件名并构建完整文件路径
    filename = os.path.basename(model.model_file_url)
    
    # 构建完整的文件路径
    if model.model_file_url.startswith('/static/'):
        # 移除开头的 '/static/' 并构建完整路径
        relative_path = model.model_file_url[8:]  # 移除 '/static/'
        file_path = os.path.join(settings.STATIC_DIR, relative_path)
    else:
        # 兼容旧格式，直接使用文件名
        file_path = os.path.join(settings.STATIC_DIR, "models", filename)
    

    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Model file not found on disk: {file_path}")
    
    try:
        # 检查是否存在对应的 .fastdog 文件
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        fastdog_filename = f"{base_name}.fastdog"
        # 基于原文件路径构建 .fastdog 文件路径
        fastdog_path = os.path.join(os.path.dirname(file_path), fastdog_filename)
        

        
        if os.path.exists(fastdog_path):
            # 如果 .fastdog 文件存在，直接读取
            with open(fastdog_path, 'rb') as f:
                binary_data = f.read()
            file_size = len(binary_data)
            cache_key = get_cache_key(fastdog_path)
            cache_status = "FASTDOG_DIRECT"
            
            # 更新缓存统计
            cache_stats["total_requests"] += 1
            cache_stats["hits"] += 1  # 视为缓存命中，因为避免了转换
        else:
            # 如果 .fastdog 文件不存在，使用原有的转换流程
            # 生成缓存键
            cache_key = get_cache_key(file_path)
            
            # 更新缓存统计
            cache_stats["total_requests"] += 1
            cache_info = cached_convert_gltf_to_binary.cache_info()
            
            # 使用缓存转换GLTF文件
            binary_data = cached_convert_gltf_to_binary(file_path, cache_key)
            file_size = len(binary_data)
            
            # 检查是否为缓存命中
            new_cache_info = cached_convert_gltf_to_binary.cache_info()
            if new_cache_info.hits > cache_info.hits:
                cache_stats["hits"] += 1
                cache_status = "HIT"
            else:
                cache_stats["misses"] += 1
                cache_status = "MISS"
        
        # 处理Range请求
        if range:
            start, end = range.replace("bytes=", "").split("-")
            start = int(start)
            end = min(file_size - 1, int(end) if end else file_size - 1)
        else:
            start, end = 0, file_size - 1
        
        def binary_iterator():
            data_stream = io.BytesIO(binary_data)
            data_stream.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                # 优化块大小以减少系统调用
                chunk_size = min(4 * 1024 * 1024, remaining)  # 4MB chunks
                chunk = data_stream.read(chunk_size)
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
        
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "X-Original-Size": str(os.path.getsize(file_path)),
            "X-Compression-Ratio": f"{file_size / os.path.getsize(file_path):.2f}",
            "X-Format": "fastdog-binary-v1",
            "X-Cache-Key": cache_key,
            "X-Cache-Status": cache_status,
            "X-Cache-Hit-Rate": f"{(cache_stats['hits'] / cache_stats['total_requests'] * 100):.1f}%" if cache_stats['total_requests'] > 0 else "0.0%",
            "Cache-Control": "public, max-age=3600",  # 1小时缓存
            "ETag": f'"{cache_key}"',
            "X-Model-ID": str(model.id),
            "X-Model-Name": model.name,
            "X-Model-UUID": model.uuid
        }
        
        return StreamingResponse(
            binary_iterator(), 
            status_code=206 if range else 200, 
            headers=headers, 
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert model: {str(e)}")

