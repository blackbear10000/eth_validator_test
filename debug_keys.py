#!/usr/bin/env python3
"""
Debug script to check keys_data.json content
"""

import json
import os
from pathlib import Path

def debug_keys_data():
    """Debug keys_data.json content"""
    keys_file = Path("data/keys/keys_data.json")
    
    if not keys_file.exists():
        print("❌ keys_data.json not found")
        return
    
    print(f"🔍 Reading {keys_file}")
    
    with open(keys_file, 'r') as f:
        data = json.load(f)
    
    print(f"🔍 Keys data structure:")
    print(f"  - Type: {type(data)}")
    print(f"  - Keys: {len(data.get('keys', []))}")
    
    if 'keys' in data:
        for i, key in enumerate(data['keys']):
            print(f"  Key {i}:")
            print(f"    - index: {key.get('index')}")
            print(f"    - validator_public_key: {key.get('validator_public_key', 'N/A')[:20]}...")
            print(f"    - signing_key_path: {key.get('signing_key_path', 'N/A')}")

if __name__ == "__main__":
    debug_keys_data()
