#!/usr/bin/env python3
"""
Vault 初始化脚本（可选）
确保 Vault KV v2 引擎已启用

注意：
1. 这个脚本是可选的，因为 VaultClient 在初始化时会自动启用 KV v2 引擎
2. 主要用于验证 Vault 配置是否正确
3. 如果 Vault 服务未运行或未认证，请先：
   - 确保 Vault 容器已启动：docker-compose up -d vault-1
   - 设置 VAULT_TOKEN 环境变量或确保可以从 Consul 读取
"""
import sys
import os

# 检查依赖
try:
    import hvac
except ImportError:
    print("错误: 缺少 hvac 模块")
    print("请运行: pip install -r requirements.txt")
    sys.exit(1)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.vault_client import VaultClient

def main():
    """初始化 Vault"""
    print("=" * 50)
    print("Vault 初始化检查")
    print("=" * 50)
    print()
    print("注意: 这个脚本是可选的。VaultClient 会自动启用 KV v2 引擎。")
    print("主要用于验证 Vault 配置是否正确。")
    print()
    
    try:
        print("正在连接 Vault...")
        vault_client = VaultClient()
        
        print("检查 Vault 连接...")
        if vault_client.client.is_authenticated():
            print("✅ Vault 认证成功")
        else:
            print("❌ Vault 认证失败")
            print()
            print("请检查:")
            print("1. Vault 服务是否运行: docker ps | grep vault")
            print("2. VAULT_TOKEN 环境变量是否设置")
            print("3. 或者从 Consul 读取 token: python3 get_vault_token.py")
            return 1
        
        print("检查 KV v2 引擎...")
        mounts = vault_client.client.sys.list_mounted_secrets_engines()
        mount_path = f"{vault_client.mount_point}/"
        
        if mount_path in mounts:
            mount_info = mounts[mount_path]
            version = mount_info.get('options', {}).get('version', 'unknown')
            print(f"✅ KV v2 引擎已启用: {vault_client.mount_point} (version: {version})")
        else:
            print(f"⚠️  KV v2 引擎未启用，正在启用: {vault_client.mount_point}")
            vault_client.client.sys.enable_secrets_engine(
                backend_type='kv',
                path=vault_client.mount_point,
                options={'version': '2'}
            )
            print(f"✅ KV v2 引擎启用成功")
        
        print()
        print("=" * 50)
        print("Vault 初始化检查完成!")
        print("=" * 50)
        return 0
        
    except ConnectionError as e:
        print(f"❌ 连接错误: {e}")
        print()
        print("请确保:")
        print("1. Vault 容器已启动: cd ../infra && docker-compose up -d vault-1")
        print("2. 等待 Vault 初始化完成（约 30 秒）")
        print("3. 设置 VAULT_TOKEN 环境变量")
        print("   或者从 Consul 读取: python3 get_vault_token.py")
        return 1
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

