#!/usr/bin/env python3
"""
Web3Signer 密钥管理器
负责将 Vault 中的密钥动态加载到 Web3Signer
"""

import os
import sys
import json
import yaml
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
from datetime import datetime

class Web3SignerManager:
    """Web3Signer 密钥管理器"""
    
    def __init__(self, web3signer_url: str = "http://localhost:9002", 
                 vault_url: str = "http://localhost:8200",
                 vault_token: str = "dev-root-token"):
        self.web3signer_url = web3signer_url
        self.vault_url = vault_url
        self.vault_token = vault_token
        self.keys_dir = Path("infra/web3signer/keys")
        
    def _test_web3signer_connection(self) -> bool:
        """测试 Web3Signer 连接"""
        try:
            response = requests.get(f"{self.web3signer_url}/upcheck", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Web3Signer 连接失败: {e}")
            return False
    
    def _test_vault_connection(self) -> bool:
        """测试 Vault 连接"""
        try:
            headers = {"X-Vault-Token": self.vault_token}
            response = requests.get(f"{self.vault_url}/v1/sys/health", headers=headers, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Vault 连接失败: {e}")
            return False
    
    def get_loaded_keys(self) -> List[str]:
        """获取 Web3Signer 中已加载的密钥"""
        try:
            response = requests.get(f"{self.web3signer_url}/api/v1/eth2/publicKeys", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 获取密钥列表失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ 获取密钥列表失败: {e}")
            return []
    
    def get_vault_keys(self) -> List[Dict[str, Any]]:
        """从 Vault 获取所有验证者密钥"""
        try:
            # 直接使用 VaultKeyManager 来获取密钥，确保路径一致
            from core.vault_key_manager import VaultKeyManager
            
            vault_manager = VaultKeyManager(self.vault_url, self.vault_token)
            
            # 获取所有密钥
            all_keys = vault_manager.list_keys()
            
            if not all_keys:
                print("❌ Vault 中没有找到密钥")
                return []
            
            # 转换为 Web3Signer 需要的格式
            keys = []
            for key in all_keys:
                keys.append({
                    'name': key.pubkey,  # 使用公钥作为名称
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
                })
            
            print(f"✅ 从 Vault 获取到 {len(keys)} 个密钥")
            return keys
            
        except Exception as e:
            print(f"❌ 从 Vault 获取密钥失败: {e}")
            return []
    
    def create_web3signer_key_config(self, key_data: Dict[str, Any]) -> Dict[str, str]:
        """为单个密钥创建 Web3Signer 配置 - 使用完整公钥作为路径"""
        pubkey = key_data['pubkey']
        
        # 为 Web3Signer 创建兼容的 Vault 存储
        self._store_key_for_web3signer(key_data, pubkey)
        
        # 使用完整公钥作为路径
        vault_path = f"/v1/secret/data/web3signer-keys/{pubkey}"
        
        # Web3Signer HashiCorp Vault 配置格式
        # 根据官方文档：https://docs.web3signer.consensys.io/reference/key-config-file-params
        return {
            "type": "hashicorp",
            "keyType": "BLS",
            "tlsEnabled": "false",
            "keyPath": vault_path,
            "keyName": "value",  # 官方文档使用 "value" 字段名
            "serverHost": "vault",  # 使用 Docker 网络中的服务名
            "serverPort": "8200",
            "timeout": "10000",
            "token": "dev-root-token"
        }
    
    def _store_key_for_web3signer(self, key_data: Dict[str, Any], pubkey: str):
        """为 Web3Signer 存储密钥到 Vault - 使用完整公钥作为路径"""
        try:
            import requests
            
            # 从 VaultKeyManager 获取原始私钥数据
            from core.vault_key_manager import VaultKeyManager
            vault_manager = VaultKeyManager(self.vault_url, self.vault_token)
            
            # 获取完整的密钥数据
            full_key_data = vault_manager.get_key(pubkey)
            if not full_key_data:
                print(f"❌ 无法获取密钥数据: {pubkey[:10]}...")
                return
            
            # 获取私钥（已经是解密后的格式）
            privkey = full_key_data.privkey
            if privkey.startswith('0x'):
                privkey = privkey[2:]  # 移除 0x 前缀
            
            # 验证私钥格式
            if len(privkey) != 64:
                print(f"❌ 私钥格式错误: 长度 {len(privkey)}，期望 64")
                return
            
            print(f"🔍 私钥格式验证: 长度={len(privkey)}, 前缀={privkey[:8]}...")
            
            # 为 Web3Signer 创建兼容的 Vault 存储
            vault_data = {
                "value": privkey  # Web3Signer 期望的字段名
            }
            
            # 存储到 Vault（使用完整公钥作为路径）
            headers = {"X-Vault-Token": self.vault_token}
            web3signer_path = f"/v1/secret/data/web3signer-keys/{pubkey}"
            
            response = requests.post(
                f"{self.vault_url}{web3signer_path}",
                headers=headers,
                json={"data": vault_data},
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                print(f"✅ Web3Signer 密钥已存储到 Vault: {web3signer_path}")
                print(f"   存储的数据: {vault_data}")
                # 更新配置中的路径
                key_data['web3signer_path'] = web3signer_path
            else:
                print(f"❌ Web3Signer 密钥存储失败: {response.status_code} - {response.text}")
                print(f"   请求数据: {vault_data}")
                print(f"   请求路径: {web3signer_path}")
                
        except Exception as e:
            print(f"❌ 存储 Web3Signer 密钥失败: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
    
    def load_keys_to_web3signer(self) -> bool:
        """将 Vault 中的密钥加载到 Web3Signer"""
        print("🔧 开始加载密钥到 Web3Signer...")
        
        # 检查连接
        if not self._test_web3signer_connection():
            print("❌ Web3Signer 连接失败")
            return False
        
        if not self._test_vault_connection():
            print("❌ Vault 连接失败")
            return False
        
        # 获取 Vault 中的密钥
        vault_keys = self.get_vault_keys()
        if not vault_keys:
            print("❌ Vault 中没有找到密钥")
            return False
        
        print(f"📋 找到 {len(vault_keys)} 个密钥需要加载")
        
        # 确保 keys 目录存在
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
        # 调试：打印 keys 目录路径
        print(f"🔍 Keys 目录路径: {self.keys_dir.absolute()}")
        
        # 为每个密钥创建配置文件
        loaded_count = 0
        for key_data in vault_keys:
            try:
                pubkey = key_data['pubkey']
                if not pubkey:
                    print(f"⚠️  跳过无效密钥: {key_data['name']}")
                    continue
                
                # 创建 Web3Signer 密钥配置
                config = self.create_web3signer_key_config(key_data)
                
                # 调试：打印配置信息
                print(f"🔍 密钥配置调试:")
                print(f"   公钥: {pubkey[:10]}...")
                print(f"   Vault 路径: {config['keyPath']}")
                print(f"   字段名: {config['keyName']}")
                
                # 保存配置文件 (Web3Signer 需要 YAML 格式)
                config_file = self.keys_dir / f"vault-{pubkey[:16]}.yaml"
                with open(config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                
                # 验证文件是否真的被创建
                if config_file.exists():
                    print(f"✅ 密钥配置已保存: {config_file}")
                    print(f"   文件大小: {config_file.stat().st_size} bytes")
                    loaded_count += 1
                else:
                    print(f"❌ 文件保存失败: {config_file}")
                
            except Exception as e:
                print(f"❌ 处理密钥失败 {key_data['name']}: {e}")
        
        print(f"📊 成功加载 {loaded_count}/{len(vault_keys)} 个密钥")
        
        # 重启 Web3Signer 以加载新密钥
        if loaded_count > 0:
            print("🔄 重启 Web3Signer 以加载新密钥...")
            return self._restart_web3signer()
        
        return loaded_count > 0
    
    def _restart_web3signer(self) -> bool:
        """重启 Web3Signer 容器"""
        try:
            import subprocess
            # 重启 web3signer-1
            print("🔄 重启 web3signer-1...")
            result1 = subprocess.run(
                ["docker", "restart", "web3signer-1"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result1.returncode == 0:
                print("✅ web3signer-1 重启成功")
                time.sleep(5)  # 等待启动
            else:
                print(f"⚠️  web3signer-1 重启失败: {result1.stderr}")
            
            # 重启 web3signer-2
            print("🔄 重启 web3signer-2...")
            result2 = subprocess.run(
                ["docker", "restart", "web3signer-2"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result2.returncode == 0:
                print("✅ web3signer-2 重启成功")
                time.sleep(5)  # 等待启动
            else:
                print(f"⚠️  web3signer-2 重启失败: {result2.stderr}")
            
            # 设置结果
            result = result1 if result1.returncode != 0 else result2
            
            if result1.returncode == 0 and result2.returncode == 0:
                print("✅ Web3Signer 集群重启成功")
                # 等待 Web3Signer 启动
                print("⏳ 等待 Web3Signer 启动...")
                time.sleep(10)
                return self._test_web3signer_connection()
            else:
                print(f"❌ Web3Signer 重启失败")
                return False
                
        except Exception as e:
            print(f"❌ 重启 Web3Signer 失败: {e}")
            return False
    
    def verify_keys_loaded(self) -> bool:
        """验证密钥是否成功加载"""
        print("🔍 验证密钥加载状态...")
        
        # 等待 Web3Signer 完全启动
        time.sleep(5)
        
        loaded_keys = self.get_loaded_keys()
        vault_keys = self.get_vault_keys()
        
        print(f"📊 密钥状态:")
        print(f"   Vault 中的密钥: {len(vault_keys)}")
        print(f"   Web3Signer 中的密钥: {len(loaded_keys)}")
        
        if loaded_keys:
            print("✅ 密钥加载成功:")
            for key in loaded_keys:
                print(f"   - {key}")
            return True
        else:
            print("❌ 密钥加载失败")
            return False
    
    def sync_active_keys(self) -> bool:
        """同步活跃密钥到 Web3Signer - 只为 status='active' 的密钥生成配置"""
        print("🔄 同步活跃密钥到 Web3Signer...")
        
        # 检查连接
        if not self._test_web3signer_connection():
            print("❌ Web3Signer 连接失败")
            return False
        
        if not self._test_vault_connection():
            print("❌ Vault 连接失败")
            return False
        
        # 获取活跃密钥
        from core.vault_key_manager import VaultKeyManager
        vault_manager = VaultKeyManager(self.vault_url, self.vault_token)
        active_keys = vault_manager.list_keys(status='active')
        
        if not active_keys:
            print("❌ 没有找到活跃密钥")
            return False
        
        print(f"📋 找到 {len(active_keys)} 个活跃密钥需要同步")
        
        # 确保 keys 目录存在
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
        # 为每个活跃密钥创建配置文件
        synced_count = 0
        for key in active_keys:
            try:
                pubkey = key.pubkey
                if not pubkey:
                    print(f"⚠️  跳过无效密钥: {key.pubkey[:10]}...")
                    continue
                
                # 创建 Web3Signer 密钥配置
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
                
                config = self.create_web3signer_key_config(key_data)
                
                # 保存配置文件 (YAML 格式)
                config_file = self.keys_dir / f"vault-{pubkey[:16]}.yaml"
                with open(config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                
                if config_file.exists():
                    print(f"✅ 活跃密钥配置已保存: {config_file}")
                    synced_count += 1
                else:
                    print(f"❌ 文件保存失败: {config_file}")
                
            except Exception as e:
                print(f"❌ 处理密钥失败 {key.pubkey[:10]}...: {e}")
        
        print(f"📊 成功同步 {synced_count}/{len(active_keys)} 个活跃密钥")
        
        # 重启 Web3Signer 以加载新密钥
        if synced_count > 0:
            print("🔄 重启 Web3Signer 以加载新密钥...")
            return self._restart_web3signer()
        
        return synced_count > 0
    
    def activate_keys(self, pubkeys: List[str]) -> bool:
        """激活指定的密钥并生成 Web3Signer 配置"""
        print(f"🔧 激活 {len(pubkeys)} 个密钥...")
        
        try:
            from core.vault_key_manager import VaultKeyManager
            vault_manager = VaultKeyManager(self.vault_url, self.vault_token)
            
            # 批量更新密钥状态为 'active'
            success_count = 0
            for pubkey in pubkeys:
                if vault_manager.mark_key_as_active(pubkey, 'web3signer', f"激活于 {datetime.now().isoformat()}"):
                    success_count += 1
                    print(f"✅ 密钥已激活: {pubkey[:10]}...")
                else:
                    print(f"❌ 密钥激活失败: {pubkey[:10]}...")
            
            if success_count > 0:
                # 同步活跃密钥到 Web3Signer
                return self.sync_active_keys()
            
            return False
            
        except Exception as e:
            print(f"❌ 激活密钥失败: {e}")
            return False
    
    def deactivate_keys(self, pubkeys: List[str]) -> bool:
        """停用指定的密钥并移除 Web3Signer 配置"""
        print(f"🔧 停用 {len(pubkeys)} 个密钥...")
        
        try:
            from core.vault_key_manager import VaultKeyManager
            vault_manager = VaultKeyManager(self.vault_url, self.vault_token)
            
            # 批量更新密钥状态为 'retired'
            success_count = 0
            for pubkey in pubkeys:
                if vault_manager.mark_key_as_retired(pubkey, f"停用于 {datetime.now().isoformat()}"):
                    success_count += 1
                    print(f"✅ 密钥已停用: {pubkey[:10]}...")
                    
                    # 移除对应的配置文件
                    config_file = self.keys_dir / f"vault-{pubkey[:16]}.yaml"
                    if config_file.exists():
                        config_file.unlink()
                        print(f"🗑️  配置文件已删除: {config_file}")
                else:
                    print(f"❌ 密钥停用失败: {pubkey[:10]}...")
            
            if success_count > 0:
                # 重启 Web3Signer 以移除停用的密钥
                print("🔄 重启 Web3Signer 以移除停用的密钥...")
                return self._restart_web3signer()
            
            return False
            
        except Exception as e:
            print(f"❌ 停用密钥失败: {e}")
            return False
    
    def remove_inactive_key_configs(self) -> int:
        """移除非活跃密钥的配置文件"""
        print("🧹 清理非活跃密钥的配置文件...")
        
        try:
            from core.vault_key_manager import VaultKeyManager
            vault_manager = VaultKeyManager(self.vault_url, self.vault_token)
            
            # 获取所有活跃密钥
            active_keys = vault_manager.list_keys(status='active')
            active_pubkeys = {key.pubkey for key in active_keys}
            
            # 检查 keys 目录中的所有配置文件
            removed_count = 0
            for config_file in self.keys_dir.glob("vault-*.yaml"):
                # 从文件名提取公钥前缀
                filename = config_file.stem  # vault-{pubkey[:16]}
                if filename.startswith("vault-"):
                    pubkey_prefix = filename[6:]  # 移除 "vault-" 前缀
                    
                    # 检查是否有对应的活跃密钥
                    found_active = False
                    for active_pubkey in active_pubkeys:
                        if active_pubkey.startswith(pubkey_prefix):
                            found_active = True
                            break
                    
                    if not found_active:
                        config_file.unlink()
                        print(f"🗑️  已删除非活跃密钥配置: {config_file}")
                        removed_count += 1
            
            print(f"📊 清理了 {removed_count} 个非活跃密钥配置文件")
            return removed_count
            
        except Exception as e:
            print(f"❌ 清理配置文件失败: {e}")
            return 0
    
    def reload_web3signers(self) -> bool:
        """优雅地重新加载所有 Web3Signer 实例"""
        print("🔄 重新加载 Web3Signer 实例...")
        
        try:
            import subprocess
            
            # 重启 web3signer-1
            print("🔄 重启 web3signer-1...")
            result1 = subprocess.run(
                ["docker", "restart", "web3signer-1"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result1.returncode == 0:
                print("✅ web3signer-1 重启成功")
                time.sleep(5)  # 等待启动
            else:
                print(f"⚠️  web3signer-1 重启失败: {result1.stderr}")
            
            # 重启 web3signer-2
            print("🔄 重启 web3signer-2...")
            result2 = subprocess.run(
                ["docker", "restart", "web3signer-2"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result2.returncode == 0:
                print("✅ web3signer-2 重启成功")
                time.sleep(5)  # 等待启动
            else:
                print(f"⚠️  web3signer-2 重启失败: {result2.stderr}")
            
            # 验证两个实例都正常运行
            success1 = self._test_web3signer_connection()
            success2 = self._test_web3signer_connection()  # 测试第二个实例
            
            if success1 and success2:
                print("✅ 所有 Web3Signer 实例运行正常")
                return True
            else:
                print("❌ 部分 Web3Signer 实例运行异常")
                return False
                
        except Exception as e:
            print(f"❌ 重新加载 Web3Signer 失败: {e}")
            return False

    def status(self) -> Dict[str, Any]:
        """获取 Web3Signer 状态"""
        status = {
            "web3signer_connected": self._test_web3signer_connection(),
            "vault_connected": self._test_vault_connection(),
            "loaded_keys": self.get_loaded_keys(),
            "vault_keys": len(self.get_vault_keys())
        }
        
        return status


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web3Signer 密钥管理器")
    parser.add_argument("command", choices=["load", "status", "verify", "sync", "activate", "deactivate", "clean"], 
                       help="命令: load(加载密钥), status(状态), verify(验证), sync(同步活跃密钥), activate(激活密钥), deactivate(停用密钥), clean(清理配置)")
    
    # 为 activate 和 deactivate 命令添加参数
    parser.add_argument("--pubkeys", nargs="+", help="要激活/停用的公钥列表")
    parser.add_argument("--count", type=int, help="要激活的密钥数量")
    
    args = parser.parse_args()
    
    manager = Web3SignerManager()
    
    if args.command == "load":
        success = manager.load_keys_to_web3signer()
        if success:
            print("🎉 密钥加载完成")
            manager.verify_keys_loaded()
        else:
            print("❌ 密钥加载失败")
            sys.exit(1)
    
    elif args.command == "status":
        status = manager.status()
        print("📊 Web3Signer 状态:")
        print(f"   Web3Signer 连接: {'✅' if status['web3signer_connected'] else '❌'}")
        print(f"   Vault 连接: {'✅' if status['vault_connected'] else '❌'}")
        print(f"   已加载密钥: {len(status['loaded_keys'])}")
        print(f"   Vault 密钥: {status['vault_keys']}")
        
        if status['loaded_keys']:
            print("   密钥列表:")
            for key in status['loaded_keys']:
                print(f"     - {key}")
    
    elif args.command == "verify":
        success = manager.verify_keys_loaded()
        if success:
            print("✅ 密钥验证通过")
        else:
            print("❌ 密钥验证失败")
            sys.exit(1)
    
    elif args.command == "sync":
        success = manager.sync_active_keys()
        if success:
            print("✅ 活跃密钥同步完成")
        else:
            print("❌ 活跃密钥同步失败")
            sys.exit(1)
    
    elif args.command == "activate":
        if args.pubkeys:
            success = manager.activate_keys(args.pubkeys)
        elif args.count:
            # 获取指定数量的未使用密钥
            from core.vault_key_manager import VaultKeyManager
            vault_manager = VaultKeyManager(manager.vault_url, manager.vault_token)
            unused_keys = vault_manager.get_unused_keys(args.count)
            pubkeys = [key.pubkey for key in unused_keys]
            success = manager.activate_keys(pubkeys)
        else:
            print("❌ 请指定 --pubkeys 或 --count 参数")
            sys.exit(1)
        
        if success:
            print("✅ 密钥激活完成")
        else:
            print("❌ 密钥激活失败")
            sys.exit(1)
    
    elif args.command == "deactivate":
        if not args.pubkeys:
            print("❌ 请指定要停用的公钥 --pubkeys")
            sys.exit(1)
        
        success = manager.deactivate_keys(args.pubkeys)
        if success:
            print("✅ 密钥停用完成")
        else:
            print("❌ 密钥停用失败")
            sys.exit(1)
    
    elif args.command == "clean":
        removed_count = manager.remove_inactive_key_configs()
        print(f"✅ 清理完成，删除了 {removed_count} 个配置文件")


if __name__ == "__main__":
    main()
