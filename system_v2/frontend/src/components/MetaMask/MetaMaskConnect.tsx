import React, { useEffect, useState } from 'react'
import { Button, Space, Typography, Popover, message, Tag, Divider } from 'antd'
import { WalletOutlined, DisconnectOutlined, CopyOutlined, ReloadOutlined } from '@ant-design/icons'
import { useMetaMaskStore } from '../../stores/metamaskStore'
import { MetaMaskService } from '../../services/metamask'

const { Text } = Typography

const MetaMaskConnect: React.FC = () => {
  const {
    isConnected,
    account,
    chainId,
    balance,
    isLoading,
    connect,
    disconnect,
    refreshBalance,
    initialize,
  } = useMetaMaskStore()

  const [isInstalled, setIsInstalled] = useState(false)

  useEffect(() => {
    setIsInstalled(MetaMaskService.isMetaMaskInstalled())
    
    // 初始化（检查是否已连接）
    if (MetaMaskService.isMetaMaskInstalled()) {
      initialize()
    }
  }, [initialize])

  const handleConnect = async () => {
    try {
      await connect()
      message.success('MetaMask 连接成功')
    } catch (error: any) {
      message.error(error.message || '连接失败')
    }
  }

  const handleDisconnect = () => {
    disconnect()
    message.info('已断开 MetaMask 连接')
  }

  const handleCopyAddress = () => {
    if (account) {
      navigator.clipboard.writeText(account)
      message.success('地址已复制到剪贴板')
    }
  }

  const formatAddress = (address: string) => {
    if (!address) return ''
    return `${address.slice(0, 6)}...${address.slice(-4)}`
  }

  const formatBalance = (balanceWei: string | null) => {
    if (!balanceWei) return '0.0000'
    try {
      const balanceEth = BigInt(balanceWei)
      const ethValue = Number(balanceEth) / 1e18
      return ethValue.toFixed(4)
    } catch {
      return '0.0000'
    }
  }

  const formatChainId = (chainId: bigint | null) => {
    if (!chainId) return 'Unknown'
    return `0x${chainId.toString(16)}`
  }

  // MetaMask 未安装
  if (!isInstalled) {
    return (
      <Popover
        content={
          <div>
            <Text>请先安装 MetaMask 扩展</Text>
            <br />
            <Button
              type="link"
              href="https://metamask.io/download/"
              target="_blank"
              style={{ padding: 0 }}
            >
              下载 MetaMask
            </Button>
          </div>
        }
        title="MetaMask 未安装"
      >
        <Button icon={<WalletOutlined />} disabled>
          MetaMask 未安装
        </Button>
      </Popover>
    )
  }

  // 未连接状态
  if (!isConnected) {
    return (
      <Button
        type="primary"
        icon={<WalletOutlined />}
        onClick={handleConnect}
        loading={isLoading}
      >
        连接 MetaMask
      </Button>
    )
  }

  // 已连接状态
  const content = (
    <div style={{ minWidth: 280 }}>
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <div>
          <Text type="secondary" style={{ fontSize: '12px' }}>账户地址</Text>
          <br />
          <Space>
            <Text copyable={{ text: account || '' }} style={{ fontFamily: 'monospace' }}>
              {formatAddress(account || '')}
            </Text>
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={handleCopyAddress}
            />
          </Space>
        </div>
        
        <Divider style={{ margin: '8px 0' }} />
        
        <div>
          <Text type="secondary" style={{ fontSize: '12px' }}>链 ID</Text>
          <br />
          <Tag>{formatChainId(chainId)}</Tag>
        </div>
        
        <div>
          <Text type="secondary" style={{ fontSize: '12px' }}>余额</Text>
          <br />
          <Space>
            <Text strong>{formatBalance(balance)} ETH</Text>
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined />}
              onClick={refreshBalance}
            />
          </Space>
        </div>
        
        <Divider style={{ margin: '8px 0' }} />
        
        <Button
          type="default"
          danger
          icon={<DisconnectOutlined />}
          onClick={handleDisconnect}
          block
        >
          断开连接
        </Button>
      </Space>
    </div>
  )

  return (
    <Popover content={content} title="MetaMask 连接" trigger="click" placement="bottomRight">
      <Button icon={<WalletOutlined />} type="default">
        {formatAddress(account || '')}
      </Button>
    </Popover>
  )
}

export default MetaMaskConnect

