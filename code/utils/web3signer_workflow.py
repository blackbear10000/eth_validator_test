#!/usr/bin/env python3
"""
Web3Signer 完整工作流
整合密钥生成、Vault 存储、Web3Signer 加载和 validator client 配置
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.validator_manager import ValidatorManager
from core.web3signer_manager import Web3SignerManager
from utils.validator_client_config import ValidatorClientConfig

class Web3SignerWorkflow:
    """Web3Signer 完整工作流"""
    
    def __init__(self):
        self.validator_manager = ValidatorManager()
        self.web3signer_manager = Web3SignerManager()
        self.client_config = ValidatorClientConfig()
    
    def full_deployment_workflow(self, count: int = 5, client_type: str = "prysm") -> bool:
        """完整的部署工作流"""
        print("🚀 Web3Signer 完整部署工作流")
        print("=" * 50)
        
        try:
            # 1. 生成密钥
            print("📋 步骤 1: 生成验证者密钥...")
            if not self.validator_manager.generate_external_keys(count):
                print("❌ 密钥生成失败")
                return False
            print("✅ 密钥生成完成")
            
            # 2. 加载密钥到 Web3Signer
            print("\n📋 步骤 2: 加载密钥到 Web3Signer...")
            if not self.web3signer_manager.load_keys_to_web3signer():
                print("❌ 密钥加载到 Web3Signer 失败")
                return False
            print("✅ 密钥加载到 Web3Signer 完成")
            
            # 3. 验证密钥加载
            print("\n📋 步骤 3: 验证密钥加载...")
            if not self.web3signer_manager.verify_keys_loaded():
                print("❌ 密钥验证失败")
                return False
            print("✅ 密钥验证通过")
            
            # 4. 生成 validator client 配置
            print(f"\n📋 步骤 4: 生成 {client_type} 配置...")
            active_keys = self.validator_manager.key_manager.list_keys(status='active')
            if not active_keys:
                print("❌ 没有找到活跃密钥")
                return False
            
            pubkeys = [key.pubkey for key in active_keys]
            
            if client_type == "prysm":
                config_path = self.client_config.generate_prysm_config(
                    pubkeys, 
                    "http://localhost:3500",  # 假设的信标节点 URL
                    "configs/prysm"
                )
            elif client_type == "lighthouse":
                config_path = self.client_config.generate_lighthouse_config(
                    pubkeys,
                    "http://localhost:3500",
                    "configs/lighthouse"
                )
            elif client_type == "teku":
                config_path = self.client_config.generate_teku_config(
                    pubkeys,
                    "http://localhost:3500",
                    "configs/teku"
                )
            else:
                print(f"❌ 不支持的客户端类型: {client_type}")
                return False
            
            print(f"✅ {client_type} 配置已生成: {config_path}")
            
            # 5. 显示启动命令
            print(f"\n📋 步骤 5: 启动 {client_type} 验证者...")
            if client_type == "prysm":
                start_script = f"{config_path}/start-validator.sh"
                print(f"运行: {start_script}")
            elif client_type == "lighthouse":
                start_script = f"{config_path}/start-validator.sh"
                print(f"运行: {start_script}")
            elif client_type == "teku":
                start_script = f"{config_path}/start-validator.sh"
                print(f"运行: {start_script}")
            
            print("\n🎉 Web3Signer 完整部署工作流完成！")
            return True
            
        except Exception as e:
            print(f"❌ 工作流执行失败: {e}")
            return False
    
    def status_check(self) -> Dict[str, Any]:
        """检查整个系统状态"""
        print("🔍 系统状态检查")
        print("=" * 30)
        
        status = {
            "vault_keys": len(self.validator_manager.key_manager.list_keys()),
            "web3signer_status": self.web3signer_manager.status(),
            "active_keys": len(self.validator_manager.key_manager.list_keys(status='active')),
            "configs_generated": []
        }
        
        # 检查生成的配置文件
        config_dirs = ["configs/prysm", "configs/lighthouse", "configs/teku"]
        for config_dir in config_dirs:
            if Path(config_dir).exists():
                status["configs_generated"].append(config_dir)
        
        print(f"📊 状态摘要:")
        print(f"   Vault 密钥: {status['vault_keys']}")
        print(f"   活跃密钥: {status['active_keys']}")
        print(f"   Web3Signer 连接: {'✅' if status['web3signer_status']['web3signer_connected'] else '❌'}")
        print(f"   Web3Signer 密钥: {len(status['web3signer_status']['loaded_keys'])}")
        print(f"   生成的配置: {', '.join(status['configs_generated']) if status['configs_generated'] else '无'}")
        
        return status
    
    def troubleshoot(self):
        """故障排除指南"""
        print("🔧 Web3Signer 故障排除指南")
        print("=" * 40)
        
        print("\n1. 检查 Web3Signer 状态:")
        print("   ./validator.sh web3signer-status")
        
        print("\n2. 检查 Vault 连接:")
        print("   curl -H 'X-Vault-Token: dev-root-token' http://localhost:8200/v1/sys/health")
        
        print("\n3. 检查密钥加载:")
        print("   ./validator.sh load-keys")
        print("   ./validator.sh verify-keys")
        
        print("\n4. 检查 Web3Signer 日志:")
        print("   docker logs web3signer")
        
        print("\n5. 重新启动 Web3Signer:")
        print("   docker restart web3signer")
        
        print("\n6. 完整重置:")
        print("   ./validator.sh clean")
        print("   ./validator.sh generate-keys --count 5")
        print("   ./validator.sh load-keys")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web3Signer 完整工作流")
    parser.add_argument("command", choices=["deploy", "status", "troubleshoot"], 
                       help="命令: deploy(部署), status(状态), troubleshoot(故障排除)")
    parser.add_argument("--count", type=int, default=5, help="密钥数量")
    parser.add_argument("--client", choices=["prysm", "lighthouse", "teku"], 
                       default="prysm", help="验证者客户端类型")
    
    args = parser.parse_args()
    
    workflow = Web3SignerWorkflow()
    
    if args.command == "deploy":
        success = workflow.full_deployment_workflow(args.count, args.client)
        if not success:
            sys.exit(1)
    
    elif args.command == "status":
        workflow.status_check()
    
    elif args.command == "troubleshoot":
        workflow.troubleshoot()


if __name__ == "__main__":
    main()
