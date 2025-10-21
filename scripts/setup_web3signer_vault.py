#!/usr/bin/env python3
"""
为 Web3Signer 设置 Vault 密钥存储
根据官方文档：https://docs.web3signer.consensys.io/how-to/store-keys/vaults/hashicorp
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

def setup_web3signer_vault():
    """为 Web3Signer 设置 Vault 密钥存储"""
    print("🔧 为 Web3Signer 设置 Vault 密钥存储...")
    
    try:
        # 1. 初始化 VaultKeyManager
        vault_manager = VaultKeyManager()
        if not vault_manager._test_vault_connection():
            print("❌ Vault 连接失败")
            return False
        
        print("✅ Vault 连接成功")
        
        # 2. 获取所有密钥
        keys = vault_manager.list_keys()
        if not keys:
            print("❌ 没有找到密钥")
            return False
        
        print(f"📊 找到 {len(keys)} 个密钥")
        
        # 3. 为每个密钥创建 Web3Signer 兼容的 Vault 存储
        headers = {"X-Vault-Token": "dev-root-token"}
        vault_url = "http://localhost:8200"
        
        for i, key in enumerate(keys):
            try:
                # 获取私钥（解密）
                privkey = key.privkey
                if privkey.startswith('0x'):
                    privkey = privkey[2:]  # 移除 0x 前缀
                
                # 验证私钥格式
                if len(privkey) != 64:
                    print(f"❌ 密钥 {i+1} 格式错误: 长度 {len(privkey)}，期望 64")
                    continue
                
                # 为 Web3Signer 创建 Vault 存储
                # 使用官方文档的格式：/v1/secret/data/web3signerSigningKey
                web3signer_path = f"/v1/secret/data/web3signerSigningKey{i}" if i > 0 else "/v1/secret/data/web3signerSigningKey"
                
                vault_data = {
                    "value": privkey  # Web3Signer 期望的字段名
                }
                
                # 存储到 Vault
                response = requests.post(
                    f"{vault_url}{web3signer_path}",
                    headers=headers,
                    json={"data": vault_data},
                    timeout=10
                )
                
                if response.status_code in [200, 204]:
                    print(f"✅ Web3Signer 密钥 {i+1} 已存储: {web3signer_path}")
                    print(f"   公钥: {key.pubkey[:10]}...")
                    print(f"   私钥长度: {len(privkey)}")
                else:
                    print(f"❌ Web3Signer 密钥 {i+1} 存储失败: {response.status_code}")
                    print(f"   响应: {response.text}")
                    
            except Exception as e:
                print(f"❌ 处理密钥 {i+1} 失败: {e}")
                continue
        
        # 4. 验证存储结果
        print("\n🔍 验证 Vault 存储...")
        try:
            response = requests.get(f"{vault_url}/v1/secret/metadata/web3signerSigningKey", headers=headers, timeout=5)
            if response.status_code == 200:
                print("✅ Web3Signer 主密钥存储成功")
            else:
                print(f"⚠️  Web3Signer 主密钥存储状态: {response.status_code}")
        except Exception as e:
            print(f"⚠️  验证存储失败: {e}")
        
        print("\n🎉 Web3Signer Vault 设置完成！")
        print("💡 现在可以重启 Web3Signer 以加载密钥")
        
        return True
        
    except Exception as e:
        print(f"❌ 设置失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    if not setup_web3signer_vault():
        sys.exit(1)
