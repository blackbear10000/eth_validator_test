#!/usr/bin/env python3
"""
ETH Validator Testing Orchestrator
Coordinates infrastructure setup and basic testing workflow
External validator management is handled by external_validator_manager.py
"""

import os
import sys
import json
import time
import argparse
import subprocess
import signal
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add scripts directory to path
sys.path.append(os.path.dirname(__file__))

from vault_setup import VaultSetup


class TestOrchestrator:
    def __init__(self, config_file: str = "config/config.json"):
        self.config_file = config_file
        self.running_processes = []
        
        # Determine the project root directory first
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(script_dir) == "scripts":
            # If running from scripts directory, go up two levels to project root
            self.project_root = os.path.dirname(os.path.dirname(script_dir))
        else:
            # If running from project root, use current directory
            self.project_root = os.getcwd()
        
        # Ensure we have the correct project root by checking for key files
        if not os.path.exists(os.path.join(self.project_root, "infra", "docker-compose.yml")):
            # If we can't find docker-compose.yml, try to find it relative to the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if os.path.basename(script_dir) == "scripts":
                # Go up two levels from scripts to project root
                self.project_root = os.path.dirname(os.path.dirname(script_dir))
            else:
                # Go up one level from infra to project root
                self.project_root = os.path.dirname(script_dir)
        
        # Now load config after project_root is set
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load test configuration"""
        default_config = {
            "vault_url": "http://localhost:8200",
            "vault_token": "dev-root-token",
            "web3signer_url": "http://localhost:9000",
            "beacon_url": "http://localhost:5052",
            "web3_url": "http://localhost:8545",
        }

        # Use absolute path for config file
        config_path = os.path.join(self.project_root, self.config_file)
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def save_config(self):
        """Save current configuration"""
        config_path = os.path.join(self.project_root, self.config_file)
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def run_command(self, cmd: List[str], cwd: str = None, background: bool = False):
        """Run a command and handle output"""
        print(f"Running: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            cwd=cwd
        )

        if background:
            self.running_processes.append(process)
            return process

        # Wait for completion and stream output
        for line in iter(process.stdout.readline, ''):
            print(f"  {line.rstrip()}")

        process.wait()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)

        return process

    def cleanup_processes(self):
        """Clean up background processes"""
        for process in self.running_processes:
            if process.poll() is None:
                print(f"Terminating process {process.pid}")
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    process.kill()

    def start_infrastructure(self):
        """Start Vault, Consul, Web3Signer, and Kurtosis devnet"""
        print("=== Phase 1: Starting Infrastructure ===")

        # Start remote signing stack (Vault + Consul + Web3Signer)
        print("Starting Vault + Consul + Web3Signer...")
        self.run_command(["docker-compose", "up", "-d"], cwd=os.path.join(self.project_root, "infra"))

        # Wait for services to be ready
        print("Waiting for services to start...")
        time.sleep(30)

        # Setup Vault
        print("Setting up Vault...")
        vault_setup = VaultSetup(self.config["vault_url"], self.config["vault_token"])
        if not vault_setup.full_setup():
            raise RuntimeError("Vault setup failed")

        # Start Kurtosis devnet (with built-in validators)
        print("Starting Kurtosis devnet with built-in validators...")
        self.run_command([
            "kurtosis", "run",
            "github.com/ethpandaops/ethereum-package",
            "--args-file", os.path.join(self.project_root, "infra", "kurtosis", "kurtosis-config.yaml"),
            "--enclave", "eth-devnet"
        ])

        print("✅ Infrastructure started successfully!")
        print("📝 Note: Kurtosis devnet uses built-in validators")
        print("📝 Use external_validator_manager.py for additional Web3Signer validators")

    def check_infrastructure_status(self):
        """Check status of infrastructure services"""
        print("=== Infrastructure Status Check ===")
        
        # Check Docker services
        print("Checking Docker services...")
        self.run_command(["docker-compose", "ps"], cwd=os.path.join(self.project_root, "infra"))
        
        # Check Kurtosis enclaves
        print("Checking Kurtosis enclaves...")
        self.run_command(["kurtosis", "enclave", "ls"])
        
        # Check service health
        print("Checking service health...")
        try:
            import requests
            
            # Check Vault
            response = requests.get(f"{self.config['vault_url']}/v1/sys/health", timeout=5)
            if response.status_code in [200, 429]:
                print("✅ Vault is healthy")
            else:
                print("❌ Vault is not healthy")
            
            # Check Web3Signer
            response = requests.get(f"{self.config['web3signer_url']}/upcheck", timeout=5)
            if response.status_code == 200:
                print("✅ Web3Signer is healthy")
            else:
                print("❌ Web3Signer is not healthy")
                
        except Exception as e:
            print(f"⚠️ Could not check service health: {e}")
        
        print("Infrastructure status check completed!")

    def cleanup_all(self):
        """Clean up all test infrastructure"""
        print("=== Cleanup: Stopping All Services ===")

        # Stop Kurtosis enclaves
        try:
            self.run_command(["kurtosis", "enclave", "stop", "eth-devnet"])
            self.run_command(["kurtosis", "enclave", "rm", "eth-devnet"])
        except subprocess.CalledProcessError:
            print("Kurtosis enclave cleanup may have failed")

        # Stop Docker services
        try:
            self.run_command(["docker-compose", "down", "-v"], cwd=os.path.join(self.project_root, "infra"))
        except subprocess.CalledProcessError:
            print("Docker cleanup may have failed")

        # Clean up all Kurtosis system containers (using generic filters)
        try:
            print("Cleaning up Kurtosis system containers...")
            # Stop all containers with "kurtosis" in the name
            self.run_command(["bash", "-c", "docker stop $(docker ps -a --filter name=kurtosis --format '{{.Names}}') 2>/dev/null || true"])
            # Remove all containers with "kurtosis" in the name
            self.run_command(["bash", "-c", "docker rm $(docker ps -a --filter name=kurtosis --format '{{.Names}}') 2>/dev/null || true"])
        except subprocess.CalledProcessError:
            print("Kurtosis system container cleanup may have failed")

        # Cleanup processes
        self.cleanup_processes()

        print("Cleanup completed!")

    def show_help(self):
        """Show help information"""
        print("=== ETH Validator Testing Orchestrator ===")
        print()
        print("Available commands:")
        print("  start-infra     - Start infrastructure (Vault, Web3Signer, Kurtosis)")
        print("  status          - Check infrastructure status")
        print("  cleanup         - Stop all services and cleanup")
        print("  help            - Show this help")
        print()
        print("For external validator management, use:")
        print("  python3 external_validator_manager.py --help")
        print()
        print("Example workflow:")
        print("  1. python3 orchestrate.py start-infra")
        print("  2. python3 external_validator_manager.py full-test")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="ETH Validator Testing Orchestrator")
    parser.add_argument("command", choices=[
        "start-infra", "status", "cleanup", "help"
    ], help="Command to execute")
    parser.add_argument("--config", default="config/config.json", help="Config file")
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = TestOrchestrator(args.config)
    
    # Setup signal handlers for cleanup
    def signal_handler(signum, frame):
        print("\n⚠️ Received interrupt signal, cleaning up...")
        orchestrator.cleanup_all()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.command == "start-infra":
            orchestrator.start_infrastructure()
        
        elif args.command == "status":
            orchestrator.check_infrastructure_status()
        
        elif args.command == "cleanup":
            orchestrator.cleanup_all()
        
        elif args.command == "help":
            orchestrator.show_help()
        
        else:
            print(f"Unknown command: {args.command}")
            orchestrator.show_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️ Operation interrupted by user")
        orchestrator.cleanup_all()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()