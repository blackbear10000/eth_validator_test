#!/usr/bin/env python3
"""
Migration script for Web3Signer key configuration format
Migrates from old hash-based paths to new full pubkey paths
"""

import os
import sys
import json
import yaml
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from code.core.vault_key_manager import VaultKeyManager
from code.core.web3signer_manager import Web3SignerManager


class Web3SignerKeyMigrator:
    """Migrate Web3Signer keys from old format to new format"""
    
    def __init__(self, vault_url: str = "http://localhost:8200", vault_token: str = "dev-root-token"):
        self.vault_url = vault_url
        self.vault_token = vault_token
        self.vault_manager = VaultKeyManager(vault_url, vault_token)
        self.web3signer_manager = Web3SignerManager(vault_url=vault_url, vault_token=vault_token)
        
    def check_migration_needed(self) -> bool:
        """Check if migration is needed"""
        print("🔍 检查是否需要迁移...")
        
        try:
            # Check if old format keys exist in Vault
            old_keys = self._find_old_format_keys()
            if old_keys:
                print(f"📋 找到 {len(old_keys)} 个旧格式密钥需要迁移")
                return True
            else:
                print("✅ 没有找到需要迁移的旧格式密钥")
                return False
                
        except Exception as e:
            print(f"❌ 检查迁移需求失败: {e}")
            return False
    
    def _find_old_format_keys(self) -> List[str]:
        """Find keys stored in old hash-based format"""
        try:
            # List all keys in web3signer-keys path
            response = requests.get(
                f"{self.vault_url}/v1/secret/metadata/web3signer-keys",
                headers={"X-Vault-Token": self.vault_token},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'keys' in data['data']:
                    # Filter for hash-based keys (16 chars)
                    old_keys = []
                    for key_name in data['data']['keys']:
                        if len(key_name) == 16 and key_name.isalnum():
                            old_keys.append(key_name)
                    return old_keys
            
            return []
            
        except Exception as e:
            print(f"⚠️  检查旧格式密钥失败: {e}")
            return []
    
    def migrate_keys(self) -> bool:
        """Migrate keys from old format to new format"""
        print("🔄 开始迁移密钥...")
        
        try:
            # Find old format keys
            old_keys = self._find_old_format_keys()
            if not old_keys:
                print("✅ 没有需要迁移的密钥")
                return True
            
            migrated_count = 0
            
            for old_key_hash in old_keys:
                try:
                    print(f"🔧 迁移密钥: {old_key_hash}")
                    
                    # Read old format key
                    old_path = f"/v1/secret/data/web3signer-keys/{old_key_hash}"
                    response = requests.get(
                        f"{self.vault_url}{old_path}",
                        headers={"X-Vault-Token": self.vault_token},
                        timeout=10
                    )
                    
                    if response.status_code != 200:
                        print(f"⚠️  无法读取旧密钥: {old_key_hash}")
                        continue
                    
                    old_data = response.json()['data']['data']
                    if 'value' not in old_data:
                        print(f"⚠️  旧密钥格式无效: {old_key_hash}")
                        continue
                    
                    # Find corresponding key in VaultKeyManager
                    pubkey = self._find_pubkey_by_hash(old_key_hash)
                    if not pubkey:
                        print(f"⚠️  无法找到对应的公钥: {old_key_hash}")
                        continue
                    
                    # Store in new format
                    new_path = f"/v1/secret/data/web3signer-keys/{pubkey}"
                    new_data = {"value": old_data['value']}
                    
                    response = requests.post(
                        f"{self.vault_url}{new_path}",
                        headers={"X-Vault-Token": self.vault_token},
                        json={"data": new_data},
                        timeout=10
                    )
                    
                    if response.status_code in [200, 204]:
                        print(f"✅ 密钥已迁移: {pubkey[:10]}...")
                        migrated_count += 1
                        
                        # Delete old format key
                        self._delete_old_key(old_key_hash)
                    else:
                        print(f"❌ 迁移失败: {pubkey[:10]}...")
                
                except Exception as e:
                    print(f"❌ 迁移密钥失败 {old_key_hash}: {e}")
                    continue
            
            print(f"📊 迁移完成: {migrated_count}/{len(old_keys)} 个密钥")
            return migrated_count > 0
            
        except Exception as e:
            print(f"❌ 迁移过程失败: {e}")
            return False
    
    def _find_pubkey_by_hash(self, key_hash: str) -> Optional[str]:
        """Find public key by hash (reverse lookup)"""
        try:
            # Get all keys from VaultKeyManager
            all_keys = self.vault_manager.list_keys()
            
            for key in all_keys:
                # Calculate hash for this key
                import hashlib
                pubkey_hash = hashlib.sha256(key.pubkey.encode()).hexdigest()[:16]
                if pubkey_hash == key_hash:
                    return key.pubkey
            
            return None
            
        except Exception as e:
            print(f"❌ 查找公钥失败: {e}")
            return None
    
    def _delete_old_key(self, key_hash: str):
        """Delete old format key"""
        try:
            old_path = f"/v1/secret/data/web3signer-keys/{key_hash}"
            response = requests.delete(
                f"{self.vault_url}{old_path}",
                headers={"X-Vault-Token": self.vault_token},
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                print(f"🗑️  已删除旧格式密钥: {key_hash}")
            else:
                print(f"⚠️  删除旧密钥失败: {key_hash}")
                
        except Exception as e:
            print(f"⚠️  删除旧密钥异常: {e}")
    
    def update_config_files(self) -> bool:
        """Update Web3Signer config files to new format"""
        print("🔄 更新配置文件...")
        
        try:
            keys_dir = Path("infra/web3signer/keys")
            if not keys_dir.exists():
                print("📁 Keys 目录不存在，无需更新配置文件")
                return True
            
            # Remove old JSON config files
            removed_count = 0
            for config_file in keys_dir.glob("*.json"):
                config_file.unlink()
                removed_count += 1
                print(f"🗑️  已删除旧配置文件: {config_file}")
            
            # Generate new YAML config files for active keys
            if self.web3signer_manager.sync_active_keys():
                print("✅ 新配置文件已生成")
                return True
            else:
                print("❌ 生成新配置文件失败")
                return False
                
        except Exception as e:
            print(f"❌ 更新配置文件失败: {e}")
            return False
    
    def verify_migration(self) -> bool:
        """Verify migration was successful"""
        print("🔍 验证迁移结果...")
        
        try:
            # Check if old format keys still exist
            old_keys = self._find_old_format_keys()
            if old_keys:
                print(f"❌ 仍有 {len(old_keys)} 个旧格式密钥未迁移")
                return False
            
            # Check if new format keys exist
            active_keys = self.vault_manager.list_keys(status='active')
            if not active_keys:
                print("⚠️  没有活跃密钥")
                return True
            
            # Check Web3Signer config files
            keys_dir = Path("infra/web3signer/keys")
            yaml_files = list(keys_dir.glob("*.yaml"))
            
            print(f"📊 迁移验证结果:")
            print(f"   - 活跃密钥: {len(active_keys)}")
            print(f"   - 配置文件: {len(yaml_files)}")
            print(f"   - 旧格式密钥: {len(old_keys)}")
            
            if len(yaml_files) == len(active_keys):
                print("✅ 迁移验证通过")
                return True
            else:
                print("⚠️  配置文件数量与活跃密钥不匹配")
                return False
                
        except Exception as e:
            print(f"❌ 验证迁移失败: {e}")
            return False
    
    def run_migration(self) -> bool:
        """Run complete migration process"""
        print("🚀 开始 Web3Signer 密钥迁移...")
        
        try:
            # Check if migration is needed
            if not self.check_migration_needed():
                print("✅ 无需迁移")
                return True
            
            # Migrate keys
            if not self.migrate_keys():
                print("❌ 密钥迁移失败")
                return False
            
            # Update config files
            if not self.update_config_files():
                print("❌ 配置文件更新失败")
                return False
            
            # Verify migration
            if not self.verify_migration():
                print("❌ 迁移验证失败")
                return False
            
            print("🎉 迁移完成！")
            print("💡 建议重启 Web3Signer 服务以应用新配置")
            return True
            
        except Exception as e:
            print(f"❌ 迁移过程失败: {e}")
            return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web3Signer 密钥迁移工具")
    parser.add_argument("--vault-url", default="http://localhost:8200", help="Vault URL")
    parser.add_argument("--vault-token", default="dev-root-token", help="Vault token")
    parser.add_argument("--check", action="store_true", help="仅检查是否需要迁移")
    parser.add_argument("--verify", action="store_true", help="验证迁移结果")
    
    args = parser.parse_args()
    
    migrator = Web3SignerKeyMigrator(args.vault_url, args.vault_token)
    
    if args.check:
        needed = migrator.check_migration_needed()
        sys.exit(0 if not needed else 1)
    elif args.verify:
        success = migrator.verify_migration()
        sys.exit(0 if success else 1)
    else:
        success = migrator.run_migration()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
