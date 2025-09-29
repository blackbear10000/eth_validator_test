#!/usr/bin/env python3
"""
Validator Lifecycle Management
Handles validator activation, monitoring, voluntary exit, and withdrawal
"""

import os
import json
import time
import argparse
import requests
from typing import List, Dict, Any, Optional
from web3 import Web3
from dataclasses import dataclass
from enum import Enum


class ValidatorStatus(Enum):
    UNKNOWN = "unknown"
    PENDING_INITIALIZED = "pending_initialized"
    PENDING_QUEUED = "pending_queued"
    ACTIVE_ONGOING = "active_ongoing"
    ACTIVE_EXITING = "active_exiting"
    ACTIVE_SLASHED = "active_slashed"
    EXITED_UNSLASHED = "exited_unslashed"
    EXITED_SLASHED = "exited_slashed"
    WITHDRAWAL_POSSIBLE = "withdrawal_possible"
    WITHDRAWAL_DONE = "withdrawal_done"


@dataclass
class ValidatorInfo:
    index: int
    pubkey: str
    withdrawal_credentials: str
    effective_balance: int
    slashed: bool
    activation_eligibility_epoch: int
    activation_epoch: int
    exit_epoch: int
    withdrawable_epoch: int
    status: ValidatorStatus


class ValidatorLifecycleManager:
    def __init__(self, beacon_url: str = "http://localhost:5052", web3_url: str = "http://localhost:8545"):
        self.beacon_url = beacon_url.rstrip('/')
        self.web3 = Web3(Web3.HTTPProvider(web3_url)) if web3_url else None
        self.session = requests.Session()

    def get_validator_info(self, validator_id: str) -> Optional[ValidatorInfo]:
        """Get validator information from beacon node"""
        try:
            response = self.session.get(f"{self.beacon_url}/eth/v1/beacon/states/head/validators/{validator_id}")

            if response.status_code == 200:
                data = response.json()["data"]

                return ValidatorInfo(
                    index=int(data["index"]),
                    pubkey=data["validator"]["pubkey"],
                    withdrawal_credentials=data["validator"]["withdrawal_credentials"],
                    effective_balance=int(data["validator"]["effective_balance"]),
                    slashed=data["validator"]["slashed"],
                    activation_eligibility_epoch=int(data["validator"]["activation_eligibility_epoch"]),
                    activation_epoch=int(data["validator"]["activation_epoch"]),
                    exit_epoch=int(data["validator"]["exit_epoch"]),
                    withdrawable_epoch=int(data["validator"]["withdrawable_epoch"]),
                    status=ValidatorStatus(data["status"])
                )
            elif response.status_code == 404:
                print(f"Validator {validator_id} not found")
                return None
            else:
                print(f"Error getting validator info: {response.status_code} - {response.text}")
                return None

        except requests.RequestException as e:
            print(f"Network error getting validator info: {e}")
            return None

    def get_current_epoch(self) -> Optional[int]:
        """Get current epoch from beacon node"""
        try:
            response = self.session.get(f"{self.beacon_url}/eth/v1/beacon/states/head/finality_checkpoints")
            if response.status_code == 200:
                data = response.json()["data"]
                return int(data["current_justified"]["epoch"])
            else:
                print(f"Error getting current epoch: {response.status_code}")
                return None
        except requests.RequestException as e:
            print(f"Network error getting current epoch: {e}")
            return None

    def wait_for_activation(self, validator_pubkeys: List[str], timeout: int = 3600,
                           check_interval: int = 30) -> Dict[str, ValidatorStatus]:
        """Wait for validators to become active"""
        print(f"Waiting for {len(validator_pubkeys)} validators to activate...")

        start_time = time.time()
        results = {}

        while time.time() - start_time < timeout:
            all_active = True

            for pubkey in validator_pubkeys:
                if pubkey in results and results[pubkey] == ValidatorStatus.ACTIVE_ONGOING:
                    continue

                validator_info = self.get_validator_info(pubkey)
                if validator_info:
                    results[pubkey] = validator_info.status

                    if validator_info.status == ValidatorStatus.ACTIVE_ONGOING:
                        print(f"✓ Validator {pubkey[:12]}... is now ACTIVE")
                    else:
                        print(f"⏳ Validator {pubkey[:12]}... status: {validator_info.status.value}")
                        all_active = False
                else:
                    print(f"❌ Cannot find validator {pubkey[:12]}...")
                    all_active = False

            if all_active:
                print("All validators are now active!")
                return results

            print(f"Waiting {check_interval}s before next check...")
            time.sleep(check_interval)

        print(f"Timeout waiting for validators to activate after {timeout}s")
        return results

    def submit_voluntary_exit(self, validator_pubkey: str, web3signer_url: str = "http://localhost:9000") -> bool:
        """Submit voluntary exit for a validator"""
        # Get validator info
        validator_info = self.get_validator_info(validator_pubkey)
        if not validator_info:
            print(f"Cannot find validator {validator_pubkey}")
            return False

        if validator_info.status not in [ValidatorStatus.ACTIVE_ONGOING]:
            print(f"Validator {validator_pubkey} is not active (status: {validator_info.status.value})")
            return False

        # Get current epoch
        current_epoch = self.get_current_epoch()
        if current_epoch is None:
            print("Cannot determine current epoch")
            return False

        # Create voluntary exit message
        exit_message = {
            "epoch": str(current_epoch),
            "validator_index": str(validator_info.index)
        }

        try:
            # Get signature from Web3Signer
            sign_response = self.session.post(
                f"{web3signer_url}/api/v1/eth2/sign/{validator_pubkey}",
                json={
                    "type": "VOLUNTARY_EXIT",
                    "voluntary_exit": exit_message
                }
            )

            if sign_response.status_code != 200:
                print(f"Failed to sign voluntary exit: {sign_response.text}")
                return False

            signature = sign_response.json()["signature"]

            # Submit signed voluntary exit to beacon node
            voluntary_exit = {
                "message": exit_message,
                "signature": signature
            }

            submit_response = self.session.post(
                f"{self.beacon_url}/eth/v1/beacon/pool/voluntary_exits",
                json=voluntary_exit
            )

            if submit_response.status_code == 200:
                print(f"✓ Voluntary exit submitted for validator {validator_pubkey[:12]}...")
                return True
            else:
                print(f"Failed to submit voluntary exit: {submit_response.text}")
                return False

        except requests.RequestException as e:
            print(f"Network error submitting voluntary exit: {e}")
            return False

    def wait_for_exit(self, validator_pubkeys: List[str], timeout: int = 3600,
                     check_interval: int = 60) -> Dict[str, ValidatorStatus]:
        """Wait for validators to exit"""
        print(f"Waiting for {len(validator_pubkeys)} validators to exit...")

        start_time = time.time()
        results = {}

        while time.time() - start_time < timeout:
            all_exited = True

            for pubkey in validator_pubkeys:
                if pubkey in results and results[pubkey] in [ValidatorStatus.EXITED_UNSLASHED, ValidatorStatus.EXITED_SLASHED]:
                    continue

                validator_info = self.get_validator_info(pubkey)
                if validator_info:
                    results[pubkey] = validator_info.status

                    if validator_info.status in [ValidatorStatus.EXITED_UNSLASHED, ValidatorStatus.EXITED_SLASHED]:
                        print(f"✓ Validator {pubkey[:12]}... has EXITED")
                    elif validator_info.status == ValidatorStatus.ACTIVE_EXITING:
                        print(f"⏳ Validator {pubkey[:12]}... is EXITING")
                        all_exited = False
                    else:
                        print(f"⏳ Validator {pubkey[:12]}... status: {validator_info.status.value}")
                        all_exited = False
                else:
                    print(f"❌ Cannot find validator {pubkey[:12]}...")
                    all_exited = False

            if all_exited:
                print("All validators have exited!")
                return results

            print(f"Waiting {check_interval}s before next check...")
            time.sleep(check_interval)

        print(f"Timeout waiting for validators to exit after {timeout}s")
        return results

    def wait_for_withdrawal(self, validator_pubkeys: List[str], timeout: int = 3600,
                           check_interval: int = 60) -> Dict[str, ValidatorStatus]:
        """Wait for validators to be withdrawable"""
        print(f"Waiting for {len(validator_pubkeys)} validators to be withdrawable...")

        start_time = time.time()
        results = {}

        while time.time() - start_time < timeout:
            all_withdrawable = True

            for pubkey in validator_pubkeys:
                if pubkey in results and results[pubkey] == ValidatorStatus.WITHDRAWAL_DONE:
                    continue

                validator_info = self.get_validator_info(pubkey)
                if validator_info:
                    results[pubkey] = validator_info.status

                    if validator_info.status == ValidatorStatus.WITHDRAWAL_DONE:
                        print(f"✓ Validator {pubkey[:12]}... withdrawal COMPLETED")
                    elif validator_info.status == ValidatorStatus.WITHDRAWAL_POSSIBLE:
                        print(f"⏳ Validator {pubkey[:12]}... withdrawal POSSIBLE")
                        all_withdrawable = False
                    else:
                        print(f"⏳ Validator {pubkey[:12]}... status: {validator_info.status.value}")
                        all_withdrawable = False
                else:
                    print(f"❌ Cannot find validator {pubkey[:12]}...")
                    all_withdrawable = False

            if all_withdrawable:
                print("All validators have completed withdrawal!")
                return results

            print(f"Waiting {check_interval}s before next check...")
            time.sleep(check_interval)

        print(f"Timeout waiting for withdrawals after {timeout}s")
        return results

    def monitor_validators(self, validator_pubkeys: List[str], duration: int = 3600,
                          check_interval: int = 60) -> Dict[str, List[ValidatorInfo]]:
        """Monitor validators over time"""
        print(f"Monitoring {len(validator_pubkeys)} validators for {duration}s...")

        history = {pubkey: [] for pubkey in validator_pubkeys}
        start_time = time.time()

        while time.time() - start_time < duration:
            current_time = time.time()

            for pubkey in validator_pubkeys:
                validator_info = self.get_validator_info(pubkey)
                if validator_info:
                    history[pubkey].append(validator_info)
                    print(f"[{int(current_time - start_time):4d}s] {pubkey[:12]}... - "
                          f"Status: {validator_info.status.value}, "
                          f"Balance: {validator_info.effective_balance / 10**9:.2f} ETH")

            print(f"Next check in {check_interval}s...")
            time.sleep(check_interval)

        return history

    def get_validator_performance(self, validator_index: int, epochs: int = 100) -> Dict[str, Any]:
        """Get validator performance metrics"""
        try:
            response = self.session.get(
                f"{self.beacon_url}/eth/v1/beacon/states/head/validator_balances",
                params={"id": str(validator_index)}
            )

            if response.status_code == 200:
                balance_data = response.json()["data"][0]
                current_balance = int(balance_data["balance"])

                # Calculate rewards/penalties (simplified)
                initial_balance = 32 * 10**9  # 32 ETH in Gwei
                net_reward = current_balance - initial_balance

                return {
                    "validator_index": validator_index,
                    "current_balance_gwei": current_balance,
                    "current_balance_eth": current_balance / 10**9,
                    "net_reward_gwei": net_reward,
                    "net_reward_eth": net_reward / 10**9,
                    "effective_apr": (net_reward / initial_balance) * (365.25 * 24 * 3600) / (epochs * 6.4 * 32) if epochs > 0 else 0
                }
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}

        except requests.RequestException as e:
            return {"error": f"Network error: {e}"}


def main():
    parser = argparse.ArgumentParser(description="Validator Lifecycle Manager")
    parser.add_argument("--beacon-url", default="http://localhost:5052", help="Beacon node URL")
    parser.add_argument("--web3-url", default="http://localhost:8545", help="Web3 provider URL")
    parser.add_argument("--web3signer-url", default="http://localhost:9000", help="Web3Signer URL")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Wait for activation
    activate_parser = subparsers.add_parser("wait-active", help="Wait for validators to activate")
    activate_parser.add_argument("--pubkeys", nargs="+", required=True, help="Validator public keys")
    activate_parser.add_argument("--timeout", type=int, default=3600, help="Timeout in seconds")

    # Submit voluntary exit
    exit_parser = subparsers.add_parser("voluntary-exit", help="Submit voluntary exit")
    exit_parser.add_argument("--pubkey", required=True, help="Validator public key")

    # Wait for exit
    wait_exit_parser = subparsers.add_parser("wait-exit", help="Wait for validators to exit")
    wait_exit_parser.add_argument("--pubkeys", nargs="+", required=True, help="Validator public keys")
    wait_exit_parser.add_argument("--timeout", type=int, default=3600, help="Timeout in seconds")

    # Wait for withdrawal
    withdrawal_parser = subparsers.add_parser("wait-withdrawal", help="Wait for withdrawals")
    withdrawal_parser.add_argument("--pubkeys", nargs="+", required=True, help="Validator public keys")
    withdrawal_parser.add_argument("--timeout", type=int, default=3600, help="Timeout in seconds")

    # Monitor validators
    monitor_parser = subparsers.add_parser("monitor", help="Monitor validators")
    monitor_parser.add_argument("--pubkeys", nargs="+", required=True, help="Validator public keys")
    monitor_parser.add_argument("--duration", type=int, default=3600, help="Monitor duration in seconds")

    # Get status
    status_parser = subparsers.add_parser("status", help="Get validator status")
    status_parser.add_argument("--pubkeys", nargs="+", required=True, help="Validator public keys")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = ValidatorLifecycleManager(args.beacon_url, args.web3_url)

    if args.command == "wait-active":
        results = manager.wait_for_activation(args.pubkeys, args.timeout)
        print("\nFinal results:")
        for pubkey, status in results.items():
            print(f"  {pubkey[:12]}...: {status.value}")

    elif args.command == "voluntary-exit":
        success = manager.submit_voluntary_exit(args.pubkey, args.web3signer_url)
        if success:
            print("Voluntary exit submitted successfully")
        else:
            print("Failed to submit voluntary exit")

    elif args.command == "wait-exit":
        results = manager.wait_for_exit(args.pubkeys, args.timeout)
        print("\nFinal results:")
        for pubkey, status in results.items():
            print(f"  {pubkey[:12]}...: {status.value}")

    elif args.command == "wait-withdrawal":
        results = manager.wait_for_withdrawal(args.pubkeys, args.timeout)
        print("\nFinal results:")
        for pubkey, status in results.items():
            print(f"  {pubkey[:12]}...: {status.value}")

    elif args.command == "monitor":
        history = manager.monitor_validators(args.pubkeys, args.duration)
        print("\nMonitoring completed. History saved.")

    elif args.command == "status":
        for pubkey in args.pubkeys:
            validator_info = manager.get_validator_info(pubkey)
            if validator_info:
                print(f"Validator {pubkey[:12]}...:")
                print(f"  Index: {validator_info.index}")
                print(f"  Status: {validator_info.status.value}")
                print(f"  Effective Balance: {validator_info.effective_balance / 10**9:.2f} ETH")
                print(f"  Slashed: {validator_info.slashed}")
                print(f"  Activation Epoch: {validator_info.activation_epoch}")
                print(f"  Exit Epoch: {validator_info.exit_epoch}")
                print()


if __name__ == "__main__":
    main()