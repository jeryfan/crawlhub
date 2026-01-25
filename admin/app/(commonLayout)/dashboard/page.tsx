'use client'

import {
  RiAdminLine,
  RiArrowDownLine,
  RiArrowUpLine,
  RiBuilding2Line,
  RiGroupLine,
  RiTicketLine,
  RiTimeLine,
} from '@remixicon/react'
import ReactECharts from 'echarts-for-react'
import { useEffect, useRef, useState } from 'react'
import Skeleton from '@/app/components/base/skeleton'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useDashboardStats,
  useRecentAccounts,
  useRecentTenants,
} from '@/service/use-platform'
import { cn } from '@/utils/classnames'

// 数字动画 Hook
const useCountUp = (end: number, duration: number = 1000) => {
  const [count, setCount] = useState(0)
  const countRef = useRef(0)
  const startTimeRef = useRef<number | null>(null)

  useEffect(() => {
    if (end === 0) {
      setCount(0)
      return
    }

    const animate = (timestamp: number) => {
      if (!startTimeRef.current)
        startTimeRef.current = timestamp
      const progress = Math.min(
        (timestamp - startTimeRef.current) / duration,
        1,
      )

      // easeOutExpo 缓动函数
      const easeOut = progress === 1 ? 1 : 1 - 2 ** (-10 * progress)
      const currentCount = Math.floor(easeOut * end)

      if (currentCount !== countRef.current) {
        countRef.current = currentCount
        setCount(currentCount)
      }

      if (progress < 1)
        requestAnimationFrame(animate)
      else setCount(end)
    }

    startTimeRef.current = null
    requestAnimationFrame(animate)
  }, [end, duration])

  return count
}

// 统计卡片组件
type StatCardProps = {
  title: string
  value: number
  subValue?: string
  icon: React.ReactNode
  gradient: string
  trend?: number
  delay?: number
}

const StatCard = ({
  title,
  value,
  subValue,
  icon,
  gradient,
  trend,
  delay = 0,
}: StatCardProps) => {
  const animatedValue = useCountUp(value, 1200)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay)
    return () => clearTimeout(timer)
  }, [delay])

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl p-5 transition-all duration-500',
        'hover:-translate-y-1 hover:scale-[1.02] hover:shadow-lg',
        'translate-y-4 opacity-0',
        isVisible && 'translate-y-0 opacity-100',
      )}
      style={{
        background: gradient,
        transitionDelay: `${delay}ms`,
      }}
    >
      {/* 装饰背景 */}
      <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-white/10 blur-2xl" />
      <div className="absolute -bottom-8 -left-8 h-32 w-32 rounded-full bg-white/5" />

      <div className="relative flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-white/80">{title}</p>
          <p className="mt-2 text-3xl font-bold tabular-nums text-white">
            {animatedValue.toLocaleString()}
          </p>
          {subValue && <p className="mt-2 text-xs text-white/60">{subValue}</p>}
          {trend !== undefined && (
            <div
              className={cn(
                'mt-2 flex items-center gap-1 text-xs font-medium',
                trend >= 0 ? 'text-green-300' : 'text-red-300',
              )}
            >
              {trend >= 0
                ? (
                    <RiArrowUpLine className="h-3.5 w-3.5" />
                  )
                : (
                    <RiArrowDownLine className="h-3.5 w-3.5" />
                  )}
              <span>
                {Math.abs(trend)}
                % 较上周
              </span>
            </div>
          )}
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm">
          {icon}
        </div>
      </div>
    </div>
  )
}

// 状态徽章
const StatusBadge = ({ status }: { status: string }) => {
  const statusConfig: Record<
    string,
    { label: string, bgColor: string, textColor: string }
  > = {
    active: {
      label: '活跃',
      bgColor: 'bg-green-50',
      textColor: 'text-green-600',
    },
    pending: {
      label: '待激活',
      bgColor: 'bg-yellow-50',
      textColor: 'text-yellow-600',
    },
    banned: { label: '禁用', bgColor: 'bg-red-50', textColor: 'text-red-600' },
    normal: {
      label: '正常',
      bgColor: 'bg-green-50',
      textColor: 'text-green-600',
    },
    archive: {
      label: '归档',
      bgColor: 'bg-gray-100',
      textColor: 'text-gray-600',
    },
  }

  const config = statusConfig[status] || {
    label: status,
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-600',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        config.bgColor,
        config.textColor,
      )}
    >
      {config.label}
    </span>
  )
}

// 趋势图表组件
const TrendChart = ({ data, color }: { data: number[], color: string }) => {
  const option = {
    grid: {
      top: 10,
      right: 10,
      bottom: 10,
      left: 10,
    },
    xAxis: {
      type: 'category',
      show: false,
      data: data.map((_, i) => i),
    },
    yAxis: {
      type: 'value',
      show: false,
    },
    series: [
      {
        data,
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          color,
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: `${color}40` },
              { offset: 1, color: `${color}05` },
            ],
          },
        },
      },
    ],
  }

  return (
    <ReactECharts
      option={option}
      style={{ height: '100%', width: '100%' }}
      opts={{ renderer: 'svg' }}
    />
  )
}

// 用户增长图表
const UserGrowthChart = () => {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 400)
    return () => clearTimeout(timer)
  }, [])

  // 模拟数据 - 实际项目中应从 API 获取
  const mockData = {
    dates: ['12/12', '12/13', '12/14', '12/15', '12/16', '12/17', '12/18'],
    users: [120, 132, 101, 134, 90, 230, 210],
    tenants: [20, 18, 25, 22, 30, 28, 35],
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: {
        color: '#374151',
        fontSize: 12,
      },
      axisPointer: {
        type: 'cross',
        crossStyle: {
          color: '#999',
        },
      },
    },
    legend: {
      data: ['新增用户', '新增租户'],
      top: 0,
      right: 0,
      textStyle: {
        color: '#6b7280',
        fontSize: 12,
      },
    },
    grid: {
      top: 40,
      right: 20,
      bottom: 30,
      left: 50,
    },
    xAxis: {
      type: 'category',
      data: mockData.dates,
      axisLine: {
        lineStyle: { color: '#e5e7eb' },
      },
      axisTick: { show: false },
      axisLabel: {
        color: '#9ca3af',
        fontSize: 11,
      },
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: { color: '#f3f4f6', type: 'dashed' },
      },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#9ca3af',
        fontSize: 11,
      },
    },
    series: [
      {
        name: '新增用户',
        type: 'bar',
        data: mockData.users,
        barWidth: 20,
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#3b82f6' },
              { offset: 1, color: '#60a5fa' },
            ],
          },
          borderRadius: [4, 4, 0, 0],
        },
      },
      {
        name: '新增租户',
        type: 'line',
        data: mockData.tenants,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          width: 2,
          color: '#8b5cf6',
        },
        itemStyle: {
          color: '#8b5cf6',
          borderColor: '#fff',
          borderWidth: 2,
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(139, 92, 246, 0.2)' },
              { offset: 1, color: 'rgba(139, 92, 246, 0)' },
            ],
          },
        },
      },
    ],
  }

  return (
    <div
      className={cn(
        'rounded-2xl border border-components-panel-border bg-components-panel-bg p-5 transition-all duration-500',
        'translate-y-4 opacity-0',
        isVisible && 'translate-y-0 opacity-100',
      )}
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold text-text-primary">数据趋势</h3>
        <span className="text-xs text-text-tertiary">近 7 天</span>
      </div>
      <ReactECharts
        option={option}
        style={{ height: 280 }}
        opts={{ renderer: 'svg' }}
      />
    </div>
  )
}

// 列表项组件
type ListItemProps = {
  primary: string
  secondary: string
  status: string
  time: string
  delay?: number
}

const ListItem = ({
  primary,
  secondary,
  status,
  time,
  delay = 0,
}: ListItemProps) => {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay)
    return () => clearTimeout(timer)
  }, [delay])

  return (
    <div
      className={cn(
        'flex items-center justify-between rounded-xl p-3.5 transition-all duration-300',
        'bg-background-default-subtle hover:bg-state-base-hover',
        'translate-x-4 opacity-0',
        isVisible && 'translate-x-0 opacity-100',
      )}
    >
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-text-primary">{primary}</p>
        <p className="mt-0.5 truncate text-sm text-text-tertiary">
          {secondary}
        </p>
      </div>
      <div className="ml-4 flex items-center gap-3">
        <StatusBadge status={status} />
        <div className="flex items-center gap-1 whitespace-nowrap text-xs text-text-quaternary">
          <RiTimeLine className="h-3.5 w-3.5" />
          {time}
        </div>
      </div>
    </div>
  )
}

const DashboardPage = () => {
  const { data: stats, isLoading: statsLoading } = useDashboardStats()
  const { data: recentAccounts, isLoading: accountsLoading }
    = useRecentAccounts(5)
  const { data: recentTenants, isLoading: tenantsLoading }
    = useRecentTenants(5)
  const { formatDate: formatDateWithTz } = useTimestamp()

  // 格式化时间
  const formatDate = (dateStr: string | null): string => {
    if (!dateStr)
      return '-'
    return formatDateWithTz(dateStr, 'MM/DD HH:mm')
  }

  if (statsLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map(i => (
            <Skeleton key={i} className="h-36 rounded-2xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Skeleton className="h-80 rounded-2xl lg:col-span-2" />
          <Skeleton className="h-80 rounded-2xl" />
        </div>
      </div>
    )
  }

  // 计算趋势百分比（模拟数据）
  const userTrend
    = stats?.new_accounts_today && stats?.new_accounts_week
      ? Math.round(
          ((stats.new_accounts_today * 7) / stats.new_accounts_week - 1) * 100,
        )
      : 0

  return (
    <div className="space-y-6 p-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">仪表盘</h1>
          <p className="mt-1 text-sm text-text-tertiary">
            欢迎回来，这是您的数据概览
          </p>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="用户总数"
          value={stats?.total_accounts || 0}
          subValue={`活跃 ${stats?.active_accounts || 0} · 今日 +${
            stats?.new_accounts_today || 0
          }`}
          icon={<RiGroupLine className="h-6 w-6 text-white" />}
          gradient="linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)"
          trend={userTrend}
          delay={0}
        />
        <StatCard
          title="租户总数"
          value={stats?.total_tenants || 0}
          subValue={`活跃 ${stats?.active_tenants || 0}`}
          icon={<RiBuilding2Line className="h-6 w-6 text-white" />}
          gradient="linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)"
          delay={100}
        />
        <StatCard
          title="邀请码"
          value={stats?.total_invitation_codes || 0}
          subValue={`已使用 ${stats?.used_invitation_codes || 0}`}
          icon={<RiTicketLine className="h-6 w-6 text-white" />}
          gradient="linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
          delay={200}
        />
        <StatCard
          title="管理员"
          value={stats?.total_admins || 0}
          subValue={`活跃 ${stats?.active_admins || 0}`}
          icon={<RiAdminLine className="h-6 w-6 text-white" />}
          gradient="linear-gradient(135deg, #10b981 0%, #059669 100%)"
          delay={300}
        />
      </div>

      {/* 图表和快速统计 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <UserGrowthChart />
        </div>

        {/* 快速统计 */}
        <div className="h-full">
          <div className="h-full rounded-2xl border border-components-panel-border bg-components-panel-bg p-5">
            <h3 className="mb-4 font-semibold text-text-primary">本周概览</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">新增用户</span>
                <div className="flex items-center gap-2">
                  <div className="h-8 w-24">
                    <TrendChart
                      data={[30, 40, 35, 50, 49, 60, 70]}
                      color="#3b82f6"
                    />
                  </div>
                  <span className="font-semibold tabular-nums text-text-primary">
                    {stats?.new_accounts_week || 0}
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">活跃用户</span>
                <div className="flex items-center gap-2">
                  <div className="h-8 w-24">
                    <TrendChart
                      data={[65, 59, 80, 81, 56, 55, 72]}
                      color="#10b981"
                    />
                  </div>
                  <span className="font-semibold tabular-nums text-text-primary">
                    {stats?.active_accounts || 0}
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">活跃租户</span>
                <div className="flex items-center gap-2">
                  <div className="h-8 w-24">
                    <TrendChart
                      data={[20, 25, 22, 30, 28, 35, 40]}
                      color="#8b5cf6"
                    />
                  </div>
                  <span className="font-semibold tabular-nums text-text-primary">
                    {stats?.active_tenants || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 最近数据列表 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 最近注册的用户 */}
        <div className="overflow-hidden rounded-2xl border border-components-panel-border bg-components-panel-bg">
          <div className="flex items-center justify-between border-b border-divider-subtle px-5 py-4">
            <h3 className="font-semibold text-text-primary">最近注册的用户</h3>
            <span className="text-xs text-text-tertiary">最近 5 条</span>
          </div>
          <div className="space-y-2 p-3">
            {accountsLoading
              ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map(i => (
                      <Skeleton key={i} className="h-16 rounded-xl" />
                    ))}
                  </div>
                )
              : recentAccounts && recentAccounts.length > 0
                ? (
                    recentAccounts.map((account, index) => (
                      <ListItem
                        key={account.id}
                        primary={account.name}
                        secondary={account.email}
                        status={account.status}
                        time={formatDate(account.created_at)}
                        delay={500 + index * 80}
                      />
                    ))
                  )
                : (
                    <div className="py-12 text-center text-text-tertiary">
                      暂无数据
                    </div>
                  )}
          </div>
        </div>

        {/* 最近创建的租户 */}
        <div className="overflow-hidden rounded-2xl border border-components-panel-border bg-components-panel-bg">
          <div className="flex items-center justify-between border-b border-divider-subtle px-5 py-4">
            <h3 className="font-semibold text-text-primary">最近创建的租户</h3>
            <span className="text-xs text-text-tertiary">最近 5 条</span>
          </div>
          <div className="space-y-2 p-3">
            {tenantsLoading
              ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map(i => (
                      <Skeleton key={i} className="h-16 rounded-xl" />
                    ))}
                  </div>
                )
              : recentTenants && recentTenants.length > 0
                ? (
                    recentTenants.map((tenant, index) => (
                      <ListItem
                        key={tenant.id}
                        primary={tenant.name}
                        secondary={`计划: ${tenant.plan}`}
                        status={tenant.status}
                        time={formatDate(tenant.created_at)}
                        delay={500 + index * 80}
                      />
                    ))
                  )
                : (
                    <div className="py-12 text-center text-text-tertiary">
                      暂无数据
                    </div>
                  )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
