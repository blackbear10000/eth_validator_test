#!/usr/bin/env python3
"""
存款数据提交工具
将存款数据提交到以太坊网络
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from web3 import Web3
    from eth_account import Account
    from eth_utils import to_hex, to_bytes
except ImportError as e:
    print(f"❌ 导入 Web3 依赖失败: {e}")
    print("请安装依赖: pip install web3 eth-account")
    sys.exit(1)


class DepositSubmitter:
    """存款提交器"""
    
    def __init__(self, config_file: str = "config/config.json"):
        """初始化存款提交器"""
        self.config = self._load_config(config_file)
        self.web3 = None
        self.account = None
        self.deposit_contract = None
        
    def _load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            sys.exit(1)
    
    def connect_to_network(self) -> bool:
        """连接到以太坊网络"""
        try:
            # 从配置获取网络信息
            web3_url = self.config.get('kurtosis_testnet', {}).get('web3_url', 'http://localhost:8545')
            print(f"🔗 连接到网络: {web3_url}")
            
            # 连接 Web3
            self.web3 = Web3(Web3.HTTPProvider(web3_url))
            
            if not self.web3.is_connected():
                print("❌ 无法连接到以太坊网络")
                return False
            
            # 检查网络状态
            try:
                latest_block = self.web3.eth.block_number
                print(f"✅ 网络连接成功，最新区块: {latest_block}")
            except Exception as e:
                print(f"⚠️  网络连接但无法获取区块信息: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ 连接网络失败: {e}")
            return False
    
    def setup_account(self) -> bool:
        """设置账户"""
        try:
            # 从配置获取账户信息
            kurtosis_config = self.config.get('kurtosis_testnet', {})
            private_key = kurtosis_config.get('private_key')
            from_address = kurtosis_config.get('from_address')
            
            if not private_key or not from_address:
                print("❌ 配置文件中缺少账户信息")
                return False
            
            # 创建账户
            self.account = Account.from_key(private_key)
            
            # 验证地址匹配
            if self.account.address.lower() != from_address.lower():
                print(f"❌ 私钥与地址不匹配")
                print(f"   私钥对应地址: {self.account.address}")
                print(f"   配置地址: {from_address}")
                return False
            
            # 检查余额
            balance = self.web3.eth.get_balance(self.account.address)
            balance_eth = self.web3.from_wei(balance, 'ether')
            print(f"💰 账户余额: {balance_eth:.4f} ETH")
            
            if balance < self.web3.to_wei(1, 'ether'):
                print("⚠️  账户余额较低，可能无法完成存款")
            
            return True
            
        except Exception as e:
            print(f"❌ 设置账户失败: {e}")
            return False
    
    def setup_deposit_contract(self) -> bool:
        """设置存款合约"""
        try:
            # 获取存款合约地址
            contract_address = self.config.get('kurtosis_testnet', {}).get('deposit_contract_address')
            if not contract_address:
                print("❌ 配置文件中缺少存款合约地址")
                return False
            
            print(f"📋 存款合约地址: {contract_address}")
            
            # 存款合约 ABI (简化版，只包含 deposit 函数)
            deposit_abi = [
                {
                    "inputs": [
                        {"name": "pubkey", "type": "bytes"},
                        {"name": "withdrawal_credentials", "type": "bytes"},
                        {"name": "signature", "type": "bytes"},
                        {"name": "deposit_data_root", "type": "bytes32"}
                    ],
                    "name": "deposit",
                    "outputs": [],
                    "stateMutability": "payable",
                    "type": "function"
                }
            ]
            
            # 创建合约实例
            self.deposit_contract = self.web3.eth.contract(
                address=contract_address,
                abi=deposit_abi
            )
            
            print("✅ 存款合约设置成功")
            return True
            
        except Exception as e:
            print(f"❌ 设置存款合约失败: {e}")
            return False
    
    def submit_deposit(self, deposit_data: Dict) -> bool:
        """提交单个存款"""
        try:
            # 准备存款数据
            pubkey = to_bytes(hexstr=deposit_data['pubkey'])
            withdrawal_credentials = to_bytes(hexstr=deposit_data['withdrawal_credentials'])
            signature = to_bytes(hexstr=deposit_data['signature'])
            deposit_data_root = to_bytes(hexstr=deposit_data['deposit_data_root'])
            
            # 构建交易
            gas_price = self.web3.to_wei(20, 'gwei')  # 20 Gwei
            gas_limit = 200000  # 足够的 gas limit
            
            # 计算存款金额 (32 ETH)
            deposit_amount = self.web3.to_wei(32, 'ether')
            
            # 构建交易
            transaction = self.deposit_contract.functions.deposit(
                pubkey,
                withdrawal_credentials,
                signature,
                deposit_data_root
            ).build_transaction({
                'from': self.account.address,
                'value': deposit_amount,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            # 签名交易
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
            
            # 发送交易
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            print(f"📤 交易已发送: {tx_hash.hex()}")
            
            # 等待交易确认
            print("⏳ 等待交易确认...")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                print(f"✅ 存款成功确认，区块: {receipt.blockNumber}")
                print(f"💰 Gas 使用: {receipt.gasUsed}")
                return True
            else:
                print("❌ 交易失败")
                return False
                
        except Exception as e:
            print(f"❌ 提交存款失败: {e}")
            return False
    
    def submit_deposits_from_file(self, deposit_file: str) -> bool:
        """从文件提交存款数据"""
        try:
            # 读取存款数据
            with open(deposit_file, 'r') as f:
                deposits = json.load(f)
            
            if not isinstance(deposits, list):
                print("❌ 存款数据格式错误")
                return False
            
            print(f"📋 准备提交 {len(deposits)} 个存款...")
            
            # 连接网络
            if not self.connect_to_network():
                return False
            
            # 设置账户
            if not self.setup_account():
                return False
            
            # 设置合约
            if not self.setup_deposit_contract():
                return False
            
            # 提交每个存款
            success_count = 0
            failed_count = 0
            
            for i, deposit in enumerate(deposits):
                print(f"\n🔍 提交存款 {i+1}/{len(deposits)}:")
                print(f"   公钥: {deposit.get('pubkey', '')[:20]}...")
                
                if self.submit_deposit(deposit):
                    success_count += 1
                    print(f"   ✅ 存款 {i+1} 提交成功")
                else:
                    failed_count += 1
                    print(f"   ❌ 存款 {i+1} 提交失败")
                
                # 在存款之间稍作延迟
                if i < len(deposits) - 1:
                    print("⏳ 等待 2 秒...")
                    time.sleep(2)
            
            # 总结
            print(f"\n📊 提交结果:")
            print(f"   ✅ 成功: {success_count}")
            print(f"   ❌ 失败: {failed_count}")
            print(f"   📈 成功率: {success_count/(success_count+failed_count)*100:.1f}%")
            
            return failed_count == 0
            
        except Exception as e:
            print(f"❌ 提交存款数据失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="提交存款数据到以太坊网络")
    parser.add_argument("deposit_file", help="存款数据文件路径")
    parser.add_argument("--config", default="config/config.json", help="配置文件路径")
    
    args = parser.parse_args()
    
    print("🚀 存款数据提交工具")
    print("=" * 50)
    
    # 创建提交器
    submitter = DepositSubmitter(args.config)
    
    # 提交存款
    success = submitter.submit_deposits_from_file(args.deposit_file)
    
    if success:
        print("\n🎉 所有存款提交成功！")
        sys.exit(0)
    else:
        print("\n❌ 部分存款提交失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
