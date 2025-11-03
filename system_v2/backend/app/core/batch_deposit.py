"""
Batch Deposit Contract 集成
实现批量存款提交，自动分批处理（每批最多 100 个验证者）
"""
import logging
from typing import List, Dict, Any, Optional
from web3 import Web3
from eth_account import Account
from eth_utils import to_bytes, to_hex

from app.config import settings
from app.utils.exceptions import DepositGenerationError

logger = logging.getLogger(__name__)


class BatchDepositClient:
    """
    Batch Deposit Contract 客户端
    处理批量存款提交，支持自动分批
    """
    
    # 合约常量（来自 BatchDeposits.sol）
    PUBKEY_LENGTH = 48
    SIGNATURE_LENGTH = 96
    CREDENTIALS_LENGTH = 32
    MAX_VALIDATORS = 100
    MIN_DEPOSIT_AMOUNT = 32 * 10**18  # 32 ETH in wei
    MAX_DEPOSIT_AMOUNT = 2048 * 10**18  # 2048 ETH in wei
    
    def __init__(
        self,
        web3: Web3,
        contract_address: str,
        from_address: str,
        private_key: Optional[str] = None
    ):
        """
        初始化 Batch Deposit 客户端
        
        Args:
            web3: Web3 实例
            contract_address: Batch Deposit Contract 地址
            from_address: 发送交易的钱包地址
            private_key: 私钥（用于签名交易，可选，也可以从账户管理器获取）
        """
        self.web3 = web3
        self.contract_address = contract_address
        self.from_address = from_address
        self.private_key = private_key
        
        # 加载合约 ABI（简化版本，只包含必要的方法）
        self.contract_abi = [
            {
                "inputs": [
                    {"internalType": "bytes", "name": "pubkeys", "type": "bytes"},
                    {"internalType": "bytes", "name": "withdrawal_credentials", "type": "bytes"},
                    {"internalType": "bytes", "name": "signatures", "type": "bytes"},
                    {"internalType": "bytes32[]", "name": "deposit_data_roots", "type": "bytes32[]"},
                    {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
                ],
                "name": "batchDeposit",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "_fee",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        self.contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=self.contract_abi
        )
    
    def prepare_batch_data(
        self,
        deposit_data_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        准备批量存款数据，转换为合约所需格式
        
        Args:
            deposit_data_list: Deposit Data 列表
            
        Returns:
            准备好的批量数据字典
        """
        if len(deposit_data_list) == 0:
            raise ValueError("Deposit Data 列表不能为空")
        
        if len(deposit_data_list) > self.MAX_VALIDATORS:
            raise ValueError(f"单次最多支持 {self.MAX_VALIDATORS} 个验证者")
        
        # 提取所有验证者共享的提款凭证（0x01 类型，所有验证者使用同一个）
        first_withdrawal_credentials = deposit_data_list[0]['withdrawal_credentials']
        
        # 验证所有验证者使用相同的提款凭证
        for deposit_data in deposit_data_list:
            if deposit_data['withdrawal_credentials'] != first_withdrawal_credentials:
                raise ValueError("所有验证者必须使用相同的提款凭证")
        
        # 转换为字节格式
        pubkeys_bytes = b''
        signatures_bytes = b''
        deposit_data_roots = []
        amounts = []
        
        for deposit_data in deposit_data_list:
            # 公钥（48 bytes）
            pubkey_bytes = to_bytes(hexstr=deposit_data['pubkey'])
            if len(pubkey_bytes) != self.PUBKEY_LENGTH:
                raise ValueError(f"公钥长度不正确: {len(pubkey_bytes)} != {self.PUBKEY_LENGTH}")
            pubkeys_bytes += pubkey_bytes
            
            # 签名（96 bytes）
            signature_bytes = to_bytes(hexstr=deposit_data['signature'])
            if len(signature_bytes) != self.SIGNATURE_LENGTH:
                raise ValueError(f"签名长度不正确: {len(signature_bytes)} != {self.SIGNATURE_LENGTH}")
            signatures_bytes += signature_bytes
            
            # Deposit Data Root（32 bytes）
            deposit_data_root = to_bytes(hexstr=deposit_data['deposit_data_root'])
            if len(deposit_data_root) != 32:
                raise ValueError(f"Deposit Data Root 长度不正确: {len(deposit_data_root)} != 32")
            deposit_data_roots.append(deposit_data_root)
            
            # 金额（wei）
            # Deposit Data 中的 amount 是 Gwei，需要转换为 wei
            amount_gwei = deposit_data['amount']
            amount_wei = amount_gwei * 10**9  # Gwei to wei
            amounts.append(amount_wei)
        
        # 提款凭证（32 bytes）
        withdrawal_credentials_bytes = to_bytes(hexstr=first_withdrawal_credentials)
        if len(withdrawal_credentials_bytes) != self.CREDENTIALS_LENGTH:
            raise ValueError(f"提款凭证长度不正确: {len(withdrawal_credentials_bytes)} != {self.CREDENTIALS_LENGTH}")
        
        return {
            'pubkeys': pubkeys_bytes,
            'withdrawal_credentials': withdrawal_credentials_bytes,
            'signatures': signatures_bytes,
            'deposit_data_roots': deposit_data_roots,
            'amounts': amounts,
            'count': len(deposit_data_list)
        }
    
    def get_contract_fee(self) -> int:
        """
        获取合约费用
        
        Returns:
            每个验证者的费用（wei）
        """
        try:
            fee = self.contract.functions._fee().call()
            return fee
        except Exception as e:
            logger.warning(f"无法获取合约费用，使用默认值 0: {e}")
            return 0
    
    def calculate_total_value(
        self,
        deposit_data_list: List[Dict[str, Any]],
        fee: Optional[int] = None
    ) -> int:
        """
        计算需要发送的总金额（包括存款金额和费用）
        
        Args:
            deposit_data_list: Deposit Data 列表
            fee: 每个验证者的费用（可选，如果不提供则从合约查询）
            
        Returns:
            总金额（wei）
        """
        if fee is None:
            fee = self.get_contract_fee()
        
        # 计算总存款金额
        total_deposit_amount = 0
        for deposit_data in deposit_data_list:
            amount_gwei = deposit_data['amount']
            amount_wei = amount_gwei * 10**9  # Gwei to wei
            total_deposit_amount += amount_wei
        
        # 计算总费用
        total_fee = fee * len(deposit_data_list)
        
        # 总金额
        total_value = total_deposit_amount + total_fee
        
        return total_value
    
    def submit_batch_deposit(
        self,
        deposit_data_list: List[Dict[str, Any]],
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> str:
        """
        提交批量存款交易
        
        Args:
            deposit_data_list: Deposit Data 列表
            gas_price: Gas 价格（可选）
            gas_limit: Gas 限制（可选）
            
        Returns:
            交易哈希
        """
        # 准备批量数据
        batch_data = self.prepare_batch_data(deposit_data_list)
        
        # 计算总金额
        total_value = self.calculate_total_value(deposit_data_list)
        
        # 构建交易
        transaction = self.contract.functions.batchDeposit(
            batch_data['pubkeys'],
            batch_data['withdrawal_credentials'],
            batch_data['signatures'],
            batch_data['deposit_data_roots'],
            batch_data['amounts']
        ).build_transaction({
            'from': self.from_address,
            'value': total_value,
            'gas': gas_limit or settings.batch_deposit_gas_limit,
            'gasPrice': gas_price or self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(self.from_address)
        })
        
        # 签名交易
        if not self.private_key:
            raise ValueError("需要私钥来签名交易")
        
        signed_txn = self.web3.eth.account.sign_transaction(transaction, self.private_key)
        
        # 发送交易
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_hash_hex = tx_hash.hex()
        
        logger.info(f"批量存款交易已提交: {tx_hash_hex} (验证者数量: {len(deposit_data_list)})")
        
        return tx_hash_hex
    
    def submit_multiple_batches(
        self,
        deposit_data_list: List[Dict[str, Any]],
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        提交多个批次（自动分批）
        如果验证者数量超过 MAX_VALIDATORS，自动拆分为多个批次
        
        Args:
            deposit_data_list: Deposit Data 列表
            gas_price: Gas 价格（可选）
            gas_limit: Gas 限制（可选）
            
        Returns:
            批次提交结果列表，每个结果包含批次信息和交易哈希
        """
        total_count = len(deposit_data_list)
        batch_results = []
        
        # 自动分批
        for i in range(0, total_count, self.MAX_VALIDATORS):
            batch_data = deposit_data_list[i:i + self.MAX_VALIDATORS]
            batch_num = i // self.MAX_VALIDATORS + 1
            total_batches = (total_count + self.MAX_VALIDATORS - 1) // self.MAX_VALIDATORS
            
            logger.info(f"提交批次 {batch_num}/{total_batches} ({len(batch_data)} 个验证者)")
            
            try:
                tx_hash = self.submit_batch_deposit(
                    batch_data,
                    gas_price=gas_price,
                    gas_limit=gas_limit
                )
                
                batch_results.append({
                    'batch_number': batch_num,
                    'validator_count': len(batch_data),
                    'tx_hash': tx_hash,
                    'status': 'submitted',
                    'pubkeys': [dd['pubkey'] for dd in batch_data]
                })
                
            except Exception as e:
                logger.error(f"批次 {batch_num} 提交失败: {e}")
                batch_results.append({
                    'batch_number': batch_num,
                    'validator_count': len(batch_data),
                    'tx_hash': None,
                    'status': 'failed',
                    'error': str(e),
                    'pubkeys': [dd['pubkey'] for dd in batch_data]
                })
        
        logger.info(f"批量存款提交完成: {len(batch_results)} 个批次，{total_count} 个验证者")
        
        return batch_results
    
    def wait_for_confirmation(
        self,
        tx_hash: str,
        timeout: int = 300,
        confirmation_blocks: int = 1
    ) -> Dict[str, Any]:
        """
        等待交易确认
        
        Args:
            tx_hash: 交易哈希
            timeout: 超时时间（秒）
            confirmation_blocks: 需要确认的区块数
            
        Returns:
            交易收据信息
        """
        try:
            receipt = self.web3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=timeout
            )
            
            logger.info(f"交易已确认: {tx_hash} (区块: {receipt.blockNumber}, 状态: {receipt.status})")
            
            return {
                'tx_hash': tx_hash,
                'status': 'confirmed' if receipt.status == 1 else 'failed',
                'block_number': receipt.blockNumber,
                'gas_used': receipt.gasUsed,
                'receipt': receipt
            }
            
        except Exception as e:
            logger.error(f"等待交易确认失败: {tx_hash}, {e}")
            raise

