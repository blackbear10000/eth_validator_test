import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Space,
  Descriptions,
  Tag,
  message,
  Spin,
  Typography,
  Divider,
} from 'antd'
import {
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { networkApi, NetworkStatus, NetworkInfo } from '../../api/network'

const { Title, Text } = Typography

const NetworkManager: React.FC = () => {
  const [status, setStatus] = useState<NetworkStatus | null>(null)
  const [info, setInfo] = useState<NetworkInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    loadStatus()
    loadInfo()
  }, [])

  const loadStatus = async () => {
    setLoading(true)
    try {
      const response = await networkApi.getStatus() as any
      setStatus(response as NetworkStatus)
      // 如果状态是 error，但 is_running 为 false，可能是 dev net 未启动（正常情况）
      if (response.status === 'error' && !response.is_running) {
        // 不显示错误消息，因为 dev net 未启动是正常状态
        console.log('Dev net 未启动或 engine 未就绪:', response.message || response.error)
      }
    } catch (error: any) {
      // 如果请求失败，设置默认的 stopped 状态
      console.error('加载网络状态失败:', error)
      setStatus({
        enclave_name: 'eth-devnet',
        status: 'stopped',
        is_running: false,
        error: error.message
      } as NetworkStatus)
      // 不显示错误消息，因为 dev net 未启动是正常状态
    } finally {
      setLoading(false)
    }
  }

  const loadInfo = async () => {
    try {
      const response = await networkApi.getInfo() as any
      setInfo(response as NetworkInfo)
    } catch (error: any) {
      // 网络未运行时获取信息会失败，这是正常的
      console.log('获取网络信息失败（可能网络未运行）:', error)
    }
  }

  const handleStart = async () => {
    setActionLoading(true)
    try {
      await networkApi.start()
      message.success('网络启动成功')
      setTimeout(() => {
        loadStatus()
        loadInfo()
      }, 2000)
    } catch (error: any) {
      message.error(`启动网络失败: ${error.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const handleStop = async () => {
    setActionLoading(true)
    try {
      await networkApi.stop()
      message.success('网络已停止')
      setTimeout(() => {
        loadStatus()
        loadInfo()
      }, 1000)
    } catch (error: any) {
      message.error(`停止网络失败: ${error.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const getStatusTag = () => {
    if (!status) return <Tag>未知</Tag>
    if (status.is_running) {
      return <Tag color="success" icon={<CheckCircleOutlined />}>运行中</Tag>
    }
    return <Tag color="default" icon={<CloseCircleOutlined />}>已停止</Tag>
  }

  return (
    <div>
      <Title level={2}>网络管理</Title>

      {/* 网络状态卡片 */}
      <Card
        title="网络状态"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                loadStatus()
                loadInfo()
              }}
              loading={loading}
            >
              刷新
            </Button>
            {status?.is_running ? (
              <Button
                type="primary"
                danger
                icon={<StopOutlined />}
                onClick={handleStop}
                loading={actionLoading}
              >
                停止网络
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleStart}
                loading={actionLoading}
              >
                启动网络
              </Button>
            )}
          </Space>
        }
      >
        <Spin spinning={loading}>
          <Descriptions column={2} bordered>
            <Descriptions.Item label="Enclave 名称">
              {status?.enclave_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {getStatusTag()}
            </Descriptions.Item>
            {status?.error && (
              <Descriptions.Item label="错误信息" span={2}>
                <Text type="danger">{status.error}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        </Spin>
      </Card>

      {/* 网络信息卡片 */}
      {status?.is_running && info && (
        <>
          <Divider />
          <Card title="网络信息">
            <Descriptions column={2} bordered>
              {info.genesis && (
                <>
                  <Descriptions.Item label="Genesis Fork Version" span={1}>
                    <Text code>
                      {info.genesis.data?.genesis_fork_version || '-'}
                    </Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="Genesis Time" span={1}>
                    {info.genesis.data?.genesis_time
                      ? new Date(parseInt(info.genesis.data.genesis_time) * 1000).toLocaleString()
                      : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Genesis Validators Root" span={2}>
                    <Text code style={{ fontSize: '12px' }}>
                      {info.genesis.data?.genesis_validators_root?.slice(0, 20)}...
                    </Text>
                  </Descriptions.Item>
                </>
              )}
              {info.fork_schedule && (
                <Descriptions.Item label="Fork Schedule" span={2}>
                  <pre style={{ fontSize: '12px', maxHeight: '200px', overflow: 'auto' }}>
                    {JSON.stringify(info.fork_schedule, null, 2)}
                  </pre>
                </Descriptions.Item>
              )}
              {info.rpc_url && (
                <Descriptions.Item label="执行层 RPC URL" span={1}>
                  <Text code copyable>{info.rpc_url}</Text>
                </Descriptions.Item>
              )}
              {info.ws_url && (
                <Descriptions.Item label="执行层 WebSocket URL" span={1}>
                  <Text code copyable>{info.ws_url}</Text>
                </Descriptions.Item>
              )}
              {info.beacon_api_url && (
                <Descriptions.Item label="Beacon API URL" span={2}>
                  <Text code copyable>{info.beacon_api_url}</Text>
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </>
      )}

      {/* Enclave 详细信息 */}
      {status?.is_running && status.enclave_info && (
        <>
          <Divider />
          <Card title="Enclave 详细信息">
            {status.enclave_info.raw_output ? (
              <pre style={{ 
                fontSize: '12px', 
                maxHeight: '400px', 
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontFamily: 'monospace',
                backgroundColor: '#f5f5f5',
                padding: '12px',
                borderRadius: '4px'
              }}>
                {status.enclave_info.raw_output}
              </pre>
            ) : (
              <pre style={{ fontSize: '12px', maxHeight: '400px', overflow: 'auto' }}>
                {JSON.stringify(status.enclave_info, null, 2)}
              </pre>
            )}
          </Card>
        </>
      )}
    </div>
  )
}

export default NetworkManager

