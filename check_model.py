#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查模型是否存在
"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import init_db
from apps.resources.models import Model3D

async def check_model():
    """检查模型是否存在"""
    
    # 初始化数据库连接
    await init_db()
    
    uuid = '643fde5910e04622b5581909c276cbf1'
    
    # 查找模型
    model = await Model3D.get_or_none(uuid=uuid)
    
    if model:
        print(f"✅ 模型找到:")
        print(f"   ID: {model.id}")
        print(f"   UUID: {model.uuid}")
        print(f"   名称: {model.name}")
        print(f"   模型文件URL: {model.model_file_url}")
        print(f"   二进制文件URL: {model.binary_file_url}")
        
        # 检查文件是否存在
        if model.model_file_url:
            if model.model_file_url.startswith('/static/'):
                from core.settings import settings
                relative_path = model.model_file_url[8:]  # 移除 '/static/'
                file_path = os.path.join(settings.STATIC_DIR, relative_path)
            else:
                file_path = model.model_file_url
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path) / 1024 / 1024
                print(f"   ✅ 文件存在: {file_path} ({file_size:.2f} MB)")
            else:
                print(f"   ❌ 文件不存在: {file_path}")
        else:
            print(f"   ❌ 模型文件URL为空")
    else:
        print(f"❌ 未找到UUID为 {uuid} 的模型")
        
        # 列出所有模型
        all_models = await Model3D.all()
        print(f"\n数据库中共有 {len(all_models)} 个模型:")
        for m in all_models:
            print(f"   - {m.uuid}: {m.name}")

if __name__ == "__main__":
    asyncio.run(check_model())