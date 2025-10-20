#!/usr/bin/env python3
"""
Vault Setup and Integration Script
Initializes Vault with necessary policies and configurations for validator key storage
"""

import os
import json
import time
import requests
import argparse
from typing import Dict, Any, Optional


class VaultSetup:
    def __init__(self, vault_url: str = "http://localhost:8200", vault_token: str = "dev-root-token"):
        self.vault_url = vault_url
        self.vault_token = vault_token
        self.headers = {"X-Vault-Token": vault_token}

    def wait_for_vault(self, timeout: int = 60) -> bool:
        """Wait for Vault to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.vault_url}/v1/sys/health")
                if response.status_code in [200, 429, 503]:  # 429 = standby, 503 = sealed but responsive
                    print("Vault is responsive")
                    return True
            except requests.RequestException:
                pass

            print("Waiting for Vault to start...")
            time.sleep(2)

        print("Timeout waiting for Vault")
        return False

    def initialize_vault(self) -> Dict[str, Any]:
        """Initialize Vault (only if not already initialized)"""
        try:
            # Check if already initialized
            response = requests.get(f"{self.vault_url}/v1/sys/init")
            if response.status_code == 200 and response.json().get("initialized"):
                print("Vault already initialized")
                return {"already_initialized": True}

            # Initialize Vault
            init_data = {
                "secret_shares": 1,
                "secret_threshold": 1
            }

            response = requests.post(f"{self.vault_url}/v1/sys/init", json=init_data)

            if response.status_code == 200:
                result = response.json()
                print("Vault initialized successfully")
                return result
            else:
                print(f"Failed to initialize Vault: {response.text}")
                return {}

        except requests.RequestException as e:
            print(f"Error initializing Vault: {e}")
            return {}

    def unseal_vault(self, unseal_key: str) -> bool:
        """Unseal Vault"""
        try:
            response = requests.get(f"{self.vault_url}/v1/sys/seal-status")
            if response.status_code == 200:
                status = response.json()
                if not status.get("sealed", True):
                    print("Vault already unsealed")
                    return True

            # Unseal
            unseal_data = {"key": unseal_key}
            response = requests.post(f"{self.vault_url}/v1/sys/unseal", json=unseal_data)

            if response.status_code == 200:
                result = response.json()
                if not result.get("sealed", True):
                    print("Vault unsealed successfully")
                    return True
                else:
                    print("Vault still sealed after unseal attempt")
                    return False
            else:
                print(f"Failed to unseal Vault: {response.text}")
                return False

        except requests.RequestException as e:
            print(f"Error unsealing Vault: {e}")
            return False

    def setup_kv_engine(self) -> bool:
        """Setup KV v2 secrets engine"""
        try:
            # Check if already mounted
            response = requests.get(f"{self.vault_url}/v1/sys/mounts", headers=self.headers)
            if response.status_code == 200:
                mounts = response.json()
                if "secret/" in mounts.get("data", {}):
                    print("KV engine already mounted")
                    return True

            # Enable KV v2 engine
            mount_data = {
                "type": "kv-v2",
                "description": "Validator secrets storage"
            }

            response = requests.post(
                f"{self.vault_url}/v1/sys/mounts/secret",
                headers=self.headers,
                json=mount_data
            )

            if response.status_code == 204:
                print("KV v2 engine enabled at secret/")
                return True
            else:
                print(f"Failed to enable KV engine: {response.text}")
                return False

        except requests.RequestException as e:
            print(f"Error setting up KV engine: {e}")
            return False

    def create_validator_policy(self) -> bool:
        """Create policy for validator key access"""
        policy_rules = """
# Allow full access to validator secrets
path "secret/data/validators/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/validators/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Allow listing validator keys
path "secret/metadata/validators" {
  capabilities = ["list"]
}

# Allow access to Web3Signer integration
path "secret/data/web3signer/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
"""

        try:
            policy_data = {"policy": policy_rules}
            response = requests.post(
                f"{self.vault_url}/v1/sys/policies/acl/validator-policy",
                headers=self.headers,
                json=policy_data
            )

            if response.status_code == 204:
                print("Validator policy created successfully")
                return True
            else:
                print(f"Failed to create policy: {response.text}")
                return False

        except requests.RequestException as e:
            print(f"Error creating policy: {e}")
            return False

    def setup_userpass_auth(self) -> bool:
        """Setup userpass authentication"""
        try:
            # Check if already enabled
            response = requests.get(f"{self.vault_url}/v1/sys/auth", headers=self.headers)
            if response.status_code == 200:
                auth_methods = response.json()
                if "userpass/" in auth_methods.get("data", {}):
                    print("Userpass auth already enabled")
                    return self.create_validator_user()

            # Enable userpass auth
            auth_data = {"type": "userpass"}
            response = requests.post(
                f"{self.vault_url}/v1/sys/auth/userpass",
                headers=self.headers,
                json=auth_data
            )

            if response.status_code == 204:
                print("Userpass auth enabled")
                return self.create_validator_user()
            else:
                print(f"Failed to enable userpass auth: {response.text}")
                return False

        except requests.RequestException as e:
            print(f"Error setting up userpass auth: {e}")
            return False

    def create_validator_user(self) -> bool:
        """Create validator user with appropriate policies"""
        try:
            user_data = {
                "password": "admin",
                "policies": ["validator-policy"]
            }

            response = requests.post(
                f"{self.vault_url}/v1/auth/userpass/users/admin",
                headers=self.headers,
                json=user_data
            )

            if response.status_code == 204:
                print("Validator user 'admin' created successfully")
                return True
            else:
                print(f"Failed to create user: {response.text}")
                return False

        except requests.RequestException as e:
            print(f"Error creating user: {e}")
            return False

    def test_vault_access(self) -> bool:
        """Test basic Vault operations"""
        try:
            # Test write
            test_data = {
                "data": {
                    "test_key": "test_value",
                    "timestamp": str(time.time())
                }
            }

            response = requests.post(
                f"{self.vault_url}/v1/secret/data/test",
                headers=self.headers,
                json=test_data
            )

            if response.status_code != 200:
                print(f"Failed to write test data: {response.text}")
                return False

            # Test read
            response = requests.get(
                f"{self.vault_url}/v1/secret/data/test",
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                if data["data"]["data"]["test_key"] == "test_value":
                    print("Vault read/write test successful")

                    # Clean up test data
                    requests.delete(
                        f"{self.vault_url}/v1/secret/data/test",
                        headers=self.headers
                    )
                    return True
                else:
                    print("Vault read test failed - data mismatch")
                    return False
            else:
                print(f"Failed to read test data: {response.text}")
                return False

        except requests.RequestException as e:
            print(f"Error testing Vault access: {e}")
            return False

    def full_setup(self) -> bool:
        """Run full Vault setup"""
        print("Starting Vault setup...")

        # Wait for Vault to be ready
        if not self.wait_for_vault():
            return False

        # Initialize Vault
        init_result = self.initialize_vault()
        if not init_result:
            return False

        # If we got unseal keys, unseal the vault
        if "keys" in init_result and init_result["keys"]:
            if not self.unseal_vault(init_result["keys"][0]):
                return False

        # Setup KV engine
        if not self.setup_kv_engine():
            return False

        # Create policies
        if not self.create_validator_policy():
            return False

        # Setup authentication
        if not self.setup_userpass_auth():
            return False

        # Test access
        if not self.test_vault_access():
            return False

        print("Vault setup completed successfully!")
        print(f"Vault URL: {self.vault_url}")
        print("Admin credentials: admin/admin")

        if "keys" in init_result and init_result["keys"]:
            print(f"Unseal key: {init_result['keys'][0]}")
            print(f"Root token: {init_result['root_token']}")

        return True


def main():
    parser = argparse.ArgumentParser(description="Setup Vault for validator key storage")
    parser.add_argument("--vault-url", default="http://localhost:8200", help="Vault URL")
    parser.add_argument("--vault-token", default="dev-root-token", help="Vault root token")

    args = parser.parse_args()

    vault_setup = VaultSetup(args.vault_url, args.vault_token)

    if vault_setup.full_setup():
        print("Vault is ready for validator key storage!")
    else:
        print("Vault setup failed!")
        exit(1)


if __name__ == "__main__":
    main()