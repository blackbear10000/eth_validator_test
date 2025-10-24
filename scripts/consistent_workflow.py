#!/usr/bin/env python3
"""
一致的工作流程脚本
确保 activate-keys 和 create-deposits 使用相同的密钥
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'code'))

def run_consistent_workflow(count: int = 4, fork_version: str = "0x10000038", 
                          withdrawal_address: str = "0x8943545177806ED17B9F23F0a21ee5948eCaa776") -> bool:
    """运行一致的工作流程"""
    print("🚀 开始一致的工作流程...")
    print("=" * 50)
    
    try:
        from code.core.validator_manager import ExternalValidatorManager
        from code.core.vault_key_manager import VaultKeyManager
        
        # 1. 检查密钥池状态
        print("🔍 步骤 1: 检查密钥池状态...")
        manager = ExternalValidatorManager()
        pool_status = manager.get_pool_status()
        
        print(f"📊 密钥池状态:")
        print(f"   总数: {pool_status['total']}")
        print(f"   未使用: {pool_status['unused']}")
        print(f"   已激活: {pool_status['active']}")
        
        if pool_status['unused'] < count:
            print(f"❌ 可用密钥不足：需要 {count} 个，只有 {pool_status['unused']} 个")
            print("💡 请先运行: ./validator.sh init-pool --count 1000")
            return False
        
        # 2. 激活密钥
        print(f"\n🔧 步骤 2: 激活 {count} 个密钥...")
        activated_keys = manager.activate_keys_from_pool(count)
        
        if not activated_keys:
            print("❌ 密钥激活失败")
            return False
        
        print(f"✅ 成功激活 {len(activated_keys)} 个密钥")
        
        # 3. 验证激活的密钥
        print(f"\n🔍 步骤 3: 验证激活的密钥...")
        vault_manager = VaultKeyManager()
        active_keys = vault_manager.list_keys(status='active')
        
        print(f"📋 已激活密钥列表:")
        for i, key in enumerate(active_keys, 1):
            print(f"   {i}. {key.pubkey[:20]}... (批次: {key.batch_id})")
        
        # 4. 为激活的密钥创建存款数据
        print(f"\n💰 步骤 4: 为激活的密钥创建存款数据...")
        
        # 导入存款创建脚本
        sys.path.append(str(Path(__file__).parent))
        from create_deposits_for_active_keys import create_deposits_for_active_keys
        
        success = create_deposits_for_active_keys(
            fork_version=fork_version,
            count=count,
            withdrawal_address=withdrawal_address
        )
        
        if not success:
            print("❌ 存款数据创建失败")
            return False
        
        # 5. 验证 Web3Signer 同步
        print(f"\n🔗 步骤 5: 验证 Web3Signer 同步...")
        try:
            from code.core.web3signer_manager import Web3SignerManager
            web3signer_manager = Web3SignerManager()
            
            if web3signer_manager.verify_keys_loaded():
                print("✅ Web3Signer 密钥同步正常")
            else:
                print("⚠️  Web3Signer 密钥同步可能有问题")
        except Exception as e:
            print(f"⚠️  Web3Signer 验证失败: {e}")
        
        # 6. 显示最终状态
        print(f"\n📊 最终状态:")
        print(f"   激活的密钥: {len(active_keys)} 个")
        print(f"   Fork version: {fork_version}")
        print(f"   提款地址: {withdrawal_address}")
        print(f"   存款数据: data/deposits/deposit_data.json")
        
        print(f"\n🎉 一致的工作流程完成!")
        print(f"💡 下一步: ./validator.sh submit-deposits")
        
        return True
        
    except Exception as e:
        print(f"❌ 工作流程失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def check_workflow_status() -> dict:
    """检查工作流程状态"""
    print("🔍 检查工作流程状态...")
    
    try:
        from code.core.validator_manager import ExternalValidatorManager
        from code.core.vault_key_manager import VaultKeyManager
        
        # 检查密钥池状态
        manager = ExternalValidatorManager()
        pool_status = manager.get_pool_status()
        
        # 检查激活的密钥
        vault_manager = VaultKeyManager()
        active_keys = vault_manager.list_keys(status='active')
        
        # 检查存款数据
        deposits_file = Path("data/deposits/deposit_data.json")
        has_deposits = deposits_file.exists()
        
        status = {
            "pool_status": pool_status,
            "active_keys_count": len(active_keys),
            "has_deposits": has_deposits,
            "deposits_file": str(deposits_file) if has_deposits else None
        }
        
        print(f"📊 工作流程状态:")
        print(f"   密钥池总数: {pool_status['total']}")
        print(f"   未使用密钥: {pool_status['unused']}")
        print(f"   已激活密钥: {status['active_keys_count']}")
        print(f"   存款数据: {'✅' if has_deposits else '❌'}")
        
        if has_deposits:
            print(f"   存款文件: {status['deposits_file']}")
        
        return status
        
    except Exception as e:
        print(f"❌ 状态检查失败: {e}")
        return {}

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="一致的工作流程")
    parser.add_argument("--count", type=int, default=4, help="激活的密钥数量")
    parser.add_argument("--fork-version", default="0x10000038", help="Fork version")
    parser.add_argument("--withdrawal-address", 
                       default="0x8943545177806ED17B9F23F0a21ee5948eCaa776",
                       help="提款地址")
    parser.add_argument("--check-status", action="store_true", 
                       help="只检查状态，不执行工作流程")
    
    args = parser.parse_args()
    
    if args.check_status:
        status = check_workflow_status()
        sys.exit(0)
    
    success = run_consistent_workflow(
        count=args.count,
        fork_version=args.fork_version,
        withdrawal_address=args.withdrawal_address
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
