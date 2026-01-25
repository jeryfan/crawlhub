'use client'

import type { ColumnDef, SortingState } from '@/app/components/base/table'
import type { ApiUsageItem } from '@/types/api'
import {
  RiArrowDownLine,
  RiArrowUpLine,
  RiDownloadLine,
  RiErrorWarningLine,
  RiLoopLeftLine,
  RiTimeLine,
} from '@remixicon/react'
import { useCallback, useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import { SimpleSelect } from '@/app/components/base/select'
import Skeleton from '@/app/components/base/skeleton'
import {

  DataTable,

} from '@/app/components/base/table'
import useTimestamp from '@/hooks/use-timestamp'
import {
  exportApiUsage,
  useApiKeys,
  useApiUsage,
  useApiUsageByEndpoint,
  useApiUsageStats,
  useApiUsageTrends,
} from '@/service/use-api'
import { useTenants } from '@/service/use-platform'

type StatCardProps = {
  icon: React.ReactNode
  label: string
  value: string | number
  subValue?: string
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  isLoading?: boolean
}

const StatCard = ({ icon, label, value, subValue, trend, trendValue, isLoading }: StatCardProps) => {
  return (
    <div className="rounded-xl border border-divider-subtle bg-background-default-subtle p-4">
      <div className="mb-3 flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-components-panel-bg text-text-tertiary">
          {icon}
        </div>
        <span className="text-sm text-text-secondary">{label}</span>
      </div>
      {isLoading
        ? (
            <Skeleton className="h-8 w-24" />
          )
        : (
            <div className="flex items-end gap-2">
              <span className="text-2xl font-semibold text-text-primary">{value}</span>
              {subValue && <span className="mb-0.5 text-sm text-text-tertiary">{subValue}</span>}
              {trend && trendValue && (
                <span className={`mb-0.5 flex items-center text-sm ${
                  trend === 'up'
                    ? 'text-util-colors-green-green-600'
                    : trend === 'down'
                      ? 'text-util-colors-red-red-600'
                      : 'text-text-tertiary'
                }`}
                >
                  {trend === 'up'
                    ? <RiArrowUpLine className="h-3 w-3" />
                    : trend === 'down' ? <RiArrowDownLine className="h-3 w-3" /> : null}
                  {trendValue}
                </span>
              )}
            </div>
          )}
    </div>
  )
}

const dateRangeOptions = [
  { value: '7d', name: '最近7天' },
  { value: '30d', name: '最近30天' },
  { value: '90d', name: '最近90天' },
]

const getDateRange = (range: string) => {
  const end = new Date()
  const start = new Date()
  switch (range) {
    case '7d':
      start.setDate(end.getDate() - 7)
      break
    case '30d':
      start.setDate(end.getDate() - 30)
      break
    case '90d':
      start.setDate(end.getDate() - 90)
      break
  }
  return {
    start_date: start.toISOString().split('T')[0],
    end_date: end.toISOString().split('T')[0],
  }
}

type TabType = 'logs' | 'endpoints' | 'trends'

const ApiUsagePage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [activeTab, setActiveTab] = useState<TabType>('logs')
  const [dateRange, setDateRange] = useState('7d')
  const [tenantFilter, setTenantFilter] = useState<string>('')
  const [apiKeyFilter, setApiKeyFilter] = useState<string>('')
  const [sorting, setSorting] = useState<SortingState>([])

  const { formatDateTime } = useTimestamp()
  const { start_date, end_date } = getDateRange(dateRange)

  const { data: tenantsData } = useTenants({ page: 1, page_size: 100 })
  const { data: apiKeysData } = useApiKeys({ page: 1, page_size: 100 })

  const tenantOptions = useMemo(() => {
    return [
      { value: '', name: '全部租户' },
      ...(tenantsData?.items?.map(t => ({ value: t.id, name: t.name })) || []),
    ]
  }, [tenantsData])

  const apiKeyOptions = useMemo(() => {
    return [
      { value: '', name: '全部API Key' },
      ...(apiKeysData?.items?.map(k => ({ value: k.id, name: `${k.name} (${k.key_prefix}...)` })) || []),
    ]
  }, [apiKeysData])

  const { data: statsData, isLoading: statsLoading } = useApiUsageStats({
    tenant_id: tenantFilter || undefined,
    api_key_id: apiKeyFilter || undefined,
    start_date,
    end_date,
  })

  const { data: usageData, isLoading: usageLoading } = useApiUsage({
    tenant_id: tenantFilter || undefined,
    api_key_id: apiKeyFilter || undefined,
    start_date,
    end_date,
    page,
    page_size: pageSize,
  })

  const { data: endpointData, isLoading: endpointLoading } = useApiUsageByEndpoint({
    tenant_id: tenantFilter || undefined,
    api_key_id: apiKeyFilter || undefined,
    start_date,
    end_date,
  })

  const { data: trendsData, isLoading: trendsLoading } = useApiUsageTrends({
    tenant_id: tenantFilter || undefined,
    api_key_id: apiKeyFilter || undefined,
    start_date,
    end_date,
    granularity: dateRange === '7d' ? 'day' : 'hour',
  })

  const handleSortingChange = useCallback((newSorting: SortingState) => {
    setSorting(newSorting)
    setPage(1)
  }, [])

  const handleExport = () => {
    const exportUrl = exportApiUsage({
      tenant_id: tenantFilter || undefined,
      api_key_id: apiKeyFilter || undefined,
      start_date,
      end_date,
    })
    window.open(exportUrl, '_blank')
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000)
      return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000)
      return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  const getStatusCodeColor = (code: number) => {
    if (code >= 200 && code < 300)
      return 'text-util-colors-green-green-600 bg-util-colors-green-green-50'
    if (code >= 400 && code < 500)
      return 'text-util-colors-orange-orange-600 bg-util-colors-orange-orange-50'
    if (code >= 500)
      return 'text-util-colors-red-red-600 bg-util-colors-red-red-50'
    return 'text-text-secondary bg-background-section'
  }

  const usageColumns: ColumnDef<ApiUsageItem>[] = useMemo(() => [
    {
      id: 'endpoint',
      header: '端点',
      size: 250,
      cell: ({ row }) => (
        <div>
          <span className={`mr-2 inline-flex rounded px-1.5 py-0.5 text-xs font-medium ${
            row.original.method === 'GET'
              ? 'bg-blue-100 text-blue-700'
              : row.original.method === 'POST'
                ? 'bg-green-100 text-green-700'
                : row.original.method === 'PUT'
                  ? 'bg-yellow-100 text-yellow-700'
                  : row.original.method === 'DELETE'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-gray-100 text-gray-700'
          }`}
          >
            {row.original.method}
          </span>
          <span className="text-sm text-text-primary">{row.original.endpoint}</span>
        </div>
      ),
    },
    {
      id: 'api_key',
      header: 'API Key',
      size: 150,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.api_key_name || row.original.api_key_prefix || '-'}
        </span>
      ),
    },
    {
      id: 'tenant',
      header: '租户',
      size: 120,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">{row.original.tenant_name || '-'}</span>
      ),
    },
    {
      id: 'latency',
      header: '延迟',
      size: 80,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.latency_ms}
          ms
        </span>
      ),
    },
    {
      id: 'status_code',
      header: '状态码',
      size: 80,
      cell: ({ row }) => (
        <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${getStatusCodeColor(row.original.status_code)}`}>
          {row.original.status_code}
        </span>
      ),
    },
    {
      id: 'ip_address',
      header: 'IP地址',
      size: 120,
      cell: ({ row }) => (
        <span className="text-sm text-text-tertiary">{row.original.ip_address}</span>
      ),
    },
    {
      id: 'created_at',
      header: '时间',
      size: 160,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">{formatDateTime(row.original.created_at)}</span>
      ),
    },
  ], [formatDateTime])

  const endpointColumns = useMemo(() => [
    {
      id: 'endpoint',
      header: '端点',
      size: 400,
      cell: ({ row }: { row: { original: { endpoint: string } } }) => (
        <span className="font-medium text-text-primary">{row.original.endpoint}</span>
      ),
    },
    {
      id: 'request_count',
      header: '请求数',
      size: 150,
      cell: ({ row }: { row: { original: { request_count: number } } }) => (
        <span className="text-sm text-text-secondary">{formatNumber(row.original.request_count)}</span>
      ),
    },
    {
      id: 'avg_latency_ms',
      header: '平均延迟',
      size: 150,
      cell: ({ row }: { row: { original: { avg_latency_ms: number } } }) => (
        <span className="text-sm text-text-secondary">
          {row.original.avg_latency_ms.toFixed(0)}
          ms
        </span>
      ),
    },
  ], [])

  const trendsColumns = useMemo(() => [
    {
      id: 'period',
      header: '时间段',
      size: 300,
      cell: ({ row }: { row: { original: { period: string } } }) => (
        <span className="font-medium text-text-primary">{row.original.period}</span>
      ),
    },
    {
      id: 'request_count',
      header: '请求数',
      size: 200,
      cell: ({ row }: { row: { original: { request_count: number } } }) => (
        <span className="text-sm text-text-secondary">{formatNumber(row.original.request_count)}</span>
      ),
    },
  ], [])

  const tabs = [
    { key: 'logs' as const, label: '使用记录' },
    { key: 'endpoints' as const, label: '按端点统计' },
    { key: 'trends' as const, label: '趋势分析' },
  ]

  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">API 使用统计</h1>
        <Button variant="secondary" onClick={handleExport}>
          <RiDownloadLine className="mr-1 h-4 w-4" />
          导出数据
        </Button>
      </div>

      <div className="mb-6 grid shrink-0 grid-cols-3 gap-4">
        <StatCard
          icon={<RiLoopLeftLine className="h-4 w-4" />}
          label="总请求数"
          value={formatNumber(statsData?.stats?.total_requests || 0)}
          isLoading={statsLoading}
        />
        <StatCard
          icon={<RiErrorWarningLine className="h-4 w-4" />}
          label="错误率"
          value={`${(statsData?.stats?.error_rate || 0).toFixed(2)}%`}
          isLoading={statsLoading}
        />
        <StatCard
          icon={<RiTimeLine className="h-4 w-4" />}
          label="平均延迟"
          value={`${(statsData?.stats?.avg_latency_ms || 0).toFixed(0)}`}
          subValue="ms"
          isLoading={statsLoading}
        />
      </div>

      <div className="mb-4 flex shrink-0 items-center gap-3">
        <SimpleSelect
          items={dateRangeOptions}
          defaultValue={dateRange}
          onSelect={item => setDateRange(item.value as string)}
          wrapperClassName="w-32"
        />
        <SimpleSelect
          items={tenantOptions}
          defaultValue={tenantFilter}
          onSelect={item => setTenantFilter(item.value as string)}
          wrapperClassName="w-40"
        />
        <SimpleSelect
          items={apiKeyOptions}
          defaultValue={apiKeyFilter}
          onSelect={item => setApiKeyFilter(item.value as string)}
          wrapperClassName="w-48"
        />
      </div>

      <div className="mb-4 flex shrink-0 border-b border-divider-subtle">
        {tabs.map(tab => (
          <button
            key={tab.key}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'border-b-2 border-components-button-primary-bg text-text-primary'
                : 'text-text-tertiary hover:text-text-secondary'
            }`}
            onClick={() => {
              setActiveTab(tab.key)
              setPage(1)
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'logs' && (
        <DataTable
          columns={usageColumns}
          data={usageData?.items || []}
          isLoading={usageLoading}
          loadingRowCount={5}
          getRowId={row => row.id}
          enableSorting
          sorting={sorting}
          onSortingChange={handleSortingChange}
          stickyHeader
          pagination={{
            page,
            pageSize,
            total: usageData?.total || 0,
            onChange: setPage,
            onPageSizeChange: setPageSize,
          }}
        />
      )}

      {activeTab === 'endpoints' && (
        <DataTable
          columns={endpointColumns as ColumnDef<unknown>[]}
          data={endpointData || []}
          isLoading={endpointLoading}
          loadingRowCount={5}
          getRowId={(row: unknown) => `endpoint-${(row as { endpoint: string }).endpoint}`}
          stickyHeader
        />
      )}

      {activeTab === 'trends' && (
        <DataTable
          columns={trendsColumns as ColumnDef<unknown>[]}
          data={trendsData || []}
          isLoading={trendsLoading}
          loadingRowCount={5}
          getRowId={(row: unknown) => `trend-${(row as { period: string }).period}`}
          stickyHeader
        />
      )}
    </>
  )
}

export default ApiUsagePage
