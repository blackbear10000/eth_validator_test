#!/usr/bin/env python3
"""
测试 Prysm 端口检测
根据提供的 Kurtosis 输出验证端口检测逻辑
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def test_prysm_port_detection():
    """测试 Prysm 端口检测逻辑"""
    print("🧪 测试 Prysm 端口检测逻辑")
    print("=" * 50)
    
    # 模拟 Kurtosis 输出
    mock_kurtosis_output = """
========================================== User Services ==========================================
UUID           Name                                             Ports                                          Status
354e03f6ff87   cl-1-prysm-geth                                  http: 3500/tcp -> http://127.0.0.1:33522       RUNNING
                                                                  metrics: 8080/tcp -> http://127.0.0.1:33525
                                                                  profiling: 6060/tcp -> 127.0.0.1:33524
                                                                  quic-discovery: 13000/udp -> 127.0.0.1:32953
                                                                  rpc: 4000/tcp -> 127.0.0.1:33523
                                                                  tcp-discovery: 13000/tcp -> 127.0.0.1:33526
                                                                  udp-discovery: 12000/udp -> 127.0.0.1:32952
e274d5988aca   cl-2-lighthouse-reth                             http: 4000/tcp -> http://127.0.0.1:33527       RUNNING
                                                                  metrics: 5054/tcp -> http://127.0.0.1:33528
                                                                  quic-discovery: 9001/udp -> 127.0.0.1:32955
                                                                  tcp-discovery: 9000/tcp -> 127.0.0.1:33529
                                                                  udp-discovery: 9000/udp -> 127.0.0.1:32954
"""
    
    try:
        from scripts.detect_kurtosis_ports import KurtosisPortDetector
        
        # 创建检测器
        detector = KurtosisPortDetector()
        
        # 模拟解析输出
        print("🔍 解析模拟的 Kurtosis 输出...")
        parsed_services = detector._parse_table_output(mock_kurtosis_output)
        
        print(f"📋 解析到的服务: {list(parsed_services.get('services', {}).keys())}")
        
        # 检测 Beacon 端口
        print("\n🔍 检测 Beacon 端口...")
        beacon_ports = detector.detect_beacon_ports()
        
        print(f"\n📊 检测结果:")
        for client_type, url in beacon_ports.items():
            print(f"   {client_type}: {url}")
        
        # 验证 Prysm 端口
        if 'prysm' in beacon_ports:
            prysm_port = beacon_ports['prysm']
            print(f"\n✅ Prysm gRPC 端口: {prysm_port}")
            print(f"   预期: localhost:33523")
            print(f"   实际: {prysm_port}")
            
            if "33523" in prysm_port:
                print("✅ 端口检测正确！")
                return True
            else:
                print("❌ 端口检测错误！")
                return False
        else:
            print("❌ 未找到 Prysm 端口")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """主函数"""
    print("🚀 Prysm 端口检测测试")
    print("=" * 50)
    
    success = test_prysm_port_detection()
    
    if success:
        print("\n✅ 测试通过")
    else:
        print("\n❌ 测试失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
