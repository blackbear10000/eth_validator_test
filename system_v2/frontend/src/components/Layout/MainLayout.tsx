import React from 'react'
import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  KeyOutlined,
  BankOutlined,
  SettingOutlined,
  ExportOutlined,
  WalletOutlined,
  CloudServerOutlined,
  FileTextOutlined,
} from '@ant-design/icons'

const { Sider } = Layout

interface MainLayoutProps {
  children: React.ReactNode
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表板',
    },
    {
      key: '/keys',
      icon: <KeyOutlined />,
      label: '密钥管理',
    },
    {
      key: '/deposits',
      icon: <BankOutlined />,
      label: '存款管理',
    },
    {
      key: '/contracts',
      icon: <FileTextOutlined />,
      label: '合约管理',
    },
    {
      key: '/clients',
      icon: <SettingOutlined />,
      label: '客户端管理',
    },
    {
      key: '/network',
      icon: <CloudServerOutlined />,
      label: '网络管理',
    },
    {
      key: '/exits',
      icon: <ExportOutlined />,
      label: '退出管理',
    },
    {
      key: '/withdrawals',
      icon: <WalletOutlined />,
      label: '取款管理',
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible theme="light" width={200}>
        <div style={{ padding: '16px', textAlign: 'center', fontWeight: 'bold' }}>
          ETH Validator System
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        {children}
      </Layout>
    </Layout>
  )
}

export default MainLayout

