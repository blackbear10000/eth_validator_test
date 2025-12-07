import { ContractFactory } from 'ethers'
import { useMetaMaskStore } from '../stores/metamaskStore'

/**
 * Batch Deposit 合约 ABI（简化版，只包含必要的方法）
 */
const BATCH_DEPOSIT_ABI = [
  {
    inputs: [
      { internalType: 'address', name: 'depositContractAddr', type: 'address' },
      { internalType: 'uint256', name: 'initialFee', type: 'uint256' },
    ],
    stateMutability: 'nonpayable',
    type: 'constructor',
  },
  {
    inputs: [
      { internalType: 'bytes', name: 'pubkeys', type: 'bytes' },
      { internalType: 'bytes', name: 'withdrawal_credentials', type: 'bytes' },
      { internalType: 'bytes', name: 'signatures', type: 'bytes' },
      { internalType: 'bytes32[]', name: 'deposit_data_roots', type: 'bytes32[]' },
      { internalType: 'uint256[]', name: 'amounts', type: 'uint256[]' },
    ],
    name: 'batchDeposit',
    outputs: [],
    stateMutability: 'payable',
    type: 'function',
  },
  {
    inputs: [],
    name: '_fee',
    outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [],
    name: 'owner',
    outputs: [{ internalType: 'address', name: '', type: 'address' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [],
    name: 'paused',
    outputs: [{ internalType: 'bool', name: '', type: 'bool' }],
    stateMutability: 'view',
    type: 'function',
  },
]

// Batch Deposit 合约 Bytecode 需要从后端 API 获取

/**
 * 合约部署服务
 */
export class ContractDeployerService {
  /**
   * 从后端获取合约 bytecode 和 ABI
   */
  static async getContractBytecode(): Promise<{ bytecode: string; abi: any[] }> {
    const { depositsApi } = await import('../api/deposits')
    const response = await depositsApi.getBatchContractBytecode() as any
    const data = response.data || response
    return {
      bytecode: data.bytecode,
      abi: data.abi || []
    }
  }

  /**
   * 部署 Batch Deposit 合约
   * 
   * @param depositContractAddress 官方 Deposit 合约地址
   * @param initialFee 初始费用（wei）
   * @param gasLimit Gas 限制（可选）
   * @returns 交易哈希和合约地址
   */
  static async deployBatchDepositContract(
    depositContractAddress: string,
    initialFee: bigint = 0n,
    gasLimit?: bigint
  ): Promise<{ txHash: string; contractAddress?: string }> {
    const { signer, provider } = useMetaMaskStore.getState()

    if (!signer || !provider) {
      throw new Error('MetaMask 未连接，请先连接 MetaMask')
    }

    // 获取 bytecode 和 ABI（从后端）
    const { bytecode, abi } = await this.getContractBytecode()
    if (!bytecode || bytecode === '0x') {
      throw new Error('无法获取合约 bytecode，请确保后端 API 可用')
    }

    // 使用后端返回的 ABI（如果可用），否则使用默认 ABI
    const contractABI = abi && abi.length > 0 ? abi : BATCH_DEPOSIT_ABI

    // 创建合约工厂
    const factory = new ContractFactory(contractABI, bytecode, signer)

    // 估算 gas
    let estimatedGas = gasLimit
    if (!estimatedGas) {
      try {
        estimatedGas = await factory.getDeployTransaction(
          depositContractAddress,
          initialFee
        ).then((tx) => provider.estimateGas(tx))
      } catch (error) {
        console.warn('Gas 估算失败，使用默认值:', error)
        estimatedGas = 5000000n // 默认 5M gas
      }
    }

    // 部署合约
    const contract = await factory.deploy(depositContractAddress, initialFee, {
      gasLimit: estimatedGas,
    })

    // 等待交易发送（获取交易哈希）
    await contract.deploymentTransaction()?.wait(1) // 等待 1 个确认

    const txHash = contract.deploymentTransaction()?.hash
    if (!txHash) {
      throw new Error('无法获取交易哈希')
    }

    // 等待合约地址可用
    const contractAddress = await contract.getAddress()

    return {
      txHash,
      contractAddress,
    }
  }

  /**
   * 通过交易哈希部署（如果已有部署交易）
   * 用于后端已经构建好交易，前端只需要发送的场景
   */
  static async deployByTransaction(
    txHash: string,
    provider: any
  ): Promise<{ contractAddress: string }> {
    // 等待交易确认
    const receipt = await provider.waitForTransaction(txHash, 1)

    if (!receipt || !receipt.contractAddress) {
      throw new Error('交易确认失败或未找到合约地址')
    }

    return {
      contractAddress: receipt.contractAddress,
    }
  }
}

