#!/usr/bin/env python3
"""
测试端口检测结果
验证端口检测是否正确工作
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def test_port_detection():
    """测试端口检测结果"""
    print("🧪 测试端口检测结果")
    print("=" * 50)
    
    try:
        from scripts.detect_kurtosis_ports import KurtosisPortDetector
        
        # 创建检测器
        detector = KurtosisPortDetector()
        
        # 检测所有端口
        print("🔍 检测所有端口...")
        ports = detector.detect_all_ports()
        
        print(f"\n📊 检测结果:")
        for category, category_ports in ports.items():
            print(f"   {category}: {category_ports}")
        
        # 检查 Beacon 端口
        beacon_ports = ports.get("beacon", {})
        print(f"\n🔍 Beacon 端口详情:")
        for client_type, url in beacon_ports.items():
            print(f"   {client_type}: {url}")
        
        # 检查 Prysm 端口
        if 'prysm' in beacon_ports:
            prysm_url = beacon_ports['prysm']
            print(f"\n✅ 找到 Prysm 端口: {prysm_url}")
            
            # 检查端口格式
            if "://" not in prysm_url and ":" in prysm_url:
                print(f"   ✅ 格式正确: gRPC 格式")
            else:
                print(f"   ❌ 格式错误: 应该是 gRPC 格式")
        else:
            print(f"\n❌ 未找到 Prysm 端口")
        
        # 保存配置
        if beacon_ports:
            detector.save_port_config(ports)
            print(f"\n💾 端口配置已保存")
        
        return 'prysm' in beacon_ports
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """主函数"""
    print("🚀 端口检测结果测试工具")
    print("=" * 50)
    
    success = test_port_detection()
    
    if success:
        print("\n✅ 端口检测正常")
    else:
        print("\n❌ 端口检测有问题")

if __name__ == "__main__":
    main()
