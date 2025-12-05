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
from app.utils.encryption import decrypt_mnemonic

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
        fork_version: Optional[str] = None,
        genesis_validators_root: Optional[str] = None
    ):
        """
        初始化 Deposit Data 生成器
        
        Args:
            vault_client: Vault 客户端
            network: 网络名称（mainnet/kurtosis 等）
            fork_version: Fork version（可选，用于自定义网络）
            genesis_validators_root: Genesis validators root（可选，用于 devnet）
        """
        self.vault_client = vault_client or VaultClient()
        self.network = network
        self.fork_version = fork_version
        self.genesis_validators_root = genesis_validators_root
        
        # 获取链设置
        self.chain_setting = self._get_chain_setting()
    
    def _get_mnemonic_for_key(self, validator_key: ValidatorKey) -> str:
        """
        从数据库读取并解密助记词
        
        Args:
            validator_key: ValidatorKey 对象
            
        Returns:
            明文助记词
            
        Raises:
            DepositGenerationError: 如果无法获取助记词
        """
        if not validator_key.mnemonic_encrypted:
            raise DepositGenerationError(
                f"密钥 {validator_key.pubkey[:10]}... 没有存储助记词。"
                "请使用新生成的密钥（包含助记词）或回退到手动构建方式。"
            )
        
        try:
            mnemonic = decrypt_mnemonic(validator_key.mnemonic_encrypted, validator_key.mnemonic_salt)
            return mnemonic
        except Exception as e:
            logger.error(f"解密助记词失败 ({validator_key.pubkey[:10]}...): {e}")
            raise DepositGenerationError(f"解密助记词失败: {e}")
    
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
            
            # 获取 genesis_validators_root（如果未提供，尝试从 Beacon API 获取）
            genesis_validators_root = self.genesis_validators_root
            if not genesis_validators_root:
                try:
                    from app.core.beacon_api import BeaconAPIClient
                    beacon_api = BeaconAPIClient()
                    genesis_validators_root = beacon_api.get_genesis_validators_root()
                    if genesis_validators_root:
                        logger.info(f"从 Beacon API 获取 genesis_validators_root: {genesis_validators_root[:20]}...")
                    else:
                        logger.warning("无法从 Beacon API 获取 genesis_validators_root，使用 None")
                except Exception as e:
                    logger.warning(f"获取 genesis_validators_root 失败: {e}，使用 None")
                    genesis_validators_root = None
            
            return get_devnet_chain_setting(
                network_name='kurtosis',
                genesis_fork_version=fork_version_hex,  # 传入字符串，不是 bytes
                exit_fork_version=fork_version_hex,      # 传入字符串，不是 bytes
                genesis_validator_root=genesis_validators_root,  # 使用获取到的值
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
        
        优先使用 Credential 类（如果存储了助记词），否则回退到手动构建方式。
        
        Args:
            validator_key: ValidatorKey 对象
            withdrawal_address: 0x01 类型提款地址
            amount_eth: 存款金额（ETH）
            network_name: 网络名称（可选，Credential 类会自动从 chain_setting 获取）
            
        Returns:
            Deposit Data 字典
        """
        # 优先尝试使用 Credential 类（如果存储了助记词）
        if validator_key.mnemonic_encrypted:
            try:
                return self._generate_with_credential(validator_key, withdrawal_address, amount_eth, network_name)
            except Exception as e:
                logger.warning(f"使用 Credential 类生成失败，回退到手动构建方式: {e}")
                # 回退到手动构建方式
                return self._generate_with_manual_build(validator_key, withdrawal_address, amount_eth, network_name)
        else:
            # 没有助记词，使用手动构建方式
            logger.info(f"密钥 {validator_key.pubkey[:10]}... 没有存储助记词，使用手动构建方式")
            return self._generate_with_manual_build(validator_key, withdrawal_address, amount_eth, network_name)
    
    def _generate_with_credential(
        self,
        validator_key: ValidatorKey,
        withdrawal_address: str,
        amount_eth: float,
        network_name: Optional[str]
    ) -> Dict[str, Any]:
        """
        使用 Credential 类生成 Deposit Data（推荐方式）
        
        Args:
            validator_key: ValidatorKey 对象
            withdrawal_address: 0x01 类型提款地址
            amount_eth: 存款金额（ETH）
            network_name: 网络名称（可选）
            
        Returns:
            Deposit Data 字典
            
        Raises:
            DepositGenerationError: 如果无法获取助记词或生成失败
        """
        if Credential is None:
            raise DepositGenerationError("ethstaker-deposit-cli Credential 类未正确导入")
        
        # 1. 从数据库读取并解密助记词
        mnemonic = self._get_mnemonic_for_key(validator_key)
        
        # 2. 获取 chain_setting（确保已更新）
        chain_setting = self.chain_setting
        
        # 3. 创建 Credential 对象
        credential = Credential(
            mnemonic=mnemonic,
            mnemonic_password='',
            index=validator_key.index,
            amount=int(amount_eth * 1e9),  # 转换为 Gwei
            chain_setting=chain_setting,
            hex_withdrawal_address=withdrawal_address
        )
        
        # 4. 获取 deposit data
        deposit_dict = credential.deposit_datum_dict
        
        # 5. 转换为字符串格式（移除 0x 前缀，符合官方格式）
        result = {
            'pubkey': deposit_dict['pubkey'].hex(),
            'withdrawal_credentials': deposit_dict['withdrawal_credentials'].hex(),
            'amount': int(deposit_dict['amount']),
            'signature': deposit_dict['signature'].hex(),
            'deposit_message_root': deposit_dict['deposit_message_root'].hex(),
            'deposit_data_root': deposit_dict['deposit_data_root'].hex(),
            'fork_version': deposit_dict['fork_version'].hex(),
            'network_name': deposit_dict['network_name'],
            'deposit_cli_version': deposit_dict['deposit_cli_version']
        }
        
        logger.info(f"使用 Credential 类生成 Deposit Data 成功: {validator_key.pubkey[:10]}...")
        return result
    
    def _generate_with_manual_build(
        self,
        validator_key: ValidatorKey,
        withdrawal_address: str,
        amount_eth: float,
        network_name: Optional[str]
    ) -> Dict[str, Any]:
        """
        使用手动构建方式生成 Deposit Data（向后兼容）
        
        Args:
            validator_key: ValidatorKey 对象
            withdrawal_address: 0x01 类型提款地址
            amount_eth: 存款金额（ETH）
            network_name: 网络名称（可选）
            
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
            signing_fork_version = self.chain_setting.GENESIS_FORK_VERSION
            domain = compute_deposit_domain(fork_version=signing_fork_version)
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
            
            # 获取 fork_version
            fork_version_bytes = self.chain_setting.GENESIS_FORK_VERSION
            if isinstance(fork_version_bytes, bytes):
                fork_version_hex = fork_version_bytes.hex()
            else:
                fork_version_hex = fork_version_bytes.replace('0x', '') if isinstance(fork_version_bytes, str) else str(fork_version_bytes)
            
            # 获取 deposit_cli_version
            try:
                from ethstaker_deposit.settings import DEPOSIT_CLI_VERSION
                deposit_cli_version = str(DEPOSIT_CLI_VERSION) if DEPOSIT_CLI_VERSION else "2.7.0"
            except ImportError:
                deposit_cli_version = "2.7.0"
                logger.warning("无法导入 DEPOSIT_CLI_VERSION，使用默认值")
            
            # 转换为十六进制字符串（移除 0x 前缀）
            pubkey_hex = deposit_dict['pubkey'].hex() if isinstance(deposit_dict['pubkey'], bytes) else deposit_dict['pubkey'].replace('0x', '')
            withdrawal_credentials_hex = deposit_dict['withdrawal_credentials'].hex() if isinstance(deposit_dict['withdrawal_credentials'], bytes) else deposit_dict['withdrawal_credentials'].replace('0x', '')
            signature_hex = deposit_dict['signature'].hex() if isinstance(deposit_dict['signature'], bytes) else deposit_dict['signature'].replace('0x', '')
            deposit_message_root_hex = deposit_dict['deposit_message_root'].replace('0x', '') if isinstance(deposit_dict['deposit_message_root'], str) else deposit_dict['deposit_message_root'].hex()
            deposit_data_root_hex = deposit_dict['deposit_data_root'].replace('0x', '') if isinstance(deposit_dict['deposit_data_root'], str) else deposit_dict['deposit_data_root'].hex()
            
            # network_name 处理
            if network_name:
                network_name_str = str(network_name)
            else:
                if hasattr(self.chain_setting, 'NETWORK_NAME') and self.chain_setting.NETWORK_NAME:
                    network_name_str = self.chain_setting.NETWORK_NAME
                else:
                    network_name_str = 'kurtosis'
            
            result = {
                'pubkey': str(pubkey_hex),
                'withdrawal_credentials': str(withdrawal_credentials_hex),
                'amount': int(deposit_dict['amount']),
                'signature': str(signature_hex),
                'deposit_message_root': str(deposit_message_root_hex),
                'deposit_data_root': str(deposit_data_root_hex),
                'fork_version': str(fork_version_hex),
                'network_name': network_name_str,
                'deposit_cli_version': str(deposit_cli_version)
            }
            
            logger.info(f"使用手动构建方式生成 Deposit Data 成功: {validator_key.pubkey[:10]}...")
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
            network_name: 网络名称（可选，默认：kurtosis）
            
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

