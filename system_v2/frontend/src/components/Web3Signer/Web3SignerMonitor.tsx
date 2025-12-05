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
  PoweroffOutlined,
  SyncOutlined,
  DeleteOutlined,
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
  const [syncing, setSyncing] = useState(false)
  const [restarting, setRestarting] = useState(false)
  const [cleaning, setCleaning] = useState(false)

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

  const handleSyncConfigs = async () => {
    setSyncing(true)
    try {
      const result = await web3signerApi.syncConfigs()
      if (result.needs_restart) {
        message.warning(
          '配置文件已同步，但 Web3Signer 需要重启才能加载新密钥。请点击"重启 Web3Signer"按钮。',
          10
        )
      } else {
        message.success(result.message || '配置文件已同步并重新加载')
      }
      // 重新加载数据
      await loadData()
    } catch (error: any) {
      message.error(`同步配置失败: ${error.message}`)
    } finally {
      setSyncing(false)
    }
  }

  const handleRestart = async () => {
    Modal.confirm({
      title: '确认重启 Web3Signer',
      content: '重启 Web3Signer 容器会导致短暂的服务中断。HAProxy 会自动处理故障转移。是否继续？',
      okText: '确认重启',
      cancelText: '取消',
      onOk: async () => {
        setRestarting(true)
        try {
          const result = await web3signerApi.restart()
          if (result.success) {
            message.success('Web3Signer 容器重启成功，等待服务恢复...')
            // 等待一段时间后重新加载数据
            setTimeout(() => {
              loadData()
            }, 15000)
          } else {
            message.error('Web3Signer 容器重启失败，请手动重启：docker restart web3signer-1 web3signer-2')
          }
        } catch (error: any) {
          if (error.response?.status === 503) {
            message.warning(
              '后端无法执行 Docker 命令。请手动重启 Web3Signer 容器：docker restart web3signer-1 web3signer-2',
              10
            )
          } else {
            message.error(`重启失败: ${error.message}`)
          }
        } finally {
          setRestarting(false)
        }
      },
    })
  }

  const handleCleanup = async () => {
    Modal.confirm({
      title: '确认清理孤立配置文件',
      content: '这将删除所有数据库中不存在的密钥对应的配置文件。此操作不可恢复。是否继续？',
      okText: '确认清理',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        setCleaning(true)
        try {
          const result = await web3signerApi.cleanupConfigs()
          if (result.success) {
            message.success(`已清理 ${result.removed} 个孤立配置文件`)
            if (result.files.length > 0) {
              Modal.info({
                title: '已删除的文件',
                content: (
                  <div>
                    <p>共删除 {result.files.length} 个文件：</p>
                    <ul style={{ maxHeight: '300px', overflow: 'auto' }}>
                      {result.files.map((file, index) => (
                        <li key={index} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                          {file}
                        </li>
                      ))}
                    </ul>
                  </div>
                ),
                width: 600,
              })
            }
            // 重新加载数据
            await loadData()
          } else {
            message.error(`清理失败: ${result.message}`)
          }
        } catch (error: any) {
          message.error(`清理失败: ${error.message}`)
        } finally {
          setCleaning(false)
        }
      },
    })
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
        <Space>
          <Button
            icon={<SyncOutlined />}
            onClick={handleSyncConfigs}
            loading={syncing}
            type="default"
          >
            同步配置
          </Button>
          <Button
            icon={<DeleteOutlined />}
            onClick={handleCleanup}
            loading={cleaning}
            danger
          >
            清理孤立文件
          </Button>
          <Button
            icon={<PoweroffOutlined />}
            onClick={handleRestart}
            loading={restarting}
            danger
          >
            重启 Web3Signer
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
            刷新
          </Button>
        </Space>
      </Space>

      {/* 显示警告信息 */}
      {syncStatus && (
        <>
          {syncStatus.primary && syncStatus.primary.stats.missing_count > 0 && (
            <Alert
              message="Web3Signer 未加载所有密钥"
              description={
                <div>
                  <p>
                    Web3Signer-1 缺少 {syncStatus.primary.stats.missing_count} 个密钥。
                    Web3Signer 使用 key-store-path 配置时，需要重启容器才能加载新配置文件。
                  </p>
                  <p style={{ marginTop: 8 }}>
                    请点击"重启 Web3Signer"按钮或手动执行：{' '}
                    <code>docker restart web3signer-1 web3signer-2</code>
                  </p>
                </div>
              }
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
              action={
                <Button size="small" onClick={handleRestart} loading={restarting}>
                  重启
                </Button>
              }
            />
          )}
          {syncStatus.secondary && syncStatus.secondary.stats.missing_count > 0 && (
            <Alert
              message="Web3Signer-2 未加载所有密钥"
              description={
                <div>
                  <p>
                    Web3Signer-2 缺少 {syncStatus.secondary.stats.missing_count} 个密钥。
                    请重启 Web3Signer 容器以加载新配置文件。
                  </p>
                </div>
              }
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}
        </>
      )}

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

