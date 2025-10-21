#!/usr/bin/env python3
"""
测试 Web3Signer 配置和 Vault 连接
"""

import sys
import os
import requests
import json
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

def test_web3signer_config():
    """测试 Web3Signer 配置和 Vault 连接"""
    print("🔍 测试 Web3Signer 配置和 Vault 连接...")
    
    try:
        # 1. 测试 Vault 连接
        print("\n=== 1. 测试 Vault 连接 ===")
        vault_manager = VaultKeyManager()
        if not vault_manager._test_vault_connection():
            print("❌ Vault 连接失败")
            return False
        print("✅ Vault 连接成功")
        
        # 2. 测试 Web3Signer 健康状态
        print("\n=== 2. 测试 Web3Signer 健康状态 ===")
        try:
            response = requests.get("http://localhost:9000/upcheck", timeout=5)
            if response.status_code == 200 and response.text == "OK":
                print("✅ Web3Signer 健康状态正常")
            else:
                print(f"❌ Web3Signer 健康状态异常: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Web3Signer 连接失败: {e}")
            return False
        
        # 3. 测试 Web3Signer 密钥加载状态
        print("\n=== 3. 测试 Web3Signer 密钥加载状态 ===")
        try:
            response = requests.get("http://localhost:9000/api/v1/eth2/publicKeys", timeout=5)
            if response.status_code == 200:
                keys = response.json()
                print(f"✅ Web3Signer 已加载 {len(keys)} 个密钥")
                if keys:
                    print("   密钥列表:")
                    for key in keys[:3]:  # 只显示前3个
                        print(f"     - {key}")
                else:
                    print("⚠️  Web3Signer 中没有加载任何密钥")
            else:
                print(f"❌ 获取 Web3Signer 密钥列表失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 获取 Web3Signer 密钥列表失败: {e}")
        
        # 4. 测试 Vault 中的 Web3Signer 密钥
        print("\n=== 4. 测试 Vault 中的 Web3Signer 密钥 ===")
        try:
            headers = {"X-Vault-Token": "dev-root-token"}
            response = requests.get("http://localhost:8200/v1/secret/metadata/web3signer-keys", headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'keys' in data['data']:
                    web3signer_keys = data['data']['keys']
                    print(f"✅ Vault 中找到 {len(web3signer_keys)} 个 Web3Signer 密钥")
                    for key in web3signer_keys[:3]:  # 只显示前3个
                        print(f"     - {key}")
                else:
                    print("⚠️  Vault 中没有找到 Web3Signer 密钥")
            else:
                print(f"❌ 获取 Vault Web3Signer 密钥失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 获取 Vault Web3Signer 密钥失败: {e}")
        
        # 5. 测试 Web3Signer 配置文件
        print("\n=== 5. 测试 Web3Signer 配置文件 ===")
        keys_dir = project_root / "infra" / "web3signer" / "keys"
        if keys_dir.exists():
            config_files = list(keys_dir.glob("*.json"))
            print(f"✅ 找到 {len(config_files)} 个 Web3Signer 配置文件")
            for config_file in config_files[:3]:  # 只显示前3个
                print(f"     - {config_file.name}")
                # 读取并显示配置内容
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    print(f"       类型: {config.get('type', 'unknown')}")
                    print(f"       路径: {config.get('keyPath', 'unknown')}")
                except Exception as e:
                    print(f"       读取配置失败: {e}")
        else:
            print("❌ Web3Signer keys 目录不存在")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    if not test_web3signer_config():
        sys.exit(1)
