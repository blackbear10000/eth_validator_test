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
  rpc_url?: string
  ws_url?: string
  deposit_contract_address?: string
  fork_version?: string
  network_name?: string
  error?: string
  status?: any
}

export interface RpcEndpoints {
  rpc_url?: string
  host_rpc_url?: string
  ws_url?: string
  service?: string
  error?: string
  debug_info?: string
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

  // 获取 RPC 端点
  getRpcEndpoints: () => apiClient.get('/network/rpc-endpoints') as Promise<RpcEndpoints>,
}

