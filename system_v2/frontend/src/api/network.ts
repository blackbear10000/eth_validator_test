import apiClient from './client'

export interface NetworkStatus {
  enclave_name: string
  status: string
  is_running: boolean
  error?: string
  enclave_info?: any
  raw_output?: string
}

export interface NetworkInfo {
  enclave_name: string
  genesis?: any
  fork_schedule?: any
  beacon_api_url?: string
  error?: string
  status?: any
}

export const networkApi = {
  // 获取网络状态
  getStatus: () => apiClient.get('/network/status'),

  // 启动网络
  start: () => apiClient.post('/network/start'),

  // 停止网络
  stop: () => apiClient.post('/network/stop'),

  // 获取网络信息
  getInfo: () => apiClient.get('/network/info'),
}

