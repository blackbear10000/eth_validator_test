#!/usr/bin/env python3
"""
验证存款数据有效性的工具
使用 ethstaker-deposit-cli 的验证功能
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入 ethstaker-deposit-cli 的验证功能
try:
    # 添加 ethstaker-deposit-cli 路径
    ethstaker_path = project_root / "code" / "external" / "ethstaker-deposit-cli"
    sys.path.insert(0, str(ethstaker_path))
    
    from ethstaker_deposit.utils.validation import (
        verify_deposit_data_json,
        validate_deposit
    )
    from ethstaker_deposit.settings import get_chain_setting
    from ethstaker_deposit.credentials import Credential
    from ethstaker_deposit.settings import BaseChainSetting
except ImportError as e:
    print(f"❌ 导入 ethstaker-deposit-cli 失败: {e}")
    print("请确保 ethstaker-deposit-cli 已正确安装")
    sys.exit(1)


def validate_deposit_file(deposit_file: str, network: str = "mainnet") -> bool:
    """
    验证存款数据文件的有效性
    
    Args:
        deposit_file: 存款数据文件路径
        network: 网络名称 (mainnet, sepolia, etc.)
    
    Returns:
        bool: 验证是否通过
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(deposit_file):
            print(f"❌ 存款数据文件不存在: {deposit_file}")
            return False
        
        # 读取存款数据
        with open(deposit_file, 'r') as f:
            deposit_data = json.load(f)
        
        if not isinstance(deposit_data, list):
            print("❌ 存款数据格式错误: 应该是数组格式")
            return False
        
        print(f"📋 验证 {len(deposit_data)} 个存款数据...")
        print(f"🌐 网络: {network}")
        
        # 获取链设置
        try:
            chain_setting = get_chain_setting(network)
        except Exception as e:
            print(f"❌ 获取链设置失败: {e}")
            return False
        
        # 验证每个存款
        valid_count = 0
        invalid_count = 0
        
        for i, deposit in enumerate(deposit_data):
            print(f"\n🔍 验证存款 {i+1}/{len(deposit_data)}:")
            print(f"   公钥: {deposit.get('pubkey', '')[:20]}...")
            
            try:
                # 验证存款数据
                is_valid = validate_deposit(deposit, chain_setting)
                
                if is_valid:
                    print(f"   ✅ 存款 {i+1} 验证通过")
                    valid_count += 1
                else:
                    print(f"   ❌ 存款 {i+1} 验证失败")
                    invalid_count += 1
                    
            except Exception as e:
                print(f"   ❌ 存款 {i+1} 验证出错: {e}")
                invalid_count += 1
        
        # 总结
        print(f"\n📊 验证结果:")
        print(f"   ✅ 有效存款: {valid_count}")
        print(f"   ❌ 无效存款: {invalid_count}")
        print(f"   📈 成功率: {valid_count/(valid_count+invalid_count)*100:.1f}%")
        
        return invalid_count == 0
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        return False


def validate_deposit_details(deposit_file: str, network: str = "mainnet") -> None:
    """
    详细验证存款数据并显示详细信息
    
    Args:
        deposit_file: 存款数据文件路径
        network: 网络名称
    """
    try:
        with open(deposit_file, 'r') as f:
            deposit_data = json.load(f)
        
        chain_setting = get_chain_setting(network)
        
        print(f"🔍 详细验证存款数据:")
        print(f"📁 文件: {deposit_file}")
        print(f"🌐 网络: {network}")
        print(f"📊 存款数量: {len(deposit_data)}")
        print(f"⛓️  链设置: {chain_setting.NETWORK_NAME}")
        print(f"💰 最小存款: {chain_setting.MIN_DEPOSIT_AMOUNT} ETH")
        print(f"🔢 乘数: {chain_setting.MULTIPLIER}")
        
        for i, deposit in enumerate(deposit_data):
            print(f"\n📋 存款 {i+1} 详情:")
            print(f"   🔑 公钥: {deposit.get('pubkey', '')}")
            print(f"   💳 提款凭证: {deposit.get('withdrawal_credentials', '')}")
            print(f"   💰 金额: {deposit.get('amount', 0)} Gwei ({deposit.get('amount', 0)/1e9:.1f} ETH)")
            print(f"   ✍️  签名: {deposit.get('signature', '')[:20]}...")
            print(f"   🌳 消息根: {deposit.get('deposit_message_root', '')}")
            print(f"   🌳 数据根: {deposit.get('deposit_data_root', '')}")
            print(f"   🍴 分叉版本: {deposit.get('fork_version', '')}")
            print(f"   🌐 网络名称: {deposit.get('network_name', '')}")
            print(f"   📦 CLI版本: {deposit.get('deposit_cli_version', '')}")
            
            # 验证提款凭证类型
            withdrawal_creds = deposit.get('withdrawal_credentials', '')
            if withdrawal_creds.startswith('00'):
                print(f"   📝 提款类型: 0x00 (BLS)")
            elif withdrawal_creds.startswith('01'):
                print(f"   📝 提款类型: 0x01 (执行地址)")
            elif withdrawal_creds.startswith('02'):
                print(f"   📝 提款类型: 0x02 (复合提款)")
            else:
                print(f"   📝 提款类型: 未知")
        
    except Exception as e:
        print(f"❌ 详细验证失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="验证存款数据有效性")
    parser.add_argument("deposit_file", help="存款数据文件路径")
    parser.add_argument("--network", default="mainnet", 
                       choices=["mainnet", "sepolia", "goerli", "gnosis", "chiado"],
                       help="网络名称")
    parser.add_argument("--detailed", action="store_true", 
                       help="显示详细验证信息")
    
    args = parser.parse_args()
    
    print("🔍 存款数据验证工具")
    print("=" * 50)
    
    if args.detailed:
        validate_deposit_details(args.deposit_file, args.network)
    else:
        is_valid = validate_deposit_file(args.deposit_file, args.network)
        
        if is_valid:
            print("\n🎉 所有存款数据验证通过！")
            sys.exit(0)
        else:
            print("\n❌ 存款数据验证失败！")
            sys.exit(1)


if __name__ == "__main__":
    main()
