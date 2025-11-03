import apiClient from './client'

export interface DepositData {
  pubkey: string
  withdrawal_credentials: string
  amount: number
  signature: string
  deposit_data_root: string
  fork_version: string
  network_name: string
  withdrawal_address: string
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
  submit: (depositDataList: DepositData[], fromAddress: string) =>
    apiClient.post('/deposits/submit', {
      deposit_data_list: depositDataList,
      from_address: fromAddress,
    }),

  // 列出存款交易
  list: () => apiClient.get('/deposits'),

  // 同步状态
  sync: () => apiClient.post('/deposits/sync'),
}

