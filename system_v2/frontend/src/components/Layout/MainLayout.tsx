import React from 'react'
import { Layout, Menu, Dropdown, Button } from 'antd'
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
  SafetyOutlined,
  UserOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../../stores/authStore'
import MetaMaskConnect from '../MetaMask/MetaMaskConnect'

const { Sider, Header } = Layout

interface MainLayoutProps {
  children: React.ReactNode
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  // 所有用户都可以访问的菜单
  const commonMenuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表板',
    },
    {
      key: '/deposits',
      icon: <BankOutlined />,
      label: '存款管理',
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

  // 仅管理员可以访问的菜单
  const adminMenuItems = [
    {
      key: '/keys',
      icon: <KeyOutlined />,
      label: '密钥管理',
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
      key: '/web3signer',
      icon: <SafetyOutlined />,
      label: 'Web3Signer 监控',
    },
    {
      key: '/admin',
      icon: <UserOutlined />,
      label: '管理员面板',
    },
  ]

  const menuItems = isAdmin 
    ? [...commonMenuItems, ...adminMenuItems]
    : commonMenuItems

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const userMenuItems = [
    {
      key: 'user-info',
      label: (
        <div>
          <div>{user?.username || user?.wallet_address?.substring(0, 10) + '...'}</div>
          <div style={{ fontSize: '12px', color: '#999' }}>
            {user?.role === 'admin' ? '管理员' : '普通用户'}
          </div>
        </div>
      ),
      disabled: true,
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '登出',
      onClick: handleLogout,
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
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '16px' }}>
          {/* 所有用户（包括管理员）都可以连接 MetaMask */}
          <MetaMaskConnect />
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Button type="text" icon={<UserOutlined />} style={{ display: 'flex', alignItems: 'center' }}>
              {user?.username || user?.wallet_address?.substring(0, 10) + '...'}
            </Button>
          </Dropdown>
        </Header>
        {children}
      </Layout>
    </Layout>
  )
}

export default MainLayout

