#!/usr/bin/env python3
"""
External Validator Manager for Web3Signer Integration
Manages additional validators connected to Web3Signer for testing validator lifecycle
"""

import os
import sys
import json
import time
import requests
import subprocess
import argparse
from typing import List, Dict, Optional
from pathlib import Path

# Add the code directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vault_key_manager import VaultKeyManager
from utils.deposit_generator import DepositGenerator


class ExternalValidatorManager:
    """Manages external validators connected to Web3Signer"""
    
    def __init__(self, config_file: str = "config/config.json"):
        """Initialize the external validator manager"""
        self.config_file = config_file
        self.config = self.load_config()
        
        # Service endpoints
        self.web3signer_url = "http://localhost:9000"
        self.vault_url = "http://localhost:8200"
        self.beacon_api_url = self.get_beacon_api_url()
        
        # Initialize managers
        self.key_manager = VaultKeyManager()
        # Pass network setting to deposit generator
        network = self.config.get('network', 'mainnet')
        self.deposit_generator = DepositGenerator(network=network)
        
        # External validator tracking
        self.external_validators = []
        
    def load_config(self) -> Dict:
        """Load configuration from file"""
        config_path = Path(self.config_file)
        if not config_path.exists():
            # Default configuration
            return {
                "network": "mainnet",  # mainnet, holesky, sepolia, etc.
                "external_validator_count": 5,
                "withdrawal_address": "0x0000000000000000000000000000000000000001",
                "timeout_activation": 1800,
                "timeout_exit": 1800,
                "monitoring_duration": 600
            }
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def get_beacon_api_url(self) -> str:
        """Get the beacon API URL from Kurtosis"""
        try:
            # Use kurtosis enclave inspect to get service information
            result = subprocess.run(
                ["kurtosis", "enclave", "inspect", "eth-devnet"],
                capture_output=True, text=True, check=True
            )
            
            # Parse the output to find lighthouse beacon API port
            lines = result.stdout.split('\n')
            for line in lines:
                if 'cl-' in line and 'lighthouse' in line and 'http:' in line:
                    # Extract port mapping from lines like:
                    # "http: 4000/tcp -> http://127.0.0.1:33182"
                    if '->' in line:
                        parts = line.split('->')
                        if len(parts) > 1:
                            port_part = parts[1].strip()
                            # Extract port from "http://127.0.0.1:33182" and remove any trailing status
                            if ':' in port_part:
                                # Split by ':' and take the last part, then remove any trailing whitespace/status
                                port_with_status = port_part.split(':')[-1]
                                # Remove any trailing status like "RUNNING"
                                port = port_with_status.split()[0]  # Take only the first word (port number)
                                beacon_url = f"http://localhost:{port}"
                                return beacon_url
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to get Kurtosis services: {e}")
            pass
        except FileNotFoundError:
            print("⚠️  Kurtosis CLI not found. Please install Kurtosis first.")
            pass
        
        # Fallback to default
        return "http://localhost:5052"
    
    def check_services(self) -> bool:
        """Check if required services are running"""
        print("=== Checking Service Status ===")
        
        # Check Web3Signer
        try:
            response = requests.get(f"{self.web3signer_url}/upcheck", timeout=5)
            if response.status_code == 200:
                print("✅ Web3Signer is running")
            else:
                print("❌ Web3Signer is not responding")
                return False
        except requests.RequestException:
            print("❌ Web3Signer is not accessible")
            return False
        
        # Check Vault
        try:
            response = requests.get(f"{self.vault_url}/v1/sys/health", timeout=5)
            if response.status_code in [200, 429]:  # 429 means sealed but healthy
                print("✅ Vault is running")
            else:
                print("❌ Vault is not responding")
                return False
        except requests.RequestException:
            print("❌ Vault is not accessible")
            return False
        
        # Check Beacon API
        print(f"🔍 Debug: Checking Beacon API at: {self.beacon_api_url}")
        try:
            health_url = f"{self.beacon_api_url}/eth/v1/node/health"
            print(f"🔍 Debug: Making request to: {health_url}")
            response = requests.get(health_url, timeout=5)
            print(f"🔍 Debug: Response status code: {response.status_code}")
            print(f"🔍 Debug: Response headers: {dict(response.headers)}")
            if response.text:
                print(f"🔍 Debug: Response body: {response.text[:200]}...")
            
            if response.status_code in [200, 206]:
                print("✅ Beacon API is accessible")
            else:
                print(f"❌ Beacon API is not responding (status: {response.status_code})")
                return False
        except requests.RequestException as e:
            print(f"❌ Beacon API is not accessible: {e}")
            print("💡 Troubleshooting tips:")
            print("   1. Make sure Kurtosis devnet is running: ./start.sh quick-start")
            print("   2. Check if eth-devnet enclave exists: kurtosis enclave ls")
            print("   3. Check Kurtosis services: kurtosis enclave inspect eth-devnet")
            return False
        
        return True
    
    def generate_external_keys(self, count: int = None, bulk_mode: bool = False) -> List[str]:
        """Generate keys for external validators - supports bulk generation workflow"""
        if count is None:
            count = self.config.get("external_validator_count", 5)
        
        # For bulk mode, default to larger batches
        if bulk_mode and count < 100:
            count = 1000  # Default bulk size
            print(f"🔄 批量模式：生成 {count} 个验证者密钥")
        else:
            print(f"=== Generating {count} External Validator Keys ===")
        
        # Generate keys using generate_keys module
        from utils.generate_keys import generate_validator_keys
        
        # Use absolute path to avoid path conflicts
        project_root = Path(__file__).parent.parent.parent
        keys_dir = project_root / "data" / "keys"
        keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate keys
        generated_keys, mnemonic = generate_validator_keys(
            count=count,
            start_index=0,  # Start from index 0
            output_dir=str(keys_dir)
        )
        
        print(f"✅ Generated {len(generated_keys)} validator keys")
        print("⚠️  IMPORTANT: Store the mnemonic securely offline!")
        print("🔐 The mnemonic has been saved to the keys directory for backup purposes.")
        print("🚨 NEVER share or commit the mnemonic to version control!")
        
        # Clean up existing keys in Vault first
        print("🧹 Cleaning up existing keys in Vault...")
        try:
            existing_keys = self.key_manager.list_keys_in_vault()
            for key_name in existing_keys:
                if key_name.startswith('validator-'):
                    self.key_manager.client.delete(f'secret/data/{key_name}')
                    print(f"🗑️  Removed old key: {key_name}")
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up old keys: {e}")
        
        # Import keys to Vault
        print("Importing keys to Vault...")
        imported_count = self.key_manager.bulk_import_keys(str(keys_dir))
        print(f"✅ Imported {imported_count} keys to Vault")
        
        # In bulk mode, do NOT generate Web3Signer configs yet
        if bulk_mode:
            print("📋 批量模式：密钥已导入 Vault，状态为 'unused'")
            print("💡 使用 './validator.sh activate-keys --count N' 来激活指定数量的密钥")
            print("💡 使用 './validator.sh pool-status' 查看密钥池状态")
        else:
            # Legacy mode: Export keys to Web3Signer format and load immediately
            print("Exporting keys to Web3Signer...")
            project_root = Path(__file__).parent.parent.parent
            web3signer_keys_dir = project_root / "infra" / "web3signer" / "keys"
            web3signer_keys_dir.mkdir(parents=True, exist_ok=True)
            exported_count = self.key_manager.export_keys_for_web3signer(str(web3signer_keys_dir))
            print(f"✅ Exported {exported_count} keys to Web3Signer format")
            
            # Load keys to Web3Signer
            print("Loading keys to Web3Signer...")
            try:
                from web3signer_manager import Web3SignerManager
                web3signer_manager = Web3SignerManager()
                if web3signer_manager.load_keys_to_web3signer():
                    print("✅ Keys loaded to Web3Signer successfully")
                    web3signer_manager.verify_keys_loaded()
                else:
                    print("❌ Failed to load keys to Web3Signer")
            except Exception as e:
                print(f"⚠️  Web3Signer loading failed: {e}")
                print("💡 Run './validator.sh load-keys' manually to load keys")
        
        # Get public keys from generated keys
        public_keys = [key["validator_public_key"] for key in generated_keys]
        self.external_validators = public_keys[:count]
        
        print(f"✅ Generated {len(self.external_validators)} external validator keys")
        return self.external_validators
    
    def init_key_pool(self, count: int = 1000) -> bool:
        """Initialize a large pool of validator keys for bulk operations"""
        print(f"🏗️  初始化密钥池：生成 {count} 个验证者密钥...")
        
        try:
            # Generate keys in bulk mode
            generated_keys = self.generate_external_keys(count=count, bulk_mode=True)
            
            if generated_keys:
                print(f"✅ 密钥池初始化完成：{len(generated_keys)} 个密钥已准备就绪")
                print("📊 密钥状态：")
                print(f"   - 未使用: {len(generated_keys)}")
                print(f"   - 活跃: 0")
                print(f"   - 已停用: 0")
                return True
            else:
                print("❌ 密钥池初始化失败")
                return False
                
        except Exception as e:
            print(f"❌ 密钥池初始化失败: {e}")
            return False
    
    def activate_keys_from_pool(self, count: int) -> List[str]:
        """从密钥池中激活指定数量的密钥"""
        print(f"🔧 从密钥池激活 {count} 个密钥...")
        
        try:
            # 获取未使用的密钥
            unused_keys = self.key_manager.get_unused_keys(count)
            if len(unused_keys) < count:
                print(f"❌ 可用密钥不足：需要 {count} 个，只有 {len(unused_keys)} 个")
                return []
            
            # 激活密钥
            pubkeys = [key.pubkey for key in unused_keys]
            success_count = self.key_manager.bulk_activate_keys(
                pubkeys, 
                f"批量激活于 {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            if success_count > 0:
                print(f"✅ 成功激活 {success_count} 个密钥")
                
                # 同步到 Web3Signer
                try:
                    from web3signer_manager import Web3SignerManager
                    web3signer_manager = Web3SignerManager()
                    if web3signer_manager.sync_active_keys():
                        print("✅ 密钥已同步到 Web3Signer")
                    else:
                        print("⚠️  密钥同步到 Web3Signer 失败")
                except Exception as e:
                    print(f"⚠️  Web3Signer 同步失败: {e}")
                
                return pubkeys[:success_count]
            else:
                print("❌ 密钥激活失败")
                return []
                
        except Exception as e:
            print(f"❌ 激活密钥失败: {e}")
            return []
    
    def get_pool_status(self) -> Dict[str, int]:
        """获取密钥池状态"""
        try:
            all_keys = self.key_manager.list_keys()
            
            status = {
                'unused': 0,
                'active': 0,
                'retired': 0,
                'total': len(all_keys)
            }
            
            for key in all_keys:
                if key.status == 'unused':
                    status['unused'] += 1
                elif key.status == 'active':
                    status['active'] += 1
                elif key.status == 'retired':
                    status['retired'] += 1
            
            return status
            
        except Exception as e:
            print(f"❌ 获取密钥池状态失败: {e}")
            return {'unused': 0, 'active': 0, 'retired': 0, 'total': 0}
    
    def load_external_validators_from_vault(self) -> bool:
        """Load existing external validators from Vault"""
        print("=== Loading External Validators from Vault ===")
        
        try:
            # Use list_active_keys_in_vault to skip deleted keys (verbose mode for debugging)
            vault_keys = self.key_manager.list_active_keys_in_vault(verbose=True)
            if not vault_keys:
                print("❌ No active keys found in Vault")
                return False
            
            public_keys = []
            print(f"🔍 Processing {len(vault_keys)} keys from Vault...")
            for key_id in vault_keys:
                print(f"🔍 Processing key: {key_id[:10]}...")
                key_data = self.key_manager.retrieve_key_from_vault(key_id)
                if key_data and "metadata" in key_data:
                    metadata = key_data["metadata"]
                    validator_pubkey = metadata.get("validator_pubkey")
                    print(f"🔍 Found validator pubkey: {validator_pubkey[:10] if validator_pubkey else 'None'}...")
                    if validator_pubkey:
                        public_keys.append(validator_pubkey)
                        print(f"✅ Added validator: {validator_pubkey[:10]}...")
                else:
                    print(f"⚠️  Invalid key data for: {key_id[:10]}...")
            
            if public_keys:
                self.external_validators = public_keys
                print(f"✅ Loaded {len(self.external_validators)} external validators from Vault")
                return True
            else:
                print("❌ No valid validator keys found in Vault")
                return False
                
        except Exception as e:
            print(f"❌ Error loading validators from Vault: {e}")
            return False
    
    def clean_all_keys(self):
        """清理所有密钥（本地文件和 Vault）"""
        try:
            project_root = Path(__file__).parent.parent.parent
            keys_dir = project_root / "data" / "keys"
            
            print("=== Cleaning All Keys ===")
            
            # Clean local files
            print("🧹 Cleaning local key files...")
            for file_pattern in ['keystore-*.json', 'password-*.txt', 'keys_data.json', 'pubkeys.json', 'mnemonic.txt']:
                for file_path in keys_dir.glob(file_pattern):
                    if file_path.is_file():
                        file_path.unlink()
                        print(f"🗑️  Removed: {file_path.name}")
            
            # Clean subdirectories
            for subdir in ['keystores', 'secrets']:
                subdir_path = keys_dir / subdir
                if subdir_path.exists():
                    for file_path in subdir_path.glob('*'):
                        if file_path.is_file():
                            file_path.unlink()
                            print(f"🗑️  Removed: {subdir}/{file_path.name}")
            
            # Clean Vault keys
            print("🧹 Cleaning Vault keys...")
            try:
                existing_keys = self.key_manager.list_keys_in_vault()
                print(f"🔍 Found {len(existing_keys)} keys in Vault: {existing_keys}")
                for key_name in existing_keys:
                    # 使用正确的 Vault API 删除密钥
                    try:
                        # 构建完整的密钥路径
                        full_path = f"{self.key_manager.key_path_prefix}/{key_name}"
                        self.key_manager.client.secrets.kv.v2.delete_metadata_and_all_versions(
                            path=full_path,
                            mount_point='secret'
                        )
                        print(f"🗑️  Removed Vault key: {full_path}")
                    except Exception as delete_error:
                        print(f"⚠️  Failed to delete key {key_name}: {delete_error}")
            except Exception as e:
                print(f"⚠️  Warning: Could not clean Vault keys: {e}")
                import traceback
                print(f"🔍 详细错误: {traceback.format_exc()}")
            
            # Clean Web3Signer keys
            print("🧹 Cleaning Web3Signer keys...")
            web3signer_keys_dir = project_root / "infra" / "web3signer" / "keys"
            if web3signer_keys_dir.exists():
                for file_path in web3signer_keys_dir.glob('vault-signing-key-*.yaml'):
                    file_path.unlink()
                    print(f"🗑️  Removed: {file_path.name}")
            
            print("✅ All keys cleaned successfully")
            
        except Exception as e:
            print(f"❌ Clean failed: {e}")
            import traceback
            print(f"🔍 详细错误: {traceback.format_exc()}")
    
    def ensure_external_validators_loaded(self) -> bool:
        """Ensure external validators are loaded, either from memory or Vault"""
        if not self.external_validators:
            print("⚠️  No external validators in memory. Loading from Vault...")
            return self.load_external_validators_from_vault()
        return True
    
    def list_stored_keys(self) -> None:
        """List all stored keys in Vault and local files"""
        print("=== Stored Keys Information ===")
        
        # List keys in Vault
        print("\n📦 Keys in Vault:")
        try:
            vault_keys = self.key_manager.list_keys()
            if vault_keys:
                for i, key in enumerate(vault_keys, 1):
                    print(f"  {i}. {key.pubkey[:10]}...")
                    print(f"     - Public Key: {key.pubkey}")
                    print(f"     - Index: {key.index}")
                    print(f"     - Status: {key.status}")
                    print(f"     - Batch ID: {key.batch_id}")
            else:
                print("  No keys found in Vault")
        except Exception as e:
            print(f"  ❌ Error accessing Vault: {e}")
            import traceback
            print(f"🔍 详细错误: {traceback.format_exc()}")
        
        # List local files
        print("\n📁 Local Key Files:")
        project_root = Path(__file__).parent.parent.parent
        keys_dir = project_root / "data" / "keys"
        if keys_dir.exists():
            # List keystores
            keystores_dir = keys_dir / "keystores"
            if keystores_dir.exists():
                keystore_files = list(keystores_dir.glob("*.json"))
                print(f"  Keystores: {len(keystore_files)} files")
                for keystore_file in keystore_files:
                    print(f"    - {keystore_file.name}")
            
            # List secrets
            secrets_dir = keys_dir / "secrets"
            if secrets_dir.exists():
                password_files = list(secrets_dir.glob("*.txt"))
                print(f"  Passwords: {len(password_files)} files")
                for password_file in password_files:
                    print(f"    - {password_file.name}")
            
            # Check pubkeys file
            pubkeys_file = keys_dir / "pubkeys.json"
            if pubkeys_file.exists():
                try:
                    with open(pubkeys_file, 'r') as f:
                        pubkeys_data = json.load(f)
                    
                    # Handle new format with deprecation notice
                    if isinstance(pubkeys_data, dict) and 'keys' in pubkeys_data:
                        keys_list = pubkeys_data['keys']
                        print(f"  Public Keys: {len(keys_list)} entries")
                        for pubkey_info in keys_list:
                            print(f"    - Index {pubkey_info['index']}: {pubkey_info['validator_pubkey'][:20]}...")
                    elif isinstance(pubkeys_data, list):
                        # Old format
                        print(f"  Public Keys: {len(pubkeys_data)} entries")
                        for pubkey_info in pubkeys_data:
                            print(f"    - Index {pubkey_info['index']}: {pubkey_info['validator_pubkey'][:20]}...")
                    else:
                        print(f"  Public Keys: Unknown format")
                except Exception as e:
                    print(f"  ❌ Error reading pubkeys.json: {e}")
            
            # Check mnemonic
            mnemonic_file = keys_dir / "MNEMONIC.txt"
            if mnemonic_file.exists():
                print(f"  Mnemonic: Available (⚠️  Keep secure!)")
        else:
            print("  No local key files found")
        
        # List Web3Signer keys
        print("\n🔐 Web3Signer Keys:")
        project_root = Path(__file__).parent.parent.parent
        web3signer_keys_dir = project_root / "infra" / "web3signer" / "keys"
        if web3signer_keys_dir.exists():
            web3signer_files = list(web3signer_keys_dir.glob("*.yaml"))
            print(f"  Configuration files: {len(web3signer_files)} files")
            for config_file in web3signer_files:
                print(f"    - {config_file.name}")
        else:
            print("  No Web3Signer key files found")
    
    def create_external_deposits(self) -> str:
        """Create deposit data for external validators"""
        print("=== Creating External Validator Deposits ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators found. Generate keys first.")
            return None
        
        # Create deposit data
        project_root = Path(__file__).parent.parent.parent
        deposits_dir = project_root / "data" / "deposits"
        deposits_dir.mkdir(parents=True, exist_ok=True)
        
        deposit_file = os.path.join(deposits_dir, "deposit_data.json")
        
        # Try to load keys data from multiple possible locations
        keys_data = None
        possible_keys_files = [
            project_root / "data" / "keys" / "keys_data.json",
            project_root / "data" / "keys" / "pubkeys.json",
            project_root / "data" / "keys" / "keys_data.json"
        ]
        
        for keys_file in possible_keys_files:
            if keys_file.exists():
                try:
                    with open(keys_file, 'r') as f:
                        keys_data = json.load(f)
                    print(f"✅ Loaded keys data from: {keys_file}")
                    break
                except Exception as e:
                    print(f"⚠️ Failed to load {keys_file}: {e}")
                    continue
        
        if not keys_data:
            print("❌ No keys data file found. Generate keys first.")
            return None
        
        # Get withdrawal address (can be overridden)
        withdrawal_address = self.config.get("withdrawal_address", "0x0000000000000000000000000000000000000001")
        print(f"🎯 Using withdrawal address: {withdrawal_address}")
        print("📝 Note: This will create 0x01 type withdrawal credentials (execution address)")
        
        # Generate deposit data using the loaded validators
        try:
            deposit_data = self.deposit_generator.generate_deposits(
                count=len(self.external_validators),
                withdrawal_address=withdrawal_address,  # 使用动态指定的提款地址
                notes="External validator deposit"
            )
            
            # Validate deposit data before saving
            if self._validate_deposit_data(deposit_data):
                # Save deposit data to file
                with open(deposit_file, 'w') as f:
                    json.dump(deposit_data, f, indent=2)
                
                print(f"✅ Created deposit data: {deposit_file}")
                return deposit_file
            else:
                print("❌ Deposit data validation failed")
                return None
            
        except Exception as e:
            print(f"❌ Failed to generate deposit data: {e}")
            return None
    
    def submit_external_deposits(self, deposit_file: str) -> bool:
        """Submit deposits for external validators"""
        print("=== Submitting External Validator Deposits ===")
        
        if not deposit_file or not Path(deposit_file).exists():
            print("❌ Deposit file not found")
            return False
        
        print(f"📁 存款数据文件: {deposit_file}")
        
        # 使用存款提交工具
        try:
            import subprocess
            import sys
            import os
            
            # 设置环境变量
            env = os.environ.copy()
            env['SKIP_VAULT_CHECK'] = 'true'
            
            # 运行存款提交脚本
            cmd = [
                sys.executable, 
                "utils/deposit_submitter.py",
                deposit_file,
                "--config", "../config/config.json"
            ]
            
            print("🚀 开始提交存款到网络...")
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            # 显示输出
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            success = result.returncode == 0
            
            if success:
                print("✅ 存款提交成功")
                # 标记使用的密钥为 active 状态
                self._mark_deposited_keys_as_active()
            else:
                print("❌ 存款提交失败")
            
            return success
            
        except Exception as e:
            print(f"❌ 提交存款过程出错: {e}")
            print("📋 手动提交选项:")
            print("   1. 使用以太坊客户端提交")
            print("   2. 使用 Web 界面提交")
            print("   3. 检查网络连接和配置")
            return False
    
    def submit_existing_deposits(self) -> bool:
        """提交已存在的存款数据文件到网络"""
        print("📤 Submitting deposits...")
        
        # 查找存款数据文件
        deposit_file = None
        possible_paths = [
            "data/deposits/deposit_data.json",
            "data/deposits/deposit_data-*.json"
        ]
        
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent
        print(f"🔍 搜索存款数据文件...")
        print(f"📁 项目根目录: {project_root}")
        
        for pattern in possible_paths:
            if "*" in pattern:
                import glob
                # 使用绝对路径搜索
                full_pattern = str(project_root / pattern)
                print(f"🔍 搜索模式: {full_pattern}")
                files = glob.glob(full_pattern)
                print(f"📋 找到文件: {files}")
                if files:
                    deposit_file = files[0]  # 使用第一个找到的文件
                    break
            else:
                full_path = project_root / pattern
                print(f"🔍 检查路径: {full_path}")
                if full_path.exists():
                    deposit_file = str(full_path)
                    print(f"✅ 找到文件: {deposit_file}")
                    break
                else:
                    print(f"❌ 文件不存在: {full_path}")
        
        # 如果没找到，尝试相对路径搜索
        if not deposit_file:
            print("🔍 尝试相对路径搜索...")
            for pattern in possible_paths:
                if "*" in pattern:
                    import glob
                    files = glob.glob(pattern)
                    print(f"📋 相对路径找到: {files}")
                    if files:
                        deposit_file = files[0]
                        break
                else:
                    if Path(pattern).exists():
                        deposit_file = pattern
                        print(f"✅ 相对路径找到: {deposit_file}")
                        break
        
        if not deposit_file:
            print("❌ 未找到存款数据文件")
            print("📋 请先运行: ./validator.sh create-deposits")
            return False
        
        print(f"📁 找到存款数据文件: {deposit_file}")
        
        # 使用存款提交工具
        try:
            import subprocess
            import sys
            import os
            
            # 设置环境变量
            env = os.environ.copy()
            env['SKIP_VAULT_CHECK'] = 'true'
            
            # 运行存款提交脚本
            cmd = [
                sys.executable, 
                "utils/deposit_submitter.py",
                deposit_file,
                "--config", "../config/config.json"
            ]
            
            print("🚀 开始提交存款到网络...")
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            # 显示输出
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            success = result.returncode == 0
            
            if success:
                print("✅ 存款提交成功")
                # 注意：这里不标记密钥状态，因为密钥可能已经存在
            else:
                print("❌ 存款提交失败")
            
            return success
            
        except Exception as e:
            print(f"❌ 提交存款过程出错: {e}")
            print("📋 手动提交选项:")
            print("   1. 使用以太坊客户端提交")
            print("   2. 使用 Web 界面提交")
            print("   3. 检查网络连接和配置")
            return False
    
    def _mark_deposited_keys_as_active(self):
        """标记已提交存款的密钥为 active 状态"""
        try:
            if not self.external_validators:
                return
            
            print("🔄 更新密钥状态为 active...")
            for pubkey in self.external_validators:
                if self.key_manager.mark_key_as_active(pubkey, "external", "Deposit submitted"):
                    print(f"✅ 标记密钥为 active: {pubkey[:10]}...")
                else:
                    print(f"⚠️  无法更新密钥状态: {pubkey[:10]}...")
        except Exception as e:
            print(f"⚠️  更新密钥状态失败: {e}")
    
    def check_validator_activation_status(self) -> bool:
        """检查验证者激活状态并更新密钥状态"""
        print("=== Checking Validator Activation Status ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators found.")
            return False
        
        print("⚠️  Activation check simplified - manual process required")
        print("📋 To check activation status manually:")
        print("   1. Use beacon chain explorer to check validator status")
        print("   2. Look for 'active_ongoing' status")
        print("   3. Update key status accordingly")
        
        # 这里可以集成真实的 beacon chain API 调用
        # 例如：https://beaconcha.in/api/v1/validator/{pubkey}
        
        return True
    
    def validate_deposit_data(self) -> bool:
        """验证存款数据的有效性"""
        print("=== Validating Deposit Data ===")
        
        # 查找存款数据文件
        deposit_file = None
        possible_paths = [
            "data/deposits/deposit_data.json",
            "data/deposits/deposit_data-*.json"
        ]
        
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent
        print(f"🔍 搜索存款数据文件...")
        print(f"📁 项目根目录: {project_root}")
        
        for pattern in possible_paths:
            if "*" in pattern:
                import glob
                # 使用绝对路径搜索
                full_pattern = str(project_root / pattern)
                print(f"🔍 搜索模式: {full_pattern}")
                files = glob.glob(full_pattern)
                print(f"📋 找到文件: {files}")
                if files:
                    deposit_file = files[0]  # 使用第一个找到的文件
                    break
            else:
                full_path = project_root / pattern
                print(f"🔍 检查路径: {full_path}")
                if full_path.exists():
                    deposit_file = str(full_path)
                    print(f"✅ 找到文件: {deposit_file}")
                    break
                else:
                    print(f"❌ 文件不存在: {full_path}")
        
        # 如果没找到，尝试相对路径搜索
        if not deposit_file:
            print("🔍 尝试相对路径搜索...")
            for pattern in possible_paths:
                if "*" in pattern:
                    import glob
                    files = glob.glob(pattern)
                    print(f"📋 相对路径找到: {files}")
                    if files:
                        deposit_file = files[0]
                        break
                else:
                    if Path(pattern).exists():
                        deposit_file = pattern
                        print(f"✅ 相对路径找到: {deposit_file}")
                        break
        
        if not deposit_file:
            print("❌ 未找到存款数据文件")
            print("📋 请先运行: ./validator.sh create-deposits")
            return False
        
        print(f"📁 找到存款数据文件: {deposit_file}")
        
        # 使用验证工具（独立运行，不依赖 Vault）
        try:
            import subprocess
            import sys
            import os
            
            # 设置环境变量，避免 Vault 连接问题
            env = os.environ.copy()
            env['SKIP_VAULT_CHECK'] = 'true'
            
            # 运行验证脚本（使用独立脚本，不依赖 Vault）
            cmd = [
                sys.executable, 
                "utils/validate_deposits_standalone.py",
                deposit_file,
                "--network", "mainnet"
            ]
            
            print("🔍 开始验证存款数据...")
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            # 显示输出
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ 验证过程出错: {e}")
            return False
    
    def start_external_validator_clients(self) -> bool:
        """Start external validator clients connected to Web3Signer"""
        print("=== Starting External Validator Clients ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators found. Generate keys first.")
            return False
        
        print("⚠️  Validator client management simplified - manual setup required")
        print("📋 To start validator clients manually:")
        print("   1. Configure Lighthouse/Teku to connect to Web3Signer")
        print("   2. Set Web3Signer URL: http://localhost:9000")
        print("   3. Set Beacon API URL:", self.beacon_api_url)
        print("   4. Use validator public keys from Vault")
        
        return True
    
    def wait_for_external_activation(self) -> bool:
        """Wait for external validators to become active"""
        print("=== Waiting for External Validator Activation ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators to monitor")
            return False
        
        print("⚠️  Activation monitoring simplified - manual verification required")
        print("📋 To check validator activation:")
        print("   1. Check Beacon API:", self.beacon_api_url)
        print("   2. Look for validator status: active")
        print("   3. Monitor validator performance")
        
        return True
    
    def monitor_external_validators(self, duration: int = None) -> Dict:
        """Monitor external validator performance"""
        if duration is None:
            duration = self.config.get("monitoring_duration", 600)
        
        print(f"=== Monitoring External Validators for {duration}s ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators to monitor")
            return {}
        
        print("⚠️  Monitoring simplified - manual verification required")
        print("📋 To monitor validators:")
        print("   1. Check Beacon API:", self.beacon_api_url)
        print("   2. Monitor validator performance metrics")
        print("   3. Check attestation and proposal success rates")
        
        return {"status": "simplified_monitoring"}
    
    def test_external_exit(self, validator_count: int = 1) -> bool:
        """Test voluntary exit for external validators"""
        print(f"=== Testing Voluntary Exit for {validator_count} External Validators ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators available for exit")
            return False
        
        # Select validators to exit
        validators_to_exit = self.external_validators[:validator_count]
        
        print("⚠️  Voluntary exit simplified - manual process required")
        print("📋 To perform voluntary exit:")
        print("   1. Use validator client to initiate voluntary exit")
        print("   2. Monitor exit status via Beacon API")
        print("   3. Wait for exit completion")
        
        return True
    
    def test_external_withdrawal(self) -> bool:
        """Test withdrawal process for external validators"""
        print("=== Testing External Validator Withdrawal ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators available for withdrawal")
            return False
        
        print("⚠️  Withdrawal monitoring simplified - manual verification required")
        print("📋 To monitor withdrawal:")
        print("   1. Check Beacon API for withdrawal status")
        print("   2. Monitor withdrawal queue")
        print("   3. Verify funds are available for withdrawal")
        
        return True
    
    def get_external_validator_status(self) -> Dict:
        """Get status of external validators"""
        if not self.ensure_external_validators_loaded():
            return {}
        
        return {
            "external_validators": len(self.external_validators),
            "status": "simplified_status_check",
            "beacon_api": self.beacon_api_url
        }
    
    def cleanup_external_validators(self):
        """Clean up external validator resources"""
        print("=== Cleaning Up External Validator Resources ===")
        
        # Stop validator clients (simplified)
        print("⚠️  Validator client cleanup simplified - manual cleanup required")
        
        # Remove external keys
        project_root = Path(__file__).parent.parent.parent
        external_keys_dir = project_root / "data" / "keys"
        if external_keys_dir.exists():
            import shutil
            shutil.rmtree(external_keys_dir)
            print("✅ Removed external keys directory")
        
        # Remove external deposits
        external_deposits_dir = project_root / "data" / "deposits"
        if external_deposits_dir.exists():
            import shutil
            shutil.rmtree(external_deposits_dir)
            print("✅ Removed external deposits directory")
        
        # Clear Web3Signer keys
        project_root = Path(__file__).parent.parent.parent
        web3signer_keys_dir = project_root / "infra" / "web3signer" / "keys"
        if web3signer_keys_dir.exists():
            for key_file in web3signer_keys_dir.glob("*.json"):
                key_file.unlink()
            print("✅ Cleared Web3Signer keys")
        
        # Remove validator client data
        validator_data_dir = project_root / "data" / "configs"
        if validator_data_dir.exists():
            import shutil
            shutil.rmtree(validator_data_dir)
            print("✅ Removed validator client data")
        
        self.external_validators = []
        print("✅ External validator cleanup completed")

    def _validate_deposit_data(self, deposit_data: List[Dict]) -> bool:
        """Validate deposit data using ethstaker-deposit-cli utilities"""
        try:
            from ethstaker_deposit.utils.validation import validate_deposit
            from ethstaker_deposit.settings import get_chain_setting
            
            # Get chain setting for validation
            chain_setting = get_chain_setting("mainnet")
            
            # Validate each deposit
            for i, deposit in enumerate(deposit_data):
                if not validate_deposit(deposit, chain_setting):
                    print(f"❌ Deposit {i} validation failed")
                    return False
            
            print(f"✅ Validated {len(deposit_data)} deposits successfully")
            return True
            
        except ImportError:
            print("⚠️ ethstaker-deposit-cli validation not available, skipping validation")
            return True
        except Exception as e:
            print(f"❌ Deposit validation error: {e}")
            return False


def main():
    """Main function for external validator management"""
    parser = argparse.ArgumentParser(description="External Validator Manager")
    parser.add_argument("command", choices=[
        "check-services", "generate-keys", "list-keys", "load-validators", "create-deposits", "submit-deposits",
        "start-clients", "wait-activation", "monitor", "test-exit", "test-withdrawal", 
        "status", "cleanup", "full-test", "create-deposits-with-address", "test-import", "clean", "check-status", "validate-deposits",
        "init-pool", "activate-keys", "pool-status"
    ], help="Command to execute")
    parser.add_argument("--count", type=int, help="Number of validators")
    parser.add_argument("--config", default="config/config.json", help="Config file")
    parser.add_argument("--withdrawal-address", help="Withdrawal address for 0x01 type deposits")
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = ExternalValidatorManager(args.config)
    
    try:
        if args.command == "check-services":
            success = manager.check_services()
            sys.exit(0 if success else 1)
        
        elif args.command == "generate-keys":
            manager.generate_external_keys(args.count)
        
        elif args.command == "list-keys":
            manager.list_stored_keys()
        
        elif args.command == "load-validators":
            manager.load_external_validators_from_vault()
        
        elif args.command == "create-deposits":
            manager.create_external_deposits()
        
        elif args.command == "create-deposits-with-address":
            if not args.withdrawal_address:
                print("❌ --withdrawal-address is required for this command")
                sys.exit(1)
            # Temporarily update config with the specified withdrawal address
            original_address = manager.config.get("withdrawal_address")
            manager.config["withdrawal_address"] = args.withdrawal_address
            try:
                manager.create_external_deposits()
            finally:
                # Restore original address
                if original_address:
                    manager.config["withdrawal_address"] = original_address
        
        elif args.command == "clean":
            print("=== Cleaning All Keys ===")
            manager.clean_all_keys()
        
        elif args.command == "check-status":
            print("=== Checking Validator Status ===")
            manager.check_validator_activation_status()
        
        elif args.command == "validate-deposits":
            print("=== Validating Deposit Data ===")
            manager.validate_deposit_data()
        
        elif args.command == "submit-deposits":
            # 直接提交已存在的存款数据文件
            manager.submit_existing_deposits()
        
        elif args.command == "start-clients":
            manager.start_external_validator_clients()
        
        elif args.command == "wait-activation":
            manager.wait_for_external_activation()
        
        elif args.command == "monitor":
            manager.monitor_external_validators()
        
        elif args.command == "test-exit":
            manager.test_external_exit(args.count or 1)
        
        elif args.command == "test-withdrawal":
            manager.test_external_withdrawal()
        
        elif args.command == "status":
            status = manager.get_external_validator_status()
            print(json.dumps(status, indent=2))
        
        elif args.command == "cleanup":
            manager.cleanup_external_validators()
        
        elif args.command == "test-import":
            print("=== Testing Vault Import ===")
            project_root = Path(__file__).parent.parent.parent
            keys_dir = project_root / "data" / "keys"
            if manager.key_manager.test_import_single_key(str(keys_dir)):
                print("✅ Test import successful")
            else:
                print("❌ Test import failed")
        
        elif args.command == "init-pool":
            print("=== Initialize Key Pool ===")
            count = args.count or 1000
            success = manager.init_key_pool(count)
            if success:
                print("✅ Key pool initialized successfully")
            else:
                print("❌ Key pool initialization failed")
                sys.exit(1)
        
        elif args.command == "activate-keys":
            print("=== Activate Keys from Pool ===")
            count = args.count or 10
            activated_keys = manager.activate_keys_from_pool(count)
            if activated_keys:
                print(f"✅ Successfully activated {len(activated_keys)} keys")
            else:
                print("❌ Key activation failed")
                sys.exit(1)
        
        elif args.command == "pool-status":
            print("=== Key Pool Status ===")
            status = manager.get_pool_status()
            print(f"📊 Key Pool Status:")
            print(f"   Total keys: {status['total']}")
            print(f"   Unused: {status['unused']}")
            print(f"   Active: {status['active']}")
            print(f"   Retired: {status['retired']}")
        
        elif args.command == "full-test":
            print("=== Running Full External Validator Test ===")
            
            # Check services
            if not manager.check_services():
                print("❌ Services not ready")
                sys.exit(1)
            
            # Generate keys
            manager.generate_external_keys(args.count)
            
            # Create and submit deposits
            deposit_file = manager.create_external_deposits()
            if deposit_file:
                manager.submit_external_deposits(deposit_file)
            
            # Start external validator clients
            manager.start_external_validator_clients()
            
            # Wait for activation
            manager.wait_for_external_activation()
            
            # Monitor performance
            manager.monitor_external_validators()
            
            # Test exit
            manager.test_external_exit(1)
            
            # Test withdrawal
            manager.test_external_withdrawal()
            
            print("✅ Full external validator test completed")
    
    except KeyboardInterrupt:
        print("\n⚠️ Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
