#!/usr/bin/env python3
"""
为已激活的密钥创建存款数据
确保 activate-keys 和 create-deposits 使用相同的密钥
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'code'))

def create_deposits_for_active_keys(fork_version: str, count: int = None, 
                                  withdrawal_address: str = None) -> bool:
    """为已激活的密钥创建存款数据"""
    print(f"🔧 为已激活的密钥创建存款数据...")
    print(f"📋 Fork version: {fork_version}")
    
    try:
        from code.core.vault_key_manager import VaultKeyManager
        from code.utils.deposit_generator import DepositGenerator
        
        # 1. 获取已激活的密钥
        vault_manager = VaultKeyManager()
        active_keys = vault_manager.list_keys(status='active')
        
        if not active_keys:
            print("❌ 没有找到已激活的密钥")
            print("💡 请先运行: ./validator.sh activate-keys --count 4")
            return False
        
        print(f"✅ 找到 {len(active_keys)} 个已激活的密钥")
        
        # 2. 如果指定了数量，只使用前 N 个
        if count and count < len(active_keys):
            active_keys = active_keys[:count]
            print(f"📋 使用前 {count} 个密钥")
        
        # 3. 获取提款地址
        if not withdrawal_address:
            withdrawal_address = "0x8943545177806ED17B9F23F0a21ee5948eCaa776"
        
        print(f"🎯 提款地址: {withdrawal_address}")
        
        # 4. 创建存款生成器
        generator = DepositGenerator(network='kurtosis', fork_version=fork_version)
        print(f"✅ 存款生成器已创建，Fork version: {generator.fork_version}")
        
        # 5. 为每个激活的密钥创建存款数据
        deposit_data = []
        success_count = 0
        
        for i, key in enumerate(active_keys, 1):
            print(f"🔧 处理密钥 {i}/{len(active_keys)}: {key.pubkey[:10]}...")
            
            try:
                # 创建存款数据
                deposit_info = generator.create_deposit_data(
                    key=key,
                    withdrawal_address=withdrawal_address,
                    notes=f"Kurtosis deposit for active key {i}"
                )
                
                if deposit_info:
                    deposit_data.append(deposit_info)
                    success_count += 1
                    print(f"   ✅ 存款数据已创建")
                else:
                    print(f"   ❌ 存款数据创建失败")
                    
            except Exception as e:
                print(f"   ❌ 处理密钥失败: {e}")
                continue
        
        if not deposit_data:
            print("❌ 没有成功创建任何存款数据")
            return False
        
        # 6. 保存存款数据
        project_root = Path(__file__).parent.parent
        deposits_dir = project_root / "data" / "deposits"
        deposits_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存到带 fork version 的文件
        fork_suffix = fork_version.replace('0x', '')
        deposit_file = deposits_dir / f"deposit_data_active_keys_fork_{fork_suffix}.json"
        
        with open(deposit_file, 'w') as f:
            json.dump(deposit_data, f, indent=2)
        
        print(f"✅ 存款数据已保存: {deposit_file}")
        
        # 也保存到标准位置
        standard_file = deposits_dir / "deposit_data.json"
        with open(standard_file, 'w') as f:
            json.dump(deposit_data, f, indent=2)
        
        print(f"📋 也保存到标准位置: {standard_file}")
        
        # 7. 显示统计信息
        print(f"\n📊 存款数据统计:")
        print(f"   成功创建: {success_count}/{len(active_keys)} 个")
        print(f"   Fork version: {fork_version}")
        print(f"   提款地址: {withdrawal_address}")
        
        # 8. 显示样本数据
        if deposit_data:
            sample = deposit_data[0]
            print(f"\n📋 样本存款数据:")
            print(f"   公钥: {sample.get('pubkey', 'N/A')[:20]}...")
            print(f"   提款凭证: {sample.get('withdrawal_credentials', 'N/A')[:20]}...")
            print(f"   金额: {sample.get('amount', 'N/A')}")
            print(f"   网络: {sample.get('network_name', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建存款数据失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def check_active_keys_status() -> Dict[str, Any]:
    """检查已激活密钥的状态"""
    print("🔍 检查已激活密钥状态...")
    
    try:
        from code.core.vault_key_manager import VaultKeyManager
        
        vault_manager = VaultKeyManager()
        active_keys = vault_manager.list_keys(status='active')
        
        status = {
            "total_active": len(active_keys),
            "keys": []
        }
        
        for key in active_keys:
            key_info = {
                "pubkey": key.pubkey,
                "batch_id": key.batch_id,
                "client_type": key.client_type,
                "status": key.status,
                "created_at": key.created_at
            }
            status["keys"].append(key_info)
        
        print(f"📊 已激活密钥统计:")
        print(f"   总数: {status['total_active']}")
        
        if status["keys"]:
            print(f"   密钥列表:")
            for i, key in enumerate(status["keys"], 1):
                print(f"     {i}. {key['pubkey'][:20]}... (批次: {key['batch_id']})")
        
        return status
        
    except Exception as e:
        print(f"❌ 检查密钥状态失败: {e}")
        return {"total_active": 0, "keys": []}

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="为已激活的密钥创建存款数据")
    parser.add_argument("--fork-version", required=True, help="Fork version (e.g., 0x10000038)")
    parser.add_argument("--count", type=int, help="使用的密钥数量（默认使用所有激活的密钥）")
    parser.add_argument("--withdrawal-address", 
                       default="0x8943545177806ED17B9F23F0a21ee5948eCaa776",
                       help="提款地址")
    parser.add_argument("--check-status", action="store_true", 
                       help="只检查已激活密钥状态，不创建存款数据")
    
    args = parser.parse_args()
    
    if args.check_status:
        status = check_active_keys_status()
        if status["total_active"] == 0:
            print("\n💡 没有已激活的密钥，请先运行:")
            print("   ./validator.sh activate-keys --count 4")
            sys.exit(1)
        else:
            print(f"\n✅ 找到 {status['total_active']} 个已激活的密钥")
            sys.exit(0)
    
    success = create_deposits_for_active_keys(
        fork_version=args.fork_version,
        count=args.count,
        withdrawal_address=args.withdrawal_address
    )
    
    if success:
        print("\n🎉 存款数据创建完成!")
        print("💡 现在可以使用: ./validator.sh submit-deposits")
    else:
        print("\n❌ 存款数据创建失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
