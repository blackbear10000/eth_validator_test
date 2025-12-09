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
                    # 验证格式：应该是 32 字节（64 个十六进制字符）
                    root_clean = genesis_validators_root.replace('0x', '')
                    if len(root_clean) != 64:
                        logger.error(f"genesis_validators_root 长度不正确: {len(root_clean)} (期望 64)")
                        raise ValueError(f"genesis_validators_root 长度不正确: {len(root_clean)} (期望 64)")
                    logger.info(f"从 Beacon API 获取 genesis_validators_root: {genesis_validators_root[:20]}... (长度: {len(root_clean)})")
                else:
                    logger.warning("无法从 Beacon API 获取 genesis_validators_root，使用 None")
            except Exception as e:
                logger.warning(f"获取 genesis_validators_root 失败: {e}，使用 None")
                genesis_validators_root = None
            
            # 获取 EXIT_FORK_VERSION
            # 根据 Ethereum 规范和 mainnet 的做法，EXIT_FORK_VERSION 应该使用 Capella fork version
            # 对于 devnet，尝试从 fork schedule 获取 Capella fork version
            # 如果无法获取，则根据 genesis fork version 构造 Capella fork version（通常是 0x4...）
            exit_fork_version_hex = fork_version_hex  # 默认使用 genesis fork version
            try:
                from app.core.beacon_api import BeaconAPIClient
                beacon_api = BeaconAPIClient()
                
                # 方法1：尝试从 fork schedule 获取 Capella fork version
                try:
                    fork_schedule = beacon_api.get_fork_schedule()
                    if isinstance(fork_schedule, dict) and 'data' in fork_schedule:
                        fork_schedule_data = fork_schedule['data']
                        # 查找 Capella fork
                        # Capella fork version 通常是 0x40000038（根据 network-config.yaml）
                        # 在 fork schedule 中，Capella 是 current_version 为 0x40000038 的条目
                        for fork in fork_schedule_data:
                            current_version = fork.get('current_version')
                            if current_version:
                                current_version_clean = current_version.replace('0x', '').lower()
                                # Capella fork version 是 0x40000038（第一个字符是 4）
                                if len(current_version_clean) == 8 and current_version_clean[0] == '4':
                                    exit_fork_version_hex = '0x' + current_version_clean
                                    logger.info(f"从 fork schedule 获取 Capella fork version: {exit_fork_version_hex}，用作 EXIT_FORK_VERSION")
                                    break
                except Exception as e:
                    logger.debug(f"无法从 fork schedule 获取 Capella fork version: {e}")
                
                # 方法2：如果方法1失败，尝试根据 genesis fork version 构造 Capella fork version
                # 对于这个网络，Capella fork version 应该是 0x40000038（根据 network-config.yaml）
                if exit_fork_version_hex == fork_version_hex:
                    # 从 genesis fork version (0x10000038) 构造 Capella fork version (0x40000038)
                    # 规则：将第一个数字改为 4
                    genesis_clean = fork_version_hex.replace('0x', '').lower()
                    if len(genesis_clean) == 8 and genesis_clean[0] == '1':
                        # 将第一个字符从 '1' 改为 '4'
                        capella_clean = '4' + genesis_clean[1:]
                        exit_fork_version_hex = '0x' + capella_clean
                        logger.info(f"根据 genesis fork version ({fork_version_hex}) 构造 Capella fork version: {exit_fork_version_hex}，用作 EXIT_FORK_VERSION")
                    else:
                        logger.warning(f"无法根据 genesis fork version 构造 Capella fork version，使用 genesis fork version: {fork_version_hex}")
                
            except Exception as e:
                logger.warning(f"获取 Capella fork version 失败: {e}，使用 genesis fork version 作为 EXIT_FORK_VERSION")
            
            logger.info(
                f"使用 fork_version - GENESIS: {fork_version_hex}, EXIT: {exit_fork_version_hex}, "
                f"genesis_validators_root: {genesis_validators_root[:20] if genesis_validators_root else 'None'}..."
            )
            
            return get_devnet_chain_setting(
                network_name='kurtosis',
                genesis_fork_version=fork_version_hex,  # 传入格式化后的字符串
                exit_fork_version=exit_fork_version_hex,  # 使用当前 fork version
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
            
            # 验证私钥与公钥是否匹配
            try:
                derived_pubkey = bls.SkToPk(signing_private_key_int)
                derived_pubkey_hex = '0x' + derived_pubkey.hex()
                # 移除 pubkey 的 0x 前缀（如果有）进行比较
                pubkey_clean = pubkey.lower().replace('0x', '')
                derived_pubkey_clean = derived_pubkey_hex.lower().replace('0x', '')
                if derived_pubkey_clean != pubkey_clean:
                    logger.error(
                        f"私钥验证失败！期望公钥: {pubkey}, "
                        f"从私钥推导的公钥: {derived_pubkey_hex}"
                    )
                    raise ValueError(f"私钥与公钥不匹配！期望: {pubkey}, 实际: {derived_pubkey_hex}")
                logger.info(f"私钥验证成功: 私钥与公钥匹配 ({pubkey[:10]}...)")
            except Exception as e:
                logger.warning(f"私钥验证过程出错: {e}，继续生成签名")
            
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
                exit_fork_version = self.chain_setting.EXIT_FORK_VERSION
                genesis_fork_version = self.chain_setting.GENESIS_FORK_VERSION
                if isinstance(exit_fork_version, bytes):
                    exit_fork_version_hex = '0x' + exit_fork_version.hex()
                else:
                    exit_fork_version_hex = exit_fork_version
                if isinstance(genesis_fork_version, bytes):
                    genesis_fork_version_hex = '0x' + genesis_fork_version.hex()
                else:
                    genesis_fork_version_hex = genesis_fork_version
                genesis_validators_root = self.chain_setting.GENESIS_VALIDATORS_ROOT
                if isinstance(genesis_validators_root, bytes):
                    genesis_validators_root_hex = '0x' + genesis_validators_root.hex()
                    genesis_validators_root_length = len(genesis_validators_root_hex.replace('0x', ''))
                else:
                    genesis_validators_root_hex = genesis_validators_root or 'None'
                    genesis_validators_root_length = len(genesis_validators_root_hex.replace('0x', '')) if genesis_validators_root_hex != 'None' else 0
                
                logger.info(
                    f"生成退出签名参数:"
                )
                logger.info(f"  - epoch: {epoch}")
                logger.info(f"  - validator_index: {validator_index}")
                logger.info(f"  - EXIT_FORK_VERSION: {exit_fork_version_hex}")
                logger.info(f"  - GENESIS_FORK_VERSION: {genesis_fork_version_hex}")
                logger.info(f"  - GENESIS_VALIDATORS_ROOT: {genesis_validators_root_hex[:20] if genesis_validators_root_hex != 'None' else 'None'}... (长度: {genesis_validators_root_length})")
            except Exception as e:
                logger.debug(f"无法记录 chain_setting 信息: {e}")
            
            # 手动计算签名域和签名根（用于调试）
            try:
                from ethstaker_deposit.utils.ssz import compute_voluntary_exit_domain, compute_signing_root
                from ethstaker_deposit.utils.ssz import VoluntaryExit
                
                message = VoluntaryExit(epoch=epoch, validator_index=validator_index)
                domain = compute_voluntary_exit_domain(
                    fork_version=self.chain_setting.EXIT_FORK_VERSION,
                    genesis_validators_root=self.chain_setting.GENESIS_VALIDATORS_ROOT
                )
                signing_root = compute_signing_root(message, domain)
                
                logger.info(f"签名域计算:")
                logger.info(f"  - Domain: 0x{domain.hex()}")
                logger.info(f"  - Signing root: 0x{signing_root.hex()}")
                logger.info(f"  - Message epoch: {epoch}, validator_index: {validator_index}")
            except Exception as e:
                logger.debug(f"无法计算签名域: {e}")
            
            # 生成退出签名
            signed_exit = exit_transaction_generation(
                chain_setting=self.chain_setting,
                signing_key=signing_private_key_int,
                validator_index=validator_index,
                epoch=epoch
            )
            
            # 转换为字典格式（Beacon API 兼容，符合 https://github.com/ethstaker/ethstaker-deposit-cli/blob/main/docs/src/signed_exit_transaction_file.md）
            exit_data = {
                'message': {
                    'epoch': str(signed_exit.message.epoch),
                    'validator_index': str(signed_exit.message.validator_index)
                },
                'signature': '0x' + signed_exit.signature.hex()
            }
            
            # 验证签名格式
            signature_hex = exit_data['signature'].replace('0x', '')
            if len(signature_hex) != 192:  # BLS signature is 96 bytes = 192 hex chars
                logger.error(f"签名长度不正确: {len(signature_hex)} (期望 192)")
                raise ValueError(f"签名长度不正确: {len(signature_hex)} (期望 192)")
            
            # 验证签名本身（使用 ethstaker-deposit-cli 的验证函数）
            try:
                from ethstaker_deposit.utils.validation import validate_signed_exit
                
                # validate_signed_exit 使用 bytes.fromhex()，不接受 0x 前缀
                # 但 signature 使用 decode_hex()，可以接受 0x 前缀
                pubkey_no_prefix = pubkey.replace('0x', '').lower()
                signature_with_prefix = exit_data['signature']  # decode_hex 可以处理 0x 前缀
                
                is_valid = validate_signed_exit(
                    validator_index=str(validator_index),
                    epoch=str(epoch),
                    signature=signature_with_prefix,
                    pubkey=pubkey_no_prefix,
                    chain_setting=self.chain_setting
                )
                
                if not is_valid:
                    logger.error("签名验证失败：生成的签名无法通过本地验证")
                    raise ValueError("生成的退出签名无法通过本地验证")
                else:
                    logger.info("签名验证成功：生成的签名通过本地验证")
            except ImportError as e:
                logger.warning(f"无法导入验证函数: {e}，跳过签名验证")
            except Exception as e:
                logger.warning(f"签名验证过程出错: {e}，继续提交")
            
            logger.info(
                f"退出签名生成成功: {pubkey[:10]}... "
                f"(validator_index: {validator_index}, epoch: {epoch}, "
                f"signature_length: {len(signature_hex)})"
            )
            return exit_data
            
        except Exception as e:
            logger.error(f"生成退出签名失败 ({pubkey[:10]}...): {e}")
            raise DepositGenerationError(f"生成退出签名失败: {e}")

