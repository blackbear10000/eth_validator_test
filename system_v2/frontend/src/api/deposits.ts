import apiClient from './client'

export interface DepositData {
  pubkey: string
  withdrawal_credentials: string
  amount: number
  signature: string
  deposit_data_root: string
  fork_version: string
  network_name?: string
  withdrawal_address: string
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
  submitted_at: string
  confirmed_at?: string
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
  sync: () => apiClient.post('/deposits/sync'),

  // 部署 Batch Deposit 合约
  deployBatchContract: (params: {
    rpc_url?: string
    deployer_private_key: string
    network_name: string
    gas_price?: number
    gas_limit?: number
  }) => apiClient.post('/deposits/batch-contract/deploy', params),

  // 列出 Batch Deposit 合约
  listBatchContracts: (networkName?: string) =>
    apiClient.get('/deposits/batch-contract/list', {
      params: networkName ? { network_name: networkName } : {},
    }),
}

