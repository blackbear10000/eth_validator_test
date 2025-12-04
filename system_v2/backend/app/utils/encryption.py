"""
加密工具模块
提供助记词加密和解密功能
"""
import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class MnemonicEncryption:
    """助记词加密工具类"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        初始化加密工具
        
        Args:
            encryption_key: 加密密钥（可选，如果不提供则从环境变量获取或生成）
        """
        self.encryption_key = encryption_key or self._get_or_generate_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _get_or_generate_key(self) -> bytes:
        """
        获取或生成加密密钥
        
        优先从环境变量获取，如果没有则生成新的（不推荐用于生产环境）
        """
        key_str = os.getenv("MNEMONIC_ENCRYPTION_KEY")
        
        if key_str:
            try:
                # 如果环境变量是 base64 编码的，先解码
                if len(key_str) == 44 and key_str.endswith('='):
                    return key_str.encode()
                else:
                    # 尝试直接使用
                    return key_str.encode()
            except Exception as e:
                logger.warning(f"无法使用环境变量中的加密密钥: {e}")
        
        # 如果没有设置，生成新的密钥（仅用于开发环境）
        logger.warning("未设置 MNEMONIC_ENCRYPTION_KEY，生成临时密钥（不推荐用于生产环境）")
        key = Fernet.generate_key()
        
        # 输出密钥到日志（仅开发环境）
        if os.getenv("DEBUG", "false").lower() == "true":
            logger.warning(f"生成的临时加密密钥: {key.decode()}")
            logger.warning("请设置环境变量 MNEMONIC_ENCRYPTION_KEY 以使用固定密钥")
        
        return key
    
    def encrypt_mnemonic(self, mnemonic: str) -> tuple[str, str]:
        """
        加密助记词
        
        Args:
            mnemonic: 明文助记词
            
        Returns:
            (encrypted_mnemonic, salt) 元组
        """
        try:
            # 使用 Fernet 加密（Fernet 内部处理 salt）
            encrypted_bytes = self.fernet.encrypt(mnemonic.encode('utf-8'))
            encrypted_str = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            # Fernet 不需要单独的 salt，但为了兼容性，我们使用密钥的一部分作为标识
            salt = base64.b64encode(self.encryption_key[:16]).decode('utf-8')
            
            return encrypted_str, salt
        except Exception as e:
            logger.error(f"加密助记词失败: {e}")
            raise ValueError(f"加密助记词失败: {e}")
    
    def decrypt_mnemonic(self, encrypted_mnemonic: str, salt: Optional[str] = None) -> str:
        """
        解密助记词
        
        Args:
            encrypted_mnemonic: 加密后的助记词
            salt: 盐值（可选，Fernet 不需要，但保留参数以兼容）
            
        Returns:
            明文助记词
        """
        try:
            # 解码 base64
            encrypted_bytes = base64.b64decode(encrypted_mnemonic.encode('utf-8'))
            
            # 使用 Fernet 解密
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            mnemonic = decrypted_bytes.decode('utf-8')
            
            return mnemonic
        except Exception as e:
            logger.error(f"解密助记词失败: {e}")
            raise ValueError(f"解密助记词失败: {e}")


# 全局加密实例
_encryption_instance: Optional[MnemonicEncryption] = None


def get_encryption() -> MnemonicEncryption:
    """获取全局加密实例（单例模式）"""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = MnemonicEncryption()
    return _encryption_instance


def encrypt_mnemonic(mnemonic: str) -> tuple[str, str]:
    """
    加密助记词（便捷函数）
    
    Args:
        mnemonic: 明文助记词
        
    Returns:
        (encrypted_mnemonic, salt) 元组
    """
    return get_encryption().encrypt_mnemonic(mnemonic)


def decrypt_mnemonic(encrypted_mnemonic: str, salt: Optional[str] = None) -> str:
    """
    解密助记词（便捷函数）
    
    Args:
        encrypted_mnemonic: 加密后的助记词
        salt: 盐值（可选）
        
    Returns:
        明文助记词
    """
    return get_encryption().decrypt_mnemonic(encrypted_mnemonic, salt)

