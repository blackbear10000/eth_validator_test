#!/usr/bin/env python3
"""
备份系统

功能：
1. 支持 keystore 和 mnemonic 形式备份
2. 批量备份功能
3. 加密备份文件
4. 备份验证和恢复
"""

import json
import os
import sys
import argparse
import zipfile
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入我们的 Vault 密钥管理器
from vault_key_manager import VaultKeyManager, ValidatorKey

class BackupSystem:
    """备份系统"""
    
    def __init__(self, vault_url: str = "http://localhost:8200", vault_token: str = None):
        self.vault_manager = VaultKeyManager(vault_url, vault_token)
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_keystore_backup(self, 
                              pubkeys: List[str], 
                              password: str,
                              backup_name: str = None) -> str:
        """创建 keystore 格式备份"""
        
        if not backup_name:
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            backup_name = f"keystore-backup-{timestamp}"
        
        print(f"🔄 创建 keystore 备份: {backup_name}")
        
        backup_data = {
            "backup_type": "keystore",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "key_count": len(pubkeys),
            "keys": []
        }
        
        # 处理每个密钥
        for i, pubkey in enumerate(pubkeys):
            print(f"  📝 处理密钥 {i+1}/{len(pubkeys)}: {pubkey[:10]}...")
            
            key_data = self.vault_manager.get_key(pubkey)
            if not key_data:
                print(f"    ⚠️ 跳过不存在的密钥: {pubkey}")
                continue
            
            # 创建 keystore 格式
            keystore_data = self._create_keystore_entry(key_data, password)
            backup_data["keys"].append({
                "pubkey": pubkey,
                "keystore": keystore_data,
                "withdrawal_pubkey": key_data.withdrawal_pubkey,
                "batch_id": key_data.batch_id,
                "created_at": key_data.created_at,
                "status": key_data.status,
                "client_type": key_data.client_type,
                "notes": key_data.notes
            })
        
        # 保存备份文件
        backup_file = self._save_backup_file(backup_data, backup_name, "keystore")
        
        print(f"✅ Keystore 备份已创建: {backup_file}")
        return backup_file
    
    def create_mnemonic_backup(self, 
                              pubkeys: List[str], 
                              backup_name: str = None) -> str:
        """创建 mnemonic 格式备份"""
        
        if not backup_name:
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            backup_name = f"mnemonic-backup-{timestamp}"
        
        print(f"🔄 创建 mnemonic 备份: {backup_name}")
        
        backup_data = {
            "backup_type": "mnemonic",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "key_count": len(pubkeys),
            "keys": []
        }
        
        # 处理每个密钥
        for i, pubkey in enumerate(pubkeys):
            print(f"  📝 处理密钥 {i+1}/{len(pubkeys)}: {pubkey[:10]}...")
            
            key_data = self.vault_manager.get_key(pubkey)
            if not key_data:
                print(f"    ⚠️ 跳过不存在的密钥: {pubkey}")
                continue
            
            backup_data["keys"].append({
                "pubkey": pubkey,
                "mnemonic": key_data.mnemonic,
                "withdrawal_pubkey": key_data.withdrawal_pubkey,
                "batch_id": key_data.batch_id,
                "created_at": key_data.created_at,
                "status": key_data.status,
                "client_type": key_data.client_type,
                "notes": key_data.notes
            })
        
        # 保存备份文件
        backup_file = self._save_backup_file(backup_data, backup_name, "mnemonic")
        
        print(f"✅ Mnemonic 备份已创建: {backup_file}")
        return backup_file
    
    def create_encrypted_backup(self, 
                               pubkeys: List[str], 
                               encryption_password: str,
                               backup_name: str = None) -> str:
        """创建加密备份"""
        
        if not backup_name:
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            backup_name = f"encrypted-backup-{timestamp}"
        
        print(f"🔄 创建加密备份: {backup_name}")
        
        # 收集所有密钥数据
        backup_data = {
            "backup_type": "encrypted",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "key_count": len(pubkeys),
            "keys": []
        }
        
        for i, pubkey in enumerate(pubkeys):
            print(f"  📝 处理密钥 {i+1}/{len(pubkeys)}: {pubkey[:10]}...")
            
            key_data = self.vault_manager.get_key(pubkey)
            if not key_data:
                print(f"    ⚠️ 跳过不存在的密钥: {pubkey}")
                continue
            
            backup_data["keys"].append({
                "pubkey": pubkey,
                "privkey": key_data.privkey,
                "withdrawal_pubkey": key_data.withdrawal_pubkey,
                "withdrawal_privkey": key_data.withdrawal_privkey,
                "mnemonic": key_data.mnemonic,
                "batch_id": key_data.batch_id,
                "created_at": key_data.created_at,
                "status": key_data.status,
                "client_type": key_data.client_type,
                "notes": key_data.notes
            })
        
        # 加密备份数据
        encrypted_data = self._encrypt_backup_data(backup_data, encryption_password)
        
        # 保存加密备份文件
        backup_file = self._save_encrypted_backup_file(encrypted_data, backup_name)
        
        print(f"✅ 加密备份已创建: {backup_file}")
        return backup_file
    
    def create_batch_backup(self, 
                           batch_id: str, 
                           backup_format: str = "both",
                           password: str = None) -> Dict[str, str]:
        """创建批次备份"""
        
        print(f"🔄 创建批次备份: {batch_id}")
        
        # 获取批次中的所有密钥
        keys = self.vault_manager.list_keys(batch_id=batch_id)
        pubkeys = [key.pubkey for key in keys]
        
        if not pubkeys:
            print(f"❌ 批次 {batch_id} 中没有找到密钥")
            return {}
        
        print(f"📋 找到 {len(pubkeys)} 个密钥")
        
        results = {}
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_name = f"batch-{batch_id}-{timestamp}"
        
        if backup_format in ["keystore", "both"]:
            if not password:
                print("❌ keystore 格式需要密码")
                return {}
            results["keystore"] = self.create_keystore_backup(pubkeys, password, f"{backup_name}-keystore")
        
        if backup_format in ["mnemonic", "both"]:
            results["mnemonic"] = self.create_mnemonic_backup(pubkeys, f"{backup_name}-mnemonic")
        
        if backup_format == "encrypted" and password:
            results["encrypted"] = self.create_encrypted_backup(pubkeys, password, f"{backup_name}-encrypted")
        
        return results
    
    def restore_from_backup(self, 
                           backup_file: str, 
                           password: str = None,
                           dry_run: bool = False) -> bool:
        """从备份恢复密钥"""
        
        print(f"🔄 从备份恢复: {backup_file}")
        
        try:
            # 读取备份文件
            backup_data = self._load_backup_file(backup_file, password)
            
            if not backup_data:
                print("❌ 无法读取备份文件")
                return False
            
            print(f"📋 备份信息:")
            print(f"  类型: {backup_data['backup_type']}")
            print(f"  创建时间: {backup_data['created_at']}")
            print(f"  密钥数量: {backup_data['key_count']}")
            
            if dry_run:
                print("🔍 试运行模式，不会实际恢复密钥")
                for key_info in backup_data['keys']:
                    print(f"  🔑 {key_info['pubkey'][:10]}... | {key_info.get('batch_id', 'N/A')}")
                return True
            
            # 恢复密钥
            restored_count = 0
            for key_info in backup_data['keys']:
                print(f"  📝 恢复密钥: {key_info['pubkey'][:10]}...")
                
                # 创建 ValidatorKey 对象
                key_data = ValidatorKey(
                    pubkey=key_info['pubkey'],
                    privkey=key_info.get('privkey', ''),  # 可能为空（keystore格式）
                    withdrawal_pubkey=key_info['withdrawal_pubkey'],
                    withdrawal_privkey=key_info.get('withdrawal_privkey', ''),  # 可能为空
                    mnemonic=key_info.get('mnemonic', ''),  # 可能为空
                    batch_id=key_info['batch_id'],
                    created_at=key_info['created_at'],
                    status=key_info.get('status', 'unused'),
                    client_type=key_info.get('client_type'),
                    notes=key_info.get('notes')
                )
                
                # 存储到 Vault
                if self.vault_manager.store_key(key_data):
                    restored_count += 1
                else:
                    print(f"    ❌ 恢复失败")
            
            print(f"✅ 成功恢复 {restored_count}/{len(backup_data['keys'])} 个密钥")
            return restored_count > 0
            
        except Exception as e:
            print(f"❌ 恢复失败: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份文件"""
        
        backups = []
        for backup_file in self.backup_dir.glob("*.json"):
            try:
                with open(backup_file, 'r') as f:
                    backup_data = json.load(f)
                
                backups.append({
                    "file": str(backup_file),
                    "name": backup_file.stem,
                    "type": backup_data.get("backup_type", "unknown"),
                    "created_at": backup_data.get("created_at", "unknown"),
                    "key_count": backup_data.get("key_count", 0),
                    "size": backup_file.stat().st_size
                })
            except Exception as e:
                print(f"⚠️ 跳过损坏的备份文件 {backup_file}: {e}")
        
        # 按创建时间排序
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
    
    def _create_keystore_entry(self, key_data: ValidatorKey, password: str) -> Dict[str, Any]:
        """创建 keystore 条目"""
        # 这里需要实现实际的 keystore 格式
        # 简化版本，实际实现需要更复杂的加密逻辑
        return {
            "version": 3,
            "id": "mock-id",
            "address": "mock-address",
            "crypto": {
                "cipher": "aes-128-ctr",
                "ciphertext": "mock-ciphertext",
                "cipherparams": {"iv": "mock-iv"},
                "kdf": "scrypt",
                "kdfparams": {"dklen": 32, "n": 262144, "r": 8, "p": 1, "salt": "mock-salt"},
                "mac": "mock-mac"
            }
        }
    
    def _save_backup_file(self, backup_data: Dict[str, Any], backup_name: str, backup_type: str) -> str:
        """保存备份文件"""
        filename = f"{backup_name}.json"
        filepath = self.backup_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        return str(filepath)
    
    def _save_encrypted_backup_file(self, encrypted_data: bytes, backup_name: str) -> str:
        """保存加密备份文件"""
        filename = f"{backup_name}.enc"
        filepath = self.backup_dir / filename
        
        with open(filepath, 'wb') as f:
            f.write(encrypted_data)
        
        return str(filepath)
    
    def _encrypt_backup_data(self, backup_data: Dict[str, Any], password: str) -> bytes:
        """加密备份数据"""
        # 生成加密密钥
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # 加密数据
        cipher = Fernet(key)
        json_data = json.dumps(backup_data).encode()
        encrypted_data = cipher.encrypt(json_data)
        
        # 返回 salt + 加密数据
        return salt + encrypted_data
    
    def _load_backup_file(self, backup_file: str, password: str = None) -> Optional[Dict[str, Any]]:
        """加载备份文件"""
        filepath = Path(backup_file)
        
        if filepath.suffix == '.enc':
            # 加密文件
            if not password:
                print("❌ 加密备份文件需要密码")
                return None
            
            with open(filepath, 'rb') as f:
                encrypted_data = f.read()
            
            # 解密数据
            salt = encrypted_data[:16]
            encrypted_content = encrypted_data[16:]
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            
            cipher = Fernet(key)
            decrypted_data = cipher.decrypt(encrypted_content)
            
            return json.loads(decrypted_data.decode())
        
        else:
            # 普通 JSON 文件
            with open(filepath, 'r') as f:
                return json.load(f)

def main():
    parser = argparse.ArgumentParser(description='备份系统')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 创建 keystore 备份
    keystore_parser = subparsers.add_parser('keystore', help='创建 keystore 备份')
    keystore_parser.add_argument('pubkeys', nargs='+', help='验证者公钥列表')
    keystore_parser.add_argument('--password', required=True, help='keystore 密码')
    keystore_parser.add_argument('--name', help='备份名称')
    
    # 创建 mnemonic 备份
    mnemonic_parser = subparsers.add_parser('mnemonic', help='创建 mnemonic 备份')
    mnemonic_parser.add_argument('pubkeys', nargs='+', help='验证者公钥列表')
    mnemonic_parser.add_argument('--name', help='备份名称')
    
    # 创建加密备份
    encrypted_parser = subparsers.add_parser('encrypted', help='创建加密备份')
    encrypted_parser.add_argument('pubkeys', nargs='+', help='验证者公钥列表')
    encrypted_parser.add_argument('--password', required=True, help='加密密码')
    encrypted_parser.add_argument('--name', help='备份名称')
    
    # 创建批次备份
    batch_parser = subparsers.add_parser('batch', help='创建批次备份')
    batch_parser.add_argument('batch_id', help='批次ID')
    batch_parser.add_argument('--format', choices=['keystore', 'mnemonic', 'both', 'encrypted'], 
                             default='both', help='备份格式')
    batch_parser.add_argument('--password', help='密码（keystore/encrypted 格式需要）')
    
    # 恢复备份
    restore_parser = subparsers.add_parser('restore', help='从备份恢复')
    restore_parser.add_argument('backup_file', help='备份文件路径')
    restore_parser.add_argument('--password', help='密码（加密备份需要）')
    restore_parser.add_argument('--dry-run', action='store_true', help='试运行模式')
    
    # 列出备份
    list_parser = subparsers.add_parser('list', help='列出所有备份')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        backup_system = BackupSystem()
        
        if args.command == 'keystore':
            backup_system.create_keystore_backup(args.pubkeys, args.password, args.name)
        
        elif args.command == 'mnemonic':
            backup_system.create_mnemonic_backup(args.pubkeys, args.name)
        
        elif args.command == 'encrypted':
            backup_system.create_encrypted_backup(args.pubkeys, args.password, args.name)
        
        elif args.command == 'batch':
            if args.format in ['keystore', 'encrypted'] and not args.password:
                print("❌ 该格式需要密码")
                return
            
            results = backup_system.create_batch_backup(args.batch_id, args.format, args.password)
            print(f"\n✅ 批次备份完成:")
            for format_type, filepath in results.items():
                print(f"  {format_type}: {filepath}")
        
        elif args.command == 'restore':
            backup_system.restore_from_backup(args.backup_file, args.password, args.dry_run)
        
        elif args.command == 'list':
            backups = backup_system.list_backups()
            print(f"\n📋 备份文件 ({len(backups)} 个):")
            for backup in backups:
                print(f"  📁 {backup['name']}")
                print(f"     类型: {backup['type']} | 密钥: {backup['key_count']} | 大小: {backup['size']} bytes")
                print(f"     创建: {backup['created_at']}")
                print(f"     文件: {backup['file']}")
                print()
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
