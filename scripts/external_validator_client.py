#!/usr/bin/env python3
"""
External Validator Client Manager
Manages external validator clients that connect to Web3Signer for signing
"""

import os
import sys
import json
import time
import subprocess
import requests
import signal
from typing import List, Dict, Optional
from pathlib import Path
import threading


class ExternalValidatorClient:
    """Manages a single external validator client"""
    
    def __init__(self, client_type: str, beacon_api_url: str, web3signer_url: str, 
                 public_keys: List[str], data_dir: str):
        self.client_type = client_type  # 'lighthouse' or 'teku'
        self.beacon_api_url = beacon_api_url
        self.web3signer_url = web3signer_url
        self.public_keys = public_keys
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.process = None
        self.running = False
        
    def get_client_command(self) -> List[str]:
        """Get the command to start the validator client"""
        if self.client_type == "lighthouse":
            return self._get_lighthouse_command()
        elif self.client_type == "teku":
            return self._get_teku_command()
        else:
            raise ValueError(f"Unsupported client type: {self.client_type}")
    
    def _get_lighthouse_command(self) -> List[str]:
        """Get Lighthouse validator client command"""
        cmd = [
            "lighthouse", "validator",
            "--datadir", str(self.data_dir),
            "--beacon-nodes", self.beacon_api_url,
            "--validators-external-signer-url", self.web3signer_url,
            "--validators-external-signer-public-keys", ",".join(self.public_keys),
            "--enable-web3signer-slashing-protection",
            "--suggested-fee-recipient", "0x0000000000000000000000000000000000000001",
            "--log-level", "info"
        ]
        return cmd
    
    def _get_teku_command(self) -> List[str]:
        """Get Teku validator client command"""
        cmd = [
            "teku",
            "--data-path", str(self.data_dir),
            "--beacon-node-api-endpoint", self.beacon_api_url,
            "--validators-external-signer-url", self.web3signer_url,
            "--validators-external-signer-public-keys", ",".join(self.public_keys),
            "--validators-external-signer-slashing-protection-enabled", "true",
            "--validators-proposer-default-fee-recipient", "0x0000000000000000000000000000000000000001",
            "--logging", "INFO"
        ]
        return cmd
    
    def start(self) -> bool:
        """Start the validator client"""
        if self.running:
            print(f"Validator client {self.client_type} is already running")
            return True
        
        try:
            cmd = self.get_client_command()
            print(f"Starting {self.client_type} validator client...")
            print(f"Command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.running = True
            
            # Start output monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_output)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            # Wait a bit to check if it started successfully
            time.sleep(5)
            
            if self.process.poll() is None:
                print(f"✅ {self.client_type} validator client started successfully")
                return True
            else:
                print(f"❌ {self.client_type} validator client failed to start")
                self.running = False
                return False
                
        except Exception as e:
            print(f"❌ Error starting {self.client_type} validator client: {e}")
            self.running = False
            return False
    
    def _monitor_output(self):
        """Monitor validator client output"""
        if not self.process:
            return
            
        for line in iter(self.process.stdout.readline, ''):
            if line:
                print(f"[{self.client_type}] {line.rstrip()}")
    
    def stop(self):
        """Stop the validator client"""
        if not self.running or not self.process:
            return
        
        print(f"Stopping {self.client_type} validator client...")
        self.running = False
        
        try:
            self.process.terminate()
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print(f"Force killing {self.client_type} validator client...")
            self.process.kill()
            self.process.wait()
        
        print(f"✅ {self.client_type} validator client stopped")
    
    def is_running(self) -> bool:
        """Check if the validator client is running"""
        if not self.process:
            return False
        return self.process.poll() is None and self.running


class ExternalValidatorClientManager:
    """Manages multiple external validator clients"""
    
    def __init__(self, config_file: str = "test_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.clients: List[ExternalValidatorClient] = []
        
    def load_config(self) -> Dict:
        """Load configuration"""
        default_config = {
            "beacon_api_url": "http://localhost:5052",
            "web3signer_url": "http://localhost:9000",
            "client_type": "lighthouse",  # or "teku"
            "data_dir": "./external_validator_data"
        }
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def get_beacon_api_url(self) -> str:
        """Get the beacon API URL from Kurtosis"""
        try:
            # Try to get the beacon API URL from Kurtosis
            result = subprocess.run(
                ["kurtosis", "service", "ls", "eth-devnet"],
                capture_output=True, text=True, check=True
            )
            
            # Parse the output to find beacon API port
            lines = result.stdout.split('\n')
            for line in lines:
                if 'cl-' in line and 'lighthouse' in line:
                    # Extract port mapping
                    if '->' in line:
                        parts = line.split('->')
                        if len(parts) > 1:
                            port_part = parts[1].strip()
                            if ':' in port_part:
                                port = port_part.split(':')[1].split('/')[0]
                                return f"http://localhost:{port}"
        except subprocess.CalledProcessError:
            pass
        
        # Fallback to default
        return self.config.get("beacon_api_url", "http://localhost:5052")
    
    def get_public_keys_from_web3signer(self) -> List[str]:
        """Get public keys from Web3Signer"""
        try:
            response = requests.get(f"{self.config['web3signer_url']}/api/v1/eth2/publicKeys", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get public keys from Web3Signer: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error getting public keys from Web3Signer: {e}")
            return []
    
    def start_validator_clients(self, public_keys: List[str] = None) -> bool:
        """Start external validator clients"""
        if public_keys is None:
            public_keys = self.get_public_keys_from_web3signer()
        
        if not public_keys:
            print("❌ No public keys available for validator clients")
            return False
        
        beacon_api_url = self.get_beacon_api_url()
        client_type = self.config.get("client_type", "lighthouse")
        
        print(f"=== Starting External Validator Clients ===")
        print(f"Client type: {client_type}")
        print(f"Beacon API: {beacon_api_url}")
        print(f"Web3Signer: {self.config['web3signer_url']}")
        print(f"Public keys: {len(public_keys)}")
        
        # Create validator client
        data_dir = Path(self.config.get("data_dir", "./external_validator_data"))
        client = ExternalValidatorClient(
            client_type=client_type,
            beacon_api_url=beacon_api_url,
            web3signer_url=self.config['web3signer_url'],
            public_keys=public_keys,
            data_dir=str(data_dir)
        )
        
        success = client.start()
        if success:
            self.clients.append(client)
            print(f"✅ Started {client_type} validator client with {len(public_keys)} validators")
        else:
            print(f"❌ Failed to start {client_type} validator client")
        
        return success
    
    def stop_all_clients(self):
        """Stop all validator clients"""
        print("=== Stopping External Validator Clients ===")
        
        for client in self.clients:
            client.stop()
        
        self.clients.clear()
        print("✅ All external validator clients stopped")
    
    def check_clients_status(self) -> Dict:
        """Check status of all validator clients"""
        status = {
            "total_clients": len(self.clients),
            "running_clients": 0,
            "client_details": []
        }
        
        for i, client in enumerate(self.clients):
            is_running = client.is_running()
            if is_running:
                status["running_clients"] += 1
            
            status["client_details"].append({
                "client_id": i,
                "type": client.client_type,
                "running": is_running,
                "public_keys_count": len(client.public_keys)
            })
        
        return status
    
    def wait_for_validators_active(self, timeout: int = 300) -> bool:
        """Wait for validators to become active"""
        print(f"=== Waiting for Validators to Become Active (timeout: {timeout}s) ===")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check validator status via beacon API
                beacon_api_url = self.get_beacon_api_url()
                response = requests.get(f"{beacon_api_url}/eth/v1/beacon/states/head/validators", timeout=10)
                
                if response.status_code == 200:
                    validators_data = response.json()
                    validators = validators_data.get("data", [])
                    
                    # Count active validators
                    active_count = 0
                    for validator in validators:
                        if validator.get("status") == "active_ongoing":
                            active_count += 1
                    
                    print(f"Active validators: {active_count}/{len(validators)}")
                    
                    if active_count > 0:
                        print("✅ Validators are active!")
                        return True
                
            except Exception as e:
                print(f"⚠️ Error checking validator status: {e}")
            
            time.sleep(10)
        
        print("❌ Timeout waiting for validators to become active")
        return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="External Validator Client Manager")
    parser.add_argument("command", choices=[
        "start", "stop", "status", "wait-active"
    ], help="Command to execute")
    parser.add_argument("--config", default="test_config.json", help="Config file")
    parser.add_argument("--public-keys", nargs="+", help="Public keys to use")
    
    args = parser.parse_args()
    
    manager = ExternalValidatorClientManager(args.config)
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        print("\n⚠️ Received interrupt signal, stopping clients...")
        manager.stop_all_clients()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.command == "start":
            success = manager.start_validator_clients(args.public_keys)
            if success:
                print("✅ Validator clients started successfully")
                print("Press Ctrl+C to stop")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
            else:
                print("❌ Failed to start validator clients")
                sys.exit(1)
        
        elif args.command == "stop":
            manager.stop_all_clients()
        
        elif args.command == "status":
            status = manager.check_clients_status()
            print(json.dumps(status, indent=2))
        
        elif args.command == "wait-active":
            success = manager.wait_for_validators_active()
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n⚠️ Operation interrupted by user")
        manager.stop_all_clients()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        manager.stop_all_clients()
        sys.exit(1)
    finally:
        manager.stop_all_clients()


if __name__ == "__main__":
    main()
