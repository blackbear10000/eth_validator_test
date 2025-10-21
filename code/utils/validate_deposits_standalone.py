#!/usr/bin/env python3
"""
独立的存款数据验证工具
不依赖 Vault 连接
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
    
    # 检查路径是否存在
    if not ethstaker_path.exists():
        raise ImportError(f"ethstaker-deposit-cli 路径不存在: {ethstaker_path}")
    
    # 检查关键模块是否存在
    validation_module = ethstaker_path / "ethstaker_deposit" / "utils" / "validation.py"
    if not validation_module.exists():
        raise ImportError(f"validation.py 不存在: {validation_module}")
    
    from ethstaker_deposit.utils.validation import (
        verify_deposit_data_json,
        validate_deposit
    )
    from ethstaker_deposit.settings import get_chain_setting
    from ethstaker_deposit.credentials import Credential
    from ethstaker_deposit.settings import BaseChainSetting
    
    print(f"✅ 成功导入 ethstaker-deposit-cli 验证功能")
    
except ImportError as e:
    print(f"❌ 导入 ethstaker-deposit-cli 失败: {e}")
    print(f"📁 检查路径: {ethstaker_path}")
    print(f"📁 路径存在: {ethstaker_path.exists()}")
    print("📋 解决方案:")
    print("1. 确保 git submodule 已正确初始化:")
    print("   git submodule update --init --recursive")
    print("2. 安装 ethstaker-deposit-cli 依赖:")
    print("   cd code/external/ethstaker-deposit-cli")
    print("   pip install -r requirements.txt")
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


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="验证存款数据有效性")
    parser.add_argument("deposit_file", help="存款数据文件路径")
    parser.add_argument("--network", default="mainnet", 
                       choices=["mainnet", "sepolia", "goerli", "gnosis", "chiado"],
                       help="网络名称")
    
    args = parser.parse_args()
    
    print("🔍 存款数据验证工具")
    print("=" * 50)
    
    is_valid = validate_deposit_file(args.deposit_file, args.network)
    
    if is_valid:
        print("\n🎉 所有存款数据验证通过！")
        sys.exit(0)
    else:
        print("\n❌ 存款数据验证失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()