#!/usr/bin/env python3
"""
Vault 初始化脚本
确保 Vault KV v2 引擎已启用
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.vault_client import VaultClient

def main():
    """初始化 Vault"""
    print("=" * 50)
    print("Vault 初始化")
    print("=" * 50)
    
    try:
        vault_client = VaultClient()
        
        print("检查 Vault 连接...")
        if vault_client.client.is_authenticated():
            print("✅ Vault 认证成功")
        else:
            print("❌ Vault 认证失败")
            return
        
        print("检查 KV v2 引擎...")
        mounts = vault_client.client.sys.list_mounted_secrets_engines()
        mount_path = f"{vault_client.mount_point}/"
        
        if mount_path in mounts:
            print(f"✅ KV v2 引擎已启用: {vault_client.mount_point}")
        else:
            print(f"启用 KV v2 引擎: {vault_client.mount_point}")
            vault_client.client.sys.enable_secrets_engine(
                backend_type='kv',
                path=vault_client.mount_point,
                options={'version': '2'}
            )
            print(f"✅ KV v2 引擎启用成功")
        
        print("=" * 50)
        print("Vault 初始化完成!")
        print("=" * 50)
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

