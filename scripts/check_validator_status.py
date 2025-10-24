#!/usr/bin/env python3
"""
检查验证者状态
"""

import sys
import os
import requests
import json
import subprocess
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def check_prysm_process():
    """检查 Prysm 进程是否运行"""
    print("🔍 检查 Prysm 进程...")
    
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'prysm validator' in result.stdout:
            print("✅ Prysm 验证者进程正在运行")
            return True
        else:
            print("❌ Prysm 验证者进程未运行")
            return False
    except Exception as e:
        print(f"❌ 检查进程失败: {e}")
        return False

def check_web_api(port: int = 7500):
    """检查 Web API 是否可用"""
    print(f"🔍 检查 Web API 端口 {port}...")
    
    try:
        response = requests.get(f"http://127.0.0.1:{port}/eth/v1/validator/status", timeout=5)
        if response.status_code == 200:
            print(f"✅ Web API 可用: {response.status_code}")
            return True
        else:
            print(f"⚠️  Web API 响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Web API 连接失败: 端口 {port} 不可用")
        return False
    except Exception as e:
        print(f"❌ Web API 检查失败: {e}")
        return False

def check_web3signer_connection():
    """检查 Web3Signer 连接"""
    print("🔍 检查 Web3Signer 连接...")
    
    try:
        response = requests.get("http://localhost:9002/upcheck", timeout=5)
        if response.status_code == 200:
            print("✅ Web3Signer 连接正常")
            return True
        else:
            print(f"⚠️  Web3Signer 响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Web3Signer 连接失败: {e}")
        return False

def check_beacon_connection():
    """检查 Beacon 节点连接"""
    print("🔍 检查 Beacon 节点连接...")
    
    try:
        response = requests.get("http://localhost:33527/eth/v1/node/health", timeout=5)
        if response.status_code == 200:
            print("✅ Beacon 节点连接正常")
            return True
        else:
            print(f"⚠️  Beacon 节点响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Beacon 节点连接失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 验证者状态检查工具")
    print("=" * 50)
    
    # 检查各个组件
    prysm_running = check_prysm_process()
    web_api_available = check_web_api()
    web3signer_connected = check_web3signer_connection()
    beacon_connected = check_beacon_connection()
    
    print("\n📊 检查结果:")
    print(f"   Prysm 进程: {'✅' if prysm_running else '❌'}")
    print(f"   Web API: {'✅' if web_api_available else '❌'}")
    print(f"   Web3Signer: {'✅' if web3signer_connected else '❌'}")
    print(f"   Beacon 节点: {'✅' if beacon_connected else '❌'}")
    
    if all([prysm_running, web_api_available, web3signer_connected, beacon_connected]):
        print("\n✅ 所有组件状态正常")
    else:
        print("\n⚠️  部分组件状态异常，请检查配置")
        
        if not prysm_running:
            print("💡 建议: 重新启动 Prysm 验证者")
        if not web_api_available:
            print("💡 建议: 检查 Prysm 启动参数中的 --web 配置")
        if not web3signer_connected:
            print("💡 建议: 启动 Web3Signer 服务")
        if not beacon_connected:
            print("💡 建议: 检查 Beacon 节点连接")

if __name__ == "__main__":
    main()
