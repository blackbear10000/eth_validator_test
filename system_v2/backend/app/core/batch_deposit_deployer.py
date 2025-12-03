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
        
        # 确保 solc 已安装
        self._ensure_solc_installed()
    
    def _ensure_solc_installed(self):
        """确保 Solidity 编译器已安装"""
        try:
            # BatchDeposits.sol 使用 Solidity 0.8.x
            # 尝试安装 0.8.19（一个稳定的版本）
            try:
                install_solc('0.8.19')
                set_solc_version('0.8.19')
                logger.info("已安装 Solidity 编译器 0.8.19")
            except Exception as e:
                logger.warning(f"安装 Solidity 编译器失败: {e}，尝试使用已安装的版本")
                # 尝试使用已安装的版本
                try:
                    from solcx import get_installed_solc_versions
                    versions = get_installed_solc_versions()
                    if versions:
                        set_solc_version(versions[-1])
                        logger.info(f"使用已安装的 Solidity 编译器版本: {versions[-1]}")
                except:
                    pass
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
            
            # 编译合约
            # 注意：solcx 的 compile_source 可能需要不同的参数格式
            try:
                compiled_sol = compile_source(
                    source_code,
                    output_values=['abi', 'bin'],
                    solc_version='0.8.19'
                )
            except Exception as e:
                # 如果失败，尝试不指定版本（使用当前设置的版本）
                logger.warning(f"使用指定版本编译失败: {e}，尝试使用当前设置的版本")
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
            
            # 编译合约
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

