#!/usr/bin/env python3
"""
智能选择 Beacon API
根据可用性选择最佳的 beacon API 供 validator client 使用
"""

import sys
import os
import requests
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def test_beacon_api(url: str) -> bool:
    """测试 beacon API 是否可用"""
    try:
        # 测试健康检查端点
        health_url = f"{url}/eth/v1/node/health"
        response = requests.get(health_url, timeout=5)
        return response.status_code == 200
    except:
        return False

def select_best_beacon_api(available_apis: dict) -> str:
    """选择最佳的 beacon API"""
    print("🔍 选择最佳的 Beacon API...")
    
    # 优先级顺序：Prysm > Lighthouse > Teku
    priority_order = ["prysm", "lighthouse", "teku"]
    
    for client_type in priority_order:
        if client_type in available_apis and available_apis[client_type]:
            api_url = available_apis[client_type]
            print(f"🧪 测试 {client_type} Beacon API: {api_url}")
            
            if test_beacon_api(api_url):
                print(f"✅ {client_type} Beacon API 可用: {api_url}")
                return api_url
            else:
                print(f"❌ {client_type} Beacon API 不可用: {api_url}")
    
    # 如果没有找到可用的 API，返回第一个可用的
    for client_type, api_url in available_apis.items():
        if api_url:
            print(f"⚠️  使用第一个可用的 API: {client_type} -> {api_url}")
            return api_url
    
    # 最后使用默认配置
    print("⚠️  使用默认 Beacon API")
    return "http://localhost:3500"

def main():
    """主函数"""
    print("🚀 Beacon API 选择工具")
    print("=" * 40)
    
    # 这里应该从实际的端口检测结果中获取
    # 为了演示，我们使用示例数据
    available_apis = {
        "prysm": "http://localhost:33522",
        "lighthouse": "http://localhost:33527",
        "teku": None
    }
    
    best_api = select_best_beacon_api(available_apis)
    print(f"\n🎯 选择的 Beacon API: {best_api}")
    
    return best_api

if __name__ == "__main__":
    api = main()
    print(f"\n📋 建议的配置: {api}")
    sys.exit(0)
