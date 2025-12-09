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
      console.log('后端返回的原始状态:', {
        status: response.status,
        is_running: response.is_running,
        message: response.message,
        error: response.error
      })
      
      // 确保状态一致性：如果 status 不是 'running'，则 is_running 应该为 false
      const normalizedStatus: NetworkStatus = {
        ...response,
        // 如果 status 字段不是 'running'，强制设置 is_running 为 false
        is_running: response.status === 'running' && response.is_running === true,
        // 如果 is_running 为 false，确保 status 不是 'running'
        status: response.is_running === true && response.status === 'running' ? 'running' : 
                response.status === 'error' ? 'error' : 'stopped'
      }
      
      console.log('规范化后的状态:', {
        status: normalizedStatus.status,
        is_running: normalizedStatus.is_running
      })
      
      setStatus(normalizedStatus)
      // 如果状态是 error，但 is_running 为 false，可能是 dev net 未启动（正常情况）
      if (normalizedStatus.status === 'error' && !normalizedStatus.is_running) {
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
      message.success('网络启动中，请稍候...')
      
      // 轮询状态直到网络真正启动或超时
      const maxAttempts = 30 // 最多尝试30次（30秒）
      let attempts = 0
      
      const pollStatus = async (): Promise<void> => {
        attempts++
        try {
          const response = await networkApi.getStatus() as any
          const isRunning = response.status === 'running' && response.is_running === true
          
          if (isRunning) {
            // 网络已启动，更新状态
            const normalizedStatus: NetworkStatus = {
              ...response,
              is_running: true,
              status: 'running'
            }
            setStatus(normalizedStatus)
            await loadInfo()
            message.success('网络启动成功')
            setActionLoading(false)
          } else if (attempts < maxAttempts) {
            // 继续轮询
            setTimeout(pollStatus, 1000)
          } else {
            // 超时，刷新状态但不显示错误（可能还在启动中）
            await loadStatus()
            await loadInfo()
            message.warning('网络启动可能需要更长时间，请稍后刷新状态')
            setActionLoading(false)
          }
        } catch (error: any) {
          // 轮询失败，刷新状态
          await loadStatus()
          await loadInfo()
          if (attempts >= maxAttempts) {
            message.warning('网络启动可能需要更长时间，请稍后刷新状态')
          }
          setActionLoading(false)
        }
      }
      
      // 延迟2秒后开始轮询（给启动一些时间）
      setTimeout(pollStatus, 2000)
    } catch (error: any) {
      message.error(`启动网络失败: ${error.message}`)
      setActionLoading(false)
      // 刷新状态以反映当前实际情况
      await loadStatus()
    }
  }

  const handleStop = async () => {
    setActionLoading(true)
    try {
      await networkApi.stop()
      message.success('网络停止中，请稍候...')
      
      // 轮询状态直到网络真正停止或超时
      const maxAttempts = 20 // 最多尝试20次（20秒）
      let attempts = 0
      
      const pollStatus = async (): Promise<void> => {
        attempts++
        try {
          const response = await networkApi.getStatus() as any
          const isRunning = response.status === 'running' && response.is_running === true
          
          if (!isRunning) {
            // 网络已停止，更新状态
            const normalizedStatus: NetworkStatus = {
              ...response,
              is_running: false,
              status: response.status === 'error' ? 'error' : 'stopped'
            }
            setStatus(normalizedStatus)
            setInfo(null) // 清除网络信息
            message.success('网络已停止')
            setActionLoading(false)
          } else if (attempts < maxAttempts) {
            // 继续轮询
            setTimeout(pollStatus, 1000)
          } else {
            // 超时，刷新状态但不显示错误（可能还在停止中）
            await loadStatus()
            message.warning('网络停止可能需要更长时间，请稍后刷新状态')
            setActionLoading(false)
          }
        } catch (error: any) {
          // 轮询失败，刷新状态
          await loadStatus()
          if (attempts >= maxAttempts) {
            message.warning('网络停止可能需要更长时间，请稍后刷新状态')
          }
          setActionLoading(false)
        }
      }
      
      // 延迟1秒后开始轮询（给停止一些时间）
      setTimeout(pollStatus, 1000)
    } catch (error: any) {
      message.error(`停止网络失败: ${error.message}`)
      setActionLoading(false)
      // 刷新状态以反映当前实际情况
      await loadStatus()
    }
  }

  const getStatusTag = () => {
    if (!status) return <Tag>未知</Tag>
    // 确保状态一致性：只有当 status 为 'running' 且 is_running 为 true 时才显示运行中
    const isRunning = status.status === 'running' && status.is_running === true
    if (isRunning) {
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
            {status?.status === 'running' && status?.is_running === true ? (
              <Button
                type="primary"
                danger
                icon={<StopOutlined />}
                onClick={handleStop}
                loading={actionLoading}
                disabled={actionLoading}
              >
                停止网络
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleStart}
                loading={actionLoading}
                disabled={actionLoading}
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
      {status?.status === 'running' && status?.is_running === true && info && (
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
      {status?.status === 'running' && status?.is_running === true && status.enclave_info && (
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

