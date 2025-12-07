import { Contract } from 'ethers'
import { useMetaMaskStore } from '../stores/metamaskStore'
import type { DepositData } from '../api/deposits'

/**
 * 官方 Deposit 合约 ABI
 */
const DEPOSIT_CONTRACT_ABI = [
  {
    inputs: [
      { internalType: 'bytes', name: 'pubkey', type: 'bytes' },
      { internalType: 'bytes', name: 'withdrawal_credentials', type: 'bytes' },
      { internalType: 'bytes', name: 'signature', type: 'bytes' },
      { internalType: 'bytes32', name: 'deposit_data_root', type: 'bytes32' },
    ],
    name: 'deposit',
    outputs: [],
    stateMutability: 'payable',
    type: 'function',
  },
]

/**
 * Batch Deposit 合约 ABI（只包含 batchDeposit 方法）
 */
const BATCH_DEPOSIT_ABI = [
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
]

/**
 * 存款提交服务
 */
export class DepositSubmitterService {
  /**
   * 准备批量存款数据
   */
  static prepareBatchData(depositDataList: DepositData[]): {
    pubkeys: string
    withdrawal_credentials: string
    signatures: string
    deposit_data_roots: string[]
    amounts: bigint[]
    totalValue: bigint
  } {
    const pubkeys: Uint8Array[] = []
    const signatures: Uint8Array[] = []
    const deposit_data_roots: string[] = []
    const amounts: bigint[] = []

    // Batch Deposit 合约要求所有验证者使用相同的 withdrawal_credentials
    // 只使用第一个验证者的 withdrawal_credentials（32 字节）
    const firstWithdrawalCredentialsHex = depositDataList[0].withdrawal_credentials
    console.log('First withdrawal_credentials (hex):', firstWithdrawalCredentialsHex)
    
    const firstWithdrawalCredentials = this.hexToBytes(firstWithdrawalCredentialsHex)
    if (firstWithdrawalCredentials.length !== 32) {
      throw new Error(`Invalid withdrawal_credentials length: ${firstWithdrawalCredentials.length}, expected 32. Hex: ${firstWithdrawalCredentialsHex}`)
    }

    // 验证所有验证者使用相同的 withdrawal_credentials
    for (let i = 1; i < depositDataList.length; i++) {
      const withdrawalBytes = this.hexToBytes(depositDataList[i].withdrawal_credentials)
      if (withdrawalBytes.length !== 32) {
        throw new Error(`Invalid withdrawal_credentials length at index ${i}: ${withdrawalBytes.length}, expected 32`)
      }
      // 比较字节数组
      const isEqual = firstWithdrawalCredentials.every((byte, idx) => byte === withdrawalBytes[idx])
      if (!isEqual) {
        throw new Error(`所有验证者必须使用相同的 withdrawal_credentials。验证者 0 和验证者 ${i} 的 withdrawal_credentials 不匹配`)
      }
    }

    for (const data of depositDataList) {
      // 转换 pubkey (48 字节)
      const pubkeyBytes = this.hexToBytes(data.pubkey)
      if (pubkeyBytes.length !== 48) {
        throw new Error(`Invalid pubkey length: ${pubkeyBytes.length}, expected 48`)
      }
      pubkeys.push(pubkeyBytes)

      // 转换 signature (96 字节)
      const signatureBytes = this.hexToBytes(data.signature)
      if (signatureBytes.length !== 96) {
        throw new Error(`Invalid signature length: ${signatureBytes.length}, expected 96`)
      }
      signatures.push(signatureBytes)

      // deposit_data_root (32 字节，确保有 0x 前缀)
      let depositDataRoot = data.deposit_data_root
      if (!depositDataRoot.startsWith('0x')) {
        depositDataRoot = '0x' + depositDataRoot
      }
      deposit_data_roots.push(depositDataRoot)

      // amount (gwei 转 wei)
      const amountGwei = BigInt(data.amount)
      const amountWei = amountGwei * 1000000000n // 1 gwei = 10^9 wei
      amounts.push(amountWei)
    }

    // 合并为单个 bytes
    const pubkeysBytes = this.concatBytes(pubkeys)
    // withdrawal_credentials 只使用第一个验证者的（32 字节），不合并
    const withdrawalCredentialsBytes = firstWithdrawalCredentials
    const signaturesBytes = this.concatBytes(signatures)

    // 计算总金额
    const totalValue = amounts.reduce((sum, amount) => sum + amount, 0n)

    // 验证数据长度
    const validatorCount = depositDataList.length
    const expectedPubkeysLength = validatorCount * 48
    const expectedSignaturesLength = validatorCount * 96
    const expectedWithdrawalCredentialsLength = 32 // 必须是 32 字节，不是 validatorCount * 32

    if (pubkeysBytes.length !== expectedPubkeysLength) {
      throw new Error(`Pubkeys length mismatch: expected ${expectedPubkeysLength}, got ${pubkeysBytes.length}`)
    }
    if (signaturesBytes.length !== expectedSignaturesLength) {
      throw new Error(`Signatures length mismatch: expected ${expectedSignaturesLength}, got ${signaturesBytes.length}`)
    }
    if (withdrawalCredentialsBytes.length !== expectedWithdrawalCredentialsLength) {
      throw new Error(`Withdrawal credentials length mismatch: expected ${expectedWithdrawalCredentialsLength}, got ${withdrawalCredentialsBytes.length}`)
    }

    // 调试日志
    console.log('Batch Deposit Data:', {
      validatorCount,
      pubkeysLength: pubkeysBytes.length,
      withdrawalCredentialsLength: withdrawalCredentialsBytes.length,
      signaturesLength: signaturesBytes.length,
      depositDataRootsCount: deposit_data_roots.length,
      amountsCount: amounts.length,
      withdrawalCredentialsHex: '0x' + this.bytesToHex(withdrawalCredentialsBytes),
    })

    return {
      pubkeys: '0x' + this.bytesToHex(pubkeysBytes),
      withdrawal_credentials: '0x' + this.bytesToHex(withdrawalCredentialsBytes),
      signatures: '0x' + this.bytesToHex(signaturesBytes),
      deposit_data_roots,
      amounts,
      totalValue,
    }
  }

  /**
   * 通过 Batch Deposit 合约提交批量存款
   */
  static async submitBatchDeposit(
    contractAddress: string,
    depositDataList: DepositData[]
  ): Promise<string> {
    const { signer, provider } = useMetaMaskStore.getState()

    if (!signer || !provider) {
      throw new Error('MetaMask 未连接，请先连接 MetaMask')
    }

    // 准备批量数据
    const batchData = this.prepareBatchData(depositDataList)

    // 再次验证 withdrawal_credentials 长度（应该是 32 字节，即 64 个十六进制字符 + 0x = 66 字符）
    const withdrawalCredentialsHex = batchData.withdrawal_credentials
    const withdrawalCredentialsBytes = this.hexToBytes(withdrawalCredentialsHex)
    if (withdrawalCredentialsBytes.length !== 32) {
      throw new Error(
        `Withdrawal credentials length is incorrect: ${withdrawalCredentialsBytes.length} bytes (hex: ${withdrawalCredentialsHex}, length: ${withdrawalCredentialsHex.length} chars). ` +
        `Expected 32 bytes (66 hex chars with 0x prefix). ` +
        `This indicates a bug in prepareBatchData.`
      )
    }

    console.log('Final batch data before sending:', {
      withdrawalCredentialsLength: withdrawalCredentialsBytes.length,
      withdrawalCredentialsHex: withdrawalCredentialsHex.substring(0, 20) + '...',
      pubkeysLength: this.hexToBytes(batchData.pubkeys).length,
      signaturesLength: this.hexToBytes(batchData.signatures).length,
      depositDataRootsCount: batchData.deposit_data_roots.length,
      amountsCount: batchData.amounts.length,
    })

    // 创建合约实例
    const contract = new Contract(contractAddress, BATCH_DEPOSIT_ABI, signer)

    // 估算 gas
    let gasLimit: bigint
    try {
      gasLimit = await contract.batchDeposit.estimateGas(
        batchData.pubkeys,
        batchData.withdrawal_credentials,
        batchData.signatures,
        batchData.deposit_data_roots,
        batchData.amounts,
        { value: batchData.totalValue }
      )
      // 增加 20% 的 gas 缓冲
      gasLimit = (gasLimit * 120n) / 100n
    } catch (error) {
      console.warn('Gas 估算失败，使用默认值:', error)
      // 默认值：每个验证者约 200k gas，加上基础 gas
      gasLimit = BigInt(200000 * depositDataList.length + 100000)
    }

    // 发送交易
    const tx = await contract.batchDeposit(
      batchData.pubkeys,
      batchData.withdrawal_credentials,
      batchData.signatures,
      batchData.deposit_data_roots,
      batchData.amounts,
      {
        value: batchData.totalValue,
        gasLimit,
      }
    )

    return tx.hash
  }

  /**
   * 通过官方 Deposit 合约提交单个存款
   */
  static async submitSingleDeposit(
    contractAddress: string,
    depositData: DepositData
  ): Promise<string> {
    const { signer } = useMetaMaskStore.getState()

    if (!signer) {
      throw new Error('MetaMask 未连接，请先连接 MetaMask')
    }

    // 转换数据
    const pubkeyBytes = this.hexToBytes(depositData.pubkey)
    const withdrawalBytes = this.hexToBytes(depositData.withdrawal_credentials)
    const signatureBytes = this.hexToBytes(depositData.signature)
    // 确保 deposit_data_root 有 0x 前缀
    let depositDataRoot = depositData.deposit_data_root
    if (!depositDataRoot.startsWith('0x')) {
      depositDataRoot = '0x' + depositDataRoot
    }

    // 计算金额（gwei 转 wei）
    const amountGwei = BigInt(depositData.amount)
    const amountWei = amountGwei * 1000000000n

    // 创建合约实例
    const contract = new Contract(contractAddress, DEPOSIT_CONTRACT_ABI, signer)

    // 估算 gas
    let gasLimit: bigint
    try {
      gasLimit = await contract.deposit.estimateGas(
        '0x' + this.bytesToHex(pubkeyBytes),
        '0x' + this.bytesToHex(withdrawalBytes),
        '0x' + this.bytesToHex(signatureBytes),
        depositDataRoot,
        { value: amountWei }
      )
      gasLimit = (gasLimit * 120n) / 100n // 增加 20% 缓冲
    } catch (error) {
      console.warn('Gas 估算失败，使用默认值:', error)
      gasLimit = 200000n // 默认 200k gas
    }

    // 发送交易
    const tx = await contract.deposit(
      '0x' + this.bytesToHex(pubkeyBytes),
      '0x' + this.bytesToHex(withdrawalBytes),
      '0x' + this.bytesToHex(signatureBytes),
      depositDataRoot,
      {
        value: amountWei,
        gasLimit,
      }
    )

    return tx.hash
  }

  /**
   * 通过官方 Deposit 合约提交多个存款（逐个发送）
   */
  static async submitMultipleDeposits(
    contractAddress: string,
    depositDataList: DepositData[]
  ): Promise<string[]> {
    const txHashes: string[] = []

    for (const depositData of depositDataList) {
      const txHash = await this.submitSingleDeposit(contractAddress, depositData)
      txHashes.push(txHash)
    }

    return txHashes
  }

  // 工具函数
  private static hexToBytes(hex: string): Uint8Array {
    if (!hex) {
      throw new Error('Hex string is empty or null')
    }
    const cleanHex = hex.startsWith('0x') ? hex.slice(2) : hex
    if (cleanHex.length % 2 !== 0) {
      throw new Error(`Invalid hex string length: ${hex} (length: ${cleanHex.length})`)
    }
    const bytes = new Uint8Array(cleanHex.length / 2)
    for (let i = 0; i < cleanHex.length; i += 2) {
      bytes[i / 2] = parseInt(cleanHex.substr(i, 2), 16)
    }
    return bytes
  }

  private static bytesToHex(bytes: Uint8Array): string {
    return Array.from(bytes)
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')
  }

  private static concatBytes(arrays: Uint8Array[]): Uint8Array {
    const totalLength = arrays.reduce((sum, arr) => sum + arr.length, 0)
    const result = new Uint8Array(totalLength)
    let offset = 0
    for (const arr of arrays) {
      result.set(arr, offset)
      offset += arr.length
    }
    return result
  }
}

