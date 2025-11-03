import apiClient from './client'

export interface SystemHealth {
  vault: boolean
  postgresql: boolean
  web3signer_primary: boolean
  web3signer_secondary: boolean
  haproxy: boolean
  beacon_api: boolean
  overall: boolean
}

export interface SystemOverview {
  total_keys: number
  keys_by_status: Record<string, number>
  total_deposits: number
  active_validators: number
  total_rewards_eth: number
  system_health: SystemHealth
}

export const monitoringApi = {
  // 系统健康检查
  health: () => apiClient.get('/monitoring/health'),

  // 系统概览
  overview: () => apiClient.get('/monitoring/overview'),

  // 验证者性能
  getValidatorPerformance: (pubkey: string) =>
    apiClient.get(`/monitoring/validators/${pubkey}`),
}

