"""
数据验证函数
"""
from typing import Any
from app.core.eth_tools import validate_eth_address, validate_pubkey


def validate_withdrawal_address(address: str) -> bool:
    """验证提款地址"""
    return validate_eth_address(address)


def validate_validator_pubkey(pubkey: str) -> bool:
    """验证验证者公钥"""
    return validate_pubkey(pubkey)

