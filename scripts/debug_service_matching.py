#!/usr/bin/env python3
"""
调试服务名称匹配
检查 Prysm 服务名称匹配逻辑
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def test_service_matching():
    """测试服务名称匹配逻辑"""
    print("🧪 测试服务名称匹配逻辑")
    print("=" * 50)
    
    # 模拟服务名称
    service_names = [
        "cl-1-prysm-geth",
        "cl-2-lighthouse-reth", 
        "el-1-geth-prysm",
        "el-2-reth-lighthouse"
    ]
    
    print("🔍 测试服务名称匹配:")
    for service_name in service_names:
        print(f"\n📋 服务名称: {service_name}")
        print(f"   小写: {service_name.lower()}")
        
        # 检查 Prysm 匹配条件
        has_prysm = 'prysm' in service_name.lower()
        has_cl = 'cl-' in service_name.lower()
        is_prysm_match = has_prysm and has_cl
        
        print(f"   包含 'prysm': {has_prysm}")
        print(f"   包含 'cl-': {has_cl}")
        print(f"   Prysm 匹配: {is_prysm_match}")
        
        if is_prysm_match:
            print("   ✅ 这是 Prysm 服务")
        else:
            print("   ❌ 不是 Prysm 服务")
        
        # 检查 Lighthouse 匹配条件
        has_lighthouse = 'lighthouse' in service_name.lower()
        is_lighthouse_match = has_lighthouse and has_cl
        
        print(f"   包含 'lighthouse': {has_lighthouse}")
        print(f"   Lighthouse 匹配: {is_lighthouse_match}")
        
        if is_lighthouse_match:
            print("   ✅ 这是 Lighthouse 服务")
        else:
            print("   ❌ 不是 Lighthouse 服务")

def main():
    """主函数"""
    print("🚀 服务名称匹配调试工具")
    print("=" * 50)
    
    test_service_matching()

if __name__ == "__main__":
    main()
