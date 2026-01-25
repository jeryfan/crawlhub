'use client'

import type { ColumnDef } from '@/app/components/base/table'
import type { RechargeOrderItem, SubscriptionOrderItem } from '@/types/billing'
import {
  RiMoneyDollarCircleLine,
  RiTimeLine,
  RiVipCrownLine,
  RiWallet3Line,
} from '@remixicon/react'
import { useMemo, useState } from 'react'
import Input from '@/app/components/base/input'
import Pagination from '@/app/components/base/pagination'
import { SimpleSelect } from '@/app/components/base/select'
import TabSlider from '@/app/components/base/tab-slider'
import { DataTable } from '@/app/components/base/table'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useBillingStats,
  useRechargeOrders,
  useSubscriptionOrders,
} from '@/service/use-admin-billing'
import { PaymentMethod, RechargeOrderStatus, SubscriptionOrderStatus } from '@/types/billing'

// 状态徽章
const StatusBadge = ({ status, type }: { status: string, type: 'recharge' | 'subscription' }) => {
  const rechargeStatusConfig: Record<string, { label: string, color: string }> = {
    [RechargeOrderStatus.PENDING]: { label: '待支付', color: 'bg-util-colors-yellow-yellow-500' },
    [RechargeOrderStatus.PAID]: { label: '已支付', color: 'bg-util-colors-green-green-500' },
    [RechargeOrderStatus.CANCELLED]: { label: '已取消', color: 'bg-util-colors-gray-gray-500' },
    [RechargeOrderStatus.EXPIRED]: { label: '已过期', color: 'bg-util-colors-red-red-500' },
  }

  const subscriptionStatusConfig: Record<string, { label: string, color: string }> = {
    [SubscriptionOrderStatus.ACTIVE]: { label: '生效中', color: 'bg-util-colors-green-green-500' },
    [SubscriptionOrderStatus.EXPIRED]: { label: '已过期', color: 'bg-util-colors-red-red-500' },
    [SubscriptionOrderStatus.CANCELLED]: { label: '已取消', color: 'bg-util-colors-gray-gray-500' },
  }

  const config = type === 'recharge'
    ? rechargeStatusConfig[status]
    : subscriptionStatusConfig[status]

  if (!config)
    return <span>{status}</span>

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`h-1.5 w-1.5 rounded-full ${config.color}`} />
      <span className="text-sm text-text-secondary">{config.label}</span>
    </span>
  )
}

// 支付方式徽章
const PaymentMethodBadge = ({ method }: { method: string }) => {
  const config: Record<string, { label: string, color: string }> = {
    [PaymentMethod.WECHAT]: { label: '微信支付', color: 'text-green-600 bg-green-50' },
    [PaymentMethod.ALIPAY]: { label: '支付宝', color: 'text-blue-600 bg-blue-50' },
  }
  const item = config[method] || { label: method, color: 'text-gray-600 bg-gray-50' }

  return (
    <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${item.color}`}>
      {item.label}
    </span>
  )
}

// 计划徽章
const PlanBadge = ({ plan }: { plan: string }) => {
  const config: Record<string, { label: string, color: string }> = {
    basic: { label: 'Basic', color: 'text-gray-600 bg-gray-100' },
    pro: { label: 'Pro', color: 'text-blue-600 bg-blue-50' },
    max: { label: 'Max', color: 'text-purple-600 bg-purple-50' },
  }
  const item = config[plan] || { label: plan, color: 'text-gray-600 bg-gray-100' }

  return (
    <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${item.color}`}>
      {item.label}
    </span>
  )
}

// 格式化金额
const formatAmount = (amount: number | string): string => {
  const num = typeof amount === 'string' ? Number.parseFloat(amount) : amount
  return `¥${num.toFixed(2)}`
}

// 统计卡片
const StatCard = ({ icon, label, value, color }: {
  icon: React.ReactNode
  label: string
  value: string | number
  color: string
}) => (
  <div className="rounded-xl border border-divider-subtle bg-components-panel-bg p-4">
    <div className="flex items-center gap-3">
      <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${color}`}>
        {icon}
      </div>
      <div>
        <p className="text-sm text-text-tertiary">{label}</p>
        <p className="text-xl font-semibold text-text-primary">{value}</p>
      </div>
    </div>
  </div>
)

const BillingPage = () => {
  const [activeTab, setActiveTab] = useState('recharge')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const { formatDateTime } = useTimestamp()

  const { data: statsData } = useBillingStats()

  const { data: rechargeData, isLoading: rechargeLoading } = useRechargeOrders({
    page,
    page_size: pageSize,
    status: statusFilter || undefined,
  })

  const { data: subscriptionData, isLoading: subscriptionLoading } = useSubscriptionOrders({
    page,
    page_size: pageSize,
    status: statusFilter || undefined,
  })

  // 充值订单表格列
  const rechargeColumns: ColumnDef<RechargeOrderItem, unknown>[] = useMemo(() => [
    {
      id: 'tenant',
      header: '租户',
      cell: ({ row }) => (
        <div>
          <p className="font-medium text-text-primary">{row.original.tenant_name}</p>
          <p className="text-xs text-text-tertiary">
            {row.original.tenant_id.slice(0, 8)}
            ...
          </p>
        </div>
      ),
      meta: { skeletonClassName: 'h-10 w-32' },
    },
    {
      id: 'user',
      header: '用户',
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.account_name || '-'}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-24' },
    },
    {
      id: 'amount',
      header: '金额',
      cell: ({ row }) => (
        <span className="font-semibold text-text-primary">
          {formatAmount(row.original.amount)}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-20' },
    },
    {
      id: 'payment_method',
      header: '支付方式',
      cell: ({ row }) => <PaymentMethodBadge method={row.original.payment_method} />,
      meta: { skeletonClassName: 'h-6 w-16' },
    },
    {
      id: 'status',
      header: '状态',
      cell: ({ row }) => <StatusBadge status={row.original.status} type="recharge" />,
      meta: { skeletonClassName: 'h-6 w-16' },
    },
    {
      id: 'trade_no',
      header: '交易号',
      cell: ({ row }) => (
        <span
          className="block max-w-[120px] truncate text-sm text-text-secondary"
          title={row.original.trade_no || ''}
        >
          {row.original.trade_no || '-'}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-24' },
    },
    {
      id: 'paid_at',
      header: '支付时间',
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {formatDateTime(row.original.paid_at)}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-32' },
    },
    {
      id: 'created_at',
      header: '创建时间',
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {formatDateTime(row.original.created_at)}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-32' },
    },
  ], [formatDateTime])

  // 订阅订单表格列
  const subscriptionColumns: ColumnDef<SubscriptionOrderItem, unknown>[] = useMemo(() => [
    {
      id: 'tenant',
      header: '租户',
      cell: ({ row }) => (
        <div>
          <p className="font-medium text-text-primary">{row.original.tenant_name}</p>
          <p className="text-xs text-text-tertiary">
            {row.original.tenant_id.slice(0, 8)}
            ...
          </p>
        </div>
      ),
      meta: { skeletonClassName: 'h-10 w-32' },
    },
    {
      id: 'user',
      header: '用户',
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.account_name || '-'}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-24' },
    },
    {
      id: 'plan',
      header: '计划',
      cell: ({ row }) => <PlanBadge plan={row.original.plan} />,
      meta: { skeletonClassName: 'h-6 w-16' },
    },
    {
      id: 'price',
      header: '价格',
      cell: ({ row }) => (
        <span className="font-semibold text-text-primary">
          {formatAmount(row.original.price)}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-20' },
    },
    {
      id: 'status',
      header: '状态',
      cell: ({ row }) => <StatusBadge status={row.original.status} type="subscription" />,
      meta: { skeletonClassName: 'h-6 w-16' },
    },
    {
      id: 'auto_renew',
      header: '自动续费',
      cell: ({ row }) => (
        <span className={`text-sm ${row.original.is_auto_renew ? 'text-green-600' : 'text-text-tertiary'}`}>
          {row.original.is_auto_renew ? '是' : '否'}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-12' },
    },
    {
      id: 'period',
      header: '有效期',
      cell: ({ row }) => (
        <div className="text-sm text-text-secondary">
          <p>{formatDateTime(row.original.starts_at)}</p>
          <p className="text-text-tertiary">
            -
            {formatDateTime(row.original.expires_at)}
          </p>
        </div>
      ),
      meta: { skeletonClassName: 'h-10 w-32' },
    },
    {
      id: 'created_at',
      header: '创建时间',
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {formatDateTime(row.original.created_at)}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-32' },
    },
  ], [formatDateTime])

  const rechargeStatusOptions = [
    { value: '', name: '全部状态' },
    { value: RechargeOrderStatus.PENDING, name: '待支付' },
    { value: RechargeOrderStatus.PAID, name: '已支付' },
    { value: RechargeOrderStatus.CANCELLED, name: '已取消' },
    { value: RechargeOrderStatus.EXPIRED, name: '已过期' },
  ]

  const subscriptionStatusOptions = [
    { value: '', name: '全部状态' },
    { value: SubscriptionOrderStatus.ACTIVE, name: '生效中' },
    { value: SubscriptionOrderStatus.EXPIRED, name: '已过期' },
    { value: SubscriptionOrderStatus.CANCELLED, name: '已取消' },
  ]

  const handleTabChange = (value: string) => {
    setActiveTab(value)
    setPage(1)
    setStatusFilter('')
  }

  const currentData = activeTab === 'recharge' ? rechargeData : subscriptionData
  const _isLoading = activeTab === 'recharge' ? rechargeLoading : subscriptionLoading

  return (
    <>
      <div className="mb-6 shrink-0">
        <h1 className="text-2xl font-semibold text-text-primary">账单管理</h1>
        <p className="mt-1 text-text-tertiary">管理充值订单和订阅订单</p>
      </div>

      {/* 统计卡片 */}
      <div className="mb-6 grid shrink-0 grid-cols-4 gap-4">
        <StatCard
          icon={<RiMoneyDollarCircleLine className="h-5 w-5 text-green-600" />}
          label="总充值金额"
          value={formatAmount(statsData?.total_recharge_amount || 0)}
          color="bg-green-50"
        />
        <StatCard
          icon={<RiVipCrownLine className="h-5 w-5 text-blue-600" />}
          label="订阅收入"
          value={formatAmount(statsData?.total_subscription_revenue || 0)}
          color="bg-blue-50"
        />
        <StatCard
          icon={<RiWallet3Line className="h-5 w-5 text-purple-600" />}
          label="活跃订阅"
          value={statsData?.active_subscriptions || 0}
          color="bg-purple-50"
        />
        <StatCard
          icon={<RiTimeLine className="h-5 w-5 text-orange-600" />}
          label="待支付订单"
          value={statsData?.pending_orders || 0}
          color="bg-orange-50"
        />
      </div>

      {/* Tab 切换 */}
      <div className="mb-6 shrink-0">
        <TabSlider
          value={activeTab}
          onChange={handleTabChange}
          options={[
            { value: 'recharge', text: '充值订单' },
            { value: 'subscription', text: '订阅订单' },
          ]}
        />
      </div>

      {/* 筛选 */}
      <div className="mb-6 flex shrink-0 items-center gap-4">
        <div className="relative max-w-md">
          <Input
            showLeftIcon
            showClearIcon
            wrapperClassName="!w-[200px]"
            placeholder="搜索租户名称"
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
          />
        </div>
        <SimpleSelect
          className="w-32"
          defaultValue={statusFilter}
          items={activeTab === 'recharge' ? rechargeStatusOptions : subscriptionStatusOptions}
          onSelect={(item) => {
            setStatusFilter(item.value as string)
            setPage(1)
          }}
        />
      </div>

      {/* 表格 */}
      {activeTab === 'recharge'
        ? (
            <DataTable
              columns={rechargeColumns}
              data={rechargeData?.items || []}
              isLoading={rechargeLoading}
              loadingRowCount={5}
              emptyText="暂无充值订单"
              stickyHeader
            />
          )
        : (
            <DataTable
              columns={subscriptionColumns}
              data={subscriptionData?.items || []}
              isLoading={subscriptionLoading}
              loadingRowCount={5}
              emptyText="暂无订阅订单"
              stickyHeader
            />
          )}

      {/* 分页 */}
      {currentData && currentData.total_pages > 1 && (
        <div className="mt-4 flex shrink-0 justify-end">
          <Pagination
            current={page}
            onChange={setPage}
            total={currentData.total}
            limit={pageSize}
            onLimitChange={setPageSize}
          />
        </div>
      )}
    </>
  )
}

export default BillingPage
