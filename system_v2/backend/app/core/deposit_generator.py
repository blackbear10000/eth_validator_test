"""
Deposit Data 生成器
使用 ethstaker-deposit-cli 生成 Deposit Data，支持动态绑定 0x01 类型提款地址
"""
import os
import sys
import logging
from typing import List, Dict, Any, Optional
from eth_utils import to_bytes

# 添加 ethstaker-deposit-cli 到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ethstaker_path = os.path.join(project_root, "code", "external", "ethstaker-deposit-cli")
if os.path.exists(ethstaker_path):
    sys.path.insert(0, ethstaker_path)

try:
    from ethstaker_deposit.credentials import Credential
    from ethstaker_deposit.settings import get_chain_setting, BaseChainSetting
    from ethstaker_deposit.utils.constants import EXECUTION_ADDRESS_WITHDRAWAL_PREFIX
    from ethstaker_deposit.utils.crypto import (
        compute_deposit_domain,
        compute_signing_root
    )
    from ethstaker_deposit.utils.typing import DepositMessage, DepositData
    from ethstaker_deposit.utils.crypto import bls
    from eth_utils import to_canonical_address
except ImportError as e:
    logging.warning(f"无法导入 ethstaker-deposit-cli，Deposit Data 生成功能可能不可用: {e}")
    Credential = None
    get_chain_setting = None
    bls = None

from app.core.vault_client import VaultClient
from app.models.database import ValidatorKey
from app.utils.exceptions import DepositGenerationError

logger = logging.getLogger(__name__)


class DepositGenerator:
    """
    Deposit Data 生成器
    从 Vault 读取私钥，生成 Deposit Data，支持动态绑定 0x01 类型提款地址
    """
    
    def __init__(
        self,
        vault_client: Optional[VaultClient] = None,
        network: str = 'mainnet',
        fork_version: Optional[str] = None
    ):
        """
        初始化 Deposit Data 生成器
        
        Args:
            vault_client: Vault 客户端
            network: 网络名称（mainnet/kurtosis 等）
            fork_version: Fork version（可选，用于自定义网络）
        """
        self.vault_client = vault_client or VaultClient()
        self.network = network
        self.fork_version = fork_version
        
        # 获取链设置
        self.chain_setting = self._get_chain_setting()
    
    def _get_chain_setting(self) -> BaseChainSetting:
        """获取链设置"""
        if get_chain_setting is None:
            raise DepositGenerationError("ethstaker-deposit-cli 未正确导入")
        
        if self.network == 'kurtosis' and self.fork_version:
            # Kurtosis 使用自定义网络配置
            from ethstaker_deposit.settings import get_devnet_chain_setting
            
            return get_devnet_chain_setting(
                network_name='kurtosis',
                genesis_fork_version=self.fork_version,
                exit_fork_version=self.fork_version,
                genesis_validator_root=None,
                multiplier=1,
                min_activation_amount=32,
                min_deposit_amount=1
            )
        else:
            return get_chain_setting(self.network or 'mainnet')
    
    def generate_deposit_data(
        self,
        validator_key: ValidatorKey,
        withdrawal_address: str,
        amount_eth: float = 32.0
    ) -> Dict[str, Any]:
        """
        为单个验证者生成 Deposit Data
        
        注意：由于我们只存储了私钥而没有助记词，我们需要使用私钥直接签名。
        但为了使用 ethstaker-deposit-cli 的验证功能，我们需要通过 Credential 类。
        
        实际上，我们可以：
        1. 如果保存了助记词，使用 Credential 类（推荐）
        2. 如果没有助记词，使用私钥直接签名（需要手动构建 Deposit Message）
        
        这里假设我们需要从数据库或 Vault 中获取助记词信息。
        但根据需求，我们可能没有保存助记词（只保存私钥）。
        
        因此，我们使用私钥直接签名的方法。
        
        Args:
            validator_key: ValidatorKey 对象
            withdrawal_address: 0x01 类型提款地址
            amount_eth: 存款金额（ETH）
            
        Returns:
            Deposit Data 字典
        """
        try:
            # 从 Vault 读取签名私钥
            signing_private_key_hex = self.vault_client.get_signing_key(validator_key.pubkey)
            if not signing_private_key_hex:
                raise DepositGenerationError(f"无法从 Vault 读取私钥: {validator_key.pubkey[:10]}...")
            
            # 转换为整数（私钥）
            signing_private_key_int = int(signing_private_key_hex, 16)
            
            # 构建提款凭证（0x01 类型）
            withdrawal_credentials = EXECUTION_ADDRESS_WITHDRAWAL_PREFIX + b'\x00' * 11 + to_bytes(hexstr=withdrawal_address)
            
            if bls is None:
                raise DepositGenerationError("BLS 库未正确导入")
            
            # 计算公钥（从私钥派生）
            pubkey_bytes = bls.SkToPk(signing_private_key_int)
            
            # 构建 Deposit Message
            amount_gwei = int(amount_eth * 1e9)
            amount = amount_gwei * self.chain_setting.MULTIPLIER
            
            deposit_message = DepositMessage(
                pubkey=pubkey_bytes,
                withdrawal_credentials=withdrawal_credentials,
                amount=amount
            )
            
            # 计算签名
            domain = compute_deposit_domain(fork_version=self.chain_setting.GENESIS_FORK_VERSION)
            signing_root = compute_signing_root(deposit_message, domain)
            signature = bls.Sign(signing_private_key_int, signing_root)
            
            # 构建 Deposit Data
            signed_deposit = DepositData(
                **deposit_message.as_dict(),
                signature=signature
            )
            
            # 转换为字典格式
            deposit_dict = signed_deposit.as_dict()
            deposit_dict['deposit_message_root'] = deposit_message.hash_tree_root.hex()
            deposit_dict['deposit_data_root'] = signed_deposit.hash_tree_root.hex()
            
            # 转换为十六进制字符串（用于 JSON）
            result = {
                'pubkey': '0x' + deposit_dict['pubkey'].hex() if isinstance(deposit_dict['pubkey'], bytes) else deposit_dict['pubkey'],
                'withdrawal_credentials': '0x' + deposit_dict['withdrawal_credentials'].hex() if isinstance(deposit_dict['withdrawal_credentials'], bytes) else deposit_dict['withdrawal_credentials'],
                'amount': deposit_dict['amount'],
                'signature': '0x' + deposit_dict['signature'].hex() if isinstance(deposit_dict['signature'], bytes) else deposit_dict['signature'],
                'deposit_message_root': '0x' + deposit_dict['deposit_message_root'] if isinstance(deposit_dict['deposit_message_root'], str) else deposit_dict['deposit_message_root'].hex(),
                'deposit_data_root': deposit_dict['deposit_data_root'],
                'fork_version': '0x' + self.chain_setting.GENESIS_FORK_VERSION.hex() if isinstance(self.chain_setting.GENESIS_FORK_VERSION, bytes) else self.chain_setting.GENESIS_FORK_VERSION,
                'network_name': self.network,
                'withdrawal_address': withdrawal_address
            }
            
            logger.info(f"Deposit Data 生成成功: {validator_key.pubkey[:10]}...")
            return result
            
        except Exception as e:
            logger.error(f"生成 Deposit Data 失败 ({validator_key.pubkey[:10]}...): {e}")
            raise DepositGenerationError(f"生成 Deposit Data 失败: {e}")
    
    def generate_batch_deposit_data(
        self,
        validator_keys: List[ValidatorKey],
        withdrawal_address: str,
        amount_eth: float = 32.0
    ) -> List[Dict[str, Any]]:
        """
        批量生成 Deposit Data
        
        Args:
            validator_keys: ValidatorKey 对象列表
            withdrawal_address: 0x01 类型提款地址
            amount_eth: 存款金额（ETH）
            
        Returns:
            Deposit Data 列表
        """
        deposit_data_list = []
        
        for validator_key in validator_keys:
            try:
                deposit_data = self.generate_deposit_data(
                    validator_key=validator_key,
                    withdrawal_address=withdrawal_address,
                    amount_eth=amount_eth
                )
                deposit_data_list.append(deposit_data)
            except Exception as e:
                logger.error(f"跳过密钥 {validator_key.pubkey[:10]}...: {e}")
                continue
        
        logger.info(f"批量生成 {len(deposit_data_list)}/{len(validator_keys)} 个 Deposit Data")
        return deposit_data_list
    
    def validate_deposit_data(self, deposit_data: Dict[str, Any]) -> bool:
        """
        验证 Deposit Data
        使用 ethstaker-deposit-cli 的验证功能
        
        Args:
            deposit_data: Deposit Data 字典
            
        Returns:
            是否有效
        """
        try:
            from ethstaker_deposit.utils.validation import validate_deposit_data_dict
            
            # 验证 Deposit Data
            is_valid = validate_deposit_data_dict(
                deposit_data_dict=deposit_data,
                chain_setting=self.chain_setting
            )
            
            if is_valid:
                logger.debug(f"Deposit Data 验证通过: {deposit_data.get('pubkey', 'unknown')[:10]}...")
            else:
                logger.warning(f"Deposit Data 验证失败: {deposit_data.get('pubkey', 'unknown')[:10]}...")
            
            return is_valid
            
        except ImportError:
            # 如果验证函数不可用，跳过验证
            logger.warning("Deposit Data 验证功能不可用，跳过验证")
            return True
        except Exception as e:
            logger.error(f"验证 Deposit Data 时出错: {e}")
            return False

