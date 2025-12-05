import apiClient from './client'

export interface Web3SignerInstanceStatus {
  healthy: boolean
  url: string
}

export interface Web3SignerStatus {
  primary: Web3SignerInstanceStatus
  secondary: Web3SignerInstanceStatus
  haproxy: Web3SignerInstanceStatus
}

export interface Web3SignerKeyInfo {
  pubkey: string
  in_database: boolean
  status?: string | null
  activated_at?: string | null
}

export interface Web3SignerKeysResponse {
  primary?: {
    keys: Web3SignerKeyInfo[]
    count: number
    error?: string
  }
  secondary?: {
    keys: Web3SignerKeyInfo[]
    count: number
    error?: string
  }
}

export interface Web3SignerSyncStats {
  db_active_count: number
  web3signer_count: number
  missing_count: number
  extra_count: number
  synced_count: number
}

export interface Web3SignerSyncStatus {
  primary?: {
    missing_in_web3signer: string[]
    extra_in_web3signer: string[]
    synced: string[]
    stats: Web3SignerSyncStats
    error?: string
  }
  secondary?: {
    missing_in_web3signer: string[]
    extra_in_web3signer: string[]
    synced: string[]
    stats: Web3SignerSyncStats
    error?: string
  }
}

export interface Web3SignerSyncConfigsResponse {
  sync_result: {
    created: number
    removed: number
    skipped: number
    errors: number
  }
  reload_result: {
    success: boolean
    warning?: string
    error?: string
  }
  success: boolean
  needs_restart?: boolean
  message?: string
}

export interface Web3SignerRestartResponse {
  primary: boolean
  secondary: boolean
  success: boolean
}

export interface Web3SignerCleanupResponse {
  success: boolean
  removed: number
  errors: number
  files: string[]
  message: string
}

export const web3signerApi = {
  // 获取 Web3Signer 状态
  getStatus: () => apiClient.get('/web3signer/status') as Promise<Web3SignerStatus>,

  // 获取 Web3Signer 密钥列表
  getKeys: (instance: 'primary' | 'secondary' | 'both' = 'both') =>
    apiClient.get('/web3signer/keys', { params: { instance } }) as Promise<Web3SignerKeysResponse>,

  // 获取同步状态
  getSyncStatus: (instance: 'primary' | 'secondary' | 'both' = 'both') =>
    apiClient.get('/web3signer/sync-status', { params: { instance } }) as Promise<Web3SignerSyncStatus>,

  // 同步配置文件并重新加载
  syncConfigs: (cleanupOrphaned: boolean = true) =>
    apiClient.post(`/web3signer/sync-configs?cleanup_orphaned=${cleanupOrphaned}`) as Promise<Web3SignerSyncConfigsResponse>,

  // 重启 Web3Signer 容器
  restart: () =>
    apiClient.post('/web3signer/restart') as Promise<Web3SignerRestartResponse>,

  // 清理孤立的配置文件
  cleanupConfigs: () =>
    apiClient.post('/web3signer/cleanup-configs') as Promise<Web3SignerCleanupResponse>,
}

