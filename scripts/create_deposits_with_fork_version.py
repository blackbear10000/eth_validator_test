#!/usr/bin/env python3
"""
Create deposits with custom fork version for Kurtosis network
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_deposits_with_custom_fork_version(fork_version: str, count: int = 5, 
                                           withdrawal_address: str = None):
    """Create deposits with custom fork version"""
    print(f"🔧 Creating deposits with fork version: {fork_version}")
    
    try:
        from code.utils.deposit_generator import DepositGenerator
        from code.core.validator_manager import ExternalValidatorManager
        
        # Create deposit generator with custom fork version
        generator = DepositGenerator(network='kurtosis', fork_version=fork_version)
        
        print(f"✅ Deposit generator created with fork version: {generator.fork_version}")
        
        # Get withdrawal address
        if not withdrawal_address:
            # Try to get from config
            try:
                manager = ExternalValidatorManager()
                withdrawal_address = manager.config.get("withdrawal_address", 
                                                      "0x0000000000000000000000000000000000000001")
            except:
                withdrawal_address = "0x0000000000000000000000000000000000000001"
        
        print(f"🎯 Using withdrawal address: {withdrawal_address}")
        
        # Generate deposits
        deposit_data = generator.generate_deposits(
            count=count,
            withdrawal_address=withdrawal_address,
            notes=f"Kurtosis deposit with fork version {fork_version}"
        )
        
        if not deposit_data:
            print("❌ No deposit data generated")
            return False
        
        # Save deposit data
        project_root = Path(__file__).parent.parent
        deposits_dir = project_root / "data" / "deposits"
        deposits_dir.mkdir(parents=True, exist_ok=True)
        
        deposit_file = deposits_dir / f"deposit_data_fork_{fork_version.replace('0x', '')}.json"
        
        with open(deposit_file, 'w') as f:
            json.dump(deposit_data, f, indent=2)
        
        print(f"✅ Deposit data saved: {deposit_file}")
        
        # Also save to standard location
        standard_file = deposits_dir / "deposit_data.json"
        with open(standard_file, 'w') as f:
            json.dump(deposit_data, f, indent=2)
        
        print(f"📋 Also saved to standard location: {standard_file}")
        
        # Show sample deposit data
        if deposit_data:
            sample = deposit_data[0]
            print(f"\\n📊 Sample deposit data:")
            print(f"   Network Name: {sample.get('network_name')}")
            print(f"   Fork Version: {sample.get('fork_version')}")
            print(f"   Withdrawal Credentials: {sample.get('withdrawal_credentials')}")
            print(f"   Amount: {sample.get('amount')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating deposits: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def detect_and_create_deposits():
    """Auto-detect fork version and create deposits"""
    print("🔍 Auto-detecting Kurtosis fork version...")
    
    try:
        from code.utils.deposit_generator import DepositGenerator
        
        # Create generator to detect fork version
        generator = DepositGenerator(network='kurtosis')
        detected_fork_version = generator.fork_version
        
        print(f"✅ Detected fork version: {detected_fork_version}")
        
        # Create deposits with detected fork version
        return create_deposits_with_custom_fork_version(detected_fork_version)
        
    except Exception as e:
        print(f"❌ Error in auto-detection: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Create deposits with custom fork version")
    parser.add_argument("--fork-version", help="Fork version (e.g., 0x10000038)")
    parser.add_argument("--count", type=int, default=5, help="Number of deposits to create")
    parser.add_argument("--withdrawal-address", help="Withdrawal address")
    parser.add_argument("--auto-detect", action="store_true", help="Auto-detect fork version")
    
    args = parser.parse_args()
    
    if args.auto_detect:
        success = detect_and_create_deposits()
    elif args.fork_version:
        success = create_deposits_with_custom_fork_version(
            fork_version=args.fork_version,
            count=args.count,
            withdrawal_address=args.withdrawal_address
        )
    else:
        print("❌ Please specify --fork-version or --auto-detect")
        print("\\nExamples:")
        print("  python3 scripts/create_deposits_with_fork_version.py --fork-version 0x10000038")
        print("  python3 scripts/create_deposits_with_fork_version.py --auto-detect")
        return False
    
    if success:
        print("\\n🎉 Deposit creation completed successfully!")
        print("💡 You can now use: ./validator.sh submit-deposits")
    else:
        print("\\n❌ Deposit creation failed")
        return False
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
