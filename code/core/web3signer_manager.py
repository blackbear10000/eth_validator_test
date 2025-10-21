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

class Web3SignerManager:
    """Web3Signer 密钥管理器"""
    
    def __init__(self, web3signer_url: str = "http://localhost:9000", 
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
            from vault_key_manager import VaultKeyManager
            
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
        """为单个密钥创建 Web3Signer 配置"""
        # 计算与 VaultKeyManager 一致的路径
        import hashlib
        pubkey = key_data['pubkey']
        pubkey_hash = hashlib.sha256(pubkey.encode()).hexdigest()[:16]
        vault_path = f"/v1/secret/data/validator-keys/{pubkey_hash}"
        
        # Web3Signer HashiCorp Vault 配置格式
        # 注意：Web3Signer 需要正确的 Vault 连接配置
        return {
            "type": "hashicorp",
            "keyType": "BLS",
            "tlsEnabled": "false",
            "keyPath": vault_path,
            "keyName": "privkey",  # VaultKeyManager 中存储私钥的字段名
            "serverHost": "vault",  # 使用 Docker 网络中的服务名
            "serverPort": "8200",
            "timeout": "10000",
            "token": "dev-root-token"
        }
    
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
                
                # 保存配置文件 (Web3Signer 需要 JSON 格式)
                config_file = self.keys_dir / f"vault-signing-key-{pubkey}.json"
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                print(f"✅ 密钥配置已保存: {config_file}")
                loaded_count += 1
                
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
            result = subprocess.run(
                ["docker", "restart", "web3signer"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Web3Signer 重启成功")
                # 等待 Web3Signer 启动
                print("⏳ 等待 Web3Signer 启动...")
                time.sleep(10)
                return self._test_web3signer_connection()
            else:
                print(f"❌ Web3Signer 重启失败: {result.stderr}")
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
    parser.add_argument("command", choices=["load", "status", "verify"], 
                       help="命令: load(加载密钥), status(状态), verify(验证)")
    
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


if __name__ == "__main__":
    main()
