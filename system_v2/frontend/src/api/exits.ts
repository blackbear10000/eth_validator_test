import apiClient from './client'

export interface ExitRequest {
  pubkey: string
  epoch?: number
}

export interface ExitResponse {
  pubkey: string
  status: string
  exit_data?: {
    message: {
      epoch: string
      validator_index: string
    }
    signature: string
  }
}

export const exitsApi = {
  // 生成退出签名
  generateExit: async (pubkey: string, epoch?: number) => {
    const params = new URLSearchParams({ pubkey })
    if (epoch !== undefined) params.append('epoch', epoch.toString())
    return apiClient.post(`/exits/generate?${params.toString()}`)
  },

  // 提交退出
  submitExit: async (pubkey: string, epoch?: number) => {
    const params = new URLSearchParams({ pubkey })
    if (epoch !== undefined) params.append('epoch', epoch.toString())
    return apiClient.post(`/exits/submit?${params.toString()}`)
  },

  // 批量退出
  batchExit: (pubkeys: string[], epoch?: number) =>
    apiClient.post('/exits/batch', { pubkeys, epoch: epoch || null }),

  // 完成退出流程
  completeExit: (pubkey: string) =>
    apiClient.post(`/exits/${pubkey}/complete`),

  // 移除已退出密钥
  removeKey: (pubkey: string) =>
    apiClient.delete(`/exits/${pubkey}/remove-key`),
}

