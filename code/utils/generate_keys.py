#!/usr/bin/env python3
"""
Ethereum Validator Key Generation Script
Uses ethstaker-deposit-cli for official BLS12-381 key generation
"""

import os
import sys
import json
import argparse
import secrets
from pathlib import Path
from typing import List, Dict, Any

# Add ethstaker-deposit-cli to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'external', 'ethstaker-deposit-cli'))

from ethstaker_deposit.credentials import Credential
from ethstaker_deposit.settings import get_chain_setting
from ethstaker_deposit.key_handling.key_derivation.mnemonic import get_mnemonic
from ethstaker_deposit.key_handling.keystore import ScryptKeystore


def generate_mnemonic() -> str:
    """Generate a new BIP39 mnemonic using ethstaker-deposit-cli"""
    # Get the correct path to word lists
    words_path = os.path.join(os.path.dirname(__file__), '..', 'external', 'ethstaker-deposit-cli', 'ethstaker_deposit', 'key_handling', 'key_derivation', 'word_lists')
    return get_mnemonic(language='english', words_path=words_path)


def derive_keys_from_mnemonic(mnemonic: str, start_index: int, count: int, network: str = 'mainnet') -> List[Dict[str, Any]]:
    """Derive validator keys from mnemonic using ethstaker-deposit-cli Credential class"""
    chain_setting = get_chain_setting(network)
    keys = []
    
    for i in range(start_index, start_index + count):
        # Use official Credential class for proper key derivation
        credential = Credential(
            mnemonic=mnemonic,
            mnemonic_password='',
            index=i,
            amount=32000000000,  # 32 ETH in Gwei
            chain_setting=chain_setting,
            hex_withdrawal_address=None  # BLS withdrawal initially
        )
        
        keys.append({
            'index': i,
            'validator_public_key': '0x' + credential.signing_pk.hex(),  # 48 bytes
            'validator_private_key': '0x' + credential.signing_sk.to_bytes(32, 'big').hex(),
            'withdrawal_public_key': '0x' + credential.withdrawal_pk.hex(),
            'withdrawal_private_key': '0x' + credential.withdrawal_sk.to_bytes(32, 'big').hex(),
            'signing_key_path': credential.signing_key_path,
            'withdrawal_key_path': f"m/12381/3600/{i}/0"
        })
    
    return keys


def create_keystore(private_key: int, password: str, path: str = "m/12381/3600/0/0/0") -> Dict[str, Any]:
    """Create EIP-2335 keystore format using ethstaker-deposit-cli"""
    # Convert private key to bytes
    private_key_bytes = private_key.to_bytes(32, 'big')
    
    # Create a ScryptKeystore (which has proper KDF parameters)
    from ethstaker_deposit.key_handling.keystore import ScryptKeystore
    
    # Use ethstaker-deposit-cli's keystore encryption
    keystore = ScryptKeystore.encrypt(
        secret=private_key_bytes,
        password=password,
        path=path
    )
    
    # Convert to dictionary format with proper hex encoding
    def bytes_to_hex(obj):
        """Recursively convert bytes to hex strings"""
        if isinstance(obj, bytes):
            return obj.hex()
        elif isinstance(obj, dict):
            return {k: bytes_to_hex(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [bytes_to_hex(item) for item in obj]
        else:
            return obj
    
    keystore_dict = {
        "crypto": {
            "kdf": {
                "function": keystore.crypto.kdf.function,
                "params": bytes_to_hex(keystore.crypto.kdf.params),
                "message": keystore.crypto.kdf.message.hex()
            },
            "checksum": {
                "function": keystore.crypto.checksum.function,
                "params": bytes_to_hex(keystore.crypto.checksum.params),
                "message": keystore.crypto.checksum.message.hex()
            },
            "cipher": {
                "function": keystore.crypto.cipher.function,
                "params": bytes_to_hex(keystore.crypto.cipher.params),
                "message": keystore.crypto.cipher.message.hex()
            }
        },
        "description": "Validator signing key",
        "pubkey": keystore.pubkey,
        "path": keystore.path,
        "uuid": keystore.uuid,
        "version": keystore.version
    }
    
    return keystore_dict


def generate_withdrawal_credentials(withdrawal_address: str) -> str:
    """Generate withdrawal credentials for an address"""
    # For Ethereum 2.0, withdrawal credentials start with 0x01 followed by 11 zeros and the address
    withdrawal_address = withdrawal_address.lower().replace('0x', '')
    withdrawal_credentials = '01' + '00' * 11 + withdrawal_address
    return '0x' + withdrawal_credentials


def derive_keys_from_mnemonic(mnemonic: str, start_index: int, count: int) -> List[Dict[str, Any]]:
    """Derive validator keys from mnemonic using official BLS12-381"""
    seed = mnemonic_to_seed(mnemonic)

    keys = []
    for i in range(start_index, start_index + count):
        # Derive validator signing key (m/12381/3600/i/0/0)
        validator_sk = derive_private_key(seed, [12381, 3600, i, 0, 0])
        validator_pk = derive_public_key(validator_sk)

        # Derive withdrawal key (m/12381/3600/i/0)
        withdrawal_sk = derive_private_key(seed, [12381, 3600, i, 0])
        withdrawal_pk = derive_public_key(withdrawal_sk)

        # Create keystore for the validator key
        password = f"validator_{i}_password"
        keystore = create_keystore(validator_sk, password, f"m/12381/3600/{i}/0/0")

        keys.append({
            'index': i,
            'validator_private_key': hex(validator_sk),
            'validator_public_key': validator_pk.hex(),
            'withdrawal_private_key': hex(withdrawal_sk),
            'withdrawal_public_key': withdrawal_pk.hex(),
            'keystore': keystore,
            'password': password
        })

    return keys


def save_keys_locally(keys: List[Dict[str, Any]], output_dir: str, mnemonic: str, network: str = 'mainnet'):
    """Save keys to local files for backup using ethstaker-deposit-cli format"""
    os.makedirs(output_dir, exist_ok=True)

    # Save individual keystores
    keystores_dir = os.path.join(output_dir, 'keystores')
    os.makedirs(keystores_dir, exist_ok=True)

    # Save secrets for password management
    secrets_dir = os.path.join(output_dir, 'secrets')
    os.makedirs(secrets_dir, exist_ok=True)

    # Create complete keys data with mnemonic
    keys_data = {
        'mnemonic': mnemonic,
        'network': network,
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'keys': []
    }

    # Save public key index (for backward compatibility)
    pubkeys = []

    for key_data in keys:
        index = key_data['index']
        password = f'validator_{index}_password'

        # Create keystore using ethstaker-deposit-cli
        chain_setting = get_chain_setting(network)
        credential = Credential(
            mnemonic=mnemonic,
            mnemonic_password='',
            index=index,
            amount=32000000000,
            chain_setting=chain_setting,
            hex_withdrawal_address=None
        )

        # Generate keystore
        keystore = credential.signing_keystore(password)
        
        # Save keystore
        keystore_path = os.path.join(keystores_dir, f'keystore-{index:04d}.json')
        keystore.save(keystore_path)

        # Save password
        password_path = os.path.join(secrets_dir, f'password-{index:04d}.txt')
        with open(password_path, 'w') as f:
            f.write(password)

        # Add to keys_data
        keys_data['keys'].append({
            'index': index,
            'validator_public_key': key_data['validator_public_key'],
            'validator_private_key': key_data['validator_private_key'],
            'withdrawal_public_key': key_data['withdrawal_public_key'],
            'withdrawal_private_key': key_data['withdrawal_private_key'],
            'signing_key_path': key_data['signing_key_path'],
            'withdrawal_key_path': key_data['withdrawal_key_path'],
            'keystore_filename': f'keystore-{index:04d}.json',
            'password': password
        })

        # Collect public key info for backward compatibility
        pubkeys.append({
            'index': index,
            'validator_pubkey': key_data['validator_public_key'],
            'withdrawal_pubkey': key_data['withdrawal_public_key']
        })

    # Save complete keys data (primary file)
    with open(os.path.join(output_dir, 'keys_data.json'), 'w') as f:
        json.dump(keys_data, f, indent=2)

    # Save public key index (for backward compatibility)
    # Add deprecation notice
    pubkeys_with_notice = {
        "_deprecated": "This file is deprecated. Use keys_data.json instead.",
        "_migration": "All data is now in keys_data.json with mnemonic and complete key information.",
        "keys": pubkeys
    }
    with open(os.path.join(output_dir, 'pubkeys.json'), 'w') as f:
        json.dump(pubkeys_with_notice, f, indent=2)

    # Save mnemonic separately with warning
    mnemonic_path = os.path.join(output_dir, 'mnemonic.txt')
    with open(mnemonic_path, 'w') as f:
        f.write("KEEP THIS FILE SECURE - DO NOT SHARE\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Mnemonic: {mnemonic}\n")
        f.write(f"Network: {network}\n")
        f.write(f"Generated: {keys_data['timestamp']}\n")

    print(f"Generated {len(keys)} validator keys using official BLS12-381")
    print(f"Keys saved to: {output_dir}")
    print(f"Keystores: {keystores_dir}")
    print(f"Secrets: {secrets_dir}")
    print(f"Mnemonic: {mnemonic_path}")
    print("BACKUP MNEMONIC OFFLINE IMMEDIATELY!")


def generate_validator_keys(count: int, start_index: int = 0, output_dir: str = "./keys", mnemonic: str = None, network: str = 'mainnet'):
    """Main key generation function using ethstaker-deposit-cli Credential class"""

    if mnemonic is None:
        mnemonic = generate_mnemonic()
        print(f"Generated new mnemonic: {mnemonic}")
        print("IMPORTANT: Store this mnemonic securely offline!")
    else:
        print("Using provided mnemonic")

    # Derive keys from mnemonic using official BLS12-381 Credential class
    keys = derive_keys_from_mnemonic(mnemonic, start_index, count, network)

    # Save keys locally with mnemonic
    save_keys_locally(keys, output_dir, mnemonic, network)

    return keys, mnemonic


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Ethereum validator keys using ethstaker-deposit-cli")
    parser.add_argument("--count", type=int, default=10, help="Number of validator keys to generate")
    parser.add_argument("--start-index", type=int, default=0, help="Starting index for key derivation")
    parser.add_argument("--output-dir", default="./keys", help="Output directory for keys")
    parser.add_argument("--mnemonic", help="Existing mnemonic to use (if not provided, generates new one)")

    args = parser.parse_args()

    keys, mnemonic = generate_validator_keys(
        count=args.count,
        start_index=args.start_index,
        output_dir=args.output_dir,
        mnemonic=args.mnemonic,
        network='mainnet'  # Default to mainnet
    )

    print(f"\n✅ Key generation complete!")
    print(f"📁 Keys saved to: {args.output_dir}")
    print(f"🔑 Mnemonic saved to: {os.path.join(args.output_dir, 'mnemonic.txt')}")
    print("⚠️  BACKUP MNEMONIC OFFLINE IMMEDIATELY!")