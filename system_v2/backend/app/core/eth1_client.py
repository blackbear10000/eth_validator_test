"""
ETH1 客户端
封装 ETH1 RPC 调用，用于检查交易状态和内存池
"""
import logging
from typing import Optional, Dict, Any
from web3 import Web3
from web3.exceptions import TransactionNotFound

logger = logging.getLogger(__name__)


class ETH1Client:
    """
    ETH1 客户端
    提供交易状态查询和内存池检查功能
    """
    
    def __init__(self, rpc_url: str):
        """
        初始化 ETH1 客户端
        
        Args:
            rpc_url: ETH1 RPC URL
        """
        self.rpc_url = rpc_url
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not self.web3.is_connected():
            raise ValueError(f"无法连接到 RPC: {rpc_url}")
    
    def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        获取交易状态
        
        Args:
            tx_hash: 交易哈希
            
        Returns:
            交易状态字典，包含:
            - status: 'mempool' | 'confirmed' | 'failed' | 'not_found'
            - receipt: 交易收据（如果已确认）
            - block_number: 区块号（如果已确认）
        """
        try:
            # 尝试获取交易收据（如果已确认）
            try:
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                
                if receipt.status == 1:
                    return {
                        'status': 'confirmed',
                        'receipt': receipt,
                        'block_number': receipt.blockNumber,
                        'gas_used': receipt.gasUsed,
                    }
                else:
                    return {
                        'status': 'failed',
                        'receipt': receipt,
                        'block_number': receipt.blockNumber,
                    }
            except TransactionNotFound:
                # 交易未确认，检查是否在内存池中
                if self.check_transaction_in_mempool(tx_hash):
                    return {
                        'status': 'mempool',
                        'receipt': None,
                        'block_number': None,
                    }
                else:
                    return {
                        'status': 'not_found',
                        'receipt': None,
                        'block_number': None,
                    }
        except Exception as e:
            logger.error(f"获取交易状态失败 ({tx_hash[:10]}...): {e}")
            return {
                'status': 'error',
                'error': str(e),
                'receipt': None,
                'block_number': None,
            }
    
    def check_transaction_in_mempool(self, tx_hash: str) -> bool:
        """
        检查交易是否在内存池中
        
        Args:
            tx_hash: 交易哈希
            
        Returns:
            是否在内存池中
        """
        try:
            # 方法1: 使用 geth 的 txpool.content
            try:
                txpool_content = self.web3.geth.txpool.content()
                
                # 检查 pending 和 queued 队列
                for account, txs in txpool_content.get('pending', {}).items():
                    for nonce, tx_list in txs.items():
                        for tx in tx_list:
                            if tx.get('hash') == tx_hash:
                                return True
                
                for account, txs in txpool_content.get('queued', {}).items():
                    for nonce, tx_list in txs.items():
                        for tx in tx_list:
                            if tx.get('hash') == tx_hash:
                                return True
            except Exception as e:
                logger.debug(f"无法使用 txpool.content 检查内存池: {e}")
            
            # 方法2: 尝试获取交易（如果存在但未确认，可能在内存池中）
            try:
                tx = self.web3.eth.get_transaction(tx_hash)
                if tx and tx.blockNumber is None:
                    # 交易存在但未被打包，可能在内存池中
                    return True
            except TransactionNotFound:
                pass
            except Exception as e:
                logger.debug(f"无法通过 get_transaction 检查内存池: {e}")
            
            # 方法3: 使用 eth_pendingTransactions (如果支持)
            try:
                pending_txs = self.web3.manager.request_blocking("eth_pendingTransactions", [])
                for tx in pending_txs:
                    if tx.get('hash') == tx_hash:
                        return True
            except Exception as e:
                logger.debug(f"无法使用 eth_pendingTransactions 检查内存池: {e}")
            
            return False
            
        except Exception as e:
            logger.warning(f"检查交易是否在内存池中失败 ({tx_hash[:10]}...): {e}")
            return False
    
    def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        获取交易收据
        
        Args:
            tx_hash: 交易哈希
            
        Returns:
            交易收据或 None
        """
        try:
            receipt = self.web3.eth.get_transaction_receipt(tx_hash)
            return {
                'status': receipt.status,
                'block_number': receipt.blockNumber,
                'gas_used': receipt.gasUsed,
                'transaction_hash': receipt.transactionHash.hex(),
            }
        except TransactionNotFound:
            return None
        except Exception as e:
            logger.error(f"获取交易收据失败 ({tx_hash[:10]}...): {e}")
            return None
    
    def health_check(self) -> bool:
        """
        检查客户端健康状态
        
        Returns:
            是否健康
        """
        try:
            block_number = self.web3.eth.block_number
            return block_number is not None
        except Exception as e:
            logger.error(f"ETH1 客户端健康检查失败: {e}")
            return False

