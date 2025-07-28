#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试GLB格式文件压缩功能
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.resources.admin import convert_model_to_binary, parse_glb_to_gltf, convert_glb_to_fastdog_binary
import json

def test_glb_compression():
    """测试GLB文件压缩功能"""
    
    # 测试文件路径
    glb_file_path = "f:/study/codes/fastdog/static/models/SU7.glb"
    gltf_file_path = "f:/study/codes/fastdog/static/models/merge.gltf"
    
    print("=== GLB/GLTF 压缩功能测试 ===")
    
    # 测试GLB文件
    if os.path.exists(glb_file_path):
        print(f"\n📁 测试GLB文件: {os.path.basename(glb_file_path)}")
        
        try:
            # 读取GLB文件
            with open(glb_file_path, 'rb') as f:
                glb_data = f.read()
            
            original_size = len(glb_data)
            print(f"   原始大小: {original_size / 1024 / 1024:.2f} MB ({original_size} bytes)")
            
            # 测试GLB解析
            print("   🔍 解析GLB文件...")
            gltf_json = parse_glb_to_gltf(glb_data)
            print(f"   ✅ GLB解析成功，包含 {len(gltf_json)} 个顶级属性")
            
            # 测试压缩
            print("   🗜️ 压缩GLB文件...")
            compressed_data = convert_model_to_binary(glb_data, ".glb")
            compressed_size = len(compressed_data)
            
            compression_ratio = compressed_size / original_size
            space_saved = (1 - compression_ratio) * 100
            
            print(f"   ✅ GLB压缩成功!")
            print(f"   压缩后大小: {compressed_size / 1024 / 1024:.2f} MB ({compressed_size} bytes)")
            print(f"   压缩比: {compression_ratio:.3f}")
            print(f"   节省空间: {space_saved:.1f}%")
            
            # 验证压缩数据的文件头
            if compressed_data[:8] == b'FASTDOG1':
                print("   ✅ 压缩数据格式正确 (FASTDOG1 格式)")
            else:
                print("   ❌ 压缩数据格式错误")
                
        except Exception as e:
            print(f"   ❌ GLB处理失败: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print(f"   ❌ GLB文件不存在: {glb_file_path}")
    
    # 测试GLTF文件作为对比
    if os.path.exists(gltf_file_path):
        print(f"\n📁 测试GLTF文件: {os.path.basename(gltf_file_path)}")
        
        try:
            # 读取GLTF文件
            with open(gltf_file_path, 'rb') as f:
                gltf_data = f.read()
            
            original_size = len(gltf_data)
            print(f"   原始大小: {original_size / 1024 / 1024:.2f} MB ({original_size} bytes)")
            
            # 测试压缩
            print("   🗜️ 压缩GLTF文件...")
            compressed_data = convert_model_to_binary(gltf_data, ".gltf")
            compressed_size = len(compressed_data)
            
            compression_ratio = compressed_size / original_size
            space_saved = (1 - compression_ratio) * 100
            
            print(f"   ✅ GLTF压缩成功!")
            print(f"   压缩后大小: {compressed_size / 1024 / 1024:.2f} MB ({compressed_size} bytes)")
            print(f"   压缩比: {compression_ratio:.3f}")
            print(f"   节省空间: {space_saved:.1f}%")
            
        except Exception as e:
            print(f"   ❌ GLTF处理失败: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print(f"   ❌ GLTF文件不存在: {gltf_file_path}")
    
    print("\n=== 测试完成 ===")

def test_glb_parsing_details():
    """详细测试GLB解析过程"""
    
    glb_file_path = "f:/study/codes/fastdog/static/models/SU7.glb"
    
    if not os.path.exists(glb_file_path):
        print(f"GLB文件不存在: {glb_file_path}")
        return
    
    print("\n=== GLB解析详细测试 ===")
    
    try:
        with open(glb_file_path, 'rb') as f:
            glb_data = f.read()
        
        print(f"文件大小: {len(glb_data)} bytes")
        
        # 检查文件头
        if len(glb_data) >= 12:
            magic = glb_data[:4]
            version = int.from_bytes(glb_data[4:8], 'little')
            length = int.from_bytes(glb_data[8:12], 'little')
            
            print(f"魔数: {magic}")
            print(f"版本: {version}")
            print(f"文件长度: {length}")
            
            if magic == b'glTF' and version == 2:
                print("✅ GLB文件格式验证通过")
                
                # 解析JSON chunk
                offset = 12
                if len(glb_data) >= offset + 8:
                    json_chunk_length = int.from_bytes(glb_data[offset:offset+4], 'little')
                    json_chunk_type = glb_data[offset+4:offset+8]
                    
                    print(f"JSON chunk长度: {json_chunk_length}")
                    print(f"JSON chunk类型: {json_chunk_type}")
                    
                    if json_chunk_type == b'JSON':
                        json_data = glb_data[offset+8:offset+8+json_chunk_length]
                        try:
                            gltf_json = json.loads(json_data.decode('utf-8'))
                            print(f"✅ JSON解析成功，包含键: {list(gltf_json.keys())}")
                            
                            # 检查是否有二进制数据
                            binary_offset = offset + 8 + json_chunk_length
                            if len(glb_data) > binary_offset:
                                print(f"包含二进制数据，从偏移 {binary_offset} 开始")
                                remaining_size = len(glb_data) - binary_offset
                                print(f"二进制数据大小: {remaining_size} bytes")
                            
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON解析失败: {e}")
                    else:
                        print(f"❌ 无效的JSON chunk类型: {json_chunk_type}")
                else:
                    print("❌ 文件太小，无法包含完整的chunk头")
            else:
                print(f"❌ 无效的GLB文件: magic={magic}, version={version}")
        else:
            print("❌ 文件太小，无法包含GLB头")
            
    except Exception as e:
        print(f"❌ GLB解析测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_glb_compression()
    test_glb_parsing_details()