#!/usr/bin/env python3
"""
测试 Kurtosis 网络集成功能
验证动态端口检测和 validator client 配置
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def test_port_detection():
    """测试端口检测功能"""
    print("🧪 测试 Kurtosis 端口检测...")
    
    try:
        from scripts.detect_kurtosis_ports import KurtosisPortDetector
        
        detector = KurtosisPortDetector()
        ports = detector.detect_all_ports()
        
        print("📊 检测结果:")
        print(json.dumps(ports, indent=2))
        
        if ports.get("beacon"):
            print("✅ Beacon API 端口检测成功")
            return True
        else:
            print("❌ 未检测到 Beacon API 端口")
            return False
            
    except Exception as e:
        print(f"❌ 端口检测测试失败: {e}")
        return False

def test_validator_client_config():
    """测试 validator client 配置生成"""
    print("\n🧪 测试 Validator Client 配置...")
    
    try:
        from scripts.start_validator_client import ValidatorClientStarter
        
        starter = ValidatorClientStarter()
        
        print("📋 检测到的 Beacon URLs:")
        for client_type, url in starter.beacon_urls.items():
            print(f"   {client_type}: {url}")
        
        # 测试配置生成（不实际启动）
        test_pubkeys = ["0x1234567890abcdef" * 8]  # 测试公钥
        
        try:
            config_path = starter.generate_client_config("prysm", test_pubkeys)
            print(f"✅ 配置生成成功: {config_path}")
            return True
        except Exception as e:
            print(f"❌ 配置生成失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Validator Client 配置测试失败: {e}")
        return False

def test_service_check():
    """测试服务状态检查"""
    print("\n🧪 测试服务状态检查...")
    
    try:
        from scripts.start_validator_client import ValidatorClientStarter
        
        starter = ValidatorClientStarter()
        services = starter.check_services()
        
        print("📊 服务状态:")
        for service, status in services.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {service}")
        
        return True
        
    except Exception as e:
        print(f"❌ 服务状态检查测试失败: {e}")
        return False

def test_config_file_handling():
    """测试配置文件处理"""
    print("\n🧪 测试配置文件处理...")
    
    try:
        from scripts.detect_kurtosis_ports import KurtosisPortDetector
        
        # 创建测试配置
        test_ports = {
            "beacon": {
                "prysm": "http://localhost:3500",
                "lighthouse": "http://localhost:5052"
            },
            "execution": {
                "geth": "http://localhost:8545"
            }
        }
        
        detector = KurtosisPortDetector()
        
        # 测试保存配置
        config_file = detector.save_port_config(test_ports, "test_kurtosis_ports.json")
        print(f"✅ 配置保存成功: {config_file}")
        
        # 测试加载配置
        loaded_ports = detector.load_port_config("test_kurtosis_ports.json")
        print(f"✅ 配置加载成功: {len(loaded_ports)} 个服务组")
        
        # 清理测试文件
        test_file = Path(project_root) / "test_kurtosis_ports.json"
        if test_file.exists():
            test_file.unlink()
            print("🧹 测试文件已清理")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置文件处理测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 测试 Kurtosis 网络集成功能")
    print("=" * 50)
    
    tests = [
        ("端口检测", test_port_detection),
        ("Validator Client 配置", test_validator_client_config),
        ("服务状态检查", test_service_check),
        ("配置文件处理", test_config_file_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 运行测试: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 通过率: {passed}/{len(results)} ({passed/len(results)*100:.1f}%)")
    
    if passed == len(results):
        print("\n🎉 所有测试通过！Kurtosis 集成功能正常")
        return True
    else:
        print(f"\n⚠️  {len(results) - passed} 个测试失败，请检查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
