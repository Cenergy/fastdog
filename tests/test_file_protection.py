#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件访问保护功能测试脚本

测试受保护文件的访问控制是否正常工作
"""

import requests
import sys

def test_file_protection():
    """测试文件访问保护功能"""
    base_url = "http://localhost:8008"
    
    # 测试用例
    test_cases = [
        {
            "name": "受保护文件 - .gltf",
            "url": f"{base_url}/static/uploads/models/test.gltf",
            "expected_status": 403,
            "description": "直接访问受保护的 .gltf 文件应该被拒绝"
        },
        {
            "name": "受保护文件 - .fastdog",
            "url": f"{base_url}/static/uploads/models/test.fastdog",
            "expected_status": 403,
            "description": "直接访问受保护的 .fastdog 文件应该被拒绝"
        },
        {
            "name": "受保护文件 - .glb",
            "url": f"{base_url}/static/uploads/models/test.glb",
            "expected_status": 403,
            "description": "直接访问受保护的 .glb 文件应该被拒绝"
        },
        {
            "name": "非受保护文件 - .jpg",
            "url": f"{base_url}/static/uploads/models/test.jpg",
            "expected_status": 404,
            "description": "访问非受保护文件应该正常（404是因为文件不存在）"
        },
        {
            "name": "API访问模型文件",
            "url": f"{base_url}/api/v1/resources/models/test.gltf",
            "expected_status": 404,
            "description": "通过API访问模型文件应该正常（404是因为文件不存在）"
        }
    ]
    
    print("开始测试文件访问保护功能...\n")
    
    all_passed = True
    
    for test_case in test_cases:
        try:
            response = requests.get(test_case["url"], timeout=5)
            status_code = response.status_code
            
            if status_code == test_case["expected_status"]:
                print(f"✅ {test_case['name']}: 通过 (状态码: {status_code})")
            else:
                print(f"❌ {test_case['name']}: 失败 (期望: {test_case['expected_status']}, 实际: {status_code})")
                all_passed = False
                
            print(f"   描述: {test_case['description']}")
            print()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ {test_case['name']}: 请求失败 - {e}")
            all_passed = False
            print()
    
    if all_passed:
        print("🎉 所有测试通过！文件访问保护功能正常工作。")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查配置。")
        return 1

if __name__ == "__main__":
    exit_code = test_file_protection()
    sys.exit(exit_code)