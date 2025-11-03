"""
Ethereum 工具函数
"""
from typing import Optional
from eth_utils import to_bytes, to_hex, to_checksum_address
from web3 import Web3


def validate_eth_address(address: str) -> bool:
    """验证以太坊地址格式"""
    try:
        if not address.startswith('0x'):
            return False
        if len(address) != 42:
            return False
        int(address, 16)  # 验证是否为有效的十六进制
        return True
    except (ValueError, AttributeError):
        return False


def validate_pubkey(pubkey: str) -> bool:
    """验证 BLS12-381 公钥格式"""
    try:
        pubkey_clean = pubkey.lower().replace('0x', '')
        if len(pubkey_clean) != 96:  # 48 bytes = 96 hex chars
            return False
        int(pubkey_clean, 16)  # 验证是否为有效的十六进制
        return True
    except (ValueError, AttributeError):
        return False


def wei_to_eth(wei: int) -> float:
    """Wei 转换为 ETH"""
    return wei / 1e18


def eth_to_wei(eth: float) -> int:
    """ETH 转换为 Wei"""
    return int(eth * 1e18)


def gwei_to_wei(gwei: int) -> int:
    """Gwei 转换为 Wei"""
    return gwei * 1e9


def format_eth_amount(wei: int, decimals: int = 4) -> str:
    """格式化 ETH 金额"""
    eth = wei_to_eth(wei)
    return f"{eth:.{decimals}f} ETH"

