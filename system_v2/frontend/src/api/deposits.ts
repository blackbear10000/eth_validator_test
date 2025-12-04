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
}

export const depositsApi = {
  // 生成 Deposit Data
  generate: (params: {
    pubkeys?: string[]
    withdrawal_address: string
    amount_eth?: number
    fork_version?: string
  }) => apiClient.post('/deposits/generate', params),

  // 提交批量存款
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

  // 列出存款交易
  list: () => apiClient.get('/deposits'),

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

  // 部署 Batch Deposit 合约
  deployBatchContract: (params: {
    rpc_url?: string
    deployer_private_key: string
    network_name: string
    deposit_contract_address?: string
    initial_fee?: number
    gas_price?: number
    gas_limit?: number
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

