#!/usr/bin/env python3
"""
Web3Signer 诊断工具
"""

import requests
import json
import sys

def test_web3signer():
    """测试 Web3Signer 连接和状态"""
    base_url = "http://localhost:9000"
    
    print("🔍 Web3Signer 诊断工具")
    print("=" * 50)
    
    # 测试基本连接
    print("1. 测试基本连接...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text[:100]}...")
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        return False
    
    # 测试健康检查
    print("\n2. 测试健康检查端点...")
    endpoints = ["/health", "/healthcheck", "/upcheck", "/status"]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            print(f"   {endpoint}: {response.status_code} - {response.text[:50]}")
        except Exception as e:
            print(f"   {endpoint}: 连接失败 - {e}")
    
    # 测试密钥列表
    print("\n3. 测试密钥列表...")
    try:
        response = requests.get(f"{base_url}/api/v1/eth2/publicKeys", timeout=5)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            keys = response.json()
            print(f"   找到 {len(keys)} 个密钥:")
            for key in keys:
                print(f"     - {key}")
        else:
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ❌ 获取密钥列表失败: {e}")
    
    # 测试 Vault 连接
    print("\n4. 测试 Vault 连接...")
    try:
        vault_response = requests.get("http://localhost:8200/v1/sys/health", timeout=5)
        print(f"   Vault 状态: {vault_response.status_code}")
    except Exception as e:
        print(f"   ❌ Vault 连接失败: {e}")
    
    return True

if __name__ == "__main__":
    test_web3signer()
