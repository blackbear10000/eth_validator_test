#!/usr/bin/env python3
"""
检查 Beacon 链同步状态
"""

import sys
import os
import requests
import json
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def check_beacon_sync(beacon_url: str = "http://localhost:33527"):
    """检查 Beacon 链同步状态"""
    print(f"🔍 检查 Beacon 链同步状态: {beacon_url}")
    
    try:
        # 检查健康状态
        health_url = f"{beacon_url}/eth/v1/node/health"
        health_response = requests.get(health_url, timeout=10)
        print(f"✅ Beacon 节点健康状态: {health_response.status_code}")
        
        # 检查同步状态
        sync_url = f"{beacon_url}/eth/v1/node/syncing"
        sync_response = requests.get(sync_url, timeout=10)
        
        if sync_response.status_code == 200:
            sync_data = sync_response.json()
            print(f"📊 同步状态:")
            print(f"   是否同步中: {sync_data.get('data', {}).get('is_syncing', 'Unknown')}")
            print(f"   当前槽位: {sync_data.get('data', {}).get('head_slot', 'Unknown')}")
            print(f"   同步槽位: {sync_data.get('data', {}).get('sync_distance', 'Unknown')}")
            
            if sync_data.get('data', {}).get('is_syncing', True):
                print("⚠️  Beacon 链仍在同步中，请等待同步完成")
                return False
            else:
                print("✅ Beacon 链已同步完成")
                return True
        else:
            print(f"❌ 无法获取同步状态: {sync_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 检查 Beacon 同步状态失败: {e}")
        return False

def check_validator_status(validator_url: str = "http://127.0.0.1:7500"):
    """检查验证者状态"""
    print(f"🔍 检查验证者状态: {validator_url}")
    
    try:
        # 检查验证者状态
        status_url = f"{validator_url}/eth/v1/validator/status"
        status_response = requests.get(status_url, timeout=10)
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"📊 验证者状态:")
            print(f"   状态: {status_data.get('data', {}).get('status', 'Unknown')}")
            print(f"   激活时间: {status_data.get('data', {}).get('activation_epoch', 'Unknown')}")
            return True
        else:
            print(f"❌ 无法获取验证者状态: {status_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 检查验证者状态失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 Beacon 链同步状态检查工具")
    print("=" * 50)
    
    # 检查 Beacon 链同步
    beacon_synced = check_beacon_sync()
    
    if beacon_synced:
        # 检查验证者状态
        validator_ready = check_validator_status()
        
        if validator_ready:
            print("\n✅ 系统状态正常，验证者可以正常运行")
        else:
            print("\n⚠️  验证者状态异常，请检查验证者配置")
    else:
        print("\n⚠️  Beacon 链仍在同步中，请等待同步完成后再启动验证者")

if __name__ == "__main__":
    main()
