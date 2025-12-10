import apiClient from './client'

export interface DepositData {
  pubkey: string
  withdrawal_credentials: string
  amount: number
  signature: string
  deposit_message_root: string
  deposit_data_root: string
  fork_version: string
  network_name: string
  deposit_cli_version: string
}

export interface BatchDepositContract {
  id: number
  contract_address: string
  network_name: string
  rpc_url: string
  deployer_address: string
  deployment_tx_hash: string
  block_number?: number
  gas_used?: number
  deployed_at: string
  notes?: string
}

export interface DepositTransaction {
  id: number
  pubkey: string
  tx_hash: string
  batch_id?: string
  status: string
  amount_eth: number
  amount_wei?: number
  submitted_at: string
  confirmed_at?: string
  validated_at?: string
  block_number?: number
  validator_index?: number
  activation_epoch?: number
  exit_epoch?: number
  effective_balance_gwei?: number
  validation_error?: string
  status_history?: Array<{
    from_status: string
    to_status: string
    timestamp: string
    reason?: string
  }>
  notes?: string
  // 余额和收益信息（可选）
  balance_eth?: number
  effective_balance_eth?: number
  earnings_eth?: number
}

export const depositsApi = {
  // 生成 Deposit Data
  generate: (params: {
    count?: number
    pubkeys?: string[]
    withdrawal_address: string
    amount_eth?: number
    fork_version?: string
    network_name?: string
  }) => apiClient.post('/deposits/generate', params),

  // 提交批量存款（使用私钥签名，向后兼容）
  submit: (
    depositDataList: DepositData[],
    fromAddress: string,
    privateKey: string,
    depositType: 'official' | 'batch' = 'batch',
    batchContractAddress?: string,
    officialContractAddress?: string
  ) =>
    apiClient.post('/deposits/submit', {
      deposit_data_list: depositDataList,
      from_address: fromAddress,
      private_key: privateKey,
      deposit_type: depositType,
      batch_contract_address: batchContractAddress,
      official_deposit_contract_address: officialContractAddress,
    }),

  // 通过交易哈希提交存款（MetaMask 方式）
  submitByTxHashes: (
    txHashes: string[],
    fromAddress: string,
    depositType: 'official' | 'batch',
    depositDataList?: DepositData[],
    batchContractAddress?: string,
    officialContractAddress?: string
  ) =>
    apiClient.post('/deposits/submit-by-tx-hashes', {
      tx_hashes: txHashes,
      from_address: fromAddress,
      deposit_type: depositType,
      deposit_data_list: depositDataList,
      batch_contract_address: batchContractAddress,
      official_deposit_contract_address: officialContractAddress,
    }),

  // 列出存款交易
  list: (includeBalance?: boolean) =>
    apiClient.get('/deposits', {
      params: includeBalance ? { include_balance: true } : {},
    }),

  // 同步状态
  sync: (txHash?: string, validateImmediately?: boolean) => {
    const params: any = {}
    if (txHash) params.tx_hash = txHash
    if (validateImmediately !== undefined) params.validate_immediately = validateImmediately
    return apiClient.post('/deposits/sync', null, { params })
  },

  // 验证存款交易
  validate: (txHash: string) => apiClient.post(`/deposits/${txHash}/validate`),

  // 获取存款交易详细状态
  getStatus: (txHash: string) => apiClient.get(`/deposits/${txHash}/status`),

  // 获取 Batch Deposit 合约 bytecode 和 ABI
  getBatchContractBytecode: () => apiClient.get('/deposits/batch-contract/bytecode'),

  // 部署 Batch Deposit 合约（MetaMask 方式）
  deployBatchContract: (params: {
    rpc_url?: string
    deployer_private_key?: string // 已废弃，保留用于向后兼容
    network_name: string
    deposit_contract_address?: string
    initial_fee?: number
    gas_price?: number
    gas_limit?: number
    deployer_address?: string // MetaMask 部署时使用
    deployment_tx_hash?: string // MetaMask 部署时使用
  }) => apiClient.post('/deposits/batch-contract/deploy', params),

  // 列出 Batch Deposit 合约
  listBatchContracts: (networkName?: string) =>
    apiClient.get('/deposits/batch-contract/list', {
      params: networkName ? { network_name: networkName } : {},
    }),

  // 获取单个 Batch Deposit 合约详情
  getBatchContract: (contractId: number) =>
    apiClient.get(`/deposits/batch-contract/${contractId}`),

  // 获取 Batch Deposit 合约统计数据
  getBatchContractStatistics: (contractId: number) =>
    apiClient.get(`/deposits/batch-contract/${contractId}/statistics`),

  // 获取合约存款记录
  getContractDeposits: (contractId: number, limit?: number, offset?: number) =>
    apiClient.get(`/deposits/batch-contract/${contractId}/deposits`, {
      params: { limit, offset }
    }),
}

export interface BatchContractStatistics {
  contract_id: number
  contract_address: string
  deposit_count: number
  total_amount_eth: number
  validator_count: number
  contract_fee_wei?: number
  contract_fee_gwei?: number
  contract_balance_wei?: number
  contract_balance_eth?: number
  is_paused?: boolean
  owner_address?: string
}

