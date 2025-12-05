import React, { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Typography,
  Row,
  Col,
  Statistic,
  Alert,
  Descriptions,
  Divider,
  Spin,
  message,
} from 'antd'
import {
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import {
  web3signerApi,
  Web3SignerStatus,
  Web3SignerKeysResponse,
  Web3SignerSyncStatus,
} from '../../api/web3signer'

const { Title } = Typography

const Web3SignerMonitor: React.FC = () => {
  const [status, setStatus] = useState<Web3SignerStatus | null>(null)
  const [keys, setKeys] = useState<Web3SignerKeysResponse | null>(null)
  const [syncStatus, setSyncStatus] = useState<Web3SignerSyncStatus | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [statusData, keysData, syncData] = await Promise.all([
        web3signerApi.getStatus(),
        web3signerApi.getKeys('both'),
        web3signerApi.getSyncStatus('both'),
      ])
      setStatus(statusData)
      setKeys(keysData)
      setSyncStatus(syncData)
    } catch (error: any) {
      message.error(`加载数据失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const keysColumns = [
    {
      title: '公钥',
      dataIndex: 'pubkey',
      key: 'pubkey',
      render: (text: string) => (
        <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
          {text.slice(0, 20)}...
        </span>
      ),
    },
    {
      title: '在数据库中',
      dataIndex: 'in_database',
      key: 'in_database',
      render: (inDb: boolean) =>
        inDb ? (
          <Tag color="success">是</Tag>
        ) : (
          <Tag color="warning">否</Tag>
        ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string | null) => (status ? <Tag>{status}</Tag> : '-'),
    },
    {
      title: '激活时间',
      dataIndex: 'activated_at',
      key: 'activated_at',
      render: (time: string | null) =>
        time ? new Date(time).toLocaleString() : '-',
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Title level={2}>Web3Signer 监控</Title>
        <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
          刷新
        </Button>
      </Space>

      <Spin spinning={loading}>
        {/* 状态卡片 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card>
              <Statistic
                title="Web3Signer-1"
                value={status?.primary.healthy ? '运行中' : '异常'}
                prefix={status?.primary.healthy ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                valueStyle={{ color: status?.primary.healthy ? '#3f8600' : '#cf1322' }}
              />
              <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                {status?.primary.url}
              </div>
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="Web3Signer-2"
                value={status?.secondary.healthy ? '运行中' : '异常'}
                prefix={status?.secondary.healthy ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                valueStyle={{ color: status?.secondary.healthy ? '#3f8600' : '#cf1322' }}
              />
              <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                {status?.secondary.url}
              </div>
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="HAProxy"
                value={status?.haproxy.healthy ? '运行中' : '异常'}
                prefix={status?.haproxy.healthy ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                valueStyle={{ color: status?.haproxy.healthy ? '#3f8600' : '#cf1322' }}
              />
              <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                {status?.haproxy.url}
              </div>
            </Card>
          </Col>
        </Row>

        {/* 密钥统计 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={12}>
            <Card title="Web3Signer-1 密钥统计">
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="已加载密钥"
                    value={keys?.primary?.count || 0}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="在数据库中"
                    value={
                      keys?.primary?.keys?.filter((k) => k.in_database).length || 0
                    }
                    valueStyle={{ color: '#3f8600' }}
                  />
                </Col>
              </Row>
              {keys?.primary?.error && (
                <Alert
                  message="错误"
                  description={keys.primary.error}
                  type="error"
                  style={{ marginTop: 16 }}
                />
              )}
            </Card>
          </Col>
          <Col span={12}>
            <Card title="Web3Signer-2 密钥统计">
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="已加载密钥"
                    value={keys?.secondary?.count || 0}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="在数据库中"
                    value={
                      keys?.secondary?.keys?.filter((k) => k.in_database).length || 0
                    }
                    valueStyle={{ color: '#3f8600' }}
                  />
                </Col>
              </Row>
              {keys?.secondary?.error && (
                <Alert
                  message="错误"
                  description={keys.secondary.error}
                  type="error"
                  style={{ marginTop: 16 }}
                />
              )}
            </Card>
          </Col>
        </Row>

        {/* 同步状态对比 */}
        {(syncStatus?.primary || syncStatus?.secondary) && (
          <>
            <Divider>同步状态对比</Divider>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              {syncStatus.primary && !syncStatus.primary.error && (
                <Col span={12}>
                  <Card title="Web3Signer-1 同步状态">
                    <Descriptions column={1} bordered size="small">
                      <Descriptions.Item label="数据库 ACTIVE 密钥数">
                        {syncStatus.primary.stats.db_active_count}
                      </Descriptions.Item>
                      <Descriptions.Item label="Web3Signer 密钥数">
                        {syncStatus.primary.stats.web3signer_count}
                      </Descriptions.Item>
                      <Descriptions.Item label="已同步">
                        <Tag color="success">
                          {syncStatus.primary.stats.synced_count}
                        </Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="缺失（在数据库但未加载）">
                        <Tag color="warning">
                          {syncStatus.primary.stats.missing_count}
                        </Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="多余（已加载但不在数据库）">
                        <Tag color="error">
                          {syncStatus.primary.stats.extra_count}
                        </Tag>
                      </Descriptions.Item>
                    </Descriptions>
                    {syncStatus.primary.missing_in_web3signer.length > 0 && (
                      <Alert
                        message="缺失的密钥"
                        description={
                          <div>
                            {syncStatus.primary.missing_in_web3signer.slice(0, 5).map((key) => (
                              <div key={key} style={{ fontFamily: 'monospace', fontSize: '11px' }}>
                                {key.slice(0, 20)}...
                              </div>
                            ))}
                            {syncStatus.primary.missing_in_web3signer.length > 5 && (
                              <div>... 还有 {syncStatus.primary.missing_in_web3signer.length - 5} 个</div>
                            )}
                          </div>
                        }
                        type="warning"
                        style={{ marginTop: 16 }}
                        icon={<WarningOutlined />}
                      />
                    )}
                    {syncStatus.primary.extra_in_web3signer.length > 0 && (
                      <Alert
                        message="多余的密钥"
                        description={
                          <div>
                            {syncStatus.primary.extra_in_web3signer.slice(0, 5).map((key) => (
                              <div key={key} style={{ fontFamily: 'monospace', fontSize: '11px' }}>
                                {key.slice(0, 20)}...
                              </div>
                            ))}
                            {syncStatus.primary.extra_in_web3signer.length > 5 && (
                              <div>... 还有 {syncStatus.primary.extra_in_web3signer.length - 5} 个</div>
                            )}
                          </div>
                        }
                        type="error"
                        style={{ marginTop: 16 }}
                        icon={<WarningOutlined />}
                      />
                    )}
                  </Card>
                </Col>
              )}
              {syncStatus.secondary && !syncStatus.secondary.error && (
                <Col span={12}>
                  <Card title="Web3Signer-2 同步状态">
                    <Descriptions column={1} bordered size="small">
                      <Descriptions.Item label="数据库 ACTIVE 密钥数">
                        {syncStatus.secondary.stats.db_active_count}
                      </Descriptions.Item>
                      <Descriptions.Item label="Web3Signer 密钥数">
                        {syncStatus.secondary.stats.web3signer_count}
                      </Descriptions.Item>
                      <Descriptions.Item label="已同步">
                        <Tag color="success">
                          {syncStatus.secondary.stats.synced_count}
                        </Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="缺失（在数据库但未加载）">
                        <Tag color="warning">
                          {syncStatus.secondary.stats.missing_count}
                        </Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="多余（已加载但不在数据库）">
                        <Tag color="error">
                          {syncStatus.secondary.stats.extra_count}
                        </Tag>
                      </Descriptions.Item>
                    </Descriptions>
                    {syncStatus.secondary.missing_in_web3signer.length > 0 && (
                      <Alert
                        message="缺失的密钥"
                        description={
                          <div>
                            {syncStatus.secondary.missing_in_web3signer.slice(0, 5).map((key) => (
                              <div key={key} style={{ fontFamily: 'monospace', fontSize: '11px' }}>
                                {key.slice(0, 20)}...
                              </div>
                            ))}
                            {syncStatus.secondary.missing_in_web3signer.length > 5 && (
                              <div>... 还有 {syncStatus.secondary.missing_in_web3signer.length - 5} 个</div>
                            )}
                          </div>
                        }
                        type="warning"
                        style={{ marginTop: 16 }}
                        icon={<WarningOutlined />}
                      />
                    )}
                    {syncStatus.secondary.extra_in_web3signer.length > 0 && (
                      <Alert
                        message="多余的密钥"
                        description={
                          <div>
                            {syncStatus.secondary.extra_in_web3signer.slice(0, 5).map((key) => (
                              <div key={key} style={{ fontFamily: 'monospace', fontSize: '11px' }}>
                                {key.slice(0, 20)}...
                              </div>
                            ))}
                            {syncStatus.secondary.extra_in_web3signer.length > 5 && (
                              <div>... 还有 {syncStatus.secondary.extra_in_web3signer.length - 5} 个</div>
                            )}
                          </div>
                        }
                        type="error"
                        style={{ marginTop: 16 }}
                        icon={<WarningOutlined />}
                      />
                    )}
                  </Card>
                </Col>
              )}
            </Row>
          </>
        )}

        {/* 密钥列表 */}
        <Row gutter={16}>
          {keys?.primary && (
            <Col span={12}>
              <Card title="Web3Signer-1 密钥列表">
                <Table
                  columns={keysColumns}
                  dataSource={keys.primary.keys}
                  rowKey="pubkey"
                  pagination={{ pageSize: 10 }}
                  size="small"
                />
              </Card>
            </Col>
          )}
          {keys?.secondary && (
            <Col span={12}>
              <Card title="Web3Signer-2 密钥列表">
                <Table
                  columns={keysColumns}
                  dataSource={keys.secondary.keys}
                  rowKey="pubkey"
                  pagination={{ pageSize: 10 }}
                  size="small"
                />
              </Card>
            </Col>
          )}
        </Row>
      </Spin>
    </div>
  )
}

export default Web3SignerMonitor

