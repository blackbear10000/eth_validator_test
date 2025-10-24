#!/usr/bin/env python3
"""
测试 Prysm 配置生成
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'code'))

def test_prysm_config():
    """测试 Prysm 配置生成"""
    print("🧪 测试 Prysm 配置生成...")
    
    try:
        from utils.validator_client_config import ValidatorClientConfig
        
        # 创建配置生成器
        config_generator = ValidatorClientConfig()
        
        # 测试地址转换
        test_urls = [
            "http://localhost:33522",
            "http://localhost:4000", 
            "localhost:4000",
            "localhost:33523"
        ]
        
        print("🔍 测试地址转换:")
        for url in test_urls:
            grpc_url = config_generator._convert_http_to_grpc(url)
            print(f"   {url} -> {grpc_url}")
        
        # 测试配置生成
        test_pubkeys = ["0x1234567890abcdef" * 8]
        beacon_url = "localhost:33523"  # 使用检测到的 gRPC 地址
        
        print(f"\n🔧 生成 Prysm 配置...")
        print(f"   Beacon URL: {beacon_url}")
        print(f"   验证者数量: {len(test_pubkeys)}")
        
        config_path = config_generator.generate_prysm_config(
            test_pubkeys, 
            beacon_url, 
            "test_configs/prysm"
        )
        
        print(f"✅ 配置已生成: {config_path}")
        
        # 检查生成的文件
        config_file = Path(config_path) / "validator-config.yaml"
        if config_file.exists():
            print(f"✅ 配置文件存在: {config_file}")
            
            # 读取并显示配置内容
            import yaml
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            print(f"📋 配置内容:")
            print(f"   beacon-rpc-provider: {config.get('beacon-rpc-provider')}")
            print(f"   web3signer-url: {config.get('web3signer-url')}")
            print(f"   monitoring-port: {config.get('monitoring-port')}")
            print(f"   验证者公钥数量: {len(config.get('web3signer-public-keys', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    print("🚀 Prysm 配置测试工具")
    print("=" * 40)
    
    success = test_prysm_config()
    
    if success:
        print("\n✅ 测试完成")
    else:
        print("\n❌ 测试失败")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
