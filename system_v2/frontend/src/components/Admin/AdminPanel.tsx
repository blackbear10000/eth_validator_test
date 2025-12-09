import React, { useState, useEffect } from 'react'
import {
  Card,
  Tabs,
  Button,
  Table,
  Space,
  Select,
  Input,
  DatePicker,
  Upload,
  message,
  Tag,
  Modal,
} from 'antd'
import {
  DownloadOutlined,
  UploadOutlined,
  FileTextOutlined,
  HistoryOutlined,
} from '@ant-design/icons'
import apiClient from '../../api/client'
import dayjs from 'dayjs'

const { TabPane } = Tabs
const { RangePicker } = DatePicker

interface AuditLog {
  id: number
  user_id: number | null
  action: string
  resource_type: string
  resource_id: string | null
  details: any
  ip_address: string | null
  created_at: string
}

const AdminPanel: React.FC = () => {
  const [exportFormat, setExportFormat] = useState<'json' | 'csv'>('json')
  const [exportTables, setExportTables] = useState<string>('')
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditFilters, setAuditFilters] = useState({
    action: undefined as string | undefined,
    resource_type: undefined as string | undefined,
    start_date: undefined as string | undefined,
    end_date: undefined as string | undefined,
  })

  // 导出数据
  const handleExport = async () => {
    try {
      const params = new URLSearchParams({
        format: exportFormat,
      })
      if (exportTables) {
        params.append('tables', exportTables)
      }

      const response = await apiClient.get(`/admin/export?${params.toString()}`, {
        responseType: 'blob',
      }) as any

      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `export_${dayjs().format('YYYYMMDD_HHmmss')}.${exportFormat === 'json' ? 'json' : 'zip'}`)
      document.body.appendChild(link)
      link.click()
      link.remove()

      message.success('导出成功')
    } catch (error: any) {
      message.error(`导出失败: ${error.message}`)
    }
  }

  // 导入数据
  const handleImport = async (file: File) => {
    try {
      const formData = new FormData()
      formData.append('file', file)

      await apiClient.post('/admin/import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      message.success('导入成功')
      return false // 阻止默认上传行为
    } catch (error: any) {
      message.error(`导入失败: ${error.message}`)
      return false
    }
  }

  // 加载审计日志
  const loadAuditLogs = async () => {
    setAuditLoading(true)
    try {
      const params: any = {}
      if (auditFilters.action) params.action = auditFilters.action
      if (auditFilters.resource_type) params.resource_type = auditFilters.resource_type
      if (auditFilters.start_date) params.start_date = auditFilters.start_date
      if (auditFilters.end_date) params.end_date = auditFilters.end_date

      const response = await apiClient.get('/admin/audit-logs', { params }) as any
      setAuditLogs(response.items || [])
    } catch (error: any) {
      message.error(`加载审计日志失败: ${error.message}`)
    } finally {
      setAuditLoading(false)
    }
  }

  useEffect(() => {
    loadAuditLogs()
  }, [])

  const auditColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '用户ID',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 100,
      render: (id: number | null) => id || '-',
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action: string) => {
        const colorMap: Record<string, string> = {
          create: 'green',
          update: 'blue',
          delete: 'red',
        }
        return <Tag color={colorMap[action] || 'default'}>{action}</Tag>
      },
    },
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      key: 'resource_type',
      width: 150,
    },
    {
      title: '资源ID',
      dataIndex: 'resource_id',
      key: 'resource_id',
      width: 150,
      render: (id: string | null) => id || '-',
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 150,
      render: (ip: string | null) => ip || '-',
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
  ]

  return (
    <div>
      <Card title="管理员面板">
        <Tabs defaultActiveKey="export">
          <TabPane
            tab={
              <span>
                <DownloadOutlined /> 数据导出
              </span>
            }
            key="export"
          >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <div>
                <label>导出格式：</label>
                <Select
                  value={exportFormat}
                  onChange={setExportFormat}
                  style={{ width: 200, marginLeft: 8 }}
                >
                  <Select.Option value="json">JSON</Select.Option>
                  <Select.Option value="csv">CSV (ZIP)</Select.Option>
                </Select>
              </div>
              <div>
                <label>导出表（留空导出所有表）：</label>
                <Input
                  value={exportTables}
                  onChange={(e) => setExportTables(e.target.value)}
                  placeholder="例如: users,validator_keys,deposit_transactions"
                  style={{ width: 400, marginLeft: 8 }}
                />
              </div>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={handleExport}
              >
                导出数据
              </Button>
            </Space>
          </TabPane>

          <TabPane
            tab={
              <span>
                <UploadOutlined /> 数据导入
              </span>
            }
            key="import"
          >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <div>
                <Upload
                  accept=".json"
                  beforeUpload={handleImport}
                  showUploadList={false}
                >
                  <Button icon={<UploadOutlined />}>选择 JSON 文件并导入</Button>
                </Upload>
              </div>
              <div style={{ color: '#999', fontSize: '12px' }}>
                注意：导入会直接插入数据，请确保数据格式正确
              </div>
            </Space>
          </TabPane>

          <TabPane
            tab={
              <span>
                <HistoryOutlined /> 审计日志
              </span>
            }
            key="audit"
          >
            <Space direction="vertical" size="large" style={{ width: '100%', marginBottom: 16 }}>
              <Space>
                <Select
                  placeholder="操作类型"
                  allowClear
                  style={{ width: 150 }}
                  value={auditFilters.action}
                  onChange={(value) => setAuditFilters({ ...auditFilters, action: value })}
                >
                  <Select.Option value="create">创建</Select.Option>
                  <Select.Option value="update">更新</Select.Option>
                  <Select.Option value="delete">删除</Select.Option>
                </Select>
                <Input
                  placeholder="资源类型"
                  allowClear
                  style={{ width: 200 }}
                  value={auditFilters.resource_type}
                  onChange={(e) => setAuditFilters({ ...auditFilters, resource_type: e.target.value })}
                />
                <RangePicker
                  onChange={(dates) => {
                    if (dates && dates[0] && dates[1]) {
                      setAuditFilters({
                        ...auditFilters,
                        start_date: dates[0].format('YYYY-MM-DD'),
                        end_date: dates[1].format('YYYY-MM-DD'),
                      })
                    } else {
                      setAuditFilters({
                        ...auditFilters,
                        start_date: undefined,
                        end_date: undefined,
                      })
                    }
                  }}
                />
                <Button type="primary" onClick={loadAuditLogs}>
                  查询
                </Button>
              </Space>
            </Space>
            <Table
              columns={auditColumns}
              dataSource={auditLogs}
              loading={auditLoading}
              rowKey="id"
              pagination={{
                pageSize: 50,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }}
            />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default AdminPanel

