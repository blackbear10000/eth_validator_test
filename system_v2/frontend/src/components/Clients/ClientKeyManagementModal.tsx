import React, { useState, useEffect } from 'react'
import {
  Modal,
  Table,
  Button,
  Space,
  Tag,
  message,
  Popconfirm,
  Select,
  Spin,
  Alert,
  Typography,
  Divider,
  InputNumber,
} from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { clientsApi, ClientInstance } from '../../api/clients'
import { keysApi } from '../../api/keys'

const { Option } = Select
const { Text } = Typography

interface KeyComparison {
  pubkey: string
  in_database: boolean
  in_validator_client: boolean
  status: 'both' | 'database_only' | 'validator_only'
  db_key_info?: {
    status: string
    activated_at?: string
    deposited_at?: string
  }
}

interface ClientKeyManagementModalProps {
  visible: boolean
  client: ClientInstance | null
  onClose: () => void
  onRefresh?: () => void
}

const ClientKeyManagementModal: React.FC<ClientKeyManagementModalProps> = ({
  visible,
  client,
  onClose,
  onRefresh,
}) => {
  const [loading, setLoading] = useState(false)
  const [comparison, setComparison] = useState<KeyComparison[]>([])
  const [availableKeys, setAvailableKeys] = useState<any[]>([])
  const [selectedKeys, setSelectedKeys] = useState<string[]>([])
  const [addingKeys, setAddingKeys] = useState(false)
  const [removingKeys, setRemovingKeys] = useState<string[]>([])
  const [syncingOrphaned, setSyncingOrphaned] = useState(false)
  const [removingOrphaned, setRemovingOrphaned] = useState(false)
  const [compareInfo, setCompareInfo] = useState<{
    container_running?: boolean
    warning?: string
    api_error?: string
  }>({})
  const [batchSelectCount, setBatchSelectCount] = useState<number>(0)

  useEffect(() => {
    if (visible && client) {
      loadData()
    }
  }, [visible, client])

  const loadData = async () => {
    if (!client) return

    setLoading(true)
    try {
      // 加载对比信息
      const compareResult = await clientsApi.getKeysCompare(client.id) as any
      // 确保 comparison 始终是数组
      const comparisonArray = Array.isArray(compareResult?.comparison) 
        ? compareResult.comparison 
        : []
      setComparison(comparisonArray)
      
      // 保存对比信息（容器运行状态、警告等）
      setCompareInfo({
        container_running: compareResult?.container_running,
        warning: compareResult?.warning,
        api_error: compareResult?.api_error
      })

      // 加载可用密钥列表（用于添加）
      // 使用新的 API，自动排除已被其他激活的客户端选中并使用的密钥（不管客户端是否在运行）
      // 不传 status 参数，返回所有已提交状态的密钥（PENDING, DEPOSITED, ACTIVE_ON_CHAIN）
      try {
        const availableResult = await clientsApi.getAvailableKeys(client.id, undefined, 1000) as any
        setAvailableKeys(availableResult.items || [])
      } catch (error: any) {
        // 如果新 API 失败，降级使用旧方法
        console.warn('获取可用密钥失败，使用降级方案:', error)
        const keysResult = await keysApi.list() as any
        const allKeys = keysResult?.items || []
        
        const currentPubkeys = new Set(
          comparisonArray.filter((k: KeyComparison) => k.in_database).map((k: KeyComparison) => k.pubkey.toLowerCase())
        )
        const available = allKeys.filter(
          (key: any) => !currentPubkeys.has(key.pubkey.toLowerCase())
        )
        setAvailableKeys(available)
      }
    } catch (error: any) {
      message.error(`加载数据失败: ${error.message}`)
      // 确保即使出错也设置空数组
      setComparison([])
      setAvailableKeys([])
    } finally {
      setLoading(false)
    }
  }

  const handleAddKeys = async (keysToAdd?: string[]) => {
    if (!client) return
    
    const keys = keysToAdd || selectedKeys
    if (keys.length === 0) return

    setAddingKeys(true)
    try {
      await clientsApi.assignKeys(client.id, keys)
      message.success(`成功分配 ${keys.length} 个密钥`)
      setSelectedKeys([])
      setBatchSelectCount(0)
      await loadData()
      onRefresh?.()
    } catch (error: any) {
      message.error(`分配密钥失败: ${error.message}`)
    } finally {
      setAddingKeys(false)
    }
  }

  const handleRemoveKey = async (pubkey: string) => {
    if (!client) return

    setRemovingKeys([...removingKeys, pubkey])
    try {
      await clientsApi.removeKeys(client.id, [pubkey])
      message.success('密钥已移除')
      await loadData()
      onRefresh?.()
    } catch (error: any) {
      message.error(`移除密钥失败: ${error.message}`)
    } finally {
      setRemovingKeys(removingKeys.filter(k => k !== pubkey))
    }
  }

  const handleSyncOrphanedKeys = async () => {
    if (!client) return

    setSyncingOrphaned(true)
    try {
      const result = await clientsApi.syncOrphanedKeys(client.id) as any
      const syncedCount = result.synced_count || 0
      const skippedCount = result.skipped_count || 0
      const errorCount = result.error_count || 0
      
      if (syncedCount > 0) {
        message.success(`成功同步 ${syncedCount} 个密钥到数据库`)
      }
      if (skippedCount > 0) {
        message.warning(`${skippedCount} 个密钥被跳过（可能已存在或分配给其他客户端）`)
      }
      if (errorCount > 0) {
        message.error(`${errorCount} 个密钥同步失败`)
      }
      
      await loadData()
      onRefresh?.()
    } catch (error: any) {
      message.error(`同步孤儿密钥失败: ${error.message}`)
    } finally {
      setSyncingOrphaned(false)
    }
  }

  const handleRemoveOrphanedKeys = async () => {
    if (!client) return

    setRemovingOrphaned(true)
    try {
      const result = await clientsApi.removeOrphanedKeys(client.id) as any
      const removedCount = result.removed_count || 0
      const errorCount = result.error_count || 0
      
      if (removedCount > 0) {
        message.success(`成功从 Validator Client 删除 ${removedCount} 个密钥`)
      }
      if (errorCount > 0) {
        message.error(`${errorCount} 个密钥删除失败`)
      }
      
      await loadData()
      onRefresh?.()
    } catch (error: any) {
      message.error(`删除孤儿密钥失败: ${error.message}`)
    } finally {
      setRemovingOrphaned(false)
    }
  }

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'both':
        return <Tag color="success" icon={<CheckCircleOutlined />}>已同步</Tag>
      case 'database_only':
        return <Tag color="warning" icon={<ExclamationCircleOutlined />}>仅数据库</Tag>
      case 'validator_only':
        return <Tag color="error" icon={<CloseCircleOutlined />}>仅客户端</Tag>
      default:
        return <Tag>{status}</Tag>
    }
  }

  const columns = [
    {
      title: '公钥',
      dataIndex: 'pubkey',
      key: 'pubkey',
      width: 200,
      render: (text: string) => (
        <Text copyable={{ text }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
          {text.slice(0, 20)}...{text.slice(-8)}
        </Text>
      ),
    },
    {
      title: '同步状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '数据库状态',
      key: 'in_database',
      width: 120,
      render: (_: any, record: KeyComparison) => (
        record.in_database ? (
          <Tag color="blue">已分配</Tag>
        ) : (
          <Tag>未分配</Tag>
        )
      ),
    },
    {
      title: 'Validator Client 状态',
      key: 'in_validator_client',
      width: 150,
      render: (_: any, record: KeyComparison) => (
        record.in_validator_client ? (
          <Tag color="green">已加载</Tag>
        ) : (
          <Tag>未加载</Tag>
        )
      ),
    },
    {
      title: '密钥状态',
      key: 'key_status',
      width: 120,
      render: (_: any, record: KeyComparison) => {
        if (record.db_key_info?.status) {
          const status = record.db_key_info.status
          const colorMap: Record<string, string> = {
            'active': 'success',
            'deposit_data_generated': 'processing',
            'pending': 'warning',
            'deposited': 'cyan',
            'active_on_chain': 'green',
            'unused': 'default',
          }
          return <Tag color={colorMap[status] || 'default'}>{status}</Tag>
        }
        return <Tag>-</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: KeyComparison) => (
        record.in_database ? (
          <Popconfirm
            title="确定要移除这个密钥吗？"
            description="移除后密钥将从客户端中删除，但不会从数据库中删除"
            onConfirm={() => handleRemoveKey(record.pubkey)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              loading={removingKeys.includes(record.pubkey)}
            >
              移除
            </Button>
          </Popconfirm>
        ) : null
      ),
    },
  ]

  // 统计信息
  const stats = {
    total: comparison.length,
    inBoth: comparison.filter(k => k.status === 'both').length,
    onlyInDb: comparison.filter(k => k.status === 'database_only').length,
    onlyInValidator: comparison.filter(k => k.status === 'validator_only').length,
  }

  return (
    <Modal
      title={`密钥管理 - ${client?.name || ''}`}
      open={visible}
      onCancel={onClose}
      width={1000}
      footer={[
        <Button key="refresh" icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
          刷新
        </Button>,
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
    >
      <Spin spinning={loading}>
        {/* 统计信息 */}
        <Space style={{ marginBottom: 16 }} wrap>
          <Tag>总计: {stats.total}</Tag>
          <Tag color="success">已同步: {stats.inBoth}</Tag>
          <Tag color="warning">仅数据库: {stats.onlyInDb}</Tag>
          <Tag color="error">仅客户端: {stats.onlyInValidator}</Tag>
        </Space>

        {/* 警告信息 */}
        {compareInfo.warning && (
          <Alert
            message={compareInfo.container_running === false ? "容器未运行" : "无法获取 Validator Client 密钥列表"}
            description={compareInfo.warning}
            type={compareInfo.container_running === false ? "info" : "warning"}
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        {!compareInfo.warning && stats.onlyInDb > 0 && (
          <Alert
            message="部分密钥仅在数据库中"
            description={`有 ${stats.onlyInDb} 个密钥已分配到数据库，但未加载到 Validator Client。请检查 Remote Validator API 是否正常工作。`}
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        {!compareInfo.warning && stats.onlyInValidator > 0 && (
          <Alert
            message="部分密钥仅在 Validator Client 中"
            description={
              <div>
                <div style={{ marginBottom: 8 }}>
                  有 {stats.onlyInValidator} 个密钥已加载到 Validator Client，但未在数据库中记录。这可能是配置不一致导致的。
                </div>
                <Space>
                  <Button
                    size="small"
                    type="primary"
                    onClick={handleSyncOrphanedKeys}
                    loading={syncingOrphaned}
                    disabled={!compareInfo.container_running}
                  >
                    同步到数据库
                  </Button>
                  <Popconfirm
                    title="确定要删除这些孤儿密钥吗？"
                    description="这将从 Validator Client 中删除这些密钥，但不会影响数据库"
                    onConfirm={handleRemoveOrphanedKeys}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      size="small"
                      danger
                      loading={removingOrphaned}
                      disabled={!compareInfo.container_running}
                    >
                      从客户端删除
                    </Button>
                  </Popconfirm>
                </Space>
              </div>
            }
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Divider>密钥列表</Divider>

        {/* 添加密钥 */}
        <div style={{ marginBottom: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space wrap>
              <Select
                mode="multiple"
                placeholder="选择要添加的密钥"
                style={{ width: 400 }}
                value={selectedKeys}
                onChange={setSelectedKeys}
                showSearch
                filterOption={(input, option) => {
                  const children = option?.children as string | undefined
                  return children ? children.toLowerCase().includes(input.toLowerCase()) : false
                }}
              >
                {availableKeys.map((key) => (
                  <Option key={key.pubkey} value={key.pubkey}>
                    {key.pubkey.slice(0, 20)}... ({key.status})
                  </Option>
                ))}
              </Select>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => handleAddKeys()}
                loading={addingKeys}
                disabled={selectedKeys.length === 0}
              >
                添加密钥
              </Button>
            </Space>
            <Space>
              <InputNumber
                min={0}
                max={availableKeys.length}
                value={batchSelectCount}
                onChange={(value) => {
                  // 处理 null 或 undefined 的情况
                  // 注意：当输入框被清空时，value 可能是 null，但我们不应该立即设置为0
                  if (value === null || value === undefined) {
                    // 如果输入框被清空，保持当前值不变（不更新状态）
                    return
                  }
                  const count = Number(value)
                  // 确保 count 是有效数字
                  if (isNaN(count) || count < 0) {
                    return
                  }
                  setBatchSelectCount(count)
                  // 自动选择相应数量的可用密钥
                  if (count > 0 && availableKeys.length > 0) {
                    const keysToSelect = availableKeys
                      .slice(0, count)
                      .map((k: any) => k.pubkey)
                    setSelectedKeys(keysToSelect)
                  } else if (count === 0) {
                    // 明确输入0时清空选择
                    setSelectedKeys([])
                  }
                }}
                onPressEnter={() => {
                  // 按回车键时，如果有输入数量，自动提交
                  if (batchSelectCount > 0 && availableKeys.length > 0) {
                    const keysToSelect = availableKeys
                      .slice(0, batchSelectCount)
                      .map((k: any) => k.pubkey)
                    if (keysToSelect.length > 0) {
                      handleAddKeys(keysToSelect)
                    }
                  }
                }}
                onBlur={() => {
                  // 失去焦点时，如果当前值为 null 或 undefined，恢复之前的值
                  // 这样可以防止用户输入数字后，失去焦点时数字变为0
                  if (batchSelectCount === null || batchSelectCount === undefined) {
                    // 如果当前值为空，但之前有选择，保持选择状态
                    if (selectedKeys.length > 0) {
                      // 根据已选择的密钥数量恢复输入框的值
                      setBatchSelectCount(selectedKeys.length)
                    }
                  } else if (batchSelectCount > 0 && availableKeys.length > 0) {
                    // 确保选择状态与输入值一致
                    const keysToSelect = availableKeys
                      .slice(0, batchSelectCount)
                      .map((k: any) => k.pubkey)
                    setSelectedKeys(keysToSelect)
                  }
                }}
                placeholder="输入数量（自动选择）"
                style={{ width: 200 }}
              />
              <Button
                onClick={() => {
                  if (selectedKeys.length > 0) {
                    handleAddKeys()
                  } else if (batchSelectCount > 0 && availableKeys.length > 0) {
                    // 如果 selectedKeys 为空但 batchSelectCount 有值，先选择再提交
                    const keysToSelect = availableKeys
                      .slice(0, batchSelectCount)
                      .map((k: any) => k.pubkey)
                    if (keysToSelect.length > 0) {
                      handleAddKeys(keysToSelect)
                    }
                  } else {
                    message.warning('请先输入数量或选择密钥')
                  }
                }}
                type="primary"
                icon={<PlusOutlined />}
                disabled={selectedKeys.length === 0 && (batchSelectCount === 0 || batchSelectCount === null || batchSelectCount === undefined)}
                loading={addingKeys}
              >
                添加密钥 ({selectedKeys.length || batchSelectCount || 0})
              </Button>
              <span style={{ color: '#999', fontSize: '12px' }}>
                可用密钥: {availableKeys.length} 个（已排除被其他激活的客户端使用的密钥）
              </span>
            </Space>
          </Space>
        </div>

        {/* 密钥列表表格 */}
        <Table
          columns={columns}
          dataSource={comparison}
          rowKey="pubkey"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个密钥`,
          }}
          size="small"
        />
      </Spin>
    </Modal>
  )
}

export default ClientKeyManagementModal


