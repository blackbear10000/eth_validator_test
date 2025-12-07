import { create } from 'zustand'
import { BrowserProvider, JsonRpcSigner } from 'ethers'
import { MetaMaskService } from '../services/metamask'

interface MetaMaskState {
  isConnected: boolean
  account: string | null
  chainId: bigint | null
  provider: BrowserProvider | null
  signer: JsonRpcSigner | null
  balance: string | null
  isLoading: boolean
  error: string | null
}

interface MetaMaskActions {
  connect: () => Promise<void>
  disconnect: () => void
  refreshAccount: () => Promise<void>
  refreshBalance: () => Promise<void>
  setError: (error: string | null) => void
  initialize: () => Promise<void>
}

type MetaMaskStore = MetaMaskState & MetaMaskActions

const metamaskService = new MetaMaskService()

export const useMetaMaskStore = create<MetaMaskStore>((set, get) => ({
  // 初始状态
  isConnected: false,
  account: null,
  chainId: null,
  provider: null,
  signer: null,
  balance: null,
  isLoading: false,
  error: null,

  // 连接 MetaMask
  connect: async () => {
    set({ isLoading: true, error: null })
    try {
      const { account, chainId } = await metamaskService.connect()
      const provider = metamaskService.getProvider()
      const signer = metamaskService.getSigner()

      // 获取余额
      let balance: string | null = null
      try {
        balance = await metamaskService.getBalance(account)
      } catch (error) {
        console.warn('获取余额失败:', error)
      }

      set({
        isConnected: true,
        account,
        chainId,
        provider,
        signer,
        balance,
        isLoading: false,
      })

      // 设置事件监听
      setupEventListeners()
    } catch (error: any) {
      set({
        isConnected: false,
        account: null,
        chainId: null,
        provider: null,
        signer: null,
        balance: null,
        isLoading: false,
        error: error.message || '连接失败',
      })
      throw error
    }
  },

  // 断开连接
  disconnect: () => {
    metamaskService.disconnect()
    set({
      isConnected: false,
      account: null,
      chainId: null,
      provider: null,
      signer: null,
      balance: null,
      error: null,
    })
  },

  // 刷新账户信息
  refreshAccount: async () => {
    const account = await metamaskService.getCurrentAccount()
    const chainId = await metamaskService.getCurrentChainId()

    if (account && chainId) {
      const provider = metamaskService.getProvider()
      const signer = metamaskService.getSigner()

      // 获取余额
      let balance: string | null = null
      try {
        balance = await metamaskService.getBalance(account)
      } catch (error) {
        console.warn('获取余额失败:', error)
      }

      set({
        isConnected: true,
        account,
        chainId,
        provider,
        signer,
        balance,
      })
    } else {
      set({
        isConnected: false,
        account: null,
        chainId: null,
        provider: null,
        signer: null,
        balance: null,
      })
    }
  },

  // 刷新余额
  refreshBalance: async () => {
    const { account } = get()
    if (!account) {
      return
    }

    try {
      const balance = await metamaskService.getBalance(account)
      set({ balance })
    } catch (error) {
      console.warn('刷新余额失败:', error)
    }
  },

  // 设置错误
  setError: (error: string | null) => {
    set({ error })
  },

  // 初始化（检查是否已连接）
  initialize: async () => {
    set({ isLoading: true })
    try {
      const result = await metamaskService.initialize()
      if (result) {
        const { account, chainId } = result
        const provider = metamaskService.getProvider()
        const signer = metamaskService.getSigner()

        // 获取余额
        let balance: string | null = null
        try {
          balance = await metamaskService.getBalance(account)
        } catch (error) {
          console.warn('获取余额失败:', error)
        }

        set({
          isConnected: true,
          account,
          chainId,
          provider,
          signer,
          balance,
          isLoading: false,
        })

        // 设置事件监听
        setupEventListeners()
      } else {
        set({
          isConnected: false,
          account: null,
          chainId: null,
          provider: null,
          signer: null,
          balance: null,
          isLoading: false,
        })
      }
    } catch (error: any) {
      set({
        isConnected: false,
        account: null,
        chainId: null,
        provider: null,
        signer: null,
        balance: null,
        isLoading: false,
        error: error.message || '初始化失败',
      })
    }
  },
}))

// 设置事件监听器
let accountsChangedUnsubscribe: (() => void) | null = null
let chainChangedUnsubscribe: (() => void) | null = null

function setupEventListeners() {
  // 清理旧的监听器
  if (accountsChangedUnsubscribe) {
    accountsChangedUnsubscribe()
  }
  if (chainChangedUnsubscribe) {
    chainChangedUnsubscribe()
  }

  // 监听账户切换
  accountsChangedUnsubscribe = metamaskService.onAccountsChanged((accounts) => {
    const store = useMetaMaskStore.getState()
    if (accounts.length === 0) {
      // 用户断开连接
      store.disconnect()
    } else {
      // 账户切换
      store.refreshAccount()
    }
  })

  // 监听链切换
  chainChangedUnsubscribe = metamaskService.onChainChanged((chainIdHex) => {
    const store = useMetaMaskStore.getState()
    const chainId = BigInt(chainIdHex)
    store.refreshAccount()
    // 可以在这里添加链切换的提示
    console.log('链已切换:', chainId.toString())
  })
}

