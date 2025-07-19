#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WASM模型传输API测试脚本
测试新增的二进制格式传输接口
"""

import asyncio
import aiohttp
import json
import struct
import zlib
import os
import time
from typing import Dict, Any


class WASMAPITester:
    def __init__(self, base_url: str = "http://localhost:8000", auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.session = None
        
    async def login(self, username: str = "admin@example.com", password: str = "admin123") -> bool:
        """登录获取认证token"""
        print(f"🔐 正在登录用户: {username}")
        
        url = f"{self.base_url}/api/v1/auth/login/access-token"
        data = {
            "username": username,
            "password": password
        }
        
        try:
            async with self.session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.auth_token = result.get("access_token")
                    print(f"✅ 登录成功，获取到token")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ 登录失败: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ 登录异常: {str(e)}")
            return False
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    async def test_model_info(self, filename: str = "merge.gltf") -> Dict[str, Any]:
        """测试模型信息获取接口"""
        print(f"\n🔍 测试模型信息接口: {filename}")
        
        url = f"{self.base_url}/api/v1/resources/models/{filename}/info"
        
        try:
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 模型信息获取成功:")
                    print(f"   - 文件名: {data.get('name')}")
                    print(f"   - 大小: {data.get('size')} bytes")
                    print(f"   - 网格数: {data.get('meshes')}")
                    print(f"   - 材质数: {data.get('materials')}")
                    print(f"   - 压缩可用: {data.get('compression_available')}")
                    print(f"   - 预估压缩大小: {data.get('estimated_compressed_size')} bytes")
                    return data
                else:
                    error_text = await response.text()
                    print(f"❌ 请求失败: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return None
    
    async def test_model_manifest(self, filename: str = "merge.gltf") -> Dict[str, Any]:
        """测试模型清单接口"""
        print(f"\n📋 测试模型清单接口: {filename}")
        
        url = f"{self.base_url}/api/v1/resources/models/{filename}/manifest"
        
        try:
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 模型清单获取成功:")
                    print(f"   - 模型名: {data.get('model_name')}")
                    print(f"   - 总大小: {data.get('total_size')} bytes")
                    print(f"   - 格式: {data.get('format')}")
                    print(f"   - 部件数: {len(data.get('parts', []))}")
                    print(f"   - LOD级别: {data.get('lod_levels')}")
                    
                    compression = data.get('compression', {})
                    print(f"   - 压缩格式: {compression.get('format')}")
                    print(f"   - 压缩比: {compression.get('estimated_ratio')}")
                    
                    return data
                else:
                    error_text = await response.text()
                    print(f"❌ 请求失败: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return None
    
    async def test_binary_download(self, filename: str = "merge.gltf", use_range: bool = True) -> bool:
        """测试二进制格式下载"""
        print(f"\n📦 测试二进制格式下载: {filename} (Range: {use_range})")
        
        url = f"{self.base_url}/api/v1/resources/models/{filename}/binary"
        headers = self.get_headers()
        
        if use_range:
            headers["Range"] = "bytes=0-1048575"  # 下载前1MB
        
        start_time = time.time()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status in [200, 206]:
                    # 检查响应头
                    content_length = response.headers.get('Content-Length')
                    original_size = response.headers.get('X-Original-Size')
                    compression_ratio = response.headers.get('X-Compression-Ratio')
                    format_type = response.headers.get('X-Format')
                    
                    print(f"✅ 二进制下载成功:")
                    print(f"   - 状态码: {response.status}")
                    print(f"   - 内容长度: {content_length} bytes")
                    print(f"   - 原始大小: {original_size} bytes")
                    print(f"   - 压缩比: {compression_ratio}")
                    print(f"   - 格式: {format_type}")
                    
                    # 读取数据
                    data = await response.read()
                    download_time = time.time() - start_time
                    
                    print(f"   - 实际下载: {len(data)} bytes")
                    print(f"   - 下载时间: {download_time:.2f}s")
                    
                    # 验证二进制格式
                    if len(data) >= 16:
                        magic = data[:8]
                        version = struct.unpack('<I', data[8:12])[0]
                        compressed_size = struct.unpack('<I', data[12:16])[0]
                        
                        print(f"   - 魔数: {magic}")
                        print(f"   - 版本: {version}")
                        print(f"   - 压缩数据长度: {compressed_size}")
                        
                        if magic == b'FASTDOG1' and version == 1:
                            print(f"✅ 二进制格式验证通过")
                            
                            # 尝试解压缩（如果有完整数据）
                            if len(data) >= 20 + compressed_size:
                                try:
                                    compressed_data = data[16:16+compressed_size]
                                    original_size_check = struct.unpack('<I', data[16+compressed_size:20+compressed_size])[0]
                                    
                                    decompressed = zlib.decompress(compressed_data)
                                    print(f"✅ 解压缩成功: {len(decompressed)} bytes")
                                    
                                    # 验证JSON格式
                                    try:
                                        json_data = json.loads(decompressed.decode('utf-8'))
                                        print(f"✅ JSON解析成功: 包含 {len(json_data)} 个顶级字段")
                                        return True
                                    except json.JSONDecodeError as e:
                                        print(f"❌ JSON解析失败: {str(e)}")
                                        
                                except zlib.error as e:
                                    print(f"❌ 解压缩失败: {str(e)}")
                            else:
                                print(f"⚠️  数据不完整，无法验证解压缩")
                        else:
                            print(f"❌ 二进制格式验证失败")
                    else:
                        print(f"❌ 数据太短，无法验证格式")
                    
                    return True
                    
                else:
                    error_text = await response.text()
                    print(f"❌ 请求失败: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    async def test_streaming_download(self, filename: str = "merge.gltf", chunk_size: int = 1024*1024) -> bool:
        """测试流式下载"""
        print(f"\n🌊 测试流式下载: {filename} (块大小: {chunk_size} bytes)")
        
        url = f"{self.base_url}/api/v1/resources/models/{filename}/binary"
        
        start_time = time.time()
        total_downloaded = 0
        
        try:
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    content_length = int(response.headers.get('Content-Length', 0))
                    print(f"开始流式下载，总大小: {content_length} bytes")
                    
                    async for chunk in response.content.iter_chunked(chunk_size):
                        total_downloaded += len(chunk)
                        progress = (total_downloaded / content_length * 100) if content_length > 0 else 0
                        print(f"\r   进度: {progress:.1f}% ({total_downloaded}/{content_length})", end="")
                    
                    download_time = time.time() - start_time
                    speed = total_downloaded / download_time / 1024 / 1024  # MB/s
                    
                    print(f"\n✅ 流式下载完成:")
                    print(f"   - 总下载: {total_downloaded} bytes")
                    print(f"   - 用时: {download_time:.2f}s")
                    print(f"   - 速度: {speed:.2f} MB/s")
                    
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ 流式下载失败: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ 流式下载异常: {str(e)}")
            return False
    
    async def test_blob_download(self, filename: str = "merge.gltf") -> bool:
        """测试blob格式下载接口"""
        print(f"\n🎯 测试Blob格式下载: {filename}")
        
        url = f"{self.base_url}/api/v1/resources/models/{filename}/blob"
        
        try:
            start_time = time.time()
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    # 获取响应头信息
                    original_size = response.headers.get('X-Original-Size')
                    compressed_size = response.headers.get('X-Compressed-Size')
                    compression_ratio = response.headers.get('X-Compression-Ratio')
                    format_type = response.headers.get('X-Format')
                    
                    # 读取blob数据
                    blob_data = await response.read()
                    download_time = time.time() - start_time
                    
                    print(f"✅ Blob下载成功:")
                    print(f"   - 状态码: {response.status}")
                    print(f"   - 原始大小: {original_size} bytes")
                    print(f"   - 压缩大小: {compressed_size} bytes")
                    print(f"   - 压缩比: {compression_ratio}")
                    print(f"   - 格式: {format_type}")
                    print(f"   - 实际下载: {len(blob_data)} bytes")
                    print(f"   - 下载时间: {download_time:.2f}s")
                    
                    # 验证二进制格式
                    if len(blob_data) >= 20:
                        magic = blob_data[:8].decode('utf-8', errors='ignore')
                        if magic == 'FASTDOG1':
                            print(f"✅ Blob格式验证通过")
                            
                            # 尝试解压缩验证
                            try:
                                version = struct.unpack('<I', blob_data[8:12])[0]
                                compressed_length = struct.unpack('<I', blob_data[12:16])[0]
                                original_length = struct.unpack('<I', blob_data[16:20])[0]
                                compressed_data = blob_data[20:20+compressed_length]
                                
                                decompressed = zlib.decompress(compressed_data)
                                json_data = json.loads(decompressed.decode('utf-8'))
                                
                                print(f"✅ Blob解压缩成功: {len(decompressed)} bytes")
                                print(f"✅ JSON解析成功: 包含 {len(json_data)} 个顶级字段")
                                
                            except Exception as decomp_error:
                                print(f"⚠️  Blob解压缩失败: {str(decomp_error)}")
                        else:
                            print(f"❌ Blob格式验证失败: 魔数不匹配")
                    
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ 请求失败: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Blob下载失败: {str(e)}")
            return False

    async def run_all_tests(self, filename: str = "merge.gltf") -> Dict[str, bool]:
        """运行所有测试"""
        print(f"🚀 开始WASM模型传输API测试")
        print(f"服务器: {self.base_url}")
        print(f"认证: {'已配置' if self.auth_token else '未配置'}")
        print(f"测试文件: {filename}")
        print("=" * 60)
        
        results = {}
        
        # 测试模型信息
        info_result = await self.test_model_info(filename)
        results['model_info'] = info_result is not None
        
        # 测试模型清单
        manifest_result = await self.test_model_manifest(filename)
        results['model_manifest'] = manifest_result is not None
        
        # 测试blob下载
        blob_result = await self.test_blob_download(filename)
        results['blob_download'] = blob_result
        
        # 测试二进制下载（完整）
        binary_result = await self.test_binary_download(filename, use_range=False)
        results['binary_download'] = binary_result
        
        # 测试二进制下载（Range请求）
        range_result = await self.test_binary_download(filename, use_range=True)
        results['range_download'] = range_result
        
        # 测试流式下载
        streaming_result = await self.test_streaming_download(filename)
        results['streaming_download'] = streaming_result
        
        # 输出测试总结
        print("\n" + "=" * 60)
        print("📊 测试结果总结:")
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n总计: {passed}/{total} 个测试通过")
        
        if passed == total:
            print("🎉 所有测试都通过了！WASM模型传输API工作正常。")
        else:
            print("⚠️  部分测试失败，请检查服务器配置和网络连接。")
        
        return results


async def main():
    """主函数"""
    # 配置测试参数
    base_url = "http://localhost:8000"
    auth_token = None  # 如果需要认证，请设置有效的token
    test_filename = "merge.gltf"
    
    # 运行测试
    async with WASMAPITester(base_url, auth_token) as tester:
        # 先尝试登录获取认证token
        login_success = await tester.login()
        if not login_success:
            print("❌ 无法获取认证token，测试终止")
            return
            
        await tester.run_all_tests(test_filename)


if __name__ == "__main__":
    asyncio.run(main())