"""
官方 Deposit 合约客户端
直接调用官方 Deposit 合约的 deposit() 方法
支持单个和批量存款（通过循环调用）
"""
import logging
from typing import List, Dict, Any, Optional
from web3 import Web3
from eth_account import Account
from eth_utils import to_bytes

logger = logging.getLogger(__name__)

# 官方 Deposit 合约标准 ABI（只包含 deposit 方法）
DEPOSIT_CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "bytes", "name": "pubkey", "type": "bytes"},
            {"internalType": "bytes", "name": "withdrawal_credentials", "type": "bytes"},
            {"internalType": "bytes", "name": "signature", "type": "bytes"},
            {"internalType": "bytes32", "name": "deposit_data_root", "type": "bytes32"}
        ],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

# 标准 Deposit 合约地址（不同网络）
STANDARD_DEPOSIT_CONTRACTS = {
    "mainnet": "0x00000000219ab540356cBB839Cbe05303d7705Fa",
    "goerli": "0xff50b3d0C56e451cF6671c5d82cB12943C2b4F3A",
    "sepolia": "0x7f02C3E3c98b133055B8B348B2Ac625669e295B1",
    "holesky": "0x4242424242424242424242424242424242424242"
}


class OfficialDepositClient:
    """
    官方 Deposit 合约客户端
    处理直接调用官方 Deposit 合约的存款操作
    """
    
    def __init__(
        self,
        web3: Web3,
        contract_address: str,
        from_address: str,
        private_key: Optional[str] = None
    ):
        """
        初始化官方 Deposit 客户端
        
        Args:
            web3: Web3 实例
            contract_address: Deposit 合约地址
            from_address: 发送交易的钱包地址
            private_key: 私钥（用于签名交易）
        """
        self.web3 = web3
        self.contract_address = contract_address
        self.from_address = from_address
        self.private_key = private_key
        
        # 创建合约实例
        self.contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=DEPOSIT_CONTRACT_ABI
        )
    
    def submit_single_deposit(
        self,
        deposit_data: Dict[str, Any],
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> str:
        """
        提交单个存款
        
        Args:
            deposit_data: Deposit Data 字典
            gas_price: Gas 价格（可选）
            gas_limit: Gas 限制（可选）
            
        Returns:
            交易哈希
        """
        if not self.private_key:
            raise ValueError("需要私钥来签名交易")
        
        # 准备参数
        pubkey_bytes = to_bytes(hexstr=deposit_data['pubkey'])
        withdrawal_credentials_bytes = to_bytes(hexstr=deposit_data['withdrawal_credentials'])
        signature_bytes = to_bytes(hexstr=deposit_data['signature'])
        deposit_data_root_bytes = to_bytes(hexstr=deposit_data['deposit_data_root'])
        
        # 计算金额（从 Gwei 转换为 wei）
        amount_gwei = deposit_data['amount']
        amount_wei = amount_gwei * 10**9
        
        # 构建交易
        transaction = self.contract.functions.deposit(
            pubkey_bytes,
            withdrawal_credentials_bytes,
            signature_bytes,
            deposit_data_root_bytes
        ).build_transaction({
            'from': self.from_address,
            'value': amount_wei,
            'gas': gas_limit or 200000,  # 单个存款通常需要约 200k gas
            'gasPrice': gas_price or self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(self.from_address)
        })
        
        # 签名交易
        signed_txn = self.web3.eth.account.sign_transaction(transaction, self.private_key)
        
        # 发送交易（兼容 web3.py 6.0+）
        # web3.py 6.0+ 使用 raw_transaction（下划线），旧版本使用 rawTransaction（驼峰）
        raw_transaction = getattr(signed_txn, 'raw_transaction', None) or getattr(signed_txn, 'rawTransaction', None)
        if raw_transaction is None:
            raise ValueError("无法获取原始交易数据，签名交易对象缺少 raw_transaction 或 rawTransaction 属性")
        
        tx_hash = self.web3.eth.send_raw_transaction(raw_transaction)
        tx_hash_hex = tx_hash.hex()
        
        logger.info(f"官方 Deposit 交易已提交: {tx_hash_hex}")
        
        return tx_hash_hex
    
    def submit_multiple_deposits(
        self,
        deposit_data_list: List[Dict[str, Any]],
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        提交多个存款（通过循环调用单个存款方法）
        
        注意：官方 Deposit 合约不支持批量存款，所以需要为每个验证者发送单独的交易。
        这会产生较高的 gas 费用，但可以确保每个存款都是独立的交易。
        
        Args:
            deposit_data_list: Deposit Data 列表
            gas_price: Gas 价格（可选）
            gas_limit: Gas 限制（可选，每个交易）
            
        Returns:
            提交结果列表，每个结果包含交易哈希和状态
        """
        results = []
        
        for i, deposit_data in enumerate(deposit_data_list):
            try:
                logger.info(f"提交存款 {i+1}/{len(deposit_data_list)}: {deposit_data['pubkey'][:20]}...")
                
                tx_hash = self.submit_single_deposit(
                    deposit_data,
                    gas_price=gas_price,
                    gas_limit=gas_limit
                )
                
                results.append({
                    'pubkey': deposit_data['pubkey'],
                    'tx_hash': tx_hash,
                    'status': 'submitted',
                    'index': i
                })
                
            except Exception as e:
                logger.error(f"提交存款 {i+1} 失败: {e}")
                results.append({
                    'pubkey': deposit_data.get('pubkey', 'unknown'),
                    'tx_hash': None,
                    'status': 'failed',
                    'error': str(e),
                    'index': i
                })
        
        logger.info(f"官方 Deposit 提交完成: {len([r for r in results if r['status'] == 'submitted'])}/{len(deposit_data_list)} 成功")
        
        return results
    
    @staticmethod
    def get_standard_contract_address(network_name: str) -> Optional[str]:
        """
        获取标准 Deposit 合约地址
        
        Args:
            network_name: 网络名称（mainnet, goerli, sepolia, holesky）
            
        Returns:
            合约地址，如果网络不支持则返回 None
        """
        return STANDARD_DEPOSIT_CONTRACTS.get(network_name.lower())

