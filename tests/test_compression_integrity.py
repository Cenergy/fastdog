#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试压缩数据的完整性
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.resources.admin import convert_model_to_binary, convert_glb_to_fastdog_binary
import struct
import zlib
import json

def test_compression_integrity():
    """测试压缩数据的完整性"""
    
    glb_file_path = "f:/study/codes/fastdog/static/models/SU7.glb"
    
    if not os.path.exists(glb_file_path):
        print(f"GLB文件不存在: {glb_file_path}")
        return
    
    print("=== 压缩数据完整性测试 ===")
    
    try:
        # 读取原始GLB文件
        with open(glb_file_path, 'rb') as f:
            original_glb_data = f.read()
        
        print(f"原始GLB文件大小: {len(original_glb_data)} bytes")
        
        # 压缩GLB文件
        compressed_data = convert_model_to_binary(original_glb_data, ".glb")
        print(f"压缩后数据大小: {len(compressed_data)} bytes")
        
        # 解析压缩数据的文件头
        if len(compressed_data) >= 12:
            magic = compressed_data[:8]
            version = struct.unpack('<I', compressed_data[8:12])[0]
            
            print(f"压缩文件魔数: {magic}")
            print(f"压缩文件版本: {version}")
            
            if magic == b'FASTDOG1':
                print("✅ 压缩文件格式正确")
                
                if version == 2:  # GLB格式
                    print("✅ 版本号正确 (GLB格式)")
                    
                    # 读取压缩数据长度
                    compressed_length = struct.unpack('<I', compressed_data[12:16])[0]
                    print(f"压缩数据长度: {compressed_length} bytes")
                    
                    # 提取压缩数据
                    compressed_glb = compressed_data[16:16+compressed_length]
                    
                    # 解压缩数据
                    try:
                        decompressed_glb = zlib.decompress(compressed_glb)
                        print(f"解压缩后数据大小: {len(decompressed_glb)} bytes")
                        
                        # 验证数据完整性
                        if decompressed_glb == original_glb_data:
                            print("✅ 数据完整性验证通过！压缩和解压缩过程无损")
                            
                            # 计算压缩效率
                            compression_ratio = len(compressed_glb) / len(original_glb_data)
                            space_saved = (1 - compression_ratio) * 100
                            
                            print(f"实际压缩比: {compression_ratio:.3f}")
                            print(f"节省空间: {space_saved:.1f}%")
                            
                            # 验证原始数据长度字段
                            if len(compressed_data) >= 20:
                                original_length = struct.unpack('<I', compressed_data[16+compressed_length:20+compressed_length])[0]
                                print(f"记录的原始长度: {original_length} bytes")
                                
                                if original_length == len(original_glb_data):
                                    print("✅ 原始长度记录正确")
                                else:
                                    print(f"❌ 原始长度记录错误: 期望 {len(original_glb_data)}, 实际 {original_length}")
                        else:
                            print("❌ 数据完整性验证失败！解压缩后的数据与原始数据不匹配")
                            print(f"原始数据前32字节: {original_glb_data[:32]}")
                            print(f"解压缩数据前32字节: {decompressed_glb[:32]}")
                            
                    except zlib.error as e:
                        print(f"❌ 解压缩失败: {e}")
                        
                else:
                    print(f"❌ 版本号错误: 期望 2, 实际 {version}")
            else:
                print(f"❌ 压缩文件魔数错误: {magic}")
        else:
            print("❌ 压缩数据太小，无法包含完整的文件头")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_gltf_compression_integrity():
    """测试GLTF压缩数据的完整性"""
    
    gltf_file_path = "f:/study/codes/fastdog/static/models/merge.gltf"
    
    if not os.path.exists(gltf_file_path):
        print(f"GLTF文件不存在: {gltf_file_path}")
        return
    
    print("\n=== GLTF压缩数据完整性测试 ===")
    
    try:
        # 读取原始GLTF文件
        with open(gltf_file_path, 'rb') as f:
            original_gltf_data = f.read()
        
        print(f"原始GLTF文件大小: {len(original_gltf_data)} bytes")
        
        # 解析原始JSON
        original_json = json.loads(original_gltf_data.decode('utf-8'))
        print(f"原始JSON包含键: {list(original_json.keys())}")
        
        # 压缩GLTF文件
        compressed_data = convert_model_to_binary(original_gltf_data, ".gltf")
        print(f"压缩后数据大小: {len(compressed_data)} bytes")
        
        # 解析压缩数据
        if len(compressed_data) >= 12:
            magic = compressed_data[:8]
            version = struct.unpack('<I', compressed_data[8:12])[0]
            
            if magic == b'FASTDOG1' and version == 1:  # GLTF格式
                print("✅ GLTF压缩文件格式正确")
                
                # 读取压缩JSON数据长度
                compressed_length = struct.unpack('<I', compressed_data[12:16])[0]
                compressed_json = compressed_data[16:16+compressed_length]
                
                # 解压缩JSON数据
                try:
                    decompressed_json_bytes = zlib.decompress(compressed_json)
                    decompressed_json = json.loads(decompressed_json_bytes.decode('utf-8'))
                    
                    print(f"解压缩JSON包含键: {list(decompressed_json.keys())}")
                    
                    # 验证JSON数据完整性
                    if decompressed_json == original_json:
                        print("✅ GLTF JSON数据完整性验证通过！")
                        
                        compression_ratio = len(compressed_json) / len(original_gltf_data)
                        space_saved = (1 - compression_ratio) * 100
                        
                        print(f"JSON压缩比: {compression_ratio:.3f}")
                        print(f"节省空间: {space_saved:.1f}%")
                    else:
                        print("❌ GLTF JSON数据完整性验证失败！")
                        
                except Exception as e:
                    print(f"❌ GLTF解压缩失败: {e}")
            else:
                print(f"❌ GLTF压缩文件格式错误: magic={magic}, version={version}")
                
    except Exception as e:
        print(f"❌ GLTF测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_compression_integrity()
    test_gltf_compression_integrity()