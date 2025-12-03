"""
密钥管理服务
负责密钥生成、存储、状态管理
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

# 直接导入 ethstaker-deposit-cli（通过 pip 安装）
try:
    from ethstaker_deposit.credentials import Credential
    from ethstaker_deposit.settings import get_chain_setting
    from ethstaker_deposit.key_handling.key_derivation.mnemonic import get_mnemonic
    from ethstaker_deposit.utils.constants import WORD_LISTS_PATH
    import importlib.resources
    import ethstaker_deposit
    HAS_IMPORTLIB = True
except ImportError as e:
    logging.error(f"无法导入 ethstaker-deposit-cli，密钥生成功能不可用: {e}")
    logging.error("请确保已安装 ethstaker-deposit-cli: pip install git+https://github.com/ethstaker/ethstaker-deposit-cli.git")
    Credential = None
    get_chain_setting = None
    get_mnemonic = None
    WORD_LISTS_PATH = None
    HAS_IMPORTLIB = False

from app.models.database import ValidatorKey
from app.models.enums import ValidatorKeyStatus
from app.core.vault_client import VaultClient
from app.utils.exceptions import KeyGenerationError, VaultError, DatabaseError

logger = logging.getLogger(__name__)


class KeyManagementService:
    """
    密钥管理服务
    提供密钥生成、存储、状态管理等核心功能
    """
    
    # 类级别的临时目录缓存（避免重复创建）
    _temp_word_lists_dir = None
    
    def __init__(
        self,
        db: Session,
        vault_client: Optional[VaultClient] = None
    ):
        """
        初始化密钥管理服务
        
        Args:
            db: 数据库会话
            vault_client: Vault 客户端（可选，会自动创建）
        """
        self.db = db
        self.vault_client = vault_client or VaultClient()
    
    def generate_mnemonic(self) -> str:
        """
        生成新的 BIP39 助记词
        
        Returns:
            BIP39 助记词字符串
        """
        if get_mnemonic is None:
            raise KeyGenerationError("ethstaker-deposit-cli 未正确导入")
        
        try:
            import os
            import tempfile
            import shutil
            import urllib.request
            
            # 尝试获取正确的 word lists 路径
            words_path = None
            
            # 方法1: 使用 WORD_LISTS_PATH 常量（如果可用且路径存在）
            if WORD_LISTS_PATH:
                if os.path.exists(WORD_LISTS_PATH):
                    words_path = WORD_LISTS_PATH
                    logger.debug(f"使用 WORD_LISTS_PATH: {words_path}")
            
            # 方法2: 尝试使用包的 __file__ 属性
            if not words_path:
                try:
                    package_path = os.path.dirname(ethstaker_deposit.__file__)
                    words_path = os.path.join(
                        package_path, 
                        'key_handling', 
                        'key_derivation', 
                        'word_lists'
                    )
                    if os.path.exists(words_path) and os.path.exists(os.path.join(words_path, 'english.txt')):
                        logger.debug(f"使用包路径: {words_path}")
                    else:
                        words_path = None
                except Exception as e:
                    logger.warning(f"无法通过包路径获取: {e}")
            
            # 方法3: 使用 importlib.resources 读取文件内容并创建临时目录
            if not words_path and HAS_IMPORTLIB:
                try:
                    # 检查是否已有缓存的临时目录
                    if KeyManagementService._temp_word_lists_dir and os.path.exists(KeyManagementService._temp_word_lists_dir):
                        english_file = os.path.join(KeyManagementService._temp_word_lists_dir, 'english.txt')
                        if os.path.exists(english_file):
                            words_path = KeyManagementService._temp_word_lists_dir
                            logger.debug(f"使用缓存的临时目录: {words_path}")
                    
                    if not words_path:
                        # 创建临时目录
                        temp_dir = tempfile.mkdtemp(prefix='ethstaker_word_lists_')
                        logger.debug(f"创建临时目录: {temp_dir}")
                        
                        # 使用 importlib.resources 读取文件内容
                        if hasattr(importlib.resources, 'files'):
                            # Python 3.9+ 使用 files() API
                            word_lists_ref = importlib.resources.files('ethstaker_deposit').joinpath(
                                'key_handling', 'key_derivation', 'word_lists'
                            )
                            
                            # 尝试读取 english.txt 文件
                            try:
                                english_file_ref = word_lists_ref.joinpath('english.txt')
                                english_content = english_file_ref.read_text(encoding='utf-8')
                                
                                # 创建 word_lists 目录
                                temp_word_lists_dir = os.path.join(temp_dir, 'word_lists')
                                os.makedirs(temp_word_lists_dir, exist_ok=True)
                                
                                # 写入 english.txt
                                english_file_path = os.path.join(temp_word_lists_dir, 'english.txt')
                                with open(english_file_path, 'w', encoding='utf-8') as f:
                                    f.write(english_content)
                                
                                # 缓存临时目录路径
                                KeyManagementService._temp_word_lists_dir = temp_word_lists_dir
                                words_path = temp_word_lists_dir
                                logger.info(f"使用 importlib.resources 创建临时 word lists 目录: {words_path}")
                            except Exception as e:
                                logger.warning(f"无法通过 importlib.resources 读取文件: {e}")
                                if temp_dir and os.path.exists(temp_dir):
                                    shutil.rmtree(temp_dir)
                        else:
                            # Python < 3.9 使用 path() API
                            word_lists_ref = importlib.resources.path(
                                'ethstaker_deposit.key_handling.key_derivation.word_lists', 
                                'english.txt'
                            )
                            with word_lists_ref as path:
                                # 如果文件存在，使用其父目录
                                if os.path.exists(path):
                                    words_path = str(path.parent)
                                    logger.info(f"使用 importlib.resources.path: {words_path}")
                except Exception as e:
                    logger.warning(f"importlib.resources 方法失败: {e}")
            
            # 方法4: 从 GitHub 下载 word lists 文件（如果前面的方法都失败）
            if not words_path:
                try:
                    logger.info("尝试从 GitHub 下载 word lists 文件...")
                    
                    # 检查是否已有缓存的临时目录
                    if KeyManagementService._temp_word_lists_dir and os.path.exists(KeyManagementService._temp_word_lists_dir):
                        english_file = os.path.join(KeyManagementService._temp_word_lists_dir, 'english.txt')
                        if os.path.exists(english_file):
                            words_path = KeyManagementService._temp_word_lists_dir
                            logger.debug(f"使用缓存的临时目录: {words_path}")
                    
                    if not words_path:
                        # 创建临时目录
                        temp_dir = tempfile.mkdtemp(prefix='ethstaker_word_lists_')
                        temp_word_lists_dir = os.path.join(temp_dir, 'word_lists')
                        os.makedirs(temp_word_lists_dir, exist_ok=True)
                        
                        # 从 GitHub 下载 english.txt
                        github_url = "https://raw.githubusercontent.com/ethstaker/ethstaker-deposit-cli/main/ethstaker_deposit/key_handling/key_derivation/word_lists/english.txt"
                        
                        try:
                            logger.info(f"从 GitHub 下载: {github_url}")
                            with urllib.request.urlopen(github_url, timeout=10) as response:
                                english_content = response.read().decode('utf-8')
                            
                            # 验证内容（应该包含 2048 行）
                            lines = [l.strip() for l in english_content.split('\n') if l.strip()]
                            if len(lines) != 2048:
                                raise ValueError(f"Word list 文件行数不正确: 期望 2048，实际 {len(lines)}")
                            
                            # 写入文件
                            english_file_path = os.path.join(temp_word_lists_dir, 'english.txt')
                            with open(english_file_path, 'w', encoding='utf-8') as f:
                                f.write(english_content)
                            
                            # 缓存临时目录路径
                            KeyManagementService._temp_word_lists_dir = temp_word_lists_dir
                            words_path = temp_word_lists_dir
                            logger.info(f"成功从 GitHub 下载并创建临时 word lists 目录: {words_path}")
                        except Exception as e:
                            logger.warning(f"从 GitHub 下载失败: {e}")
                            if temp_dir and os.path.exists(temp_dir):
                                shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"GitHub 下载方法失败: {e}")
            
            # 如果仍然找不到路径，抛出错误
            if not words_path:
                raise KeyGenerationError(
                    "无法找到或下载 word lists 文件。"
                    "请检查网络连接或手动下载 word_lists 文件。"
                )
            
            # 验证路径是否存在
            english_file = os.path.join(words_path, 'english.txt')
            if not os.path.exists(english_file):
                raise KeyGenerationError(
                    f"Word lists 文件不存在: {english_file}"
                )
            
            # 生成助记词
            mnemonic = get_mnemonic(language='english', words_path=words_path)
            
            logger.info("助记词生成成功")
            return mnemonic
        except KeyGenerationError:
            raise
        except Exception as e:
            logger.error(f"助记词生成失败: {e}", exc_info=True)
            raise KeyGenerationError(f"助记词生成失败: {e}")
    
    def derive_keys_from_mnemonic(
        self,
        mnemonic: str,
        start_index: int,
        count: int,
        network: str = 'mainnet'
    ) -> List[Dict[str, Any]]:
        """
        从助记词派生验证者密钥
        
        Args:
            mnemonic: BIP39 助记词
            start_index: 起始索引
            count: 生成数量
            network: 网络名称（mainnet/kurtosis 等）
            
        Returns:
            密钥信息列表
        """
        if Credential is None or get_chain_setting is None:
            raise KeyGenerationError("ethstaker-deposit-cli 未正确导入")
        
        try:
            chain_setting = get_chain_setting(network)
            keys = []
            
            for i in range(start_index, start_index + count):
                # 使用官方 Credential 类进行密钥派生
                # hex_withdrawal_address=None 表示使用 BLS 提款（0x00 类型）
                # 后续可以动态绑定到执行层地址（0x01 类型）
                credential = Credential(
                    mnemonic=mnemonic,
                    mnemonic_password='',
                    index=i,
                    amount=32000000000,  # 32 ETH in Gwei
                    chain_setting=chain_setting,
                    hex_withdrawal_address=None  # BLS withdrawal initially
                )
                
                keys.append({
                    'index': i,
                    'pubkey': '0x' + credential.signing_pk.hex(),  # 48 bytes BLS12-381
                    'signing_private_key': '0x' + credential.signing_sk.to_bytes(32, 'big').hex(),
                    'withdrawal_pubkey': '0x' + credential.withdrawal_pk.hex(),
                    'withdrawal_private_key': '0x' + credential.withdrawal_sk.to_bytes(32, 'big').hex(),
                    'signing_key_path': credential.signing_key_path,
                    'withdrawal_key_path': f"m/12381/3600/{i}/0"
                })
            
            logger.info(f"从助记词派生 {count} 个密钥成功（索引 {start_index} 到 {start_index + count - 1}）")
            return keys
            
        except Exception as e:
            logger.error(f"密钥派生失败: {e}")
            raise KeyGenerationError(f"密钥派生失败: {e}")
    
    def batch_generate_keys(
        self,
        count: int,
        batch_id: Optional[str] = None,
        mnemonic: Optional[str] = None,
        start_index: Optional[int] = None,
        network: str = 'mainnet'
    ) -> Dict[str, Any]:
        """
        批量生成验证者密钥
        
        Args:
            count: 生成数量
            batch_id: 批次ID（可选）
            mnemonic: 助记词（可选，如果不提供则生成新的）
            start_index: 起始索引（可选，如果不提供则从数据库查询最大索引+1）
            network: 网络名称
            
        Returns:
            包含生成的密钥信息和助记词的字典
        """
        try:
            # 生成或使用提供的助记词
            if mnemonic is None:
                mnemonic = self.generate_mnemonic()
                logger.info("使用新生成的助记词")
            else:
                logger.info("使用提供的助记词")
            
            # 确定起始索引
            if start_index is None:
                # 查询数据库中最大的索引
                from sqlalchemy import func
                max_index = self.db.query(func.max(ValidatorKey.index)).scalar()
                
                if max_index is not None:
                    start_index = max_index + 1
                else:
                    start_index = 0
            
            # 派生密钥
            keys = self.derive_keys_from_mnemonic(mnemonic, start_index, count, network)
            
            # 如果没有提供 batch_id，生成一个
            if batch_id is None:
                batch_id = f"batch-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            
            # 存储密钥
            stored_keys = []
            for key_data in keys:
                validator_key = self._store_key(
                    pubkey=key_data['pubkey'],
                    withdrawal_pubkey=key_data['withdrawal_pubkey'],
                    signing_private_key=key_data['signing_private_key'],
                    index=key_data['index'],
                    signing_key_path=key_data['signing_key_path'],
                    batch_id=batch_id
                )
                stored_keys.append(validator_key)
            
            # 提交事务
            self.db.commit()
            
            logger.info(f"批量生成并存储 {len(stored_keys)} 个密钥成功（批次: {batch_id}）")
            
            return {
                'mnemonic': mnemonic,
                'batch_id': batch_id,
                'count': len(stored_keys),
                'start_index': start_index,
                'end_index': start_index + len(stored_keys) - 1,
                'pubkeys': [k.pubkey for k in stored_keys]
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"批量生成密钥失败: {e}")
            raise KeyGenerationError(f"批量生成密钥失败: {e}")
    
    def _store_key(
        self,
        pubkey: str,
        withdrawal_pubkey: str,
        signing_private_key: str,
        index: int,
        signing_key_path: str,
        batch_id: Optional[str] = None
    ) -> ValidatorKey:
        """
        存储密钥（私有方法）
        将密钥存储到 Vault（私钥）和 PostgreSQL（元数据）
        
        Args:
            pubkey: 验证者公钥
            withdrawal_pubkey: 提款公钥
            signing_private_key: 签名私钥
            index: 索引
            signing_key_path: 签名密钥路径
            batch_id: 批次ID
            
        Returns:
            ValidatorKey 对象
        """
        try:
            # 1. 存储私钥到 Vault
            self.vault_client.store_signing_key(
                pubkey=pubkey,
                signing_private_key=signing_private_key
            )
            
            # 2. 存储元数据到 PostgreSQL
            validator_key = ValidatorKey(
                pubkey=pubkey.lower(),  # 统一使用小写
                withdrawal_pubkey=withdrawal_pubkey.lower(),
                status=ValidatorKeyStatus.UNUSED.value,
                index=index,
                signing_key_path=signing_key_path,
                batch_id=batch_id,
                created_at=datetime.utcnow()
            )
            
            self.db.add(validator_key)
            self.db.flush()  # 获取 ID 但不提交
            
            logger.debug(f"密钥已存储: {pubkey[:10]}...")
            return validator_key
            
        except Exception as e:
            logger.error(f"存储密钥失败 ({pubkey[:10]}...): {e}")
            if isinstance(e, VaultError):
                raise
            raise DatabaseError(f"存储密钥失败: {e}")
    
    def activate_keys(
        self,
        count: Optional[int] = None,
        pubkeys: Optional[List[str]] = None,
        batch_id: Optional[str] = None
    ) -> List[ValidatorKey]:
        """
        激活密钥（从 unused 状态转为 active 状态）
        
        Args:
            count: 激活数量（如果不提供 pubkeys）
            pubkeys: 要激活的公钥列表（如果提供则忽略 count）
            batch_id: 批次ID（可选，用于筛选）
            
        Returns:
            激活的密钥列表
        """
        try:
            # 构建查询条件
            query = self.db.query(ValidatorKey).filter(
                ValidatorKey.status == ValidatorKeyStatus.UNUSED.value
            )
            
            if batch_id:
                query = query.filter(ValidatorKey.batch_id == batch_id)
            
            if pubkeys:
                # 激活指定的公钥
                pubkeys_lower = [pk.lower() for pk in pubkeys]
                query = query.filter(ValidatorKey.pubkey.in_(pubkeys_lower))
            elif count:
                # 激活指定数量的密钥（按创建时间排序）
                query = query.order_by(ValidatorKey.created_at).limit(count)
            else:
                raise ValueError("必须提供 count 或 pubkeys 参数")
            
            keys = query.all()
            
            if not keys:
                logger.warning("没有可激活的密钥")
                return []
            
            # 更新状态
            now = datetime.utcnow()
            for key in keys:
                key.status = ValidatorKeyStatus.ACTIVE.value
                key.activated_at = now
            
            self.db.commit()
            
            logger.info(f"成功激活 {len(keys)} 个密钥")
            return keys
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"激活密钥失败: {e}")
            raise DatabaseError(f"激活密钥失败: {e}")
    
    def update_key_status(
        self,
        pubkey: str,
        status: ValidatorKeyStatus,
        **kwargs
    ) -> ValidatorKey:
        """
        更新密钥状态
        
        Args:
            pubkey: 验证者公钥
            status: 新状态
            **kwargs: 其他字段更新（如 deposited_at, exited_at 等）
            
        Returns:
            更新后的 ValidatorKey 对象
        """
        try:
            key = self.db.query(ValidatorKey).filter(
                ValidatorKey.pubkey == pubkey.lower()
            ).first()
            
            if not key:
                raise ValueError(f"密钥不存在: {pubkey}")
            
            # 更新状态
            key.status = status.value
            
            # 更新时间戳
            now = datetime.utcnow()
            if status == ValidatorKeyStatus.ACTIVE and not key.activated_at:
                key.activated_at = now
            elif status in [ValidatorKeyStatus.DEPOSITED, ValidatorKeyStatus.PENDING] and not key.deposited_at:
                key.deposited_at = now
            elif status == ValidatorKeyStatus.EXITED and not key.exited_at:
                key.exited_at = now
            
            # 更新其他字段
            for field, value in kwargs.items():
                if hasattr(key, field):
                    setattr(key, field, value)
            
            self.db.commit()
            
            logger.info(f"密钥状态已更新: {pubkey[:10]}... -> {status.value}")
            return key
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新密钥状态失败: {e}")
            raise DatabaseError(f"更新密钥状态失败: {e}")
    
    def get_key(self, pubkey: str) -> Optional[ValidatorKey]:
        """
        获取密钥信息
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            ValidatorKey 对象或 None
        """
        return self.db.query(ValidatorKey).filter(
            ValidatorKey.pubkey == pubkey.lower()
        ).first()
    
    def list_keys(
        self,
        status: Optional[ValidatorKeyStatus] = None,
        batch_id: Optional[str] = None,
        client_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> tuple[List[ValidatorKey], int]:
        """
        列出密钥
        
        Args:
            status: 状态筛选
            batch_id: 批次ID筛选
            client_type: 客户端类型筛选
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            (密钥列表, 总数) 元组
        """
        query = self.db.query(ValidatorKey)
        
        if status:
            query = query.filter(ValidatorKey.status == status.value)
        if batch_id:
            query = query.filter(ValidatorKey.batch_id == batch_id)
        if client_type:
            query = query.filter(ValidatorKey.client_type == client_type)
        
        # 获取总数
        total = query.count()
        
        # 按创建时间倒序（必须在 limit/offset 之前）
        query = query.order_by(ValidatorKey.created_at.desc())
        
        # 应用分页
        if limit:
            query = query.limit(limit).offset(offset)
        
        keys = query.all()
        return keys, total
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        获取密钥池状态统计
        
        Returns:
            状态统计字典
        """
        # 统计各状态的数量
        status_counts = {}
        for status in ValidatorKeyStatus:
            count = self.db.query(ValidatorKey).filter(
                ValidatorKey.status == status.value
            ).count()
            status_counts[status.value] = count
        
        # 总数量
        total = self.db.query(ValidatorKey).count()
        
        return {
            'total': total,
            'by_status': status_counts
        }

