import apiClient from './client'

export interface ClientInstance {
  id: number
  name: string
  client_type: string
  beacon_api_url?: string
  grpc_endpoint?: string
  web3signer_url: string
  is_active: boolean
  status: string
  created_at: string
  key_count: number
}

export const clientsApi = {
  // 创建客户端
  create: (params: {
    name: string
    client_type: string
    beacon_api_url?: string
    grpc_endpoint?: string
    web3signer_url?: string
    notes?: string
  }) => apiClient.post('/clients', params),

  // 列出客户端
  list: (clientType?: string) =>
    apiClient.get('/clients', { params: clientType ? { client_type: clientType } : {} }),

  // 分配密钥
  assignKeys: (clientId: number, pubkeys: string[]) =>
    apiClient.put(`/clients/${clientId}/keys`, { pubkeys }),

  // 重新加载密钥
  reloadKeys: (clientId: number) =>
    apiClient.post(`/clients/${clientId}/reload-keys`),
}

