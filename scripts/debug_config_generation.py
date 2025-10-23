#!/usr/bin/env python3
"""
调试配置文件生成问题
"""

import os
import sys
import yaml
from pathlib import Path

# Add the code directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.web3signer_manager import Web3SignerManager
from core.vault_key_manager import VaultKeyManager

def debug_config_generation():
    """调试配置文件生成"""
    print("🔍 调试配置文件生成...")
    
    # 初始化管理器
    web3signer_manager = Web3SignerManager()
    vault_manager = VaultKeyManager()
    
    # 检查连接
    print("🔍 检查连接状态...")
    print(f"   Web3Signer 连接: {'✅' if web3signer_manager._test_web3signer_connection() else '❌'}")
    print(f"   Vault 连接: {'✅' if web3signer_manager._test_vault_connection() else '❌'}")
    
    # 获取活跃密钥
    print("🔍 获取活跃密钥...")
    active_keys = vault_manager.list_keys(status='active')
    print(f"   找到 {len(active_keys)} 个活跃密钥")
    
    if not active_keys:
        print("❌ 没有活跃密钥")
        return
    
    # 检查keys目录
    keys_dir = web3signer_manager.keys_dir
    print(f"🔍 Keys目录: {keys_dir}")
    print(f"   目录存在: {keys_dir.exists()}")
    print(f"   目录可写: {keys_dir.is_dir() and os.access(keys_dir, os.W_OK)}")
    
    # 尝试创建第一个密钥的配置
    key = active_keys[0]
    pubkey = key.pubkey
    print(f"🔍 处理密钥: {pubkey[:10]}...")
    
    try:
        # 创建密钥数据
        key_data = {
            'pubkey': key.pubkey,
            'data': {
                'pubkey': key.pubkey,
                'privkey': key.privkey,
                'withdrawal_pubkey': key.withdrawal_pubkey,
                'withdrawal_privkey': key.withdrawal_privkey,
                'mnemonic': key.mnemonic,
                'index': key.index,
                'signing_key_path': key.signing_key_path,
                'batch_id': key.batch_id,
                'created_at': key.created_at,
                'status': key.status,
                'client_type': key.client_type,
                'notes': key.notes
            }
        }
        
        print("🔍 创建Web3Signer配置...")
        config = web3signer_manager.create_web3signer_key_config(key_data)
        print(f"   配置内容: {config}")
        
        # 保存配置文件
        config_file = keys_dir / f"vault-{pubkey[:16]}.yaml"
        print(f"🔍 保存配置文件: {config_file}")
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"   文件保存完成")
        print(f"   文件存在: {config_file.exists()}")
        if config_file.exists():
            print(f"   文件大小: {config_file.stat().st_size} bytes")
            print(f"   文件内容:")
            with open(config_file, 'r') as f:
                print(f.read())
        
    except Exception as e:
        print(f"❌ 处理密钥失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_config_generation()
