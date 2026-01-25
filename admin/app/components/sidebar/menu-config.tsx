'use client'

import type { MenuItem } from '@/types/sidebar'
import {
  RiAdminLine,
  RiBuilding2Line,
  RiDashboardLine,
  RiExchangeLine,
  RiGroupLine,
  RiKey2Line,
  RiSettings3Line,
  RiTicketLine,
  RiWallet3Line,
} from '@remixicon/react'

export const menuItems: MenuItem[] = [
  {
    key: 'dashboard',
    label: '仪表盘',
    icon: <RiDashboardLine className="h-5 w-5" />,
    path: '/dashboard',
  },
  {
    key: 'users',
    label: '用户管理',
    icon: <RiGroupLine className="h-5 w-5" />,
    path: '/users',
  },
  {
    key: 'admins',
    label: '管理员管理',
    icon: <RiAdminLine className="h-5 w-5" />,
    path: '/admins',
  },
  {
    key: 'tenants',
    label: '租户管理',
    icon: <RiBuilding2Line className="h-5 w-5" />,
    path: '/tenants',
  },
  {
    key: 'billing',
    label: '账单管理',
    icon: <RiWallet3Line className="h-5 w-5" />,
    path: '/billing',
  },
  {
    key: 'invitation-codes',
    label: '邀请码管理',
    icon: <RiTicketLine className="h-5 w-5" />,
    path: '/invitation-codes',
  },
  {
    key: 'keys',
    label: 'API管理',
    icon: <RiKey2Line className="h-5 w-5" />,
    children: [
      {
        key: 'keys-api',
        label: 'API Key管理',
        path: '/keys/api',
      },
      {
        key: 'keys-usage',
        label: 'API使用统计',
        path: '/keys/usage',
      },
    ],
  },
  {
    key: 'proxy',
    label: '代理管理',
    icon: <RiExchangeLine className="h-5 w-5" />,
    children: [
      {
        key: 'proxy-routes',
        label: '路由配置',
        path: '/proxy/routes',
      },
      {
        key: 'proxy-logs',
        label: '请求日志',
        path: '/proxy/logs',
      },
    ],
  },
  {
    key: 'settings',
    label: '系统设置',
    icon: <RiSettings3Line className="h-5 w-5" />,
    children: [
      {
        key: 'settings-general',
        label: '基础配置',
        path: '/settings/general',
      },
      {
        key: 'settings-subscription-plans',
        label: '订阅计划',
        path: '/settings/subscription-plans',
      },
    ],
  },
]
