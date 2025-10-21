#!/usr/bin/env python3
"""
测试 Vault 路径和密钥访问
"""

import sys
import os
from pathlib import Path

# 设置正确的 Python 路径
def setup_python_path():
    """设置 Python 路径以正确导入模块"""
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    
    # 添加项目根目录到路径
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # 添加 code 目录到路径
    code_dir = project_root / "code"
    if str(code_dir) not in sys.path:
        sys.path.insert(0, str(code_dir))
    
    # 添加 code/core 目录到路径
    core_dir = project_root / "code" / "core"
    if str(core_dir) not in sys.path:
        sys.path.insert(0, str(core_dir))
    
    return project_root

# 设置路径
project_root = setup_python_path()

# 现在可以导入模块
from vault_key_manager import VaultKeyManager

def test_vault_paths():
    """测试 Vault 路径和密钥访问"""
    print("🔍 测试 Vault 路径和密钥访问...")
    
    try:
        # 初始化 VaultKeyManager
        vault_manager = VaultKeyManager()
        
        # 测试连接
        if not vault_manager._test_vault_connection():
            print("❌ Vault 连接失败")
            return False
        
        print("✅ Vault 连接成功")
        
        # 获取所有密钥
        keys = vault_manager.list_keys()
        print(f"📊 找到 {len(keys)} 个密钥")
        
        if not keys:
            print("❌ 没有找到密钥")
            return False
        
        # 测试第一个密钥的路径
        first_key = keys[0]
        print(f"🔍 测试密钥: {first_key.pubkey[:10]}...")
        
        # 获取密钥路径
        key_path = vault_manager._get_key_path(first_key.pubkey)
        print(f"📁 密钥路径: {key_path}")
        
        # 测试读取密钥
        retrieved_key = vault_manager.retrieve_key_from_vault(first_key.pubkey)
        if retrieved_key:
            print("✅ 密钥读取成功")
            # retrieved_key 是字典，不是 ValidatorKey 对象
            metadata = retrieved_key.get('metadata', {})
            print(f"   公钥: {metadata.get('validator_pubkey', 'N/A')[:10]}...")
            print(f"   状态: {metadata.get('status', 'N/A')}")
            print(f"   批次ID: {metadata.get('batch_id', 'N/A')}")
        else:
            print("❌ 密钥读取失败")
            return False
        
        # 测试 Vault API 路径
        import requests
        headers = {"X-Vault-Token": "dev-root-token"}
        
        # 测试 metadata 路径
        metadata_url = "http://localhost:8200/v1/secret/metadata/validator-keys"
        print(f"🔍 测试 metadata 路径: {metadata_url}")
        response = requests.get(metadata_url, headers=headers, timeout=5)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("✅ metadata 路径可访问")
        else:
            print(f"❌ metadata 路径不可访问: {response.text}")
        
        # 测试 data 路径
        data_url = f"http://localhost:8200/v1/secret/data/{key_path}"
        print(f"🔍 测试 data 路径: {data_url}")
        response = requests.get(data_url, headers=headers, timeout=5)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("✅ data 路径可访问")
            data = response.json()
            print(f"   字段: {list(data['data']['data'].keys())}")
        else:
            print(f"❌ data 路径不可访问: {response.text}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    if not test_vault_paths():
        sys.exit(1)
