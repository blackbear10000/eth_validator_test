"""
验证者退出签名生成器
使用 ethstaker-deposit-cli 生成 Voluntary Exit 签名
"""
import logging
from typing import Dict, Any, Optional

# 直接导入 ethstaker-deposit-cli（通过 pip 安装）
try:
    from ethstaker_deposit.utils.exit_transaction import exit_transaction_generation
    from ethstaker_deposit.settings import get_chain_setting, BaseChainSetting
    from ethstaker_deposit.utils.ssz import SignedVoluntaryExit
    from py_ecc.bls import G2ProofOfPossession as bls
except ImportError as e:
    logging.error(f"无法导入 ethstaker-deposit-cli，退出功能不可用: {e}")
    logging.error("请确保已安装 ethstaker-deposit-cli: pip install git+https://github.com/ethstaker/ethstaker-deposit-cli.git")
    exit_transaction_generation = None
    get_chain_setting = None
    BaseChainSetting = None
    bls = None

from app.core.vault_client import VaultClient
from app.utils.exceptions import DepositGenerationError

logger = logging.getLogger(__name__)


class ExitGenerator:
    """
    验证者退出签名生成器
    生成 Voluntary Exit 签名
    """
    
    def __init__(
        self,
        vault_client: Optional[VaultClient] = None,
        network: str = 'mainnet',
        fork_version: Optional[str] = None
    ):
        """
        初始化退出生成器
        
        Args:
            vault_client: Vault 客户端
            network: 网络名称
            fork_version: Fork version（可选）
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
        
        if self.network in ['kurtosis', 'devnet'] and self.fork_version:
            from ethstaker_deposit.settings import get_devnet_chain_setting
            
            # fork_version 格式化处理（与 deposit_generator.py 保持一致）
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
                # 添加 0x 前缀
                fork_version_hex = '0x' + fork_version_str
            elif isinstance(self.fork_version, bytes):
                # 如果是 bytes，转换为十六进制字符串
                fork_version_hex = '0x' + self.fork_version.hex()
            else:
                raise DepositGenerationError(f"fork_version 必须是字符串或 bytes，收到: {type(self.fork_version)}")
            
            # 获取 genesis_validators_root（如果未提供，尝试从 Beacon API 获取）
            genesis_validators_root = None
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
            
            logger.info(f"使用 fork_version: {fork_version_hex}, genesis_validators_root: {genesis_validators_root[:20] if genesis_validators_root else 'None'}...")
            
            return get_devnet_chain_setting(
                network_name='kurtosis',
                genesis_fork_version=fork_version_hex,  # 传入格式化后的字符串
                exit_fork_version=fork_version_hex,      # 传入格式化后的字符串
                genesis_validator_root=genesis_validators_root,
                multiplier=1,
                min_activation_amount=32,
                min_deposit_amount=1
            )
        else:
            return get_chain_setting(self.network or 'mainnet')
    
    def generate_exit_signature(
        self,
        pubkey: str,
        validator_index: int,
        epoch: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        生成验证者退出签名
        
        Args:
            pubkey: 验证者公钥
            validator_index: 验证者索引（链上）
            epoch: 退出 epoch（可选，如果不提供则使用当前 epoch）
            
        Returns:
            退出签名数据字典
        """
        if exit_transaction_generation is None or bls is None:
            raise DepositGenerationError("ethstaker-deposit-cli 退出功能未正确导入")
        
        try:
            # 从 Vault 读取签名私钥
            signing_private_key_hex = self.vault_client.get_signing_key(pubkey)
            if not signing_private_key_hex:
                raise ValueError(f"无法从 Vault 读取私钥: {pubkey[:10]}...")
            
            # 转换为整数
            signing_private_key_int = int(signing_private_key_hex, 16)
            
            # 如果未提供 epoch，从 Beacon API 查询当前 epoch
            if epoch is None:
                from app.core.beacon_api import BeaconAPIClient
                beacon_api = BeaconAPIClient()
                try:
                    # 获取当前 epoch（从 finalized checkpoint）
                    state_data = beacon_api._get("/eth/v1/beacon/states/finalized/finality_checkpoints")
                    if isinstance(state_data, dict) and 'data' in state_data:
                        state_data = state_data['data']
                    epoch = int(state_data.get('finalized', {}).get('epoch', 0))
                    logger.info(f"从 Beacon API 获取当前 epoch: {epoch}")
                except Exception as e:
                    logger.warning(f"无法从 Beacon API 获取当前 epoch: {e}，使用默认值 0")
                    epoch = 0
            
            # 记录 chain_setting 信息（用于调试）
            try:
                fork_version = self.chain_setting.EXIT_FORK_VERSION
                if isinstance(fork_version, bytes):
                    fork_version_hex = '0x' + fork_version.hex()
                else:
                    fork_version_hex = fork_version
                genesis_validators_root = self.chain_setting.GENESIS_VALIDATORS_ROOT
                if isinstance(genesis_validators_root, bytes):
                    genesis_validators_root_hex = '0x' + genesis_validators_root.hex()
                else:
                    genesis_validators_root_hex = genesis_validators_root
                logger.info(
                    f"生成退出签名 - epoch: {epoch}, validator_index: {validator_index}, "
                    f"fork_version: {fork_version_hex}, "
                    f"genesis_validators_root: {genesis_validators_root_hex[:20] if genesis_validators_root_hex else 'None'}..."
                )
            except Exception as e:
                logger.debug(f"无法记录 chain_setting 信息: {e}")
            
            # 生成退出签名
            signed_exit = exit_transaction_generation(
                chain_setting=self.chain_setting,
                signing_key=signing_private_key_int,
                validator_index=validator_index,
                epoch=epoch
            )
            
            # 转换为字典格式（Beacon API 兼容）
            exit_data = {
                'message': {
                    'epoch': str(signed_exit.message.epoch),
                    'validator_index': str(signed_exit.message.validator_index)
                },
                'signature': '0x' + signed_exit.signature.hex()
            }
            
            logger.info(f"退出签名生成成功: {pubkey[:10]}... (validator_index: {validator_index}, epoch: {epoch})")
            return exit_data
            
        except Exception as e:
            logger.error(f"生成退出签名失败 ({pubkey[:10]}...): {e}")
            raise DepositGenerationError(f"生成退出签名失败: {e}")

