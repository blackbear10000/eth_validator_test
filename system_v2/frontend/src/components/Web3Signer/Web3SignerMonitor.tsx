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
  Divider,
  Spin,
  message,
  Modal,
  Dropdown,
  MenuProps,
} from 'antd'
import {
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PoweroffOutlined,
  SyncOutlined,
  MoreOutlined,
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

  const handleSyncConfigs = async (forceRegenerate: boolean = false) => {
    setSyncing(true)
    try {
      const result = await web3signerApi.syncConfigs(true, forceRegenerate)
      if (result.needs_restart) {
        message.warning('配置文件已同步，但需要重启 Web3Signer 才能加载新密钥', 5)
      } else {
        message.success(result.message || '配置文件已同步')
      }
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

  const handleRegenerate = async () => {
    Modal.confirm({
      title: '确认重新生成所有配置文件',
      content: '这将删除所有现有配置文件并重新生成，确保格式正确。此操作会使用最新的 Vault token 和路径格式。是否继续？',
      okText: '确认重新生成',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          const result = await web3signerApi.regenerateConfigs()
          if (result.success) {
            message.success(result.message)
            // 重新加载数据
            await loadData()
          } else {
            message.error(`重新生成失败: ${result.message}`)
          }
        } catch (error: any) {
          message.error(`重新生成失败: ${error.message}`)
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
        try {
          const result = await web3signerApi.cleanupConfigs()
          if (result.success) {
            message.success(`已清理 ${result.removed} 个孤立配置文件`)
            await loadData()
          } else {
            message.error(`清理失败: ${result.message}`)
          }
        } catch (error: any) {
          message.error(`清理失败: ${error.message}`)
        }
      },
    })
  }

  // 检查是否有同步问题
  const hasSyncIssues = () => {
    if (!syncStatus) return false
    const primaryMissing = syncStatus.primary?.stats.missing_count || 0
    const secondaryMissing = syncStatus.secondary?.stats.missing_count || 0
    const primaryExtra = syncStatus.primary?.stats.extra_count || 0
    const secondaryExtra = syncStatus.secondary?.stats.extra_count || 0
    return primaryMissing > 0 || secondaryMissing > 0 || primaryExtra > 0 || secondaryExtra > 0
  }

  // 更多操作菜单
  const moreMenuItems: MenuProps['items'] = [
    {
      key: 'regenerate',
      label: '重新生成配置',
      icon: <SyncOutlined />,
      onClick: () => handleRegenerate(),
      danger: true,
    },
    {
      key: 'cleanup',
      label: '清理孤立文件',
      icon: <DeleteOutlined />,
      onClick: () => handleCleanup(),
      danger: true,
    },
  ]

  const keysColumns = [
    {
      title: '#',
      key: 'index',
      width: 60,
      render: (_: any, __: any, index: number) => index + 1,
    },
    {
      title: '公钥',
      dataIndex: 'pubkey',
      key: 'pubkey',
      render: (text: string) => {
        const normalized = text.toLowerCase().trim()
        const pubkey = normalized.startsWith('0x') ? normalized : `0x${normalized}`
        const start = pubkey.slice(0, 20)
        const end = pubkey.slice(-6)
        return (
          <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
            {start}...{end}
          </span>
        )
      },
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
            onClick={() => handleSyncConfigs(false)}
            loading={syncing}
            type={hasSyncIssues() ? 'primary' : 'default'}
          >
            同步配置
          </Button>
          {hasSyncIssues() && (
            <Button
              icon={<PoweroffOutlined />}
              onClick={handleRestart}
              loading={restarting}
              danger
            >
              重启服务
            </Button>
          )}
          <Dropdown menu={{ items: moreMenuItems }} trigger={['click']}>
            <Button icon={<MoreOutlined />}>更多</Button>
          </Dropdown>
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
            刷新
          </Button>
        </Space>
      </Space>

      {/* 只在有同步问题时显示警告 */}
      {hasSyncIssues() && syncStatus && (
        <Alert
          message="密钥同步异常"
          description={
            <div>
              {syncStatus.primary?.stats.missing_count && syncStatus.primary.stats.missing_count > 0 && (
                <p>Web3Signer-1 缺少 {syncStatus.primary.stats.missing_count} 个密钥</p>
              )}
              {syncStatus.secondary?.stats.missing_count && syncStatus.secondary.stats.missing_count > 0 && (
                <p>Web3Signer-2 缺少 {syncStatus.secondary.stats.missing_count} 个密钥</p>
              )}
              <p style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                提示：Web3Signer 使用 key-store-path 配置时，需要重启容器才能加载新配置文件
              </p>
            </div>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          closable
        />
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

        {/* 同步状态对比 - 只在有异常时显示详细信息 */}
        {hasSyncIssues() && (syncStatus?.primary || syncStatus?.secondary) && (
          <>
            <Divider>同步状态详情</Divider>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              {syncStatus.primary && !syncStatus.primary.error && (
                <Col span={12}>
                  <Card title="Web3Signer-1 同步状态" size="small">
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic
                          title="数据库密钥"
                          value={syncStatus.primary.stats.db_active_count}
                          valueStyle={{ fontSize: '16px' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="已加载"
                          value={syncStatus.primary.stats.web3signer_count}
                          valueStyle={{ fontSize: '16px' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="已同步"
                          value={syncStatus.primary.stats.synced_count}
                          valueStyle={{ color: '#3f8600', fontSize: '16px' }}
                        />
                      </Col>
                    </Row>
                    {(syncStatus.primary.stats.missing_count > 0 || syncStatus.primary.stats.extra_count > 0) && (
                      <div style={{ marginTop: 16 }}>
                        {syncStatus.primary.stats.missing_count > 0 && (
                          <Tag color="warning" style={{ marginBottom: 8 }}>
                            缺失 {syncStatus.primary.stats.missing_count} 个
                          </Tag>
                        )}
                        {syncStatus.primary.stats.extra_count > 0 && (
                          <Tag color="error" style={{ marginBottom: 8 }}>
                            多余 {syncStatus.primary.stats.extra_count} 个
                          </Tag>
                        )}
                      </div>
                    )}
                  </Card>
                </Col>
              )}
              {syncStatus.secondary && !syncStatus.secondary.error && (
                <Col span={12}>
                  <Card title="Web3Signer-2 同步状态" size="small">
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic
                          title="数据库密钥"
                          value={syncStatus.secondary.stats.db_active_count}
                          valueStyle={{ fontSize: '16px' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="已加载"
                          value={syncStatus.secondary.stats.web3signer_count}
                          valueStyle={{ fontSize: '16px' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="已同步"
                          value={syncStatus.secondary.stats.synced_count}
                          valueStyle={{ color: '#3f8600', fontSize: '16px' }}
                        />
                      </Col>
                    </Row>
                    {(syncStatus.secondary.stats.missing_count > 0 || syncStatus.secondary.stats.extra_count > 0) && (
                      <div style={{ marginTop: 16 }}>
                        {syncStatus.secondary.stats.missing_count > 0 && (
                          <Tag color="warning" style={{ marginBottom: 8 }}>
                            缺失 {syncStatus.secondary.stats.missing_count} 个
                          </Tag>
                        )}
                        {syncStatus.secondary.stats.extra_count > 0 && (
                          <Tag color="error" style={{ marginBottom: 8 }}>
                            多余 {syncStatus.secondary.stats.extra_count} 个
                          </Tag>
                        )}
                      </div>
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

