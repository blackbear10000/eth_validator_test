# ETH Validators Workflow Testing Plan (Kurtosis + Web3Signer + Vault + Consul)

## 1. Objectives & Scope
- **Objective**: Validate the full lifecycle of Ethereum validators — from key generation, deposit registration, activation, to voluntary exit and withdrawal.  
- **Scope**:
  - Build a local Ethereum devnet with **Kurtosis**.
  - Use **Web3Signer** as the remote signing service.
  - Use **Vault + Consul** for storing and managing validator keys (simplified testing setup).
  - Accelerate deposit queue and activation times for faster functional validation.
- **Out of scope**:
  - No performance or stress testing.
  - No complex monitoring or alerting.

---

## 2. Modular Architecture
### 2.1 Local Devnet (Kurtosis)
- Spin up four Execution + Consensus client pairs:
  - geth + prysm
  - reth + lighthouse
  - geth + lighthouse
  - reth + prysm
- Adjust network parameters (slot duration, epoch length, churn limit, etc.) to accelerate validator deposits and activation.
- Use Kurtosis enclaves with isolated port mappings to avoid conflicts.

### 2.2 Remote Signing Stack
- **Web3Signer**: Remote signing service (HTTP REST).
- **Vault**: Stores BLS private keys.
- **Consul**: Acts as Vault’s storage backend for persistence and consistency.
- Web3Signer pulls keys from Vault via Key Manager API and provides signing to validator clients.

### 2.3 Validator Keys & Deposit Flow
- **Pre-generation**: Bulk-generate validator keys (BLS keystores) and back them up offline.
- **Storage**: Load private keys into Vault; keep pubkey index for tracking and registration.
- **Deposit data generation**:
  - After client provides withdrawal address + validator count, generate deposit_data.json.
  - Can be done with `deposit-cli` or `ethdo`.
- **Batch deposits**:
  - Use an audited **Batch Deposit Contract** (e.g., stakefish) to submit multiple validator deposits in a single transaction (limited by gas).

### 2.4 Validator Lifecycle Management
- **Validator Client** (e.g., Lighthouse, Prysm) connects to Web3Signer for signing.
- **Startup order**:
  1. Beacon Node (CL).
  2. Validator Client (configured to use Web3Signer).
  3. Web3Signer (with keys loaded from Vault).
- **Lifecycle states**:
  - After deposit → `pending_queued`
  - With accelerated parameters → `active_ongoing`
  - On voluntary exit → `exiting` → `exited`
  - Funds withdrawn to the withdrawal address.

---

## 3. Workflow Overview
### Phase 1: Environment Setup
1. Launch Vault + Consul + Web3Signer via Docker Compose.  
2. Launch four EL/CL pairs with Kurtosis, using accelerated parameters.  

### Phase 2: Key Management
1. Pre-generate large batches of validator keys.  
2. Store private keys in Vault, back them up offline.  
3. Save pubkey metadata for indexing.  

### Phase 3: Deposits & Registration
1. Client provides withdrawal address and validator count.  
2. Generate deposit_data.json files accordingly.  
3. Submit deposits via batch contract.  
4. Validators move into the queue.  

### Phase 4: Activation & Operation
1. Validator Client connects to Web3Signer.  
2. Deposited validators go from `pending_queued` → `active_ongoing`.  
3. Validators start attesting and proposing blocks.  

### Phase 5: Exit & Withdrawal
1. Trigger voluntary exit transaction.  
2. Validator status flows to `exiting` → `exited`.  
3. Funds automatically withdrawn to withdrawal address.  

---

## 4. Ports & Containerization
- Consul: 8500  
- Vault: 8200  
- Web3Signer: 9000  
- Kurtosis: dynamically maps EL/CL ports  
- All services containerized to avoid conflicts and simplify cleanup.  

---

## 5. Validation Checklist
- Vault can securely store and retrieve BLS private keys.  
- Web3Signer loads keys via Key Manager API and exposes public keys.  
- Validator Clients connect to Web3Signer and perform signing requests.  
- deposit_data.json files are correctly generated and used in deposits.  
- Validator lifecycle flows correctly from pending → active → exited → withdrawn.  

---

## 6. Summary
- **Minimal, containerized environment** focused only on workflow validation.  
- **Web3Signer + Vault + Consul** form the key management and remote signing stack.  
- **Kurtosis** provides a controllable Ethereum devnet with accelerated parameters.  
- Covers the **full validator lifecycle**: key generation, deposit, activation, exit, and withdrawal.  
