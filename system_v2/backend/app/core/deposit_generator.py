"""
Deposit Data 生成器
使用 ethstaker-deposit-cli 生成 Deposit Data，支持动态绑定 0x01 类型提款地址
"""
import logging
from typing import List, Dict, Any, Optional
from eth_utils import to_bytes

# 直接导入 ethstaker-deposit-cli（通过 pip 安装）
try:
    from ethstaker_deposit.credentials import Credential
    from ethstaker_deposit.settings import get_chain_setting, BaseChainSetting
    from ethstaker_deposit.utils.constants import EXECUTION_ADDRESS_WITHDRAWAL_PREFIX
    from ethstaker_deposit.utils.ssz import (
        compute_deposit_domain,
        compute_signing_root,
        DepositMessage,
        DepositData
    )
    from py_ecc.bls import G2ProofOfPossession as bls
    from eth_utils import to_canonical_address
except ImportError as e:
    logging.error(f"无法导入 ethstaker-deposit-cli，Deposit Data 生成功能不可用: {e}")
    logging.error("请确保已安装 ethstaker-deposit-cli: pip install git+https://github.com/ethstaker/ethstaker-deposit-cli.git")
    Credential = None
    get_chain_setting = None
    BaseChainSetting = None  # 类型占位符
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
    
    def _get_chain_setting(self):
        """获取链设置"""
        if get_chain_setting is None:
            raise DepositGenerationError("ethstaker-deposit-cli 未正确导入")
        
        if self.network in ['kurtosis', 'devnet'] and self.fork_version:
            # Kurtosis/devnet 使用自定义网络配置
            from ethstaker_deposit.settings import get_devnet_chain_setting
            
            # fork_version 应该是十六进制字符串（带或不带 0x 前缀）
            # get_devnet_chain_setting 期望字符串类型，内部会调用 decode_hex 处理
            if isinstance(self.fork_version, str):
                fork_version_str = self.fork_version.strip()
                # 移除 0x 前缀（如果有）
                if fork_version_str.startswith('0x'):
                    fork_version_str = fork_version_str[2:]
                # 确保是有效的十六进制字符串
                if not fork_version_str:
                    raise DepositGenerationError(f"无效的 fork_version: {self.fork_version}")
                # 补齐到 8 个字符（4 bytes），如果不足则前面补0
                if len(fork_version_str) < 8:
                    fork_version_str = fork_version_str.zfill(8)
                elif len(fork_version_str) > 8:
                    fork_version_str = fork_version_str[:8]
                # 验证是否为有效的十六进制字符串
                try:
                    int(fork_version_str, 16)
                except ValueError as e:
                    raise DepositGenerationError(f"无效的 fork_version 格式（不是有效的十六进制）: {self.fork_version}, 错误: {e}")
                # 添加 0x 前缀（get_devnet_chain_setting 内部会处理）
                fork_version_hex = '0x' + fork_version_str
            elif isinstance(self.fork_version, bytes):
                # 如果是 bytes，转换为十六进制字符串
                fork_version_hex = '0x' + self.fork_version.hex()
            else:
                raise DepositGenerationError(f"fork_version 必须是字符串或 bytes，收到: {type(self.fork_version)}")
            
            return get_devnet_chain_setting(
                network_name='kurtosis',
                genesis_fork_version=fork_version_hex,  # 传入字符串，不是 bytes
                exit_fork_version=fork_version_hex,      # 传入字符串，不是 bytes
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
        amount_eth: float = 32.0,
        network_name: Optional[str] = None
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
            # 使用 chain_setting.GENESIS_FORK_VERSION 来计算签名（这是实际用于签名的 fork_version）
            signing_fork_version = self.chain_setting.GENESIS_FORK_VERSION
            domain = compute_deposit_domain(fork_version=signing_fork_version)
            signing_root = compute_signing_root(deposit_message, domain)
            signature = bls.Sign(signing_private_key_int, signing_root)
            
            # 记录签名时使用的 fork_version（用于调试）
            if isinstance(signing_fork_version, bytes):
                signing_fork_version_hex = signing_fork_version.hex()
            else:
                signing_fork_version_hex = signing_fork_version.replace('0x', '') if isinstance(signing_fork_version, str) else str(signing_fork_version)
            logger.debug(f"签名使用的 fork_version: {signing_fork_version_hex} (bytes: {signing_fork_version.hex() if isinstance(signing_fork_version, bytes) else 'N/A'})")
            
            # 构建 Deposit Data
            signed_deposit = DepositData(
                **deposit_message.as_dict(),
                signature=signature
            )
            
            # 转换为字典格式
            deposit_dict = signed_deposit.as_dict()
            deposit_dict['deposit_message_root'] = deposit_message.hash_tree_root.hex()
            deposit_dict['deposit_data_root'] = signed_deposit.hash_tree_root.hex()
            
            # 获取 fork_version（十六进制字符串，不带 0x 前缀）
            # 重要：始终使用 chain_setting.GENESIS_FORK_VERSION（与签名时使用的一致）
            # 这样可以确保返回的 fork_version 和签名时使用的完全一致，验证工具才能正确验证签名
            fork_version_bytes = self.chain_setting.GENESIS_FORK_VERSION
            if isinstance(fork_version_bytes, bytes):
                fork_version_hex = fork_version_bytes.hex()
            else:
                # 如果已经是字符串，移除 0x 前缀
                fork_version_hex = fork_version_bytes.replace('0x', '') if isinstance(fork_version_bytes, str) else str(fork_version_bytes)
            
            # 验证 fork_version 一致性（用于调试）
            if fork_version_hex.lower() != signing_fork_version_hex.lower():
                logger.warning(
                    f"fork_version 不一致！签名使用: {signing_fork_version_hex}, "
                    f"返回: {fork_version_hex}. 这可能导致验证失败。"
                )
            else:
                logger.debug(f"返回的 fork_version: {fork_version_hex} (与签名时使用的一致)")
            
            # 获取 deposit_cli_version（确保是字符串）
            try:
                from ethstaker_deposit.settings import DEPOSIT_CLI_VERSION
                deposit_cli_version = str(DEPOSIT_CLI_VERSION) if DEPOSIT_CLI_VERSION else "2.7.0"
            except ImportError:
                # 如果无法导入，使用默认值
                deposit_cli_version = "2.7.0"  # 默认版本
                logger.warning("无法导入 DEPOSIT_CLI_VERSION，使用默认值")
            
            # 转换为十六进制字符串（用于 JSON）
            # 根据官方格式：pubkey、withdrawal_credentials、signature 应该是十六进制字符串（不带 0x 前缀）
            pubkey_hex = deposit_dict['pubkey'].hex() if isinstance(deposit_dict['pubkey'], bytes) else deposit_dict['pubkey'].replace('0x', '')
            withdrawal_credentials_hex = deposit_dict['withdrawal_credentials'].hex() if isinstance(deposit_dict['withdrawal_credentials'], bytes) else deposit_dict['withdrawal_credentials'].replace('0x', '')
            signature_hex = deposit_dict['signature'].hex() if isinstance(deposit_dict['signature'], bytes) else deposit_dict['signature'].replace('0x', '')
            deposit_message_root_hex = deposit_dict['deposit_message_root'] if isinstance(deposit_dict['deposit_message_root'], str) else deposit_dict['deposit_message_root'].hex()
            deposit_message_root_hex = deposit_message_root_hex.replace('0x', '')
            deposit_data_root_hex = deposit_dict['deposit_data_root'] if isinstance(deposit_dict['deposit_data_root'], str) else deposit_dict['deposit_data_root'].hex()
            deposit_data_root_hex = deposit_data_root_hex.replace('0x', '')
            
            # network_name 参数优先，如果没有提供则使用默认值
            if network_name:
                network_name_str = str(network_name)
            else:
                # 默认使用 testnet
                network_name_str = 'testnet'
            
            # 确保 fork_version_hex 是字符串
            fork_version_str = str(fork_version_hex) if fork_version_hex else '00000000'
            
            result = {
                'pubkey': str(pubkey_hex),
                'withdrawal_credentials': str(withdrawal_credentials_hex),
                'amount': int(deposit_dict['amount']),
                'signature': str(signature_hex),
                'deposit_message_root': str(deposit_message_root_hex),
                'deposit_data_root': str(deposit_data_root_hex),
                'fork_version': fork_version_str,
                'network_name': str(network_name),
                'deposit_cli_version': str(deposit_cli_version)
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
        amount_eth: float = 32.0,
        network_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        批量生成 Deposit Data
        
        Args:
            validator_keys: ValidatorKey 对象列表
            withdrawal_address: 0x01 类型提款地址
            amount_eth: 存款金额（ETH）
            network_name: 网络名称（可选，默认：testnet）
            
        Returns:
            Deposit Data 列表
        """
        deposit_data_list = []
        
        for validator_key in validator_keys:
            try:
                deposit_data = self.generate_deposit_data(
                    validator_key=validator_key,
                    withdrawal_address=withdrawal_address,
                    amount_eth=amount_eth,
                    network_name=network_name
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

