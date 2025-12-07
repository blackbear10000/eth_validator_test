import { BrowserProvider, JsonRpcSigner, Eip1193Provider } from 'ethers'

/**
 * MetaMask 服务
 * 处理与 MetaMask 的交互
 */
export class MetaMaskService {
  private provider: BrowserProvider | null = null
  private signer: JsonRpcSigner | null = null

  /**
   * 检查 MetaMask 是否安装
   */
  static isMetaMaskInstalled(): boolean {
    return typeof window !== 'undefined' && typeof window.ethereum !== 'undefined' && (window.ethereum.isMetaMask === true)
  }

  /**
   * 获取 MetaMask Provider
   */
  static getEthereumProvider(): Eip1193Provider | null {
    if (typeof window === 'undefined' || typeof window.ethereum === 'undefined') {
      return null
    }
    return window.ethereum as Eip1193Provider
  }

  /**
   * 连接 MetaMask
   */
  async connect(): Promise<{ account: string; chainId: bigint }> {
    if (!MetaMaskService.isMetaMaskInstalled()) {
      throw new Error('MetaMask 未安装，请先安装 MetaMask 扩展')
    }

    const ethereum = MetaMaskService.getEthereumProvider()
    if (!ethereum) {
      throw new Error('无法获取 Ethereum Provider')
    }

    try {
      // 请求账户访问权限
      const accounts = await ethereum.request({ method: 'eth_requestAccounts' }) as string[]
      
      if (!accounts || accounts.length === 0) {
        throw new Error('用户拒绝了账户访问请求')
      }

      const account = accounts[0]

      // 获取链 ID
      const chainIdHex = await ethereum.request({ method: 'eth_chainId' }) as string
      const chainId = BigInt(chainIdHex)

      // 创建 Provider 和 Signer
      this.provider = new BrowserProvider(ethereum)
      this.signer = await this.provider.getSigner()

      return { account, chainId }
    } catch (error: any) {
      if (error.code === 4001) {
        throw new Error('用户拒绝了连接请求')
      }
      throw new Error(`连接 MetaMask 失败: ${error.message}`)
    }
  }

  /**
   * 获取当前账户
   */
  async getCurrentAccount(): Promise<string | null> {
    if (!MetaMaskService.isMetaMaskInstalled()) {
      return null
    }

    const ethereum = MetaMaskService.getEthereumProvider()
    if (!ethereum) {
      return null
    }

    try {
      const accounts = await ethereum.request({ method: 'eth_accounts' }) as string[]
      return accounts.length > 0 ? accounts[0] : null
    } catch (error) {
      console.error('获取当前账户失败:', error)
      return null
    }
  }

  /**
   * 获取当前链 ID
   */
  async getCurrentChainId(): Promise<bigint | null> {
    if (!MetaMaskService.isMetaMaskInstalled()) {
      return null
    }

    const ethereum = MetaMaskService.getEthereumProvider()
    if (!ethereum) {
      return null
    }

    try {
      const chainIdHex = await ethereum.request({ method: 'eth_chainId' }) as string
      return BigInt(chainIdHex)
    } catch (error) {
      console.error('获取链 ID 失败:', error)
      return null
    }
  }

  /**
   * 获取账户余额
   */
  async getBalance(account: string): Promise<string> {
    if (!this.provider) {
      const ethereum = MetaMaskService.getEthereumProvider()
      if (!ethereum) {
        throw new Error('无法获取 Provider')
      }
      this.provider = new BrowserProvider(ethereum)
    }

    const balance = await this.provider.getBalance(account)
    return balance.toString()
  }

  /**
   * 获取 Provider 实例
   */
  getProvider(): BrowserProvider | null {
    return this.provider
  }

  /**
   * 获取 Signer 实例
   */
  getSigner(): JsonRpcSigner | null {
    return this.signer
  }

  /**
   * 初始化 Provider 和 Signer（如果已连接）
   */
  async initialize(): Promise<{ account: string; chainId: bigint } | null> {
    const account = await this.getCurrentAccount()
    if (!account) {
      return null
    }

    const chainId = await this.getCurrentChainId()
    if (!chainId) {
      return null
    }

    const ethereum = MetaMaskService.getEthereumProvider()
    if (!ethereum) {
      return null
    }

    this.provider = new BrowserProvider(ethereum)
    this.signer = await this.provider.getSigner()

    return { account, chainId }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.provider = null
    this.signer = null
  }

  /**
   * 监听账户切换
   */
  onAccountsChanged(callback: (accounts: string[]) => void): () => void {
    const ethereum = window.ethereum
    if (!ethereum || typeof ethereum.on !== 'function') {
      return () => {}
    }

    ethereum.on('accountsChanged', callback)

    return () => {
      if (typeof ethereum.removeListener === 'function') {
        ethereum.removeListener('accountsChanged', callback)
      }
    }
  }

  /**
   * 监听链切换
   */
  onChainChanged(callback: (chainId: string) => void): () => void {
    const ethereum = window.ethereum
    if (!ethereum || typeof ethereum.on !== 'function') {
      return () => {}
    }

    ethereum.on('chainChanged', callback)

    return () => {
      if (typeof ethereum.removeListener === 'function') {
        ethereum.removeListener('chainChanged', callback)
      }
    }
  }
}

// 扩展 Window 接口
declare global {
  interface Window {
    ethereum?: {
      isMetaMask?: boolean
      request: (args: { method: string; params?: any[] }) => Promise<any>
      on: (event: string, callback: (...args: any[]) => void) => void
      removeListener: (event: string, callback: (...args: any[]) => void) => void
    }
  }
}

