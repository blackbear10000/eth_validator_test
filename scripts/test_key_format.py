#!/usr/bin/env python3
"""
测试密钥格式和存储流程
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

def test_key_format():
    """测试密钥格式和存储流程"""
    print("🔍 测试密钥格式和存储流程...")
    
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
        if not keys:
            print("❌ 没有找到密钥")
            return False
        
        print(f"📊 找到 {len(keys)} 个密钥")
        
        # 测试第一个密钥
        first_key = keys[0]
        print(f"🔍 测试密钥: {first_key.pubkey[:10]}...")
        
        # 检查私钥格式
        print(f"🔍 私钥格式分析:")
        print(f"   原始私钥: {first_key.privkey[:10]}...")
        print(f"   私钥长度: {len(first_key.privkey)}")
        print(f"   是否有 0x 前缀: {first_key.privkey.startswith('0x')}")
        
        # 模拟 Web3Signer 格式转换
        web3signer_privkey = first_key.privkey
        if web3signer_privkey.startswith('0x'):
            web3signer_privkey = web3signer_privkey[2:]
        
        print(f"🔍 Web3Signer 格式:")
        print(f"   转换后私钥: {web3signer_privkey[:10]}...")
        print(f"   转换后长度: {len(web3signer_privkey)}")
        print(f"   是否为 64 字符: {len(web3signer_privkey) == 64}")
        
        # 检查 Vault 中的实际存储
        print(f"🔍 Vault 存储检查:")
        vault_data = vault_manager.retrieve_key_from_vault(first_key.pubkey)
        if vault_data:
            print(f"   Vault 数据字段: {list(vault_data.keys())}")
            if 'metadata' in vault_data:
                print(f"   元数据字段: {list(vault_data['metadata'].keys())}")
        else:
            print("❌ 无法从 Vault 获取数据")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    if not test_key_format():
        sys.exit(1)
