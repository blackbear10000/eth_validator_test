#!/usr/bin/env python3
"""
测试 gRPC 转换逻辑
验证 Lighthouse HTTP API 到 Prysm gRPC 的转换
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'code'))

def test_grpc_conversion():
    """测试 gRPC 转换逻辑"""
    print("🧪 测试 gRPC 转换逻辑")
    print("=" * 40)
    
    try:
        from code.utils.validator_client_config import ValidatorClientConfig
        
        # 创建配置生成器
        config_generator = ValidatorClientConfig()
        
        # 测试不同的 URL 格式
        test_urls = [
            "http://localhost:33527",  # Lighthouse HTTP API
            "http://localhost:3500",    # 标准 HTTP API
            "localhost:4000",          # 已经是 gRPC 格式
            "localhost:33522",         # 检测到的 Prysm gRPC
        ]
        
        for url in test_urls:
            print(f"\n🔍 测试 URL: {url}")
            grpc_url = config_generator._convert_http_to_grpc(url)
            print(f"   转换结果: {grpc_url}")
        
        # 测试配置生成
        print(f"\n🔧 测试 Prysm 配置生成...")
        mock_pubkeys = ["0x1234567890abcdef", "0xabcdef1234567890"]
        
        config_path = config_generator.generate_prysm_config(
            pubkeys=mock_pubkeys,
            beacon_node_url="http://localhost:33527",  # Lighthouse HTTP API
            output_dir="test_configs/prysm"
        )
        
        print(f"✅ 配置生成成功: {config_path}")
        
        # 检查生成的配置文件
        config_file = Path(config_path) / "validator-config.yaml"
        if config_file.exists():
            with open(config_file, 'r') as f:
                content = f.read()
                print(f"\n📋 生成的配置内容:")
                print(content)
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """主函数"""
    print("🚀 gRPC 转换测试工具")
    print("=" * 50)
    
    success = test_grpc_conversion()
    
    if success:
        print("\n✅ 测试完成")
    else:
        print("\n❌ 测试失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
