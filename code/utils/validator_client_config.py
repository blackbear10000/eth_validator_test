#!/usr/bin/env python3
"""
验证者客户端配置生成器

功能：
1. 支持 Prysm、Lighthouse、Teku 三种客户端
2. 从 Vault 读取密钥信息
3. 生成 Web3Signer 配置
4. 生成客户端配置文件
"""

import json
import os
import sys
import argparse
import yaml
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入我们的 Vault 密钥管理器
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from vault_key_manager import VaultKeyManager, ValidatorKey

class ValidatorClientConfig:
    """验证者客户端配置生成器"""
    
    def __init__(self, vault_url: str = "http://localhost:8200", vault_token: str = None):
        self.vault_manager = VaultKeyManager(vault_url, vault_token)
        self.web3signer_url = "http://localhost:9000"
        
    def generate_prysm_config(self, 
                             pubkeys: List[str],
                             beacon_node_url: str = "http://localhost:3500",
                             output_dir: str = "configs/prysm") -> str:
        """生成 Prysm 验证者配置"""
        
        print(f"🔧 生成 Prysm 配置...")
        
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 1. 生成 Web3Signer 配置
        web3signer_config = self._generate_web3signer_config(pubkeys)
        web3signer_file = output_path / "web3signer-config.yaml"
        with open(web3signer_file, 'w') as f:
            yaml.dump(web3signer_config, f, default_flow_style=False)
        
        # 2. 生成 Prysm 验证者配置
        prysm_config = {
            "wallet-dir": "/data/wallet",
            "wallet-password-file": "/data/wallet-password.txt",
            "beacon-rpc-provider": beacon_node_url,
            "beacon-rpc-gateway-provider": beacon_node_url,
            "web3signer-url": self.web3signer_url,
            "web3signer-public-keys": pubkeys,
            "suggested-fee-recipient": "0x0000000000000000000000000000000000000000",  # 需要用户设置
            "enable-external-slashing-protection": True,
            "slashing-protection-db-url": "postgres://user:password@localhost:5432/slashing_protection",
            "graffiti": f"Prysm-{datetime.now().strftime('%Y%m%d')}",
            "log-format": "json",
            "log-level": "info"
        }
        
        config_file = output_path / "validator-config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(prysm_config, f, default_flow_style=False)
        
        # 3. 生成启动脚本
        start_script = self._generate_prysm_start_script(pubkeys, config_file)
        script_file = output_path / "start-validator.sh"
        with open(script_file, 'w') as f:
            f.write(start_script)
        os.chmod(script_file, 0o755)
        
        print(f"✅ Prysm 配置已生成: {output_path}")
        return str(output_path)
    
    def generate_lighthouse_config(self, 
                                  pubkeys: List[str],
                                  beacon_node_url: str = "http://localhost:5052",
                                  output_dir: str = "configs/lighthouse") -> str:
        """生成 Lighthouse 验证者配置"""
        
        print(f"🔧 生成 Lighthouse 配置...")
        
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 1. 生成 Web3Signer 配置
        web3signer_config = self._generate_web3signer_config(pubkeys)
        web3signer_file = output_path / "web3signer-config.yaml"
        with open(web3signer_file, 'w') as f:
            yaml.dump(web3signer_config, f, default_flow_style=False)
        
        # 2. 生成 Lighthouse 验证者配置
        lighthouse_config = {
            "beacon-node": beacon_node_url,
            "web3signer": {
                "url": self.web3signer_url,
                "pubkeys": pubkeys
            },
            "suggested-fee-recipient": "0x0000000000000000000000000000000000000000",  # 需要用户设置
            "graffiti": f"Lighthouse-{datetime.now().strftime('%Y%m%d')}",
            "log-level": "info",
            "log-format": "json"
        }
        
        config_file = output_path / "validator-config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(lighthouse_config, f, default_flow_style=False)
        
        # 3. 生成启动脚本
        start_script = self._generate_lighthouse_start_script(pubkeys, config_file)
        script_file = output_path / "start-validator.sh"
        with open(script_file, 'w') as f:
            f.write(start_script)
        os.chmod(script_file, 0o755)
        
        print(f"✅ Lighthouse 配置已生成: {output_path}")
        return str(output_path)
    
    def generate_teku_config(self, 
                            pubkeys: List[str],
                            beacon_node_url: str = "http://localhost:5051",
                            output_dir: str = "configs/teku") -> str:
        """生成 Teku 验证者配置"""
        
        print(f"🔧 生成 Teku 配置...")
        
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 1. 生成 Web3Signer 配置
        web3signer_config = self._generate_web3signer_config(pubkeys)
        web3signer_file = output_path / "web3signer-config.yaml"
        with open(web3signer_file, 'w') as f:
            yaml.dump(web3signer_config, f, default_flow_style=False)
        
        # 2. 生成 Teku 验证者配置
        teku_config = {
            "beacon-node-api-endpoint": beacon_node_url,
            "validators-external-signer-public-keys": pubkeys,
            "validators-external-signer-url": self.web3signer_url,
            "validators-external-signer-timeout": 5000,
            "validators-external-signer-keystore": "/data/keystore",
            "validators-external-signer-keystore-password-file": "/data/keystore-password.txt",
            "validators-external-signer-truststore": "/data/truststore",
            "validators-external-signer-truststore-password-file": "/data/truststore-password.txt",
            "validators-proposer-default-fee-recipient": "0x0000000000000000000000000000000000000000",  # 需要用户设置
            "validators-graffiti": f"Teku-{datetime.now().strftime('%Y%m%d')}",
            "logging": "INFO",
            "log-destination": "console"
        }
        
        config_file = output_path / "validator-config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(teku_config, f, default_flow_style=False)
        
        # 3. 生成启动脚本
        start_script = self._generate_teku_start_script(pubkeys, config_file)
        script_file = output_path / "start-validator.sh"
        with open(script_file, 'w') as f:
            f.write(start_script)
        os.chmod(script_file, 0o755)
        
        print(f"✅ Teku 配置已生成: {output_path}")
        return str(output_path)
    
    def _generate_web3signer_config(self, pubkeys: List[str]) -> Dict[str, Any]:
        """生成 Web3Signer 配置"""
        return {
            "server": {
                "httpHost": "0.0.0.0",
                "httpPort": 9000,
                "corsAllowedOrigins": ["*"]
            },
            "logging": {
                "level": "INFO"
            },
            "keyStorePath": "/data/keystore",
            "keyStorePasswordFile": "/data/keystore-password.txt",
            "slashingProtectionEnabled": True,
            "slashingProtectionDbUrl": "postgres://user:password@localhost:5432/slashing_protection",
            "validators": {
                "validatorKeys": pubkeys
            }
        }
    
    def _generate_prysm_start_script(self, pubkeys: List[str], config_file: Path) -> str:
        """生成 Prysm 启动脚本"""
        return f"""#!/bin/bash

# Prysm 验证者启动脚本
# 生成时间: {datetime.now().isoformat()}
# 验证者数量: {len(pubkeys)}

set -e

echo "🚀 启动 Prysm 验证者..."

# 检查 Web3Signer 是否运行
echo "🔍 检查 Web3Signer 连接..."
curl -f {self.web3signer_url}/upcheck || {{
    echo "❌ Web3Signer 未运行，请先启动 Web3Signer"
    exit 1
}}

# 启动 Prysm 验证者
echo "🔧 启动验证者..."
prysm validator \\
    --config-file={config_file} \\
    --accept-terms-of-use

echo "✅ Prysm 验证者已启动"
"""
    
    def _generate_lighthouse_start_script(self, pubkeys: List[str], config_file: Path) -> str:
        """生成 Lighthouse 启动脚本"""
        return f"""#!/bin/bash

# Lighthouse 验证者启动脚本
# 生成时间: {datetime.now().isoformat()}
# 验证者数量: {len(pubkeys)}

set -e

echo "🚀 启动 Lighthouse 验证者..."

# 检查 Web3Signer 是否运行
echo "🔍 检查 Web3Signer 连接..."
curl -f {self.web3signer_url}/upcheck || {{
    echo "❌ Web3Signer 未运行，请先启动 Web3Signer"
    exit 1
}}

# 启动 Lighthouse 验证者
echo "🔧 启动验证者..."
lighthouse validator \\
    --config-file {config_file} \\
    --datadir /data/lighthouse

echo "✅ Lighthouse 验证者已启动"
"""
    
    def _generate_teku_start_script(self, pubkeys: List[str], config_file: Path) -> str:
        """生成 Teku 启动脚本"""
        return f"""#!/bin/bash

# Teku 验证者启动脚本
# 生成时间: {datetime.now().isoformat()}
# 验证者数量: {len(pubkeys)}

set -e

echo "🚀 启动 Teku 验证者..."

# 检查 Web3Signer 是否运行
echo "🔍 检查 Web3Signer 连接..."
curl -f {self.web3signer_url}/upcheck || {{
    echo "❌ Web3Signer 未运行，请先启动 Web3Signer"
    exit 1
}}

# 启动 Teku 验证者
echo "🔧 启动验证者..."
teku \\
    --config-file {config_file} \\
    --data-path /data/teku

echo "✅ Teku 验证者已启动"
"""
    
    def generate_all_configs(self, 
                           pubkeys: List[str],
                           beacon_node_urls: Dict[str, str] = None,
                           output_base_dir: str = "configs") -> Dict[str, str]:
        """为所有客户端生成配置"""
        
        if beacon_node_urls is None:
            beacon_node_urls = {
                "prysm": "http://localhost:3500",
                "lighthouse": "http://localhost:5052", 
                "teku": "http://localhost:5051"
            }
        
        results = {}
        
        # 生成 Prysm 配置
        results["prysm"] = self.generate_prysm_config(
            pubkeys, 
            beacon_node_urls["prysm"], 
            f"{output_base_dir}/prysm"
        )
        
        # 生成 Lighthouse 配置
        results["lighthouse"] = self.generate_lighthouse_config(
            pubkeys, 
            beacon_node_urls["lighthouse"], 
            f"{output_base_dir}/lighthouse"
        )
        
        # 生成 Teku 配置
        results["teku"] = self.generate_teku_config(
            pubkeys, 
            beacon_node_urls["teku"], 
            f"{output_base_dir}/teku"
        )
        
        return results
    
    def get_active_keys_by_client(self) -> Dict[str, List[ValidatorKey]]:
        """按客户端类型获取活跃密钥"""
        active_keys = self.vault_manager.list_keys(status='active')
        
        result = {
            "prysm": [],
            "lighthouse": [],
            "teku": [],
            "unknown": []
        }
        
        for key in active_keys:
            client_type = key.client_type or "unknown"
            if client_type in result:
                result[client_type].append(key)
            else:
                result["unknown"].append(key)
        
        return result

def main():
    parser = argparse.ArgumentParser(description='验证者客户端配置生成器')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 生成 Prysm 配置
    prysm_parser = subparsers.add_parser('prysm', help='生成 Prysm 配置')
    prysm_parser.add_argument('--pubkeys', nargs='+', help='验证者公钥列表')
    prysm_parser.add_argument('--beacon-node', default='http://localhost:3500', help='信标节点URL')
    prysm_parser.add_argument('--output-dir', default='configs/prysm', help='输出目录')
    
    # 生成 Lighthouse 配置
    lighthouse_parser = subparsers.add_parser('lighthouse', help='生成 Lighthouse 配置')
    lighthouse_parser.add_argument('--pubkeys', nargs='+', help='验证者公钥列表')
    lighthouse_parser.add_argument('--beacon-node', default='http://localhost:5052', help='信标节点URL')
    lighthouse_parser.add_argument('--output-dir', default='configs/lighthouse', help='输出目录')
    
    # 生成 Teku 配置
    teku_parser = subparsers.add_parser('teku', help='生成 Teku 配置')
    teku_parser.add_argument('--pubkeys', nargs='+', help='验证者公钥列表')
    teku_parser.add_argument('--beacon-node', default='http://localhost:5051', help='信标节点URL')
    teku_parser.add_argument('--output-dir', default='configs/teku', help='输出目录')
    
    # 生成所有配置
    all_parser = subparsers.add_parser('all', help='生成所有客户端配置')
    all_parser.add_argument('--pubkeys', nargs='+', help='验证者公钥列表')
    all_parser.add_argument('--output-dir', default='configs', help='输出基础目录')
    
    # 列出活跃密钥
    list_parser = subparsers.add_parser('list-active', help='列出活跃密钥')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        config_generator = ValidatorClientConfig()
        
        if args.command in ['prysm', 'lighthouse', 'teku']:
            if not args.pubkeys:
                print("❌ 请提供验证者公钥列表")
                return
            
            if args.command == 'prysm':
                config_generator.generate_prysm_config(
                    args.pubkeys, 
                    args.beacon_node, 
                    args.output_dir
                )
            elif args.command == 'lighthouse':
                config_generator.generate_lighthouse_config(
                    args.pubkeys, 
                    args.beacon_node, 
                    args.output_dir
                )
            elif args.command == 'teku':
                config_generator.generate_teku_config(
                    args.pubkeys, 
                    args.beacon_node, 
                    args.output_dir
                )
        
        elif args.command == 'all':
            if not args.pubkeys:
                print("❌ 请提供验证者公钥列表")
                return
            
            results = config_generator.generate_all_configs(args.pubkeys, None, args.output_dir)
            print(f"\n✅ 所有配置已生成:")
            for client, path in results.items():
                print(f"  {client}: {path}")
        
        elif args.command == 'list-active':
            active_keys = config_generator.get_active_keys_by_client()
            print(f"\n📋 活跃密钥统计:")
            for client, keys in active_keys.items():
                if keys:
                    print(f"  {client}: {len(keys)} 个")
                    for key in keys[:5]:  # 只显示前5个
                        print(f"    {key.pubkey[:10]}... | {key.batch_id}")
                    if len(keys) > 5:
                        print(f"    ... 还有 {len(keys) - 5} 个")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
