'use client'

import type { ColumnDef, RowSelectionState, SortingState } from '@/app/components/base/table'
import type { ProxyRoute, ProxyRouteCreate, ProxyRouteUpdate } from '@/types/proxy'
import {
  RiAddLine,
  RiCloseLine,
  RiDeleteBinLine,
  RiEditLine,
  RiToggleLine,
} from '@remixicon/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import { SimpleSelect } from '@/app/components/base/select'
import Skeleton from '@/app/components/base/skeleton'
import Switch from '@/app/components/base/switch'
import {
  createActionColumn,
  DataTable,
  DataTableToolbar,
} from '@/app/components/base/table'
import Textarea from '@/app/components/base/textarea'
import Toast from '@/app/components/base/toast'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useCreateProxyRoute,
  useDeleteProxyRoute,
  useProxyRoute,
  useProxyRoutes,
  useToggleProxyRouteStatus,
  useUpdateProxyRoute,
} from '@/service/use-proxy'

const statusOptions = [
  { value: '', name: '全部状态' },
  { value: 'enabled', name: '启用' },
  { value: 'disabled', name: '禁用' },
]

const methodOptions = [
  { value: '*', name: '全部方法' },
  { value: 'GET', name: 'GET' },
  { value: 'POST', name: 'POST' },
  { value: 'PUT', name: 'PUT' },
  { value: 'DELETE', name: 'DELETE' },
  { value: 'PATCH', name: 'PATCH' },
]

const loadBalanceModeOptions = [
  { value: 'failover', name: '故障转移' },
  { value: 'round_robin', name: '轮询' },
]

type ProxyRouteFormModalProps = {
  isOpen: boolean
  onClose: () => void
  routeId?: string | null
  onSubmit: (data: ProxyRouteCreate | ProxyRouteUpdate) => Promise<void> | void
  isLoading: boolean
}

const ProxyRouteFormModal = ({ isOpen, onClose, routeId, onSubmit, isLoading }: ProxyRouteFormModalProps) => {
  const [formData, setFormData] = useState<ProxyRouteCreate>({
    path: '',
    target_urls: [''],
    load_balance_mode: 'failover',
    methods: '*',
    description: '',
    timeout: 60,
    preserve_host: false,
    enable_logging: true,
    streaming: true,
  })

  const { data: routeDetail, isLoading: isLoadingDetail } = useProxyRoute(routeId || '')

  useEffect(() => {
    if (isOpen) {
      if (routeDetail) {
        setFormData({
          path: routeDetail.path,
          target_urls: routeDetail.target_urls,
          load_balance_mode: routeDetail.load_balance_mode,
          methods: routeDetail.methods,
          description: routeDetail.description || '',
          timeout: routeDetail.timeout,
          preserve_host: routeDetail.preserve_host,
          enable_logging: routeDetail.enable_logging,
          streaming: routeDetail.streaming,
        })
      }
      else if (!routeId) {
        setFormData({
          path: '',
          target_urls: [''],
          load_balance_mode: 'failover',
          methods: '*',
          description: '',
          timeout: 60,
          preserve_host: false,
          enable_logging: true,
          streaming: true,
        })
      }
    }
  }, [isOpen, routeDetail, routeId])

  const handleAddUrl = () => {
    setFormData({ ...formData, target_urls: [...formData.target_urls, ''] })
  }

  const handleRemoveUrl = (index: number) => {
    if (formData.target_urls.length <= 1)
      return
    setFormData({
      ...formData,
      target_urls: formData.target_urls.filter((_, i) => i !== index),
    })
  }

  const handleUrlChange = (index: number, value: string) => {
    const newUrls = [...formData.target_urls]
    newUrls[index] = value
    setFormData({ ...formData, target_urls: newUrls })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const filteredUrls = formData.target_urls.filter(url => url.trim() !== '')
    if (filteredUrls.length === 0) {
      Toast.notify({ type: 'error', message: '请至少填写一个目标地址' })
      return
    }
    onSubmit({
      ...formData,
      target_urls: filteredUrls,
    })
  }

  const isEditMode = !!routeId
  const hasMultipleTargets = formData.target_urls.length > 1

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-lg">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            {isEditMode ? '编辑代理路由' : '创建代理路由'}
          </h3>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>
        {isEditMode && isLoadingDetail
          ? (
              <div className="space-y-4">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="ml-auto h-10 w-32" />
              </div>
            )
          : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">路由路径</label>
                  <Input
                    value={formData.path}
                    onChange={e => setFormData({ ...formData, path: e.target.value })}
                    placeholder="/cc"
                    required
                  />
                  <p className="mt-1 text-xs text-text-tertiary">
                    匹配的请求路径前缀，如 /cc，请求 /proxy/cc/v1/chat 会转发到目标地址/v1/chat
                  </p>
                </div>
                <div>
                  <div className="mb-1.5 flex items-center justify-between">
                    <label className="text-sm text-text-secondary">目标地址</label>
                    <button
                      type="button"
                      onClick={handleAddUrl}
                      className="flex items-center text-xs text-primary-600 hover:text-primary-700"
                    >
                      <RiAddLine className="mr-0.5 h-3.5 w-3.5" />
                      添加
                    </button>
                  </div>
                  {formData.target_urls.map((url, index) => (
                    <div key={index} className="mb-2 flex items-center gap-2">
                      <Input
                        value={url}
                        onChange={e => handleUrlChange(index, e.target.value)}
                        placeholder="https://api.example.com"
                        className="flex-1"
                        required={index === 0}
                      />
                      {formData.target_urls.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveUrl(index)}
                          className="text-text-tertiary hover:text-red-500"
                        >
                          <RiCloseLine className="h-5 w-5" />
                        </button>
                      )}
                    </div>
                  ))}
                  <p className="text-xs text-text-tertiary">
                    路径后缀会自动拼接，如 /proxy/cc/v1/chat → 目标地址/v1/chat
                  </p>
                </div>
                {hasMultipleTargets && (
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">负载均衡模式</label>
                    <SimpleSelect
                      items={loadBalanceModeOptions}
                      defaultValue={formData.load_balance_mode}
                      onSelect={item => setFormData({ ...formData, load_balance_mode: item.value as 'round_robin' | 'failover' })}
                    />
                    <p className="mt-1 text-xs text-text-tertiary">
                      {formData.load_balance_mode === 'failover'
                        ? '故障转移：按顺序尝试，失败后切换到下一个'
                        : '轮询：依次使用每个目标地址'}
                    </p>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">允许的方法</label>
                    <SimpleSelect
                      items={methodOptions}
                      defaultValue={formData.methods}
                      onSelect={item => setFormData({ ...formData, methods: item.value as string })}
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">超时时间 (秒)</label>
                    <Input
                      type="number"
                      value={formData.timeout?.toString() || '60'}
                      onChange={e => setFormData({
                        ...formData,
                        timeout: e.target.value ? Number.parseInt(e.target.value) : 60,
                      })}
                      min={1}
                      max={300}
                    />
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">描述</label>
                  <Textarea
                    value={formData.description || ''}
                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                    placeholder="路由描述（可选）"
                    rows={2}
                  />
                </div>
                <div className="flex items-center justify-between rounded-lg border border-divider-regular p-3">
                  <div>
                    <div className="text-sm font-medium text-text-primary">保留原始 Host</div>
                    <div className="text-xs text-text-tertiary">转发请求时保留原始的 Host 头</div>
                  </div>
                  <Switch
                    defaultValue={formData.preserve_host}
                    onChange={v => setFormData({ ...formData, preserve_host: v })}
                  />
                </div>
                <div className="flex items-center justify-between rounded-lg border border-divider-regular p-3">
                  <div>
                    <div className="text-sm font-medium text-text-primary">启用日志记录</div>
                    <div className="text-xs text-text-tertiary">记录请求和响应数据用于审计</div>
                  </div>
                  <Switch
                    defaultValue={formData.enable_logging}
                    onChange={v => setFormData({ ...formData, enable_logging: v })}
                  />
                </div>
                <div className="flex items-center justify-between rounded-lg border border-divider-regular p-3">
                  <div>
                    <div className="text-sm font-medium text-text-primary">流式响应</div>
                    <div className="text-xs text-text-tertiary">启用流式转发，适合 SSE 和大文件传输</div>
                  </div>
                  <Switch
                    defaultValue={formData.streaming}
                    onChange={v => setFormData({ ...formData, streaming: v })}
                  />
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button variant="secondary" onClick={onClose}>取消</Button>
                  <Button variant="primary" type="submit" loading={isLoading}>
                    {isEditMode ? '保存' : '创建'}
                  </Button>
                </div>
              </form>
            )}
      </div>
    </Modal>
  )
}

const ProxyRoutesPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [sorting, setSorting] = useState<SortingState>([])
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectedRoute, setSelectedRoute] = useState<ProxyRoute | null>(null)

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useProxyRoutes({
    page,
    page_size: pageSize,
    status: statusFilter || undefined,
  })

  const createMutation = useCreateProxyRoute()
  const updateMutation = useUpdateProxyRoute()
  const deleteMutation = useDeleteProxyRoute()
  const toggleMutation = useToggleProxyRouteStatus()

  const handleCreate = async (formData: ProxyRouteCreate) => {
    try {
      await createMutation.mutateAsync(formData)
      Toast.notify({ type: 'success', message: '代理路由创建成功' })
      setShowCreateModal(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '创建失败' })
    }
  }

  const handleUpdate = async (formData: ProxyRouteUpdate) => {
    if (!editingId)
      return
    try {
      await updateMutation.mutateAsync({ id: editingId, data: formData })
      Toast.notify({ type: 'success', message: '代理路由更新成功' })
      setShowEditModal(false)
      setEditingId(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handleDelete = async () => {
    if (!selectedRoute)
      return
    try {
      await deleteMutation.mutateAsync(selectedRoute.id)
      Toast.notify({ type: 'success', message: '代理路由删除成功' })
      setShowDeleteModal(false)
      setSelectedRoute(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const handleToggleStatus = async (route: ProxyRoute) => {
    try {
      await toggleMutation.mutateAsync(route.id)
      Toast.notify({
        type: 'success',
        message: `路由已${route.status === 'enabled' ? '禁用' : '启用'}`,
      })
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '操作失败' })
    }
  }

  const handleSortingChange = useCallback((newSorting: SortingState) => {
    setSorting(newSorting)
    setPage(1)
  }, [])

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { bg: string, text: string, label: string }> = {
      enabled: { bg: 'bg-green-100', text: 'text-green-700', label: '启用' },
      disabled: { bg: 'bg-gray-100', text: 'text-gray-600', label: '禁用' },
    }
    const config = statusMap[status] || statusMap.disabled
    return (
      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    )
  }

  const columns: ColumnDef<ProxyRoute>[] = useMemo(() => [
    {
      id: 'path',
      header: '路由路径',
      size: 200,
      cell: ({ row }) => (
        <div>
          <div className="font-mono text-sm font-medium text-text-primary">{row.original.path}</div>
          {row.original.description && (
            <div className="text-xs text-text-tertiary">{row.original.description}</div>
          )}
        </div>
      ),
    },
    {
      id: 'target_urls',
      header: '目标地址',
      size: 300,
      cell: ({ row }) => {
        const urls = row.original.target_urls
        return (
          <div>
            <span className="font-mono text-sm text-text-secondary">{urls[0]}</span>
            {urls.length > 1 && (
              <span className="ml-2 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                +{urls.length - 1}
              </span>
            )}
          </div>
        )
      },
    },
    {
      id: 'load_balance_mode',
      header: '模式',
      size: 80,
      cell: ({ row }) => {
        const hasMultiple = row.original.target_urls.length > 1
        if (!hasMultiple)
          return <span className="text-sm text-text-tertiary">-</span>
        return (
          <span className="text-sm text-text-secondary">
            {row.original.load_balance_mode === 'round_robin' ? '轮询' : '故障转移'}
          </span>
        )
      },
    },
    {
      id: 'methods',
      header: '方法',
      size: 80,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.methods === '*' ? '全部' : row.original.methods}
        </span>
      ),
    },
    {
      id: 'status',
      header: '状态',
      size: 80,
      cell: ({ row }) => getStatusBadge(row.original.status),
    },
    {
      id: 'timeout',
      header: '超时',
      size: 60,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.timeout}
          s
        </span>
      ),
    },
    {
      id: 'enable_logging',
      header: '日志',
      size: 60,
      cell: ({ row }) => (
        <span className={`text-sm ${row.original.enable_logging ? 'text-green-600' : 'text-gray-400'}`}>
          {row.original.enable_logging ? '开启' : '关闭'}
        </span>
      ),
    },
    {
      id: 'streaming',
      header: '流式',
      size: 60,
      cell: ({ row }) => (
        <span className={`text-sm ${row.original.streaming ? 'text-blue-600' : 'text-gray-400'}`}>
          {row.original.streaming ? '开启' : '关闭'}
        </span>
      ),
    },
    {
      id: 'created_at',
      header: '创建时间',
      size: 160,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">{formatDateTime(row.original.created_at)}</span>
      ),
    },
    createActionColumn<ProxyRoute>({
      width: 120,
      sticky: true,
      actions: [
        {
          icon: RiToggleLine,
          label: '切换状态',
          onClick: row => handleToggleStatus(row),
        },
        {
          icon: RiEditLine,
          label: '编辑',
          onClick: (row) => {
            setEditingId(row.id)
            setShowEditModal(true)
          },
        },
        {
          icon: RiDeleteBinLine,
          label: '删除',
          onClick: (row) => {
            setSelectedRoute(row)
            setShowDeleteModal(true)
          },
          variant: 'danger',
        },
      ],
    }),
  ], [formatDateTime])

  const selectedCount = Object.keys(rowSelection).length

  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">代理路由管理</h1>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <RiAddLine className="mr-1 h-4 w-4" />
          创建路由
        </Button>
      </div>

      <DataTableToolbar
        className="shrink-0"
        selectedCount={selectedCount}
        filterSlot={(
          <SimpleSelect
            items={statusOptions}
            defaultValue={statusFilter}
            onSelect={item => setStatusFilter(item.value as string)}
            wrapperClassName="w-32"
          />
        )}
      />

      <DataTable
        columns={columns}
        data={data?.items || []}
        isLoading={isLoading}
        loadingRowCount={5}
        getRowId={row => row.id}
        enableRowSelection
        rowSelection={rowSelection}
        onRowSelectionChange={setRowSelection}
        enableSorting
        sorting={sorting}
        onSortingChange={handleSortingChange}
        stickyHeader
        pagination={{
          page,
          pageSize,
          total: data?.total || 0,
          onChange: setPage,
          onPageSizeChange: setPageSize,
        }}
      />

      <ProxyRouteFormModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={data => handleCreate(data as ProxyRouteCreate)}
        isLoading={createMutation.isPending}
      />
      <ProxyRouteFormModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setEditingId(null)
        }}
        routeId={editingId}
        onSubmit={data => handleUpdate(data as ProxyRouteUpdate)}
        isLoading={updateMutation.isPending}
      />
      <Confirm
        isShow={showDeleteModal}
        onCancel={() => {
          setShowDeleteModal(false)
          setSelectedRoute(null)
        }}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认删除"
        content={`确定要删除代理路由 "${selectedRoute?.path}" 吗？删除后无法恢复。`}
      />
    </>
  )
}

export default ProxyRoutesPage
