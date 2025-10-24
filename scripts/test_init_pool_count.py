#!/usr/bin/env python3
"""
Test script to verify init-pool count parameter works correctly
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_init_pool_count():
    """Test that init-pool respects the count parameter"""
    print("🧪 Testing init-pool count parameter...")
    
    # Test with different count values
    test_cases = [
        {"count": 5, "expected": 5},
        {"count": 10, "expected": 10},
        {"count": 50, "expected": 50},
    ]
    
    for test_case in test_cases:
        count = test_case["count"]
        expected = test_case["expected"]
        
        print(f"\n📋 Testing with count={count} (expected {expected} keys)")
        
        try:
            # Run init-pool command
            result = subprocess.run([
                'python3', 'code/core/validator_manager.py', 
                'init-pool', '--count', str(count)
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
            
            if result.returncode == 0:
                print(f"✅ Command executed successfully")
                
                # Check if the output mentions the correct count
                if f"生成 {count} 个验证者密钥" in result.stdout:
                    print(f"✅ Output shows correct count: {count}")
                else:
                    print(f"⚠️  Output doesn't show expected count message")
                    print(f"   Actual output: {result.stdout}")
                
                # Check pool status
                status_result = subprocess.run([
                    'python3', 'code/core/validator_manager.py', 
                    'pool-status'
                ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
                
                if status_result.returncode == 0:
                    print(f"📊 Pool status:")
                    print(status_result.stdout)
                else:
                    print(f"⚠️  Could not get pool status")
                
            else:
                print(f"❌ Command failed with return code {result.returncode}")
                print(f"   Error: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error running test: {e}")
    
    print("\n🎯 Test completed!")

def test_activate_keys_count():
    """Test that activate-keys respects the count parameter"""
    print("\n🧪 Testing activate-keys count parameter...")
    
    # Test with different count values
    test_cases = [
        {"count": 2, "expected": 2},
        {"count": 3, "expected": 3},
    ]
    
    for test_case in test_cases:
        count = test_case["count"]
        expected = test_case["expected"]
        
        print(f"\n📋 Testing activate-keys with count={count} (expected {expected} keys)")
        
        try:
            # Run activate-keys command
            result = subprocess.run([
                'python3', 'code/core/validator_manager.py', 
                'activate-keys', '--count', str(count)
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
            
            if result.returncode == 0:
                print(f"✅ Command executed successfully")
                print(f"📊 Output: {result.stdout}")
            else:
                print(f"❌ Command failed with return code {result.returncode}")
                print(f"   Error: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error running test: {e}")
    
    print("\n🎯 Activate keys test completed!")

def main():
    """Main test function"""
    print("🚀 Testing init-pool and activate-keys count parameters")
    print("=" * 60)
    
    # Test init-pool
    test_init_pool_count()
    
    # Test activate-keys
    test_activate_keys_count()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
