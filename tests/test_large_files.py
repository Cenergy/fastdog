#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试大文件上传功能
"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import init_db
from apps.resources.models import Model3D
from apps.resources.admin import Model3DAdmin

async def test_large_file_upload():
    """测试大文件上传功能"""
    
    # 初始化数据库连接
    await init_db()
    
    # 检查文件是否存在
    test_files = [
        "f:/study/codes/fastdog/static/models/merge.gltf",
        "f:/study/codes/fastdog/static/models/SU7.glb"
    ]
    
    for file_path in test_files:
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            continue
            
        file_size = os.path.getsize(file_path) / 1024 / 1024
        print(f"\n测试文件: {os.path.basename(file_path)} ({file_size:.2f} MB)")
        
        # 读取文件内容
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # 创建临时文件来模拟上传
            import tempfile
            import base64
            from io import BytesIO
            
            # 将文件内容编码为base64（模拟前端上传）
            file_extension = os.path.splitext(file_path)[1]
            if file_extension == '.gltf':
                mime_type = 'application/json'
            elif file_extension == '.glb':
                mime_type = 'model/gltf-binary'
            else:
                mime_type = 'application/octet-stream'
            
            # 创建带MIME类型前缀的base64数据（模拟前端上传格式）
            base64_content = base64.b64encode(file_content).decode('utf-8')
            base64_with_prefix = f'data:{mime_type};base64,{base64_content}'
            
            # 模拟文件上传payload
            test_payload = {
                'name': f'Test Large Model - {os.path.basename(file_path)}',
                'description': f'测试大文件上传 - {file_size:.2f}MB',
                'model_file_url': base64_with_prefix
            }
            
            # 创建admin实例并测试保存
            admin = Model3DAdmin(Model3D)
            
            print(f"开始上传文件...")
            result = await admin.save_model(None, test_payload)
            
            if result:
                print(f"✅ 上传成功! ID: {result['id']}, UUID: {result['uuid']}")
                
                # 验证文件是否正确保存
                saved_model = await Model3D.get(id=result['id'])
                print(f"模型文件URL: {saved_model.model_file_url}")
                print(f"二进制文件URL: {saved_model.binary_file_url}")
                
                # 检查文件是否真的存在
                if saved_model.model_file_url:
                    file_path_on_disk = f"f:/study/codes/fastdog{saved_model.model_file_url}"
                    if os.path.exists(file_path_on_disk):
                        disk_size = os.path.getsize(file_path_on_disk) / 1024 / 1024
                        print(f"✅ 磁盘文件存在: {disk_size:.2f} MB")
                    else:
                        print(f"❌ 磁盘文件不存在: {file_path_on_disk}")
            else:
                print(f"❌ 上传失败")
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_large_file_upload())