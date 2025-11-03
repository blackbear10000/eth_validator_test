import apiClient from './client'

export interface ValidatorKey {
  pubkey: string
  withdrawal_pubkey: string
  status: string
  index: number
  signing_key_path: string
  batch_id?: string
  created_at: string
  activated_at?: string
  deposited_at?: string
  exited_at?: string
  withdrawal_address?: string
  client_type?: string
  deposit_tx_hash?: string
}

export interface KeyPoolStatus {
  total: number
  by_status: Record<string, number>
}

export const keysApi = {
  // 批量生成密钥
  batchGenerate: (count: number, batchId?: string) =>
    apiClient.post('/keys/batch-generate', { count, batch_id: batchId }),

  // 激活密钥
  activate: (count: number, batchId?: string) =>
    apiClient.post('/keys/activate', { count, batch_id: batchId }),

  // 列出密钥
  list: (params?: {
    status?: string
    batch_id?: string
    limit?: number
    offset?: number
  }) => apiClient.get('/keys', { params }),

  // 获取密钥详情
  get: (pubkey: string) => apiClient.get(`/keys/${pubkey}`),

  // 更新密钥状态
  updateStatus: (pubkey: string, status: string) =>
    apiClient.put(`/keys/${pubkey}/status`, { status }),

  // 获取密钥池状态
  getPoolStatus: () => apiClient.get('/keys/pool/status'),
}

