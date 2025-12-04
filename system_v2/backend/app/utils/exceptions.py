"""
自定义异常类
"""


class ValidatorManagementError(Exception):
    """验证者管理基础异常"""
    pass


class KeyGenerationError(ValidatorManagementError):
    """密钥生成错误"""
    pass


class VaultError(ValidatorManagementError):
    """Vault 操作错误"""
    pass


class DatabaseError(ValidatorManagementError):
    """数据库操作错误"""
    pass


class DepositGenerationError(ValidatorManagementError):
    """Deposit Data 生成错误"""
    pass


class Web3SignerError(ValidatorManagementError):
    """Web3Signer 操作错误"""
    pass


class BeaconAPIError(ValidatorManagementError):
    """Beacon Chain API 错误"""
    pass


class ClientManagementError(ValidatorManagementError):
    """客户端管理错误"""
    pass


class RemoteValidatorAPIError(ValidatorManagementError):
    """Remote Validator API 错误"""
    pass

