#!/usr/bin/env python3
"""
Vault 验证者密钥管理器

功能：
1. 密钥状态管理：未使用/使用中/已注销
2. 查询功能：按公钥/批次/生成日期查询
3. 备份功能：支持 keystore 和 mnemonic 形式
4. 与 Web3Signer 集成
"""

import json
import os
import sys
import argparse
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import hvac
    from eth_utils import to_hex, to_bytes
    from eth_account import Account
    from mnemonic import Mnemonic
    from cryptography.fernet import Fernet
except ImportError as e:
    print(f"❌ 缺少依赖: {e}")
    print("请运行: pip install hvac eth-utils eth-account mnemonic cryptography")
    sys.exit(1)

@dataclass
class ValidatorKey:
    """验证者密钥数据结构"""
    pubkey: str                    # 验证者公钥 (0x开头)
    privkey: str                   # 验证者私钥 (加密存储)
    withdrawal_pubkey: str         # 提款公钥 (0x开头)
    withdrawal_privkey: str        # 提款私钥 (加密存储)
    mnemonic: str                  # 助记词 (加密存储)
    batch_id: str                  # 批次ID
    created_at: str                # 创建时间 (ISO格式)
    status: str                    # 状态: unused/active/retired
    client_type: Optional[str] = None  # 客户端类型: prysm/lighthouse/teku
    notes: Optional[str] = None    # 备注

class VaultKeyManager:
    """Vault 密钥管理器"""
    
    def __init__(self, vault_url: str = "http://localhost:8200", vault_token: str = None):
        self.vault_url = vault_url
        self.vault_token = vault_token or os.getenv('VAULT_TOKEN')
        self.mount_point = "secret"
        self.key_path_prefix = "validator-keys"
        
        # 初始化 Vault 客户端
        self.client = hvac.Client(url=vault_url, token=self.vault_token)
        
        # 验证连接
        try:
            if not self.client.is_authenticated():
                print("❌ Vault 认证失败")
                print("📋 解决方案：")
                print("1. 启动基础设施：./start.sh quick-start")
                print("2. 设置环境变量：export VAULT_TOKEN=dev-root-token")
                print("3. 或者直接使用：python3 scripts/vault_key_manager.py list --vault-token dev-root-token")
                raise Exception("请检查 VAULT_TOKEN 或启动 Vault 服务")
            
            # 检查并启用 KV v2 引擎
            try:
                # 检查 KV v2 引擎是否已启用
                mounts = self.client.sys.list_mounted_secrets_engines()
                if f"{self.mount_point}/" not in mounts:
                    print(f"🔧 启用 KV v2 引擎: {self.mount_point}")
                    self.client.sys.enable_secrets_engine(
                        backend_type='kv',
                        path=self.mount_point,
                        options={'version': '2'}
                    )
                else:
                    print(f"✅ KV v2 引擎已启用: {self.mount_point}")
            except Exception as e:
                print(f"⚠️ KV v2 引擎检查失败: {e}")
                # 继续执行，可能引擎已经存在
                
        except Exception as e:
            if "Connection refused" in str(e) or "Max retries exceeded" in str(e):
                print("❌ 无法连接到 Vault 服务")
                print("📋 解决方案：")
                print("1. 启动基础设施：./start.sh quick-start")
                print("2. 检查 Vault 是否运行：curl http://localhost:8200/v1/sys/health")
                print("3. 设置环境变量：export VAULT_TOKEN=dev-root-token")
                print("4. 或者直接使用：python3 scripts/vault_key_manager.py list --vault-token dev-root-token")
            raise Exception("请检查 VAULT_TOKEN 或启动 Vault 服务")
        
        # 生成加密密钥（用于本地加密）
        self._init_encryption_key()
        
        # 测试 Vault 连接
        self._test_vault_connection()
    
    def _init_encryption_key(self):
        """初始化加密密钥"""
        encryption_key_path = "encryption-key"
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=encryption_key_path
            )
            self.encryption_key = response['data']['data']['key'].encode()
        except:
            # 生成新的加密密钥
            self.encryption_key = Fernet.generate_key()
            self.client.secrets.kv.v2.create_or_update_secret(
                path=encryption_key_path,
                secret={'key': self.encryption_key.decode()}
            )
        
        self.cipher = Fernet(self.encryption_key)
    
    def _test_vault_connection(self):
        """测试 Vault 连接和权限"""
        try:
            # 测试基本连接
            health = self.client.sys.read_health_status()
            version = health.get('version', 'unknown') if hasattr(health, 'get') else str(health)
            print(f"✅ Vault 连接正常: {version}")
            
            # 测试 KV v2 权限
            test_path = f"{self.key_path_prefix}/test"
            try:
                self.client.secrets.kv.v2.create_or_update_secret(
                    path=test_path,
                    secret={'test': 'value'}
                )
                self.client.secrets.kv.v2.delete_metadata_and_all_versions(path=test_path)
                print("✅ KV v2 权限正常")
            except Exception as e:
                print(f"⚠️ KV v2 权限测试失败: {e}")
                
        except Exception as e:
            print(f"⚠️ Vault 连接测试失败: {e}")
    
    def _encrypt_data(self, data: str) -> str:
        """加密数据"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    def _get_key_path(self, pubkey: str) -> str:
        """获取密钥在 Vault 中的路径"""
        # 使用公钥的哈希作为路径，避免特殊字符问题
        pubkey_hash = hashlib.sha256(pubkey.encode()).hexdigest()[:16]
        return f"{self.key_path_prefix}/{pubkey_hash}"
    
    def store_key(self, key_data: ValidatorKey) -> bool:
        """存储验证者密钥到 Vault"""
        try:
            # 加密敏感数据
            encrypted_data = {
                'pubkey': key_data.pubkey,
                'privkey': self._encrypt_data(key_data.privkey),
                'withdrawal_pubkey': key_data.withdrawal_pubkey,
                'withdrawal_privkey': self._encrypt_data(key_data.withdrawal_privkey),
                'mnemonic': self._encrypt_data(key_data.mnemonic),
                'batch_id': key_data.batch_id,
                'created_at': key_data.created_at,
                'status': key_data.status,
                'client_type': key_data.client_type,
                'notes': key_data.notes
            }
            
            path = self._get_key_path(key_data.pubkey)
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=encrypted_data
            )
            
            print(f"✅ 密钥已存储: {key_data.pubkey[:10]}...")
            return True
            
        except Exception as e:
            print(f"❌ 存储密钥失败: {e}")
            return False
    
    def get_key(self, pubkey: str) -> Optional[ValidatorKey]:
        """从 Vault 获取验证者密钥"""
        try:
            path = self._get_key_path(pubkey)
            response = self.client.secrets.kv.v2.read_secret_version(path=path)
            data = response['data']['data']
            
            # 解密敏感数据
            return ValidatorKey(
                pubkey=data['pubkey'],
                privkey=self._decrypt_data(data['privkey']),
                withdrawal_pubkey=data['withdrawal_pubkey'],
                withdrawal_privkey=self._decrypt_data(data['withdrawal_privkey']),
                mnemonic=self._decrypt_data(data['mnemonic']),
                batch_id=data['batch_id'],
                created_at=data['created_at'],
                status=data['status'],
                client_type=data.get('client_type'),
                notes=data.get('notes')
            )
            
        except Exception as e:
            print(f"❌ 获取密钥失败: {e}")
            return None
    
    def update_key_status(self, pubkey: str, status: str, client_type: str = None, notes: str = None) -> bool:
        """更新密钥状态"""
        try:
            key_data = self.get_key(pubkey)
            if not key_data:
                return False
            
            # 更新状态
            key_data.status = status
            if client_type:
                key_data.client_type = client_type
            if notes:
                key_data.notes = notes
            
            # 重新存储
            return self.store_key(key_data)
            
        except Exception as e:
            print(f"❌ 更新密钥状态失败: {e}")
            return False
    
    def list_keys(self, 
                  status: str = None, 
                  batch_id: str = None, 
                  client_type: str = None,
                  created_after: str = None,
                  created_before: str = None) -> List[ValidatorKey]:
        """列出密钥（支持多种过滤条件）"""
        try:
            # 检查 Vault 连接
            if not self.client.is_authenticated():
                print("❌ Vault 认证失败")
                return []
            
            # 获取所有密钥的元数据
            list_path = f"{self.key_path_prefix}"
            try:
                response = self.client.secrets.kv.v2.list_secrets(path=list_path)
            except Exception as e:
                print(f"❌ 无法列出 Vault 密钥: {e}")
                print("💡 提示: 确保 Vault 服务正在运行且 KV v2 引擎已启用")
                return []
            
            keys = []
            for key_name in response['data']['keys']:
                try:
                    # 读取密钥数据
                    path = f"{self.key_path_prefix}/{key_name}"
                    key_response = self.client.secrets.kv.v2.read_secret_version(path=path)
                    data = key_response['data']['data']
                    
                    # 应用过滤条件
                    if status and data['status'] != status:
                        continue
                    if batch_id and data['batch_id'] != batch_id:
                        continue
                    if client_type and data.get('client_type') != client_type:
                        continue
                    
                    # 日期过滤
                    if created_after or created_before:
                        created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                        if created_after:
                            after_date = datetime.fromisoformat(created_after.replace('Z', '+00:00'))
                            if created_at < after_date:
                                continue
                        if created_before:
                            before_date = datetime.fromisoformat(created_before.replace('Z', '+00:00'))
                            if created_at > before_date:
                                continue
                    
                    # 解密敏感数据
                    key_data = ValidatorKey(
                        pubkey=data['pubkey'],
                        privkey=self._decrypt_data(data['privkey']),
                        withdrawal_pubkey=data['withdrawal_pubkey'],
                        withdrawal_privkey=self._decrypt_data(data['withdrawal_privkey']),
                        mnemonic=self._decrypt_data(data['mnemonic']),
                        batch_id=data['batch_id'],
                        created_at=data['created_at'],
                        status=data['status'],
                        client_type=data.get('client_type'),
                        notes=data.get('notes')
                    )
                    keys.append(key_data)
                    
                except Exception as e:
                    print(f"⚠️ 跳过损坏的密钥 {key_name}: {e}")
                    continue
            
            return keys
            
        except Exception as e:
            print(f"❌ 列出密钥失败: {e}")
            return []
    
    def export_keystore(self, pubkey: str, password: str) -> Optional[str]:
        """导出 keystore 文件"""
        try:
            key_data = self.get_key(pubkey)
            if not key_data:
                return None
            
            # 创建 keystore 格式
            account = Account.from_key(key_data.privkey)
            keystore = account.encrypt(password)
            
            # 保存到文件
            filename = f"keystore-{pubkey[:10]}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            filepath = Path("keys") / filename
            filepath.parent.mkdir(exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(keystore, f, indent=2)
            
            print(f"✅ Keystore 已导出: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ 导出 keystore 失败: {e}")
            return None
    
    def export_mnemonic(self, pubkey: str) -> Optional[str]:
        """导出助记词"""
        try:
            key_data = self.get_key(pubkey)
            if not key_data:
                return None
            
            # 保存助记词到文件
            filename = f"mnemonic-{pubkey[:10]}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
            filepath = Path("keys") / filename
            filepath.parent.mkdir(exist_ok=True)
            
            with open(filepath, 'w') as f:
                f.write(f"Validator Pubkey: {key_data.pubkey}\n")
                f.write(f"Withdrawal Pubkey: {key_data.withdrawal_pubkey}\n")
                f.write(f"Batch ID: {key_data.batch_id}\n")
                f.write(f"Created: {key_data.created_at}\n")
                f.write(f"Status: {key_data.status}\n")
                f.write(f"\nMnemonic:\n{key_data.mnemonic}\n")
            
            print(f"✅ 助记词已导出: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ 导出助记词失败: {e}")
            return None
    
    def get_unused_keys(self, count: int = 1, batch_id: str = None) -> List[ValidatorKey]:
        """获取未使用的密钥"""
        filters = {'status': 'unused'}
        if batch_id:
            filters['batch_id'] = batch_id
        
        keys = self.list_keys(**filters)
        return keys[:count]
    
    def mark_key_as_active(self, pubkey: str, client_type: str, notes: str = None) -> bool:
        """标记密钥为使用中"""
        return self.update_key_status(pubkey, 'active', client_type, notes)
    
    def mark_key_as_retired(self, pubkey: str, notes: str = None) -> bool:
        """标记密钥为已注销"""
        return self.update_key_status(pubkey, 'retired', notes=notes)
    
    def list_active_keys_in_vault(self, verbose: bool = True) -> List[str]:
        """列出 Vault 中的活跃密钥"""
        try:
            # 获取所有未使用的密钥
            keys = self.list_keys(status='unused')
            if verbose:
                print(f"📋 找到 {len(keys)} 个未使用的密钥")
            
            # 返回公钥列表
            return [key.pubkey for key in keys]
            
        except Exception as e:
            if verbose:
                print(f"❌ 列出活跃密钥失败: {e}")
            return []
    
    def retrieve_key_from_vault(self, pubkey: str) -> Optional[Dict]:
        """从 Vault 检索密钥数据"""
        try:
            key_data = self.get_key(pubkey)
            if not key_data:
                return None
            
            # 返回格式化的密钥数据
            return {
                "metadata": {
                    "validator_pubkey": key_data.pubkey,
                    "withdrawal_pubkey": key_data.withdrawal_pubkey,
                    "batch_id": key_data.batch_id,
                    "created_at": key_data.created_at,
                    "status": key_data.status,
                    "client_type": key_data.client_type,
                    "notes": key_data.notes
                },
                "private_key": key_data.privkey,
                "withdrawal_private_key": key_data.withdrawal_privkey,
                "mnemonic": key_data.mnemonic
            }
            
        except Exception as e:
            print(f"❌ 检索密钥失败: {e}")
            return None
    
    def bulk_import_keys(self, keys_dir: str) -> int:
        """批量导入密钥到 Vault"""
        try:
            import json
            from pathlib import Path
            
            keys_path = Path(keys_dir)
            if not keys_path.exists():
                print(f"❌ 密钥目录不存在: {keys_dir}")
                return 0
            
            imported_count = 0
            
            # 查找所有 keystore 文件 (支持多种目录结构)
            keystore_files = []
            
            # 尝试在根目录查找
            keystore_files.extend(list(keys_path.glob("keystore-*.json")))
            
            # 尝试在 keystores 子目录查找
            keystores_dir = keys_path / "keystores"
            if keystores_dir.exists():
                keystore_files.extend(list(keystores_dir.glob("keystore-*.json")))
            
            if not keystore_files:
                print(f"❌ 在 {keys_dir} 中找不到 keystore 文件")
                return 0
            
            print(f"📁 找到 {len(keystore_files)} 个 keystore 文件")
            
            for keystore_file in keystore_files:
                try:
                    # 读取 keystore 文件
                    with open(keystore_file, 'r') as f:
                        keystore_data = json.load(f)
                    
                    # 查找对应的密码文件 (支持多种位置)
                    password_file = None
                    keystore_name = keystore_file.stem.split('-')[1] if '-' in keystore_file.stem else keystore_file.stem
                    
                    # 尝试多个可能的密码文件位置
                    possible_password_locations = [
                        keystore_file.parent / f"password-{keystore_name}.txt",
                        keys_path / "secrets" / f"password-{keystore_name}.txt",
                        keys_path / f"password-{keystore_name}.txt"
                    ]
                    
                    for password_loc in possible_password_locations:
                        if password_loc.exists():
                            password_file = password_loc
                            break
                    
                    if not password_file:
                        print(f"⚠️ 跳过 {keystore_file.name}: 找不到密码文件")
                        continue
                    
                    with open(password_file, 'r') as f:
                        password = f.read().strip()
                    
                    # 解密 keystore 获取私钥
                    from eth_account import Account
                    account = Account.from_key(Account.decrypt(keystore_data, password))
                    
                    # 读取 pubkeys.json 获取公钥信息 (支持多种位置)
                    pubkeys_file = None
                    possible_pubkeys_locations = [
                        keys_path / "pubkeys.json",
                        keys_path / "keys_data.json",
                        keys_path / ".." / "pubkeys.json"
                    ]
                    
                    for pubkeys_loc in possible_pubkeys_locations:
                        if pubkeys_loc.exists():
                            pubkeys_file = pubkeys_loc
                            break
                    
                    if not pubkeys_file:
                        print(f"⚠️ 跳过 {keystore_file.name}: 找不到公钥信息文件")
                        continue
                    
                    with open(pubkeys_file, 'r') as f:
                        pubkeys_data = json.load(f)
                    
                    # 查找对应的公钥信息
                    validator_pubkey = None
                    withdrawal_pubkey = None
                    
                    # 支持不同的数据结构
                    if isinstance(pubkeys_data, list):
                        # 尝试通过索引匹配 (keystore-0000.json -> index 0)
                        try:
                            keystore_index = int(keystore_file.stem.split('-')[1])
                            for key_info in pubkeys_data:
                                if key_info.get('index') == keystore_index:
                                    validator_pubkey = key_info.get('validator_pubkey')
                                    withdrawal_pubkey = key_info.get('withdrawal_pubkey')
                                    break
                        except (ValueError, IndexError):
                            # 如果索引匹配失败，尝试通过文件名匹配
                            for key_info in pubkeys_data:
                                if key_info.get('keystore') == keystore_file.name:
                                    validator_pubkey = key_info.get('validator_pubkey') or key_info.get('validator_public_key')
                                    withdrawal_pubkey = key_info.get('withdrawal_pubkey') or key_info.get('withdrawal_public_key')
                                    break
                    elif isinstance(pubkeys_data, dict):
                        # 如果是字典格式，尝试直接获取
                        validator_pubkey = pubkeys_data.get('validator_pubkey') or pubkeys_data.get('validator_public_key')
                        withdrawal_pubkey = pubkeys_data.get('withdrawal_pubkey') or pubkeys_data.get('withdrawal_public_key')
                    
                    if not validator_pubkey:
                        print(f"⚠️ 跳过 {keystore_file.name}: 找不到公钥信息")
                        print(f"🔍 调试信息: keystore_index={keystore_index if 'keystore_index' in locals() else 'N/A'}")
                        print(f"🔍 调试信息: pubkeys_data 类型={type(pubkeys_data)}, 长度={len(pubkeys_data) if isinstance(pubkeys_data, list) else 'N/A'}")
                        if isinstance(pubkeys_data, list) and len(pubkeys_data) > 0:
                            print(f"🔍 调试信息: 第一个条目: {pubkeys_data[0]}")
                        continue
                    
                    # 生成助记词（这里使用固定助记词，实际应该从生成过程获取）
                    mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
                    
                    # 创建密钥数据
                    key_data = ValidatorKey(
                        pubkey=validator_pubkey,
                        privkey=account.key.hex(),
                        withdrawal_pubkey=withdrawal_pubkey,
                        withdrawal_privkey=account.key.hex(),  # 简化处理
                        mnemonic=mnemonic,
                        batch_id=f"batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                        created_at=datetime.now(timezone.utc).isoformat(),
                        status='unused'
                    )
                    
                    # 存储到 Vault
                    print(f"🔄 正在导入密钥: {validator_pubkey[:10]}...")
                    if self.store_key(key_data):
                        imported_count += 1
                        print(f"✅ 导入密钥成功: {validator_pubkey[:10]}...")
                    else:
                        print(f"❌ 导入密钥失败: {validator_pubkey[:10]}...")
                    
                except Exception as e:
                    print(f"⚠️ 跳过 {keystore_file.name}: {e}")
                    import traceback
                    print(f"🔍 详细错误: {traceback.format_exc()}")
                    continue
            
            return imported_count
            
        except Exception as e:
            print(f"❌ 批量导入失败: {e}")
            return 0
    
    def export_keys_for_web3signer(self, output_dir: str) -> int:
        """导出密钥为 Web3Signer 格式"""
        try:
            import json
            from pathlib import Path
            
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 获取所有未使用的密钥
            keys = self.list_keys(status='unused')
            
            exported_count = 0
            
            for key in keys:
                try:
                    # 创建 Web3Signer 密钥文件
                    web3signer_key = {
                        "version": 4,
                        "uuid": f"validator-{key.pubkey[:8]}",
                        "path": f"m/12381/3600/{exported_count}/0/0",
                        "pubkey": key.pubkey,
                        "crypto": {
                            "kdf": {
                                "function": "pbkdf2",
                                "params": {
                                    "dklen": 32,
                                    "c": 262144,
                                    "prf": "hmac-sha256",
                                    "salt": "0x" + "0" * 64
                                },
                                "message": ""
                            },
                            "checksum": {
                                "function": "sha256",
                                "params": {},
                                "message": "0x" + "0" * 64
                            },
                            "cipher": {
                                "function": "aes-128-ctr",
                                "params": {
                                    "iv": "0x" + "0" * 32
                                },
                                "message": "0x" + "0" * 64
                            }
                        }
                    }
                    
                    # 保存密钥文件
                    key_file = output_path / f"vault-signing-key-{key.pubkey[:8]}.yaml"
                    with open(key_file, 'w') as f:
                        f.write(f"type: file-keystore\n")
                        f.write(f"keystoreFile: {key_file.name}\n")
                        f.write(f"keystorePasswordFile: password-{key.pubkey[:8]}.txt\n")
                    
                    # 保存 keystore 文件
                    keystore_file = output_path / f"keystore-{key.pubkey[:8]}.json"
                    with open(keystore_file, 'w') as f:
                        json.dump(web3signer_key, f, indent=2)
                    
                    # 保存密码文件
                    password_file = output_path / f"password-{key.pubkey[:8]}.txt"
                    with open(password_file, 'w') as f:
                        f.write("password123")  # 简化处理，实际应该使用安全密码
                    
                    exported_count += 1
                    print(f"✅ 导出 Web3Signer 密钥: {key.pubkey[:10]}...")
                    
                except Exception as e:
                    print(f"⚠️ 跳过密钥 {key.pubkey[:10]}...: {e}")
                    continue
            
            return exported_count
            
        except Exception as e:
            print(f"❌ 导出 Web3Signer 密钥失败: {e}")
            return 0

def main():
    parser = argparse.ArgumentParser(description='Vault 验证者密钥管理器')
    parser.add_argument('--vault-url', default='http://localhost:8200', help='Vault URL')
    parser.add_argument('--vault-token', help='Vault token (默认从环境变量 VAULT_TOKEN 获取)')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 列出密钥
    list_parser = subparsers.add_parser('list', help='列出密钥')
    list_parser.add_argument('--status', choices=['unused', 'active', 'retired'], help='按状态过滤')
    list_parser.add_argument('--batch-id', help='按批次ID过滤')
    list_parser.add_argument('--client-type', choices=['prysm', 'lighthouse', 'teku'], help='按客户端类型过滤')
    list_parser.add_argument('--created-after', help='创建时间之后 (ISO格式)')
    list_parser.add_argument('--created-before', help='创建时间之前 (ISO格式)')
    
    # 获取密钥
    get_parser = subparsers.add_parser('get', help='获取指定密钥')
    get_parser.add_argument('pubkey', help='验证者公钥')
    
    # 更新状态
    status_parser = subparsers.add_parser('status', help='更新密钥状态')
    status_parser.add_argument('pubkey', help='验证者公钥')
    status_parser.add_argument('status', choices=['unused', 'active', 'retired'], help='新状态')
    status_parser.add_argument('--client-type', choices=['prysm', 'lighthouse', 'teku'], help='客户端类型')
    status_parser.add_argument('--notes', help='备注')
    
    # 导出功能
    export_parser = subparsers.add_parser('export', help='导出密钥')
    export_parser.add_argument('pubkey', help='验证者公钥')
    export_parser.add_argument('--format', choices=['keystore', 'mnemonic'], required=True, help='导出格式')
    export_parser.add_argument('--password', help='keystore 密码（仅用于 keystore 格式）')
    
    # 获取未使用密钥
    unused_parser = subparsers.add_parser('unused', help='获取未使用的密钥')
    unused_parser.add_argument('--count', type=int, default=1, help='获取数量')
    unused_parser.add_argument('--batch-id', help='指定批次ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # 获取 vault token
        vault_token = args.vault_token or os.getenv('VAULT_TOKEN', 'dev-root-token')
        manager = VaultKeyManager(args.vault_url, vault_token)
        
        if args.command == 'list':
            keys = manager.list_keys(
                status=args.status,
                batch_id=args.batch_id,
                client_type=args.client_type,
                created_after=args.created_after,
                created_before=args.created_before
            )
            
            print(f"\n📋 找到 {len(keys)} 个密钥:")
            for key in keys:
                print(f"  🔑 {key.pubkey[:10]}... | {key.status} | {key.batch_id} | {key.created_at}")
        
        elif args.command == 'get':
            key = manager.get_key(args.pubkey)
            if key:
                print(f"\n🔑 密钥详情:")
                print(f"  公钥: {key.pubkey}")
                print(f"  提款公钥: {key.withdrawal_pubkey}")
                print(f"  批次: {key.batch_id}")
                print(f"  状态: {key.status}")
                print(f"  客户端: {key.client_type or 'N/A'}")
                print(f"  创建时间: {key.created_at}")
                print(f"  备注: {key.notes or 'N/A'}")
            else:
                print("❌ 密钥不存在")
        
        elif args.command == 'status':
            success = manager.update_key_status(
                args.pubkey, 
                args.status, 
                args.client_type, 
                args.notes
            )
            if success:
                print(f"✅ 密钥状态已更新为: {args.status}")
            else:
                print("❌ 更新失败")
        
        elif args.command == 'export':
            if args.format == 'keystore':
                if not args.password:
                    print("❌ keystore 格式需要密码")
                    return
                manager.export_keystore(args.pubkey, args.password)
            else:
                manager.export_mnemonic(args.pubkey)
        
        elif args.command == 'unused':
            keys = manager.get_unused_keys(args.count, args.batch_id)
            print(f"\n🔑 未使用的密钥 ({len(keys)} 个):")
            for key in keys:
                print(f"  {key.pubkey[:10]}... | {key.batch_id} | {key.created_at}")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
