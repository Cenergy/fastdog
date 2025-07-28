#!/usr/bin/env python3
"""
简单的解码测试脚本，用于验证二进制格式
"""

import requests
import struct
import zlib
import json

def test_blob_decode():
    """测试blob端点的解码"""
    print("🎯 开始测试blob解码...")
    
    # 获取认证令牌
    auth_response = requests.post(
        'http://localhost:8000/api/v1/auth/login/access-token',
        data={'username': 'admin@example.com', 'password': 'admin123'}
    )
    
    if auth_response.status_code != 200:
        print(f"❌ 认证失败: {auth_response.status_code}")
        return
    
    token = auth_response.json()['access_token']
    print("✅ 认证成功")
    
    # 下载blob数据
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(
        'http://localhost:8000/api/v1/resources/models/merge.gltf/blob',
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ 下载失败: {response.status_code}")
        return
    
    data = response.content
    print(f"✅ 下载成功，数据大小: {len(data)} bytes")
    
    # 解析二进制格式
    try:
        # 验证魔数
        magic = data[:8].decode('utf-8')
        print(f"🔍 魔数: '{magic}'")
        
        if magic != 'FASTDOG1':
            print("❌ 无效的魔数")
            return
        
        # 读取版本
        version = struct.unpack('<I', data[8:12])[0]
        print(f"📋 版本: {version}")
        
        # 读取压缩数据长度
        compressed_length = struct.unpack('<I', data[12:16])[0]
        print(f"📋 压缩长度: {compressed_length}")
        
        # 提取压缩数据
        compressed_data = data[16:16+compressed_length]
        print(f"📋 压缩数据实际长度: {len(compressed_data)}")
        
        # 读取原始数据长度
        original_length = struct.unpack('<I', data[16+compressed_length:16+compressed_length+4])[0]
        print(f"📋 原始长度: {original_length}")
        
        # 验证总长度
        expected_total = 8 + 4 + 4 + compressed_length + 4
        print(f"📋 期望总长度: {expected_total}")
        print(f"📋 实际总长度: {len(data)}")
        
        if len(data) != expected_total:
            print(f"⚠️ 长度不匹配！")
        
        # 显示压缩数据的前几个字节（十六进制）
        hex_data = ' '.join(f'{b:02x}' for b in compressed_data[:16])
        print(f"🔍 压缩数据前16字节: {hex_data}")
        
        # 解压缩
        try:
            decompressed = zlib.decompress(compressed_data)
            print(f"✅ 解压缩成功，得到 {len(decompressed)} 字节")
            
            # 验证长度
            if len(decompressed) != original_length:
                print(f"⚠️ 解压缩长度不匹配！期望: {original_length}, 实际: {len(decompressed)}")
            
            # 解析JSON
            json_str = decompressed.decode('utf-8')
            json_data = json.loads(json_str)
            print(f"✅ JSON解析成功，包含 {len(json_data)} 个顶级字段")
            
        except Exception as e:
            print(f"❌ 解压缩失败: {e}")
            
    except Exception as e:
        print(f"❌ 解析失败: {e}")

if __name__ == '__main__':
    test_blob_decode()