#!/usr/bin/env python3
"""
ETH Validator Testing Orchestrator
Coordinates the full validator lifecycle testing workflow
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

from key_manager import KeyManager
from deposit_manager import DepositManager
from validator_lifecycle import ValidatorLifecycleManager
from vault_setup import VaultSetup


class TestOrchestrator:
    def __init__(self, config_file: str = "test_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.running_processes = []

    def load_config(self) -> Dict[str, Any]:
        """Load test configuration"""
        default_config = {
            "vault_url": "http://localhost:8200",
            "vault_token": "dev-root-token",
            "web3signer_url": "http://localhost:9000",
            "beacon_url": "http://localhost:5052",
            "web3_url": "http://localhost:8545",
            "validator_count": 10,
            "withdrawal_address": "0x1234567890123456789012345678901234567890",
            "keys_output_dir": "./keys",
            "deposit_file": "deposit_data.json",
            "timeout_activation": 1800,  # 30 minutes
            "timeout_exit": 1800,        # 30 minutes
            "timeout_withdrawal": 3600,   # 1 hour
            "monitoring_duration": 600,   # 10 minutes
        }

        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def save_config(self):
        """Save current configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def run_command(self, cmd: List[str], cwd: str = None, background: bool = False) -> subprocess.Popen:
        """Run a command with proper logging"""
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
        """Start Vault, Consul, Web3Signer, and Kurtosis"""
        print("=== Phase 1: Starting Infrastructure ===")

        # Start remote signing stack
        print("Starting Vault + Consul + Web3Signer...")
        self.run_command(["docker-compose", "up", "-d"], cwd="..")

        # Wait for services to be ready
        print("Waiting for services to start...")
        time.sleep(30)

        # Setup Vault
        print("Setting up Vault...")
        vault_setup = VaultSetup(self.config["vault_url"], self.config["vault_token"])
        if not vault_setup.full_setup():
            raise RuntimeError("Vault setup failed")

        # Start Kurtosis devnet
        print("Starting Kurtosis devnet...")
        self.run_command([
            "kurtosis", "run",
            "github.com/ethpandaops/ethereum-package",
            "--args-file", "../kurtosis/kurtosis-config.yaml",
            "--enclave", "eth-devnet"
        ])

        print("Infrastructure started successfully!")

    def generate_and_store_keys(self):
        """Generate validator keys and store in Vault"""
        print("=== Phase 2: Key Generation and Storage ===")

        # Generate keys
        print(f"Generating {self.config['validator_count']} validator keys...")
        self.run_command([
            "python3", "generate_keys.py",
            "--count", str(self.config["validator_count"]),
            "--output-dir", self.config["keys_output_dir"]
        ])

        # Store keys in Vault
        print("Importing keys to Vault...")
        key_manager = KeyManager(self.config["vault_url"], self.config["vault_token"])
        imported_count = key_manager.bulk_import_keys(self.config["keys_output_dir"])
        print(f"Imported {imported_count} keys to Vault")

        # Export keys for Web3Signer
        print("Exporting keys for Web3Signer...")
        exported_count = key_manager.export_keys_for_web3signer("../web3signer/keys")
        print(f"Exported {exported_count} keys for Web3Signer")

        print("Key generation and storage completed!")

    def create_and_submit_deposits(self):
        """Generate deposit data and submit deposits"""
        print("=== Phase 3: Deposit Creation and Submission ===")

        # Generate deposit data
        print("Generating deposit data...")
        key_manager = KeyManager(self.config["vault_url"], self.config["vault_token"])
        deposit_manager = DepositManager(self.config["web3_url"])

        # Try to load mnemonic if available
        mnemonic = None
        mnemonic_file = os.path.join(self.config["keys_output_dir"], "MNEMONIC.txt")
        if os.path.exists(mnemonic_file):
            with open(mnemonic_file, 'r') as f:
                mnemonic = f.read().strip()
                print("Using existing mnemonic for deposit data generation")

        deposit_data = deposit_manager.generate_batch_deposit_data(
            withdrawal_address=self.config["withdrawal_address"],
            validator_count=self.config["validator_count"],
            vault_manager=key_manager,
            output_file=self.config["deposit_file"],
            use_mnemonic=mnemonic
        )

        # For testing, we'll simulate deposit submission
        # In production, you would deploy and use the batch deposit contract
        print("Simulating deposit submission...")
        print(f"Would submit {len(deposit_data)} deposits to batch contract")

        print("Deposit creation completed!")

    def wait_for_validator_activation(self):
        """Wait for validators to become active"""
        print("=== Phase 4: Validator Activation ===")

        # Get validator pubkeys from deposit data
        with open(self.config["deposit_file"], 'r') as f:
            deposit_data = json.load(f)

        pubkeys = [d["pubkey"] for d in deposit_data]

        # Wait for activation
        lifecycle_manager = ValidatorLifecycleManager(
            self.config["beacon_url"],
            self.config["web3_url"]
        )

        print(f"Waiting for {len(pubkeys)} validators to activate...")
        results = lifecycle_manager.wait_for_activation(
            pubkeys,
            timeout=self.config["timeout_activation"]
        )

        active_count = sum(1 for status in results.values()
                          if status.value == "active_ongoing")

        print(f"Activation completed: {active_count}/{len(pubkeys)} validators active")

        if active_count == 0:
            print("WARNING: No validators activated. Check devnet and deposit process.")

        return pubkeys

    def monitor_validators(self, pubkeys: List[str]):
        """Monitor validator performance"""
        print("=== Phase 5: Validator Monitoring ===")

        lifecycle_manager = ValidatorLifecycleManager(
            self.config["beacon_url"],
            self.config["web3_url"]
        )

        print(f"Monitoring {len(pubkeys)} validators for {self.config['monitoring_duration']}s...")
        history = lifecycle_manager.monitor_validators(
            pubkeys,
            duration=self.config["monitoring_duration"],
            check_interval=30
        )

        print("Monitoring completed!")
        return history

    def test_voluntary_exit(self, pubkeys: List[str]):
        """Test voluntary exit process"""
        print("=== Phase 6: Voluntary Exit Testing ===")

        if not pubkeys:
            print("No validators to exit")
            return

        lifecycle_manager = ValidatorLifecycleManager(
            self.config["beacon_url"],
            self.config["web3_url"]
        )

        # Exit first validator as test
        test_pubkey = pubkeys[0]

        print(f"Submitting voluntary exit for validator {test_pubkey[:12]}...")
        success = lifecycle_manager.submit_voluntary_exit(
            test_pubkey,
            self.config["web3signer_url"]
        )

        if success:
            print("Waiting for validator to exit...")
            results = lifecycle_manager.wait_for_exit(
                [test_pubkey],
                timeout=self.config["timeout_exit"]
            )

            if results.get(test_pubkey, "").value in ["exited_unslashed", "exited_slashed"]:
                print("✓ Voluntary exit completed successfully!")
            else:
                print("⚠ Voluntary exit may not have completed in time")
        else:
            print("❌ Failed to submit voluntary exit")

    def test_withdrawal(self, pubkeys: List[str]):
        """Test withdrawal process"""
        print("=== Phase 7: Withdrawal Testing ===")

        # Filter for exited validators
        lifecycle_manager = ValidatorLifecycleManager(
            self.config["beacon_url"],
            self.config["web3_url"]
        )

        exited_pubkeys = []
        for pubkey in pubkeys:
            validator_info = lifecycle_manager.get_validator_info(pubkey)
            if validator_info and validator_info.status.value.startswith("exited"):
                exited_pubkeys.append(pubkey)

        if not exited_pubkeys:
            print("No exited validators to test withdrawal")
            return

        print(f"Waiting for withdrawal of {len(exited_pubkeys)} exited validators...")
        results = lifecycle_manager.wait_for_withdrawal(
            exited_pubkeys,
            timeout=self.config["timeout_withdrawal"]
        )

        completed_count = sum(1 for status in results.values()
                            if status.value == "withdrawal_done")

        print(f"Withdrawal testing completed: {completed_count}/{len(exited_pubkeys)} withdrawals completed")

    def generate_test_report(self, pubkeys: List[str]):
        """Generate final test report"""
        print("=== Phase 8: Test Report Generation ===")

        lifecycle_manager = ValidatorLifecycleManager(
            self.config["beacon_url"],
            self.config["web3_url"]
        )

        report = {
            "test_config": self.config,
            "timestamp": time.time(),
            "validators": {}
        }

        for pubkey in pubkeys:
            validator_info = lifecycle_manager.get_validator_info(pubkey)
            if validator_info:
                report["validators"][pubkey] = {
                    "index": validator_info.index,
                    "status": validator_info.status.value,
                    "effective_balance_eth": validator_info.effective_balance / 10**9,
                    "slashed": validator_info.slashed,
                    "activation_epoch": validator_info.activation_epoch,
                    "exit_epoch": validator_info.exit_epoch,
                }

        # Save report
        report_file = f"test_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Test report saved to: {report_file}")

        # Summary
        total_validators = len(pubkeys)
        active_validators = sum(1 for v in report["validators"].values()
                             if v["status"] == "active_ongoing")
        exited_validators = sum(1 for v in report["validators"].values()
                             if v["status"].startswith("exited"))

        print("\n=== TEST SUMMARY ===")
        print(f"Total validators: {total_validators}")
        print(f"Active validators: {active_validators}")
        print(f"Exited validators: {exited_validators}")
        print(f"Test report: {report_file}")

    def run_full_test(self):
        """Run the complete validator lifecycle test"""
        try:
            print("Starting ETH Validator Lifecycle Test")
            print("====================================")

            # Phase 1: Infrastructure
            self.start_infrastructure()

            # Phase 2: Key Management
            self.generate_and_store_keys()

            # Phase 3: Deposits
            self.create_and_submit_deposits()

            # Phase 4: Activation
            pubkeys = self.wait_for_validator_activation()

            # Phase 5: Monitoring
            self.monitor_validators(pubkeys)

            # Phase 6: Voluntary Exit
            self.test_voluntary_exit(pubkeys)

            # Phase 7: Withdrawal
            self.test_withdrawal(pubkeys)

            # Phase 8: Report
            self.generate_test_report(pubkeys)

            print("\n✓ ETH Validator Lifecycle Test Completed Successfully!")

        except KeyboardInterrupt:
            print("\nTest interrupted by user")
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            raise
        finally:
            self.cleanup_processes()

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
            self.run_command(["docker-compose", "down", "-v"], cwd="..")
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


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down...")
    if hasattr(signal_handler, 'orchestrator'):
        signal_handler.orchestrator.cleanup_all()
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="ETH Validator Testing Orchestrator")
    parser.add_argument("--config", default="test_config.json", help="Configuration file")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Full test command
    subparsers.add_parser("full-test", help="Run complete validator lifecycle test")

    # Individual phase commands
    subparsers.add_parser("start-infra", help="Start infrastructure only")
    subparsers.add_parser("generate-keys", help="Generate and store keys only")
    subparsers.add_parser("create-deposits", help="Create deposits only")
    subparsers.add_parser("wait-activation", help="Wait for activation only")
    subparsers.add_parser("monitor", help="Monitor validators only")
    subparsers.add_parser("test-exit", help="Test voluntary exit only")
    subparsers.add_parser("test-withdrawal", help="Test withdrawal only")
    subparsers.add_parser("generate-report", help="Generate report only")

    # Cleanup command
    subparsers.add_parser("cleanup", help="Clean up all services")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Setup signal handlers
    orchestrator = TestOrchestrator(args.config)
    signal_handler.orchestrator = orchestrator
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if args.command == "full-test":
            orchestrator.run_full_test()

        elif args.command == "start-infra":
            orchestrator.start_infrastructure()

        elif args.command == "generate-keys":
            orchestrator.generate_and_store_keys()

        elif args.command == "create-deposits":
            orchestrator.create_and_submit_deposits()

        elif args.command == "wait-activation":
            orchestrator.wait_for_validator_activation()

        elif args.command == "monitor":
            with open(orchestrator.config["deposit_file"], 'r') as f:
                deposit_data = json.load(f)
            pubkeys = [d["pubkey"] for d in deposit_data]
            orchestrator.monitor_validators(pubkeys)

        elif args.command == "test-exit":
            with open(orchestrator.config["deposit_file"], 'r') as f:
                deposit_data = json.load(f)
            pubkeys = [d["pubkey"] for d in deposit_data]
            orchestrator.test_voluntary_exit(pubkeys)

        elif args.command == "test-withdrawal":
            with open(orchestrator.config["deposit_file"], 'r') as f:
                deposit_data = json.load(f)
            pubkeys = [d["pubkey"] for d in deposit_data]
            orchestrator.test_withdrawal(pubkeys)

        elif args.command == "generate-report":
            with open(orchestrator.config["deposit_file"], 'r') as f:
                deposit_data = json.load(f)
            pubkeys = [d["pubkey"] for d in deposit_data]
            orchestrator.generate_test_report(pubkeys)

        elif args.command == "cleanup":
            orchestrator.cleanup_all()

    except Exception as e:
        print(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()