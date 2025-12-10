#!/usr/bin/env python3
"""
手动验证 Vault 中的密钥
用于排查 Web3Signer 签名根不匹配问题
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "system_v2" / "backend"))

from app.core.vault_client import VaultClient
from py_ecc.bls import G2ProofOfPossession as bls

def verify_vault_key(pubkey: str):
    """
    验证 Vault 中的密钥
    
    Args:
        pubkey: 验证者公钥（带或不带 0x 前缀）
    """
    print(f"\n🔍 验证密钥: {pubkey[:20]}...")
    
    # 初始化 Vault 客户端
    vault_client = VaultClient()
    
    # 1. 从 Vault 读取私钥
    print("\n1️⃣ 从 Vault 读取私钥...")
    try:
        signing_key_hex = vault_client.get_signing_key(pubkey)
        if not signing_key_hex:
            print(f"❌ 无法从 Vault 读取私钥")
            return False
        
        print(f"✅ 成功读取私钥（长度: {len(signing_key_hex)} 字符）")
        print(f"   私钥前16字符: {signing_key_hex[:16]}...")
        
        # 验证私钥格式
        if len(signing_key_hex) != 64:
            print(f"⚠️  警告: 私钥长度不是 64 字符（当前: {len(signing_key_hex)}）")
        
    except Exception as e:
        print(f"❌ 读取私钥失败: {e}")
        return False
    
    # 2. 验证私钥与公钥是否匹配
    print("\n2️⃣ 验证私钥与公钥是否匹配...")
    try:
        # 清理公钥格式
        pubkey_clean = pubkey.lower().replace('0x', '')
        
        # 从私钥推导公钥
        signing_key_int = int(signing_key_hex, 16)
        derived_pubkey_bytes = bls.SkToPk(signing_key_int)
        derived_pubkey_hex = derived_pubkey_bytes.hex()
        
        print(f"   期望公钥: {pubkey_clean}")
        print(f"   推导公钥: {derived_pubkey_hex}")
        
        if derived_pubkey_hex.lower() == pubkey_clean.lower():
            print(f"✅ 私钥与公钥匹配！")
            return True
        else:
            print(f"❌ 私钥与公钥不匹配！")
            print(f"   这是问题的根源！Vault 中存储的私钥与公钥不对应。")
            return False
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def check_vault_path(pubkey: str):
    """
    检查 Vault 中的密钥路径和内容
    
    Args:
        pubkey: 验证者公钥
    """
    print(f"\n🔍 检查 Vault 路径: {pubkey[:20]}...")
    
    from app.config import settings
    from hvac import Client as VaultClient
    
    # 初始化 Vault 客户端
    vault_url = settings.vault_url
    vault_token = settings.vault_token
    
    client = VaultClient(url=vault_url, token=vault_token)
    
    # 清理公钥
    pubkey_clean = pubkey.lower().replace('0x', '')
    
    # 尝试读取密钥
    mount_point = settings.vault_mount_point
    key_path_prefix = settings.vault_key_path_prefix
    key_path = f"{key_path_prefix}/{pubkey_clean}"
    
    print(f"\n📁 Vault 路径信息:")
    print(f"   Mount Point: {mount_point}")
    print(f"   Key Path Prefix: {key_path_prefix}")
    print(f"   完整路径: {key_path}")
    print(f"   Web3Signer 访问路径: /v1/{mount_point}/data/{key_path}")
    
    try:
        response = client.secrets.kv.v2.read_secret_version(
            path=key_path,
            mount_point=mount_point
        )
        
        if response and 'data' in response and 'data' in response['data']:
            secret_data = response['data']['data']
            print(f"\n✅ 成功读取 Vault 数据:")
            print(f"   数据键: {list(secret_data.keys())}")
            
            if 'value' in secret_data:
                value = secret_data['value']
                print(f"   value 字段长度: {len(value)} 字符")
                print(f"   value 前16字符: {value[:16]}...")
                return True
            else:
                print(f"❌ 数据中没有 'value' 字段")
                print(f"   可用字段: {list(secret_data.keys())}")
                return False
        else:
            print(f"❌ 响应格式不正确")
            return False
            
    except Exception as e:
        print(f"❌ 读取 Vault 失败: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="验证 Vault 中的密钥")
    parser.add_argument("pubkey", help="验证者公钥（带或不带 0x 前缀）")
    parser.add_argument("--check-path", action="store_true", help="检查 Vault 路径和内容")
    
    args = parser.parse_args()
    
    if args.check_path:
        check_vault_path(args.pubkey)
    else:
        verify_vault_key(args.pubkey)

