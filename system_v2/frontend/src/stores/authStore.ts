import { create } from 'zustand'
import apiClient from '../api/client'
import { useMetaMaskStore } from './metamaskStore'

interface User {
  id: number
  wallet_address?: string
  username?: string
  role: 'admin' | 'user'
}

interface AuthState {
  isAuthenticated: boolean
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null
}

interface AuthActions {
  loginWithWallet: () => Promise<void>
  loginWithPassword: (username: string, password: string) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<void>
  setError: (error: string | null) => void
}

type AuthStore = AuthState & AuthActions

export const useAuthStore = create<AuthStore>()((set, get) => ({
      // 初始状态
      isAuthenticated: false,
      user: null,
      token: null,
      isLoading: false,
      error: null,

      // 钱包登录
      loginWithWallet: async () => {
        set({ isLoading: true, error: null })
        try {
          const { account, signer } = useMetaMaskStore.getState()
          
          if (!account || !signer) {
            throw new Error('请先连接 MetaMask')
          }

          // 生成登录消息
          const message = `请签名以登录 ETH Validator Management System\n\n地址: ${account}\n时间: ${new Date().toISOString()}`
          
          // 请求签名
          const signature = await signer.signMessage(message)
          
          // 调用登录 API
          const response = await apiClient.post('/auth/wallet-login', {
            wallet_address: account,
            signature,
            message
          }) as any
          
          const { access_token, user } = response.data || response
          
          // 设置 token 到 API client
          apiClient.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
          
          set({
            isAuthenticated: true,
            user,
            token: access_token,
            isLoading: false,
            error: null
          })
        } catch (error: any) {
          set({
            isAuthenticated: false,
            user: null,
            token: null,
            isLoading: false,
            error: error.message || '登录失败'
          })
          throw error
        }
      },

      // 管理员密码登录
      loginWithPassword: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await apiClient.post('/auth/admin-login', {
            username,
            password
          }) as any
          
          const { access_token, user } = response.data || response
          
          // 设置 token 到 API client
          apiClient.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
          
          set({
            isAuthenticated: true,
            user,
            token: access_token,
            isLoading: false,
            error: null
          })
        } catch (error: any) {
          set({
            isAuthenticated: false,
            user: null,
            token: null,
            isLoading: false,
            error: error.message || '登录失败'
          })
          throw error
        }
      },

      // 登出
      logout: () => {
        // 清除 token
        delete apiClient.defaults.headers.common['Authorization']
        
        set({
          isAuthenticated: false,
          user: null,
          token: null,
          error: null
        })
      },

      // 检查认证状态
      checkAuth: async () => {
        const { token } = get()
        if (!token) {
          set({ isAuthenticated: false, user: null })
          return
        }

        try {
          // 设置 token
          apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`
          
          // 获取当前用户信息
          const response = await apiClient.get('/auth/me') as any
          const user = response.data || response
          
          set({
            isAuthenticated: true,
            user
          })
        } catch (error: any) {
          // Token 无效，清除状态
          delete apiClient.defaults.headers.common['Authorization']
          set({
            isAuthenticated: false,
            user: null,
            token: null
          })
        }
      },

      // 设置错误
      setError: (error: string | null) => {
        set({ error })
      }
    })
)

// 持久化存储（使用 localStorage）
if (typeof window !== 'undefined') {
  // 从 localStorage 恢复状态
  const stored = localStorage.getItem('auth-storage')
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      if (parsed.token) {
        useAuthStore.setState({
          token: parsed.token,
          user: parsed.user,
          isAuthenticated: parsed.isAuthenticated
        })
        // 设置 token 到 API client
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${parsed.token}`
      }
    } catch (e) {
      console.error('恢复认证状态失败:', e)
    }
  }

  // 监听状态变化并保存
  useAuthStore.subscribe((state) => {
    localStorage.setItem('auth-storage', JSON.stringify({
      token: state.token,
      user: state.user,
      isAuthenticated: state.isAuthenticated
    }))
  })
}

