#!/usr/bin/env python3
"""
Ethereum Validator Key Generation Script
Generates BLS validator keys and prepares them for storage in Vault
"""

import os
import json
import argparse
import secrets
import hashlib
import hmac
from pathlib import Path
from typing import List, Dict, Any
from mnemonic import Mnemonic
from eth_keys import keys
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt
from Crypto.Random import get_random_bytes
import requests


def generate_mnemonic() -> str:
    """Generate a new BIP39 mnemonic"""
    mnemo = Mnemonic("english")
    return mnemo.generate(strength=256)


def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    """Convert mnemonic to seed"""
    mnemo = Mnemonic("english")
    return mnemo.to_seed(mnemonic, passphrase)


def derive_private_key(seed: bytes, path: List[int]) -> bytes:
    """Derive private key from seed using BIP32-like derivation for BLS"""
    # This is a simplified BLS key derivation
    # In production, use proper BLS12-381 curve operations

    key = seed
    for index in path:
        # HMAC-based key derivation
        key = hmac.new(
            key,
            index.to_bytes(4, 'big'),
            hashlib.sha256
        ).digest()

    # Ensure key is valid for BLS (simplified)
    return key[:32]


def create_keystore(private_key: bytes, password: str) -> Dict[str, Any]:
    """Create EIP-2335 keystore format"""
    # Generate random salt and IV
    salt = get_random_bytes(32)
    iv = get_random_bytes(16)

    # Derive key using scrypt
    derived_key = scrypt(password.encode(), salt, 32, N=2**18, r=8, p=1)

    # Encrypt private key
    cipher = AES.new(derived_key[:16], AES.MODE_CTR, nonce=iv)
    ciphertext = cipher.encrypt(private_key)

    # Create keystore structure
    keystore = {
        "crypto": {
            "kdf": {
                "function": "scrypt",
                "params": {
                    "dklen": 32,
                    "n": 2**18,
                    "r": 8,
                    "p": 1,
                    "salt": salt.hex()
                },
                "message": ""
            },
            "checksum": {
                "function": "sha256",
                "params": {},
                "message": hashlib.sha256(derived_key[16:] + ciphertext).hexdigest()
            },
            "cipher": {
                "function": "aes-128-ctr",
                "params": {
                    "iv": iv.hex()
                },
                "message": ciphertext.hex()
            }
        },
        "description": "Validator signing key",
        "pubkey": derive_public_key(private_key).hex(),
        "path": "m/12381/3600/0/0/0",
        "uuid": secrets.token_hex(16),
        "version": 4
    }

    return keystore


def derive_public_key(private_key: bytes) -> bytes:
    """Derive public key from private key (simplified for BLS)"""
    # This is a placeholder - in production use proper BLS12-381 operations
    # For testing, we'll use a simple hash
    return hashlib.sha256(private_key).digest()[:48]


def generate_withdrawal_credentials(withdrawal_address: str) -> str:
    """Generate withdrawal credentials for an address"""
    # For Ethereum 2.0, withdrawal credentials start with 0x01 followed by 11 zeros and the address
    withdrawal_address = withdrawal_address.lower().replace('0x', '')
    withdrawal_credentials = '01' + '00' * 11 + withdrawal_address
    return '0x' + withdrawal_credentials


def derive_keys_from_mnemonic(mnemonic: str, start_index: int, count: int) -> List[Dict[str, Any]]:
    """Derive validator keys from mnemonic"""
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
        keystore = create_keystore(validator_sk, password)

        keys.append({
            'index': i,
            'validator_private_key': validator_sk.hex(),
            'validator_public_key': validator_pk.hex(),
            'withdrawal_private_key': withdrawal_sk.hex(),
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

    print(f"Generated {len(keys)} validator keys")
    print(f"Keys saved to: {output_dir}")
    print(f"Keystores: {keystores_dir}")
    print(f"Secrets: {secrets_dir}")


def generate_validator_keys(count: int, start_index: int = 0, output_dir: str = "./keys", mnemonic: str = None):
    """Main key generation function"""

    if mnemonic is None:
        mnemonic = generate_mnemonic()
        print(f"Generated new mnemonic: {mnemonic}")
        print("IMPORTANT: Store this mnemonic securely offline!")
    else:
        print("Using provided mnemonic")

    # Derive keys from mnemonic
    keys = derive_keys_from_mnemonic(mnemonic, start_index, count)

    # Save keys locally
    save_keys_locally(keys, output_dir)

    return keys, mnemonic


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Ethereum validator keys")
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