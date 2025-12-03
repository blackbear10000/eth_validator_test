"""
Batch Deposit 合约部署器
从 GitHub 获取合约代码，编译并部署到指定网络
参考：https://github.com/stakefish/eth2-batch-deposit
"""
import logging
import os
import tempfile
import shutil
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
from web3 import Web3
from eth_account import Account
try:
    from solcx import compile_source, install_solc, set_solc_version
except ImportError:
    try:
        from py_solc_x import compile_source, install_solc, set_solc_version
    except ImportError:
        logger.error("无法导入 solcx 或 py_solc_x，请安装 py-solc-x: pip install py-solc-x")
        raise

logger = logging.getLogger(__name__)

# Batch Deposit 合约 GitHub 仓库
BATCH_DEPOSIT_REPO = "https://github.com/stakefish/eth2-batch-deposit.git"
BATCH_DEPOSIT_CONTRACT_PATH = "contracts/BatchDeposits.sol"


class BatchDepositDeployer:
    """
    Batch Deposit 合约部署器
    从 GitHub 获取合约代码，编译并部署
    """
    
    def __init__(self, web3: Web3, deployer_private_key: str):
        """
        初始化部署器
        
        Args:
            web3: Web3 实例
            deployer_private_key: 部署者私钥（用于签名交易）
        """
        self.web3 = web3
        self.deployer_account = Account.from_key(deployer_private_key)
        self.deployer_address = self.deployer_account.address
        
        # 注意：solc 版本将在获取源代码后根据 pragma 语句动态安装
    
    def _detect_solc_version(self, source_code: str) -> str:
        """
        从合约源代码中检测所需的 Solidity 版本
        
        Args:
            source_code: 合约源代码
            
        Returns:
            Solidity 版本字符串（如 '0.8.29'）
        """
        import re
        # 匹配 pragma solidity 语句
        # 格式：pragma solidity ^0.8.29; 或 pragma solidity 0.8.29; 或 pragma solidity >=0.8.0 <0.9.0;
        pragma_match = re.search(r'pragma\s+solidity\s+([^;]+);', source_code)
        if pragma_match:
            pragma_str = pragma_match.group(1).strip()
            logger.info(f"检测到 pragma solidity: {pragma_str}")
            
            # 提取版本号（处理 ^, >=, < 等符号）
            # 优先提取精确版本号（如 0.8.29）
            exact_version_match = re.search(r'(\d+\.\d+\.\d+)', pragma_str)
            if exact_version_match:
                version = exact_version_match.group(1)
                logger.info(f"提取到精确版本号: {version}")
                return version
            
            # 如果没有精确版本，提取主版本号（如 0.8）
            major_version_match = re.search(r'(\d+\.\d+)', pragma_str)
            if major_version_match:
                major_version = major_version_match.group(1)
                # 使用该主版本的最新版本（例如 0.8 -> 0.8.29）
                logger.warning(f"未找到精确版本号，使用主版本: {major_version}，将尝试安装最新版本")
                return major_version
        
        # 默认返回 0.8.29（BatchDeposits.sol 当前使用的版本）
        logger.warning("无法从源代码检测 Solidity 版本，使用默认版本 0.8.29")
        return '0.8.29'
    
    def _ensure_solc_installed(self, required_version: Optional[str] = None):
        """
        确保 Solidity 编译器已安装
        
        Args:
            required_version: 所需的 Solidity 版本（如果为 None，则稍后从源代码检测）
        """
        try:
            if required_version:
                try:
                    install_solc(required_version)
                    set_solc_version(required_version)
                    logger.info(f"已安装 Solidity 编译器 {required_version}")
                except Exception as e:
                    logger.warning(f"安装 Solidity 编译器 {required_version} 失败: {e}，尝试使用已安装的版本")
                    # 尝试使用已安装的版本
                    try:
                        from solcx import get_installed_solc_versions
                        versions = get_installed_solc_versions()
                        if versions:
                            # 尝试找到匹配的版本
                            matching_version = None
                            for v in sorted(versions, reverse=True):
                                if v.startswith(required_version.split('.')[0] + '.' + required_version.split('.')[1]):
                                    matching_version = v
                                    break
                            
                            if matching_version:
                                set_solc_version(matching_version)
                                logger.info(f"使用已安装的匹配版本: {matching_version}")
                            else:
                                set_solc_version(versions[-1])
                                logger.warning(f"未找到匹配版本，使用已安装的最新版本: {versions[-1]}")
                    except Exception as e2:
                        logger.error(f"无法设置 Solidity 编译器版本: {e2}")
                        raise
        except Exception as e:
            logger.error(f"无法设置 Solidity 编译器: {e}")
            raise
    
    def _get_contract_source(self) -> str:
        """
        从 GitHub 获取合约源代码
        
        Returns:
            合约源代码字符串
        """
        temp_dir = None
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix='batch_deposit_contract_')
            logger.info(f"克隆 Batch Deposit 仓库到临时目录: {temp_dir}")
            
            # 克隆仓库
            subprocess.run(
                ['git', 'clone', '--depth', '1', BATCH_DEPOSIT_REPO, temp_dir],
                check=True,
                capture_output=True,
                timeout=60
            )
            
            # 读取合约文件
            contract_file = Path(temp_dir) / BATCH_DEPOSIT_CONTRACT_PATH
            if not contract_file.exists():
                raise FileNotFoundError(f"合约文件不存在: {contract_file}")
            
            source_code = contract_file.read_text(encoding='utf-8')
            logger.info(f"成功获取合约源代码（长度: {len(source_code)} 字符）")
            
            return source_code
            
        except subprocess.TimeoutExpired:
            raise Exception("克隆 GitHub 仓库超时")
        except subprocess.CalledProcessError as e:
            raise Exception(f"克隆 GitHub 仓库失败: {e.stderr.decode() if e.stderr else str(e)}")
        except Exception as e:
            raise Exception(f"获取合约源代码失败: {e}")
        finally:
            # 清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"清理临时目录失败: {e}")
    
    def _compile_contract(self, source_code: str) -> Dict[str, Any]:
        """
        编译合约
        
        Args:
            source_code: 合约源代码
            
        Returns:
            编译后的合约信息
        """
        try:
            logger.info("开始编译 Batch Deposit 合约...")
            
            # 首先检测所需的 Solidity 版本
            required_version = self._detect_solc_version(source_code)
            logger.info(f"检测到所需的 Solidity 版本: {required_version}")
            
            # 安装并设置对应的编译器版本
            self._ensure_solc_installed(required_version)
            
            # 编译合约
            try:
                compiled_sol = compile_source(
                    source_code,
                    output_values=['abi', 'bin'],
                    solc_version=required_version
                )
            except Exception as e:
                # 如果失败，尝试不指定版本（使用当前设置的版本）
                logger.warning(f"使用指定版本 {required_version} 编译失败: {e}，尝试使用当前设置的版本")
                compiled_sol = compile_source(
                    source_code,
                    output_values=['abi', 'bin']
                )
            
            # 获取合约接口（BatchDeposits）
            contract_interface = None
            for contract_name, contract_data in compiled_sol.items():
                if 'BatchDeposits' in contract_name:
                    contract_interface = contract_data
                    break
            
            if not contract_interface:
                # 如果没有找到，使用第一个合约
                contract_interface = list(compiled_sol.values())[0]
            
            logger.info("合约编译成功")
            return contract_interface
            
        except Exception as e:
            logger.error(f"编译合约失败: {e}", exc_info=True)
            raise Exception(f"编译合约失败: {e}")
    
    def deploy(
        self,
        rpc_url: str,
        network_name: str,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        部署 Batch Deposit 合约
        
        Args:
            rpc_url: RPC URL（用于验证连接）
            network_name: 网络名称
            gas_price: Gas 价格（可选）
            gas_limit: Gas 限制（可选）
            
        Returns:
            部署结果，包含合约地址和交易哈希
        """
        try:
            # 获取合约源代码
            source_code = self._get_contract_source()
            
            # 编译合约（会自动检测并安装所需的 Solidity 版本）
            contract_interface = self._compile_contract(source_code)
            
            # 获取 bytecode（可能是 'bin' 或 'bytecode'）
            bytecode = contract_interface.get('bin') or contract_interface.get('bytecode')
            if not bytecode:
                raise ValueError("编译结果中未找到 bytecode")
            
            # 创建合约实例
            contract = self.web3.eth.contract(
                abi=contract_interface['abi'],
                bytecode=bytecode
            )
            
            # 构建部署交易
            deploy_txn = contract.constructor().build_transaction({
                'from': self.deployer_address,
                'nonce': self.web3.eth.get_transaction_count(self.deployer_address),
                'gas': gas_limit or 5000000,
                'gasPrice': gas_price or self.web3.eth.gas_price
            })
            
            # 签名交易
            signed_txn = self.web3.eth.account.sign_transaction(
                deploy_txn,
                self.deployer_account.key
            )
            
            # 发送交易
            logger.info(f"发送部署交易...")
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            logger.info(f"部署交易已发送: {tx_hash_hex}")
            
            # 等待交易确认
            logger.info("等待交易确认...")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if receipt.status != 1:
                raise Exception(f"部署交易失败，状态码: {receipt.status}")
            
            # 获取合约地址
            contract_address = receipt.contractAddress
            
            logger.info(f"Batch Deposit 合约部署成功: {contract_address}")
            
            return {
                'contract_address': contract_address,
                'deployment_tx_hash': tx_hash_hex,
                'network_name': network_name,
                'deployer_address': self.deployer_address,
                'block_number': receipt.blockNumber,
                'gas_used': receipt.gasUsed
            }
            
        except Exception as e:
            logger.error(f"部署 Batch Deposit 合约失败: {e}", exc_info=True)
            raise Exception(f"部署失败: {e}")

