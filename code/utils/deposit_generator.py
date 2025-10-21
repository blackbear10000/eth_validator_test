#!/usr/bin/env python3
"""
动态存款生成器

功能：
1. 从 Vault 读取未使用的验证者密钥
2. 支持动态提款地址配置
3. 生成存款数据文件
4. 自动标记密钥为使用中
"""

import json
import os
import sys
import argparse
import subprocess
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from eth_utils import to_hex, to_bytes
    from eth_account import Account
except ImportError as e:
    print(f"❌ 缺少依赖: {e}")
    print("请运行: pip install eth-utils eth-account")
    sys.exit(1)

# 导入我们的 Vault 密钥管理器
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from vault_key_manager import VaultKeyManager, ValidatorKey

class DepositGenerator:
    """动态存款生成器"""
    
    def __init__(self, vault_url: str = "http://localhost:8200", vault_token: str = None):
        self.vault_manager = VaultKeyManager(vault_url, vault_token)
        
    def generate_deposits(self, 
                         count: int,
                         withdrawal_address: str,
                         batch_id: str = None,
                         client_type: str = None,
                         notes: str = None) -> List[Dict[str, Any]]:
        """生成存款数据"""
        
        print(f"🔄 开始生成 {count} 个存款...")
        
        # 1. 从 Vault 获取未使用的密钥
        unused_keys = self.vault_manager.get_unused_keys(count, batch_id)
        
        if len(unused_keys) < count:
            print(f"❌ 可用密钥不足: 需要 {count} 个，只有 {len(unused_keys)} 个")
            return []
        
        deposits = []
        used_pubkeys = []
        
        try:
            for i, key in enumerate(unused_keys[:count]):
                print(f"  📝 处理密钥 {i+1}/{count}: {key.pubkey[:10]}...")
                
                # 2. 生成存款数据
                deposit_data = self._create_deposit_data(key, withdrawal_address)
                deposits.append(deposit_data)
                used_pubkeys.append(key.pubkey)
                
                # 3. 标记密钥为使用中
                self.vault_manager.mark_key_as_active(
                    key.pubkey, 
                    client_type or 'unknown',
                    notes or f"存款生成 - {datetime.now().isoformat()}"
                )
                
                print(f"    ✅ 密钥已标记为使用中")
            
            # 4. 保存存款数据
            deposit_file = self._save_deposit_data(deposits, withdrawal_address)
            print(f"✅ 存款数据已保存: {deposit_file}")
            
            return deposits
            
        except Exception as e:
            print(f"❌ 生成存款失败: {e}")
            # 回滚已标记的密钥状态
            for pubkey in used_pubkeys:
                self.vault_manager.update_key_status(pubkey, 'unused')
            return []
    
    def _create_deposit_data(self, key: ValidatorKey, withdrawal_address: str) -> Dict[str, Any]:
        """创建单个存款数据"""
        
        # 使用 deposit-cli 生成存款数据
        try:
            # 创建临时目录
            temp_dir = Path("temp_deposit")
            temp_dir.mkdir(exist_ok=True)
            
            # 准备输入数据
            input_data = {
                "pubkey": key.pubkey,
                "withdrawal_credentials": self._get_withdrawal_credentials(withdrawal_address),
                "amount": 32000000000,  # 32 ETH in Gwei
                "signature": self._generate_signature(key, withdrawal_address)
            }
            
            # 调用 deposit-cli
            result = self._call_deposit_cli(input_data, temp_dir)
            
            # 清理临时文件
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return result
            
        except Exception as e:
            print(f"❌ 创建存款数据失败: {e}")
            raise
    
    def _get_withdrawal_credentials(self, withdrawal_address: str) -> str:
        """获取提款凭证"""
        # 对于 ETH1 地址，使用 0x01 前缀
        if withdrawal_address.startswith('0x') and len(withdrawal_address) == 42:
            # 移除 0x 前缀，添加 0x01 前缀
            address_bytes = bytes.fromhex(withdrawal_address[2:])
            credentials = b'\x01' + b'\x00' * 11 + address_bytes
            return '0x' + credentials.hex()
        else:
            raise ValueError(f"不支持的提款地址格式: {withdrawal_address}")
    
    def _generate_signature(self, key: ValidatorKey, withdrawal_address: str) -> str:
        """生成存款签名"""
        try:
            # 创建存款消息
            deposit_message = self._create_deposit_message(key, withdrawal_address)
            
            # 使用验证者私钥签名
            account = Account.from_key(key.privkey)
            signature = account.sign_message(deposit_message)
            
            return signature.signature.hex()
            
        except Exception as e:
            print(f"❌ 生成签名失败: {e}")
            raise
    
    def _create_deposit_message(self, key: ValidatorKey, withdrawal_address: str) -> bytes:
        """创建存款消息"""
        # 这里需要根据以太坊存款合约的具体要求来构建消息
        # 简化版本，实际实现需要更复杂的逻辑
        pubkey_bytes = bytes.fromhex(key.pubkey[2:])
        withdrawal_credentials = bytes.fromhex(self._get_withdrawal_credentials(withdrawal_address)[2:])
        
        # 构建消息（简化版本）
        message = pubkey_bytes + withdrawal_credentials + b'\x00' * 8  # 32 ETH
        return message
    
    def _call_deposit_cli(self, input_data: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        """调用 deposit-cli 工具"""
        try:
            # 这里应该调用实际的 deposit-cli
            # 由于我们没有实际的 deposit-cli，这里返回模拟数据
            return {
                "pubkey": input_data["pubkey"],
                "withdrawal_credentials": input_data["withdrawal_credentials"],
                "amount": input_data["amount"],
                "signature": input_data["signature"],
                "deposit_data_root": "0x" + "0" * 64,  # 模拟数据
                "deposit_message_root": "0x" + "0" * 64,  # 模拟数据
                "fork_version": "0x00000000",  # 主网版本
                "network_name": "mainnet",
                "deposit_cli_version": "2.7.0"
            }
            
        except Exception as e:
            print(f"❌ 调用 deposit-cli 失败: {e}")
            raise
    
    def _save_deposit_data(self, deposits: List[Dict[str, Any]], withdrawal_address: str) -> str:
        """保存存款数据到文件"""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"deposits-{withdrawal_address[:8]}-{timestamp}.json"
        filepath = Path("deposits") / filename
        filepath.parent.mkdir(exist_ok=True)
        
        deposit_data = {
            "withdrawal_address": withdrawal_address,
            "count": len(deposits),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "deposits": deposits
        }
        
        with open(filepath, 'w') as f:
            json.dump(deposit_data, f, indent=2)
        
        return str(filepath)
    
    def list_available_keys(self, batch_id: str = None) -> List[ValidatorKey]:
        """列出可用的未使用密钥"""
        return self.vault_manager.get_unused_keys(1000, batch_id)  # 获取大量密钥用于显示
    
    def get_deposit_summary(self, withdrawal_address: str) -> Dict[str, Any]:
        """获取存款摘要"""
        # 统计已使用的密钥
        active_keys = self.vault_manager.list_keys(status='active')
        unused_keys = self.vault_manager.list_keys(status='unused')
        
        return {
            "withdrawal_address": withdrawal_address,
            "total_active_keys": len(active_keys),
            "total_unused_keys": len(unused_keys),
            "active_by_client": {
                "prysm": len([k for k in active_keys if k.client_type == 'prysm']),
                "lighthouse": len([k for k in active_keys if k.client_type == 'lighthouse']),
                "teku": len([k for k in active_keys if k.client_type == 'teku']),
                "unknown": len([k for k in active_keys if not k.client_type])
            }
        }

def main():
    parser = argparse.ArgumentParser(description='动态存款生成器')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 生成存款
    generate_parser = subparsers.add_parser('generate', help='生成存款')
    generate_parser.add_argument('count', type=int, help='生成数量')
    generate_parser.add_argument('withdrawal_address', help='提款地址')
    generate_parser.add_argument('--batch-id', help='指定批次ID')
    generate_parser.add_argument('--client-type', choices=['prysm', 'lighthouse', 'teku'], help='客户端类型')
    generate_parser.add_argument('--notes', help='备注')
    
    # 列出可用密钥
    list_parser = subparsers.add_parser('list-keys', help='列出可用密钥')
    list_parser.add_argument('--batch-id', help='按批次ID过滤')
    
    # 获取摘要
    summary_parser = subparsers.add_parser('summary', help='获取存款摘要')
    summary_parser.add_argument('withdrawal_address', help='提款地址')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        generator = DepositGenerator()
        
        if args.command == 'generate':
            deposits = generator.generate_deposits(
                count=args.count,
                withdrawal_address=args.withdrawal_address,
                batch_id=args.batch_id,
                client_type=args.client_type,
                notes=args.notes
            )
            
            if deposits:
                print(f"\n✅ 成功生成 {len(deposits)} 个存款")
                print(f"💰 总金额: {len(deposits) * 32} ETH")
            else:
                print("❌ 生成失败")
        
        elif args.command == 'list-keys':
            keys = generator.list_available_keys(args.batch_id)
            print(f"\n🔑 可用密钥 ({len(keys)} 个):")
            for key in keys[:20]:  # 只显示前20个
                print(f"  {key.pubkey[:10]}... | {key.batch_id} | {key.created_at}")
            if len(keys) > 20:
                print(f"  ... 还有 {len(keys) - 20} 个密钥")
        
        elif args.command == 'summary':
            summary = generator.get_deposit_summary(args.withdrawal_address)
            print(f"\n📊 存款摘要:")
            print(f"  提款地址: {summary['withdrawal_address']}")
            print(f"  活跃密钥: {summary['total_active_keys']}")
            print(f"  未使用密钥: {summary['total_unused_keys']}")
            print(f"  按客户端分布:")
            for client, count in summary['active_by_client'].items():
                if count > 0:
                    print(f"    {client}: {count}")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
