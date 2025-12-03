import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Tag, Typography, Divider, Space } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { monitoringApi, SystemOverview } from '../../api/monitoring'
import { networkApi, NetworkStatus } from '../../api/network'
import { clientsApi, ClientInstance } from '../../api/clients'

const { Title, Text } = Typography

const Dashboard: React.FC = () => {
  const [overview, setOverview] = useState<SystemOverview | null>(null)
  const [networkStatus, setNetworkStatus] = useState<NetworkStatus | null>(null)
  const [clients, setClients] = useState<ClientInstance[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAllData()
    const interval = setInterval(loadAllData, 30000) // 每30秒刷新
    return () => clearInterval(interval)
  }, [])

  const loadAllData = async () => {
    setLoading(true)
    try {
      await Promise.all([
        loadOverview(),
        loadNetworkStatus(),
        loadClients(),
      ])
    } finally {
      setLoading(false)
    }
  }

  const loadOverview = async () => {
    try {
      const response = await monitoringApi.overview() as any
      setOverview(response as unknown as SystemOverview)
    } catch (error) {
      console.error('加载系统概览失败:', error)
    }
  }

  const loadNetworkStatus = async () => {
    try {
      const response = await networkApi.getStatus() as any
      setNetworkStatus(response as NetworkStatus)
    } catch (error) {
      console.error('加载网络状态失败:', error)
    }
  }

  const loadClients = async () => {
    try {
      const response = await clientsApi.list() as any
      setClients(response || [])
    } catch (error) {
      console.error('加载客户端列表失败:', error)
    }
  }

  const getHealthTag = (healthy: boolean) => {
    return healthy ? (
      <Tag color="success" icon={<CheckCircleOutlined />}>正常</Tag>
    ) : (
      <Tag color="error" icon={<CloseCircleOutlined />}>异常</Tag>
    )
  }

  const getNetworkStatusTag = () => {
    if (!networkStatus) return <Tag>未知</Tag>
    return networkStatus.is_running ? (
      <Tag color="success" icon={<CheckCircleOutlined />}>运行中</Tag>
    ) : (
      <Tag color="default" icon={<CloseCircleOutlined />}>已停止</Tag>
    )
  }

  return (
    <div>
      <Title level={2}>系统仪表板</Title>

      {/* 系统健康状态 */}
      <Card
        title="系统健康状态"
        extra={
          <Space>
            <Text type="secondary">最后更新: {new Date().toLocaleTimeString()}</Text>
            <ReloadOutlined onClick={loadAllData} style={{ cursor: 'pointer' }} />
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        {overview?.system_health && (
          <Row gutter={16}>
            <Col span={4}>
              <Space direction="vertical" align="center">
                <Text>Vault</Text>
                {getHealthTag(overview.system_health.vault)}
              </Space>
            </Col>
            <Col span={4}>
              <Space direction="vertical" align="center">
                <Text>PostgreSQL</Text>
                {getHealthTag(overview.system_health.postgresql)}
              </Space>
            </Col>
            <Col span={4}>
              <Space direction="vertical" align="center">
                <Text>Web3Signer Primary</Text>
                {getHealthTag(overview.system_health.web3signer_primary)}
              </Space>
            </Col>
            <Col span={4}>
              <Space direction="vertical" align="center">
                <Text>Web3Signer Secondary</Text>
                {getHealthTag(overview.system_health.web3signer_secondary)}
              </Space>
            </Col>
            <Col span={4}>
              <Space direction="vertical" align="center">
                <Text>HAProxy</Text>
                {getHealthTag(overview.system_health.haproxy)}
              </Space>
            </Col>
            <Col span={4}>
              <Space direction="vertical" align="center">
                <Text>Beacon API</Text>
                {getHealthTag(overview.system_health.beacon_api)}
              </Space>
            </Col>
          </Row>
        )}
      </Card>

      {/* 验证者统计 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总密钥数"
              value={overview?.total_keys || 0}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃验证者"
              value={overview?.active_validators || 0}
              loading={loading}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总存款数"
              value={overview?.total_deposits || 0}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总收益 (ETH)"
              value={overview?.total_rewards_eth || 0}
              precision={4}
              loading={loading}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 网络状态 */}
      <Card title="网络状态" style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col span={12}>
            <Space direction="vertical">
              <Text strong>Kurtosis 网络</Text>
              <div>
                <Text>状态: </Text>
                {getNetworkStatusTag()}
              </div>
              {networkStatus && (
                <div>
                  <Text>Enclave: </Text>
                  <Text code>{networkStatus.enclave_name}</Text>
                </div>
              )}
            </Space>
          </Col>
          <Col span={12}>
            {networkStatus?.is_running && overview?.system_health?.beacon_api && (
              <Space direction="vertical">
                <Text strong>Beacon API</Text>
                <div>
                  <Text>状态: </Text>
                  {getHealthTag(overview.system_health.beacon_api)}
                </div>
              </Space>
            )}
          </Col>
        </Row>
      </Card>

      {/* 客户端状态 */}
      <Card title="客户端状态">
        {clients.length === 0 ? (
          <Text type="secondary">暂无客户端</Text>
        ) : (
          <Row gutter={16}>
            {clients.map((client) => (
              <Col span={8} key={client.id} style={{ marginBottom: 16 }}>
                <Card size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text strong>{client.name}</Text>
                      <Tag style={{ marginLeft: 8 }}>{client.client_type}</Tag>
                    </div>
                    <div>
                      <Text type="secondary">密钥数: </Text>
                      <Text>{client.key_count}</Text>
                    </div>
                    <div>
                      <Text type="secondary">状态: </Text>
                      <Tag>{client.status}</Tag>
                    </div>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Card>
    </div>
  )
}

export default Dashboard
