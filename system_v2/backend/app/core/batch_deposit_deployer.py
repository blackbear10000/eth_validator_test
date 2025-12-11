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
        self._preinstalled_solc_path = None  # 存储预安装的 solc 路径（如果 solcx 无法识别）
        
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
                # 首先检查是否已经安装（包括预安装的版本）
                try:
                    from solcx import get_installed_solc_versions, get_executable
                    versions = get_installed_solc_versions()
                    
                    # 检查是否有精确匹配的版本
                    if required_version in versions:
                        set_solc_version(required_version)
                        logger.info(f"使用已安装的 Solidity 编译器 {required_version}")
                        return
                    
                    # 检查是否有匹配的主版本（如 0.8.x）
                    if versions:
                        matching_version = None
                        major_minor = '.'.join(required_version.split('.')[:2])  # 如 '0.8'
                        for v in sorted(versions, reverse=True):
                            if v.startswith(major_minor + '.'):
                                matching_version = v
                                break
                        
                        if matching_version:
                            set_solc_version(matching_version)
                            logger.info(f"使用已安装的匹配版本: {matching_version}（需要 {required_version}）")
                            return
                except Exception as e_check:
                    logger.debug(f"检查已安装版本时出错: {e_check}")
                
                # 如果没有找到已安装的版本，先检查预安装的版本（在尝试从网络下载之前）
                import os
                from pathlib import Path
                home_dir = Path.home()
                solcx_dir = home_dir / '.solcx'
                preinstalled_solc = solcx_dir / f'solc-v{required_version}'
                
                logger.info(f"检查预安装的 solc: {preinstalled_solc}")
                if preinstalled_solc.exists() and os.access(preinstalled_solc, os.X_OK):
                    # 直接使用预安装的二进制文件
                    self._preinstalled_solc_path = str(preinstalled_solc)
                    logger.info(f"✅ 找到预安装的 Solidity 编译器: {preinstalled_solc}，将在编译时使用")
                    # 验证版本
                    import subprocess
                    try:
                        result = subprocess.run([str(preinstalled_solc), '--version'], 
                                              capture_output=True, text=True, timeout=5)
                        logger.info(f"预安装的 solc 版本信息: {result.stdout.strip() if result.returncode == 0 else result.stderr.strip()}")
                    except Exception as e_verify:
                        logger.warning(f"验证预安装 solc 版本时出错: {e_verify}")
                    return  # 找到预安装版本，直接返回
                
                # 如果没有预安装的版本，尝试从 solc-bin 安装
                try:
                    logger.info(f"尝试从 solc-bin 安装 Solidity 编译器 {required_version}...")
                    install_solc(required_version)
                    set_solc_version(required_version)
                    logger.info(f"已从 solc-bin 安装 Solidity 编译器 {required_version}")
                except Exception as e:
                    logger.warning(f"从 solc-bin 安装 Solidity 编译器 {required_version} 失败: {e}")
                    logger.info("这可能是由于网络限制（如 Cloudflare）导致的，将尝试从 GitHub releases 下载")
                    
                    # 尝试从 GitHub releases 直接下载（备用方案）
                    try:
                        self._install_solc_from_github(required_version)
                        set_solc_version(required_version)
                        logger.info(f"✅ 已从 GitHub releases 安装 Solidity 编译器 {required_version}")
                    except Exception as e_github:
                        logger.warning(f"从 GitHub releases 安装也失败: {e_github}")
                        
                        # 最后尝试使用已安装的匹配版本
                        try:
                            from solcx import get_installed_solc_versions
                            versions = get_installed_solc_versions()
                            if versions:
                                matching_version = None
                                major_minor = '.'.join(required_version.split('.')[:2])
                                for v in sorted(versions, reverse=True):
                                    if v.startswith(major_minor + '.'):
                                        matching_version = v
                                        break
                                
                                if matching_version:
                                    set_solc_version(matching_version)
                                    logger.info(f"使用已安装的匹配版本: {matching_version}")
                                else:
                                    latest = sorted(versions, reverse=True)[0]
                                    set_solc_version(latest)
                                    logger.warning(f"未找到匹配版本，使用已安装的最新版本: {latest}（可能不兼容）")
                            else:
                                raise Exception(f"无法安装或找到 Solidity 编译器 {required_version}。所有安装方法都失败了。")
                        except Exception as e2:
                            logger.error(f"无法设置 Solidity 编译器版本: {e2}")
                            raise Exception(f"无法安装或找到 Solidity 编译器 {required_version}。错误: {e2}")
        except Exception as e:
            logger.error(f"无法设置 Solidity 编译器: {e}")
            raise
    
    def _get_contract_source(self) -> tuple[str, str]:
        """
        从 GitHub 获取合约源代码和临时目录路径
        
        Returns:
            (合约源代码字符串, 临时目录路径) 元组
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
            
            # 安装 npm 依赖（包括 OpenZeppelin）
            logger.info("安装 npm 依赖（包括 OpenZeppelin 合约）...")
            npm_result = subprocess.run(
                ['npm', 'install'],
                cwd=temp_dir,
                check=False,  # 不强制要求成功，因为可能没有 npm
                capture_output=True,
                timeout=120
            )
            if npm_result.returncode == 0:
                logger.info("npm 依赖安装成功")
            else:
                logger.warning(f"npm install 失败（可能没有安装 npm）: {npm_result.stderr.decode() if npm_result.stderr else '未知错误'}")
                # 尝试手动下载 OpenZeppelin 合约
                self._install_openzeppelin_manually(temp_dir)
            
            # 读取合约文件
            contract_file = Path(temp_dir) / BATCH_DEPOSIT_CONTRACT_PATH
            if not contract_file.exists():
                raise FileNotFoundError(f"合约文件不存在: {contract_file}")
            
            source_code = contract_file.read_text(encoding='utf-8')
            logger.info(f"成功获取合约源代码（长度: {len(source_code)} 字符）")
            
            return source_code, temp_dir
            
        except subprocess.TimeoutExpired:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            raise Exception("克隆 GitHub 仓库超时")
        except subprocess.CalledProcessError as e:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            raise Exception(f"克隆 GitHub 仓库失败: {e.stderr.decode() if e.stderr else str(e)}")
        except Exception as e:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            raise Exception(f"获取合约源代码失败: {e}")
    
    def _install_solc_from_github(self, version: str):
        """
        从 GitHub releases 直接下载并安装 solc（备用方案，避免 solc-bin 403 错误）
        
        Args:
            version: Solidity 版本（如 '0.8.29'）
        """
        import urllib.request
        import subprocess
        from pathlib import Path
        
        # solcx 的安装目录
        home_dir = Path.home()
        solcx_dir = home_dir / '.solcx'
        solcx_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建下载 URL
        # GitHub releases URL: https://github.com/ethereum/solidity/releases/download/v{version}/solc-static-linux
        download_url = f"https://github.com/ethereum/solidity/releases/download/v{version}/solc-static-linux"
        binary_path = solcx_dir / f"solc-v{version}"
        
        logger.info(f"从 GitHub releases 下载 solc {version}: {download_url}")
        try:
            urllib.request.urlretrieve(download_url, binary_path)
            binary_path.chmod(0o755)
            
            # 验证安装
            result = subprocess.run([str(binary_path), '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise Exception(f"下载的 solc 无法运行: {result.stderr}")
            
            logger.info(f"✅ solc {version} 已从 GitHub 下载到: {binary_path}")
            # 存储路径供编译时使用
            self._preinstalled_solc_path = str(binary_path)
        except Exception as e:
            # 清理失败的文件
            if binary_path.exists():
                try:
                    binary_path.unlink()
                except:
                    pass
            raise Exception(f"从 GitHub releases 下载 solc 失败: {e}")
    
    def _install_openzeppelin_manually(self, temp_dir: str):
        """
        手动下载 OpenZeppelin 合约（如果 npm 不可用）
        
        Args:
            temp_dir: 临时目录路径
        """
        try:
            import urllib.request
            import json
            import zipfile
            
            logger.info("尝试手动下载 OpenZeppelin 合约...")
            
            # 创建 node_modules 目录
            node_modules_dir = Path(temp_dir) / 'node_modules' / '@openzeppelin'
            node_modules_dir.mkdir(parents=True, exist_ok=True)
            
            # 从 GitHub 下载 OpenZeppelin contracts 的 zip 文件
            # 使用 releases 中的最新版本
            openzeppelin_url = "https://github.com/OpenZeppelin/openzeppelin-contracts/archive/refs/tags/v5.0.1.zip"
            zip_path = Path(temp_dir) / 'openzeppelin.zip'
            
            logger.info(f"从 GitHub 下载 OpenZeppelin 合约: {openzeppelin_url}")
            urllib.request.urlretrieve(openzeppelin_url, zip_path)
            
            # 解压到 node_modules/@openzeppelin/contracts
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(node_modules_dir)
            
            # 重命名解压后的目录
            extracted_dir = node_modules_dir / 'openzeppelin-contracts-5.0.1'
            contracts_dir = node_modules_dir / 'contracts'
            if extracted_dir.exists():
                if contracts_dir.exists():
                    shutil.rmtree(contracts_dir)
                extracted_dir.rename(contracts_dir)
            
            # 清理 zip 文件
            zip_path.unlink()
            
            logger.info("OpenZeppelin 合约下载成功")
            
        except Exception as e:
            logger.warning(f"手动下载 OpenZeppelin 合约失败: {e}，将尝试使用 compile_files")
    
    def _compile_contract(self, source_code: str, contract_dir: str) -> Dict[str, Any]:
        """
        编译合约
        
        Args:
            source_code: 合约源代码
            contract_dir: 合约所在目录（用于解析导入路径）
            
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
            
            # 尝试使用 compile_files 或 compile_standard（支持导入路径）
            contract_file_path = Path(contract_dir) / BATCH_DEPOSIT_CONTRACT_PATH
            node_modules_path = Path(contract_dir) / 'node_modules'
            
            # 设置导入重映射
            # solc remappings 格式: prefix=path
            # 合约中使用: import "@openzeppelin/contracts/utils/Pausable.sol"
            # 需要映射 @openzeppelin/contracts/ 到 node_modules/@openzeppelin/contracts/
            import_remappings = []
            openzeppelin_contracts_path = Path(contract_dir) / 'node_modules' / '@openzeppelin' / 'contracts'
            if openzeppelin_contracts_path.exists():
                # 使用绝对路径
                # remapping 格式: @openzeppelin/contracts/=绝对路径/
                abs_path = openzeppelin_contracts_path.resolve()
                # 正确的 remapping：@openzeppelin/contracts/ 映射到实际路径
                import_remappings.append(f"@openzeppelin/contracts/={abs_path}/")
                logger.info(f"设置导入重映射: @openzeppelin/contracts/ -> {abs_path}/")
                # 验证路径和文件
                if abs_path.exists():
                    utils_path = abs_path / 'utils' / 'Pausable.sol'
                    logger.info(f"验证 Pausable.sol 存在: {utils_path.exists()}")
                    if not utils_path.exists():
                        logger.warning(f"Pausable.sol 不存在于预期路径: {utils_path}")
                        logger.info(f"contracts 目录内容: {list(abs_path.iterdir())[:10]}")
            else:
                logger.warning(f"OpenZeppelin 合约路径不存在: {openzeppelin_contracts_path}")
                node_modules_path = Path(contract_dir) / 'node_modules'
                logger.warning(f"检查 node_modules 目录: {node_modules_path}, 存在: {node_modules_path.exists()}")
                if node_modules_path.exists():
                    logger.info(f"node_modules 内容: {list(node_modules_path.iterdir())[:10]}")
            
            # 使用 compile_standard（支持导入路径和 remappings）
            try:
                from solcx import compile_standard
                
                # 构建 sources：主合约文件
                # 使用相对路径，solc 会根据 remappings 和 allow_paths 解析导入
                sources = {
                    'contracts/BatchDeposits.sol': {
                        'content': source_code
                    }
                }
                
                # 注意：不需要手动添加 OpenZeppelin 合约到 sources
                # solc 会根据 remappings 自动解析 @openzeppelin/ 导入
                logger.info("使用 remappings 让 solc 自动解析 OpenZeppelin 导入")
                
                # 构建标准输入格式
                standard_input = {
                    'language': 'Solidity',
                    'sources': sources,
                    'settings': {
                        'outputSelection': {
                            '*': {
                                '*': ['abi', 'evm.bytecode']
                            }
                        },
                        'remappings': import_remappings if import_remappings else []
                    }
                }
                
                logger.info(f"开始编译，使用 remappings: {import_remappings}")
                contract_dir_abs = str(Path(contract_dir).resolve())
                node_modules_abs = str((Path(contract_dir) / 'node_modules').resolve())
                logger.info(f"允许的路径: {contract_dir_abs}, {node_modules_abs}")
                
                # 使用 allow_paths 让 solc 能够解析导入
                # allow_paths 应该包含 node_modules 目录
                # solcx 的 allow_paths 参数接受字符串（逗号分隔）或列表
                allow_paths_list = [contract_dir_abs, node_modules_abs]
                
                # 如果找到了预安装的 solc 路径，直接使用它
                compile_kwargs = {
                    'standard_input': standard_input,
                    'solc_version': required_version,
                    'allow_paths': allow_paths_list
                }
                if self._preinstalled_solc_path:
                    compile_kwargs['solc_binary'] = self._preinstalled_solc_path
                    logger.info(f"使用预安装的 solc 二进制文件: {self._preinstalled_solc_path}")
                
                compiled_output = compile_standard(**compile_kwargs)
                
                # 转换为统一的格式
                compiled_sol = {}
                for contract_path, contracts in compiled_output.get('contracts', {}).items():
                    for contract_name, contract_data in contracts.items():
                        key = f"{contract_path}:{contract_name}"
                        compiled_sol[key] = {
                            'abi': contract_data.get('abi', []),
                            'bin': contract_data.get('evm', {}).get('bytecode', {}).get('object', '')
                        }
                
                logger.info("使用 compile_standard 编译成功")
            except Exception as e:
                logger.error(f"compile_standard 编译失败: {e}", exc_info=True)
                raise Exception(f"编译合约失败: {e}")
            
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
        deposit_contract_address: str,
        initial_fee: int = 0,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        部署 Batch Deposit 合约
        
        Args:
            rpc_url: RPC URL（用于验证连接）
            network_name: 网络名称
            deposit_contract_address: 官方 Deposit 合约地址
            initial_fee: 初始费用（wei，必须是 gwei 的倍数，默认 0）
            gas_price: Gas 价格（可选）
            gas_limit: Gas 限制（可选）
            
        Returns:
            部署结果，包含合约地址和交易哈希
        """
        temp_dir = None
        try:
            # 获取合约源代码和临时目录
            source_code, temp_dir = self._get_contract_source()
            
            # 编译合约（会自动检测并安装所需的 Solidity 版本）
            contract_interface = self._compile_contract(source_code, temp_dir)
            
            # 获取 bytecode（可能是 'bin' 或 'bytecode'）
            bytecode = contract_interface.get('bin') or contract_interface.get('bytecode')
            if not bytecode:
                raise ValueError("编译结果中未找到 bytecode")
            
            # 创建合约实例
            contract = self.web3.eth.contract(
                abi=contract_interface['abi'],
                bytecode=bytecode
            )
            
            # 验证 initial_fee 是 gwei 的倍数（1 gwei = 10^9 wei）
            gwei = 10**9
            if initial_fee % gwei != 0:
                raise ValueError(f"初始费用必须是 gwei 的倍数。当前值: {initial_fee} wei")
            
            # 构建部署交易
            # BatchDeposit 构造函数需要两个参数：
            # 1. address depositContractAddr - 官方存款合约地址
            # 2. uint256 initialFee - 初始费用（wei）
            logger.info(f"部署 BatchDeposit 合约，参数: deposit_contract={deposit_contract_address}, initial_fee={initial_fee} wei")
            deploy_txn = contract.constructor(
                deposit_contract_address,
                initial_fee
            ).build_transaction({
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
            # web3.py 6.0+ 使用 raw_transaction（下划线），旧版本使用 rawTransaction（驼峰）
            raw_transaction = getattr(signed_txn, 'raw_transaction', None) or getattr(signed_txn, 'rawTransaction', None)
            if raw_transaction is None:
                raise ValueError("无法获取原始交易数据，签名交易对象缺少 raw_transaction 或 rawTransaction 属性")
            
            logger.info(f"发送部署交易...")
            tx_hash = self.web3.eth.send_raw_transaction(raw_transaction)
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
        finally:
            # 清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info("已清理临时目录")
                except Exception as e:
                    logger.warning(f"清理临时目录失败: {e}")

