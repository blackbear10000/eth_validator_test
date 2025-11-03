import apiClient from './client'

export interface WithdrawalEvent {
  id: number
  withdrawal_type: string
  amount_eth: number
  fee_eth: number
  net_amount_eth: number
  withdrawn_at: string
  slot?: number
  epoch?: number
}

export interface WithdrawalStatistics {
  total_count: number
  total_amount_eth: number
  total_fee_eth: number
  partial_count: number
  full_count: number
}

export const withdrawalsApi = {
  // 获取验证者取款历史
  getValidatorWithdrawals: (pubkey: string, limit?: number, offset?: number) =>
    apiClient.get(`/withdrawals/${pubkey}`, {
      params: { limit, offset },
    }),

  // 获取取款统计
  getStatistics: (pubkey: string) =>
    apiClient.get(`/withdrawals/${pubkey}/statistics`),

  // 同步取款事件
  sync: (pubkey?: string) =>
    apiClient.post('/withdrawals/sync', null, {
      params: pubkey ? { pubkey } : {},
    }),

  // 计算费用
  calculateFee: (amount_eth: number) =>
    apiClient.post('/withdrawals/calculate-fee', null, {
      params: { amount_eth },
    }),
}

