"""
交易服务
处理通过交易哈希查询和保存交易信息
"""
import logging
from typing import List, Dict, Any, Optional
from web3 import Web3
from web3.types import TxReceipt, TxData
from datetime import datetime

from app.models.database import DepositTransaction, ValidatorKey, BatchDepositContract
from app.models.enums import DepositStatus, ValidatorKeyStatus
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TransactionService:
    """交易服务"""
    
    def __init__(self, db: Session, web3: Web3):
        self.db = db
        self.web3 = web3
    
    def process_deposit_transactions(
        self,
        tx_hashes: List[str],
        from_address: str,
        deposit_type: str,
        batch_contract_address: Optional[str] = None,
        official_contract_address: Optional[str] = None,
        deposit_data_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        处理存款交易哈希，查询交易信息并保存到数据库
        
        Args:
            tx_hashes: 交易哈希列表
            from_address: 发送地址
            deposit_type: 存款类型 ('batch' 或 'official')
            batch_contract_address: Batch Deposit 合约地址
            official_contract_address: 官方 Deposit 合约地址
            deposit_data_list: Deposit Data 列表（可选，用于验证）
            
        Returns:
            处理结果列表
        """
        results = []
        
        for tx_hash in tx_hashes:
            try:
                # 查询交易
                tx = self.web3.eth.get_transaction(tx_hash)
                if not tx:
                    results.append({
                        'tx_hash': tx_hash,
                        'status': 'failed',
                        'error': '交易不存在'
                    })
                    continue
                
                # 验证发送地址
                if tx['from'].lower() != from_address.lower():
                    results.append({
                        'tx_hash': tx_hash,
                        'status': 'failed',
                        'error': f'交易发送地址不匹配: 期望 {from_address}, 实际 {tx["from"]}'
                    })
                    continue
                
                # 等待交易确认
                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt.status != 1:
                    results.append({
                        'tx_hash': tx_hash,
                        'status': 'failed',
                        'error': '交易执行失败'
                    })
                    continue
                
                # 根据存款类型处理
                if deposit_type == 'batch':
                    result = self._process_batch_deposit_transaction(
                        tx, receipt, batch_contract_address, deposit_data_list
                    )
                else:
                    result = self._process_official_deposit_transaction(
                        tx, receipt, official_contract_address, deposit_data_list
                    )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"处理交易 {tx_hash} 失败: {e}", exc_info=True)
                results.append({
                    'tx_hash': tx_hash,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    def _process_batch_deposit_transaction(
        self,
        tx: TxData,
        receipt: TxReceipt,
        contract_address: Optional[str],
        deposit_data_list: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """处理批量存款交易"""
        tx_hash = tx['hash'].hex()
        
        # 验证合约地址
        if contract_address and receipt['to']:
            if receipt['to'].lower() != contract_address.lower():
                return {
                    'tx_hash': tx_hash,
                    'status': 'failed',
                    'error': f'合约地址不匹配: 期望 {contract_address}, 实际 {receipt["to"]}'
                }
        
        # 生成批次ID（基于交易提交时间，确保同一交易的所有验证者使用相同的批次ID）
        # 使用交易的 block timestamp 或当前时间
        try:
            # 尝试从区块获取时间戳
            block = self.web3.eth.get_block(receipt['blockNumber'])
            if block and 'timestamp' in block:
                batch_timestamp = datetime.fromtimestamp(block['timestamp'])
            else:
                batch_timestamp = datetime.utcnow()
        except Exception as e:
            logger.warning(f"无法获取区块时间戳，使用当前时间: {e}")
            batch_timestamp = datetime.utcnow()
        
        batch_id = f"batch-{batch_timestamp.strftime('%Y%m%d-%H%M%S')}"
        
        # 从交易日志中解析存款信息
        # Batch Deposit 合约会触发多个 DepositEvent
        # 我们需要从 deposit_data_list 中匹配 pubkey
        
        if not deposit_data_list:
            # 如果没有提供 deposit_data_list，尝试从交易输入数据解析
            # 这比较复杂，暂时返回成功但标记为需要验证
            logger.warning(f"批量存款交易 {tx_hash} 没有提供 deposit_data_list，无法解析具体验证者")
            return {
                'tx_hash': tx_hash,
                'status': 'submitted',
                'batch_id': batch_id,  # 使用时间戳格式的批次ID
                'validator_count': 0,  # 未知
                'note': '需要手动验证交易内容'
            }
        
        # 保存每个验证者的存款记录
        saved_count = 0
        for deposit_data in deposit_data_list:
            try:
                pubkey = deposit_data.get('pubkey', '').lower().replace('0x', '')
                pubkey_db_format = f"0x{pubkey}" if not pubkey.startswith('0x') else pubkey
                
                # 查找验证者密钥
                validator_key = self.db.query(ValidatorKey).filter(
                    ValidatorKey.pubkey == pubkey_db_format
                ).first()
                
                if validator_key:
                    # 检查是否已存在
                    existing = self.db.query(DepositTransaction).filter(
                        DepositTransaction.tx_hash == tx_hash,
                        DepositTransaction.pubkey == validator_key.pubkey
                    ).first()
                    
                    if not existing:
                        # 计算金额
                        amount_gwei = deposit_data.get('amount', 32 * 1e9)
                        amount_wei = int(amount_gwei)
                        amount_eth = float(amount_wei) / 1e18
                        
                        deposit_tx = DepositTransaction(
                            pubkey=validator_key.pubkey,
                            tx_hash=tx_hash,
                            batch_id=batch_id,  # 使用时间戳格式的批次ID，确保同一交易的所有验证者使用相同的批次ID
                            status=DepositStatus.SUBMITTED.value,
                            amount_wei=amount_wei,
                            amount_eth=amount_eth,
                            block_number=receipt['blockNumber'],
                            submitted_at=batch_timestamp  # 使用批次时间戳作为提交时间
                        )
                        self.db.add(deposit_tx)
                        
                        # 更新密钥状态
                        from app.services.validator_state_machine import ValidatorStateMachine
                        state_machine = ValidatorStateMachine(self.db)
                        state_machine.transition(
                            validator_key,
                            ValidatorKeyStatus.PENDING,
                            reason='deposit_submitted',
                            metadata={'tx_hash': tx_hash}
                        )
                        validator_key.deposit_tx_hash = tx_hash
                        
                        saved_count += 1
            except Exception as e:
                logger.error(f"保存验证者 {deposit_data.get('pubkey', 'unknown')} 的存款记录失败: {e}")
        
        self.db.commit()
        
        return {
            'tx_hash': tx_hash,
            'status': 'submitted',
            'batch_id': batch_id,  # 返回时间戳格式的批次ID
            'validator_count': saved_count,
            'pubkeys': [dd.get('pubkey', '') for dd in deposit_data_list]
        }
    
    def _process_official_deposit_transaction(
        self,
        tx: TxData,
        receipt: TxReceipt,
        contract_address: Optional[str],
        deposit_data_list: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """处理官方存款交易"""
        tx_hash = tx['hash'].hex()
        
        # 验证合约地址
        if contract_address and receipt['to']:
            if receipt['to'].lower() != contract_address.lower():
                return {
                    'tx_hash': tx_hash,
                    'status': 'failed',
                    'error': f'合约地址不匹配: 期望 {contract_address}, 实际 {receipt["to"]}'
                }
        
        # 官方存款通常是单个验证者
        # 如果没有提供 deposit_data_list，尝试从交易日志解析
        if not deposit_data_list:
            logger.warning(f"官方存款交易 {tx_hash} 没有提供 deposit_data_list，无法解析验证者")
            return {
                'tx_hash': tx_hash,
                'status': 'submitted',
                'validator_count': 0,
                'note': '需要手动验证交易内容'
            }
        
        # 官方存款应该只有一个 deposit_data
        if len(deposit_data_list) > 1:
            logger.warning(f"官方存款交易 {tx_hash} 包含多个 deposit_data，只处理第一个")
        
        deposit_data = deposit_data_list[0]
        pubkey = deposit_data.get('pubkey', '').lower().replace('0x', '')
        pubkey_db_format = f"0x{pubkey}" if not pubkey.startswith('0x') else pubkey
        
        # 查找验证者密钥
        validator_key = self.db.query(ValidatorKey).filter(
            ValidatorKey.pubkey == pubkey_db_format
        ).first()
        
        if not validator_key:
            return {
                'tx_hash': tx_hash,
                'status': 'failed',
                'error': f'未找到验证者密钥: {pubkey_db_format[:20]}...'
            }
        
        # 检查是否已存在
        existing = self.db.query(DepositTransaction).filter(
            DepositTransaction.tx_hash == tx_hash,
            DepositTransaction.pubkey == validator_key.pubkey
        ).first()
        
        if existing:
            return {
                'tx_hash': tx_hash,
                'status': 'submitted',
                'validator_count': 1,
                'pubkeys': [pubkey_db_format],
                'note': '交易已存在'
            }
        
        # 计算金额
        amount_gwei = deposit_data.get('amount', 32 * 1e9)
        amount_wei = int(amount_gwei)
        amount_eth = float(amount_wei) / 1e18
        
        deposit_tx = DepositTransaction(
            pubkey=validator_key.pubkey,
            tx_hash=tx_hash,
            batch_id=None,  # 官方存款没有批次ID
            status=DepositStatus.SUBMITTED.value,
            amount_wei=amount_wei,
            amount_eth=amount_eth,
            block_number=receipt['blockNumber'],
            submitted_at=datetime.utcnow()
        )
        self.db.add(deposit_tx)
        
        # 更新密钥状态
        from app.services.validator_state_machine import ValidatorStateMachine
        state_machine = ValidatorStateMachine(self.db)
        state_machine.transition(
            validator_key,
            ValidatorKeyStatus.PENDING,
            reason='deposit_submitted',
            metadata={'tx_hash': tx_hash}
        )
        validator_key.deposit_tx_hash = tx_hash
        
        self.db.commit()
        
        return {
            'tx_hash': tx_hash,
            'status': 'submitted',
            'validator_count': 1,
            'pubkeys': [pubkey_db_format]
        }

