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

from ethstaker_deposit.key_handling.key_derivation.mnemonic import get_mnemonic, get_seed
from ethstaker_deposit.key_handling.key_derivation.path import mnemonic_and_path_to_key
from ethstaker_deposit.key_handling.key_derivation.tree import derive_master_SK, derive_child_SK
from ethstaker_deposit.utils.crypto import SHA256
from ethstaker_deposit.key_handling.keystore import Keystore
from py_ecc.optimized_bls12_381 import (
    G1,
    G2,
    curve_order,
    multiply,
    add,
    neg,
    pairing,
    Z1,
    Z2
)
from py_ecc.bls import G2ProofOfPossession as bls


def generate_mnemonic() -> str:
    """Generate a new BIP39 mnemonic using ethstaker-deposit-cli"""
    # Get the correct path to word lists
    words_path = os.path.join(os.path.dirname(__file__), '..', 'external', 'ethstaker-deposit-cli', 'ethstaker_deposit', 'key_handling', 'key_derivation', 'word_lists')
    return get_mnemonic(language='english', words_path=words_path)


def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    """Convert mnemonic to seed using ethstaker-deposit-cli"""
    return get_seed(mnemonic=mnemonic, password=passphrase)


def derive_private_key(seed: bytes, path: List[int]) -> int:
    """Derive private key from seed using official BLS12-381 derivation"""
    # Start with master key
    sk = derive_master_SK(seed)
    
    # Derive through the path
    for index in path:
        sk = derive_child_SK(parent_SK=sk, index=index)
    
    return sk


def derive_public_key(private_key: int) -> bytes:
    """Derive public key from private key using BLS12-381"""
    # Convert private key to public key on G1
    public_key_point = multiply(G1, private_key)
    
    # Serialize the public key (48 bytes)
    # BLS12-381 G1 point serialization: compressed format
    x = public_key_point[0]
    y = public_key_point[1]
    
    # Check if y is even or odd for compression
    # Convert field element to int for modulo operation
    y_int = int(y)
    if y_int % 2 == 0:
        prefix = 0x02
    else:
        prefix = 0x03
    
    # Serialize: 1 byte prefix + 48 bytes x coordinate
    x_int = int(x)
    return bytes([prefix]) + x_int.to_bytes(48, 'big')


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


def save_keys_locally(keys: List[Dict[str, Any]], output_dir: str):
    """Save keys to local files for backup"""
    os.makedirs(output_dir, exist_ok=True)

    # Save individual keystores
    keystores_dir = os.path.join(output_dir, 'keystores')
    os.makedirs(keystores_dir, exist_ok=True)

    # Save secrets for password management
    secrets_dir = os.path.join(output_dir, 'secrets')
    os.makedirs(secrets_dir, exist_ok=True)

    # Save public key index
    pubkeys = []

    for key_data in keys:
        index = key_data['index']

        # Save keystore
        keystore_path = os.path.join(keystores_dir, f'keystore-{index:04d}.json')
        with open(keystore_path, 'w') as f:
            json.dump(key_data['keystore'], f, indent=2)

        # Save password
        password_path = os.path.join(secrets_dir, f'password-{index:04d}.txt')
        with open(password_path, 'w') as f:
            f.write(key_data['password'])

        # Collect public key info
        pubkeys.append({
            'index': index,
            'validator_pubkey': key_data['validator_public_key'],
            'withdrawal_pubkey': key_data['withdrawal_public_key']
        })

    # Save public key index
    with open(os.path.join(output_dir, 'pubkeys.json'), 'w') as f:
        json.dump(pubkeys, f, indent=2)

    print(f"Generated {len(keys)} validator keys using official BLS12-381")
    print(f"Keys saved to: {output_dir}")
    print(f"Keystores: {keystores_dir}")
    print(f"Secrets: {secrets_dir}")


def generate_validator_keys(count: int, start_index: int = 0, output_dir: str = "./keys", mnemonic: str = None):
    """Main key generation function using ethstaker-deposit-cli"""

    if mnemonic is None:
        mnemonic = generate_mnemonic()
        print(f"Generated new mnemonic: {mnemonic}")
        print("IMPORTANT: Store this mnemonic securely offline!")
    else:
        print("Using provided mnemonic")

    # Derive keys from mnemonic using official BLS12-381
    keys = derive_keys_from_mnemonic(mnemonic, start_index, count)

    # Save keys locally
    save_keys_locally(keys, output_dir)

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
        mnemonic=args.mnemonic
    )

    # Save mnemonic securely (separate from keys)
    mnemonic_path = os.path.join(args.output_dir, 'MNEMONIC.txt')
    with open(mnemonic_path, 'w') as f:
        f.write(mnemonic)

    print(f"\nMnemonic saved to: {mnemonic_path}")
    print("BACKUP THIS MNEMONIC OFFLINE IMMEDIATELY!")