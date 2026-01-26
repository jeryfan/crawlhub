'use client'

import type { ColumnDef, SortingState } from '@/app/components/base/table'
import type { CrawlHubProxy, CrawlHubProxyCreate, CrawlHubProxyStatus, CrawlHubProxyUpdate, ProxyProtocol } from '@/types/crawlhub'
import {
  RiAddLine,
  RiCloseLine,
  RiDeleteBinLine,
  RiEditLine,
  RiRefreshLine,
  RiServerLine,
} from '@remixicon/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import { SimpleSelect } from '@/app/components/base/select'
import Skeleton from '@/app/components/base/skeleton'
import StatusBadge from '@/app/components/base/status-badge'
import {
  createActionColumn,
  DataTable,
  DataTableToolbar,
} from '@/app/components/base/table'
import Toast from '@/app/components/base/toast'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useCheckCrawlHubProxy,
  useCrawlHubProxies,
  useCrawlHubProxy,
  useCreateCrawlHubProxy,
  useDeleteCrawlHubProxy,
  useUpdateCrawlHubProxy,
} from '@/service/use-crawlhub'

const protocolOptions = [
  { value: 'http', name: 'HTTP' },
  { value: 'https', name: 'HTTPS' },
  { value: 'socks5', name: 'SOCKS5' },
]

const statusOptions = [
  { value: '', name: '全部状态' },
  { value: 'active', name: '可用' },
  { value: 'inactive', name: '不可用' },
  { value: 'cooldown', name: '冷却中' },
]

type ProxyFormModalProps = {
  isOpen: boolean
  onClose: () => void
  proxyId?: string | null
  onSubmit: (data: CrawlHubProxyCreate | CrawlHubProxyUpdate) => void
  isLoading: boolean
}

const ProxyFormModal = ({ isOpen, onClose, proxyId, onSubmit, isLoading }: ProxyFormModalProps) => {
  const [formData, setFormData] = useState<CrawlHubProxyCreate>({
    host: '',
    port: 8080,
    protocol: 'http',
    username: '',
    password: '',
  })

  const { data: proxyDetail, isLoading: isLoadingDetail } = useCrawlHubProxy(proxyId || '')

  useEffect(() => {
    if (isOpen) {
      if (proxyDetail) {
        setFormData({
          host: proxyDetail.host,
          port: proxyDetail.port,
          protocol: proxyDetail.protocol,
          username: proxyDetail.username || '',
          password: '',
        })
      }
      else if (!proxyId) {
        setFormData({
          host: '',
          port: 8080,
          protocol: 'http',
          username: '',
          password: '',
        })
      }
    }
  }, [isOpen, proxyDetail, proxyId])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  const isEditMode = !!proxyId

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-md">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            {isEditMode ? '编辑代理' : '添加代理'}
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
                <Skeleton className="h-10 w-full" />
                <Skeleton className="ml-auto h-10 w-32" />
              </div>
            )
          : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">主机地址</label>
                    <Input
                      value={formData.host}
                      onChange={e => setFormData({ ...formData, host: e.target.value })}
                      placeholder="例如: 192.168.1.1"
                      required
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">端口</label>
                    <Input
                      type="number"
                      value={formData.port}
                      onChange={e => setFormData({ ...formData, port: Number.parseInt(e.target.value) || 8080 })}
                      placeholder="8080"
                      required
                    />
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">协议</label>
                  <SimpleSelect
                    className="w-full"
                    defaultValue={formData.protocol}
                    items={protocolOptions}
                    onSelect={item => setFormData({ ...formData, protocol: item.value as ProxyProtocol })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">用户名（可选）</label>
                    <Input
                      value={formData.username || ''}
                      onChange={e => setFormData({ ...formData, username: e.target.value })}
                      placeholder="用户名"
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">密码（可选）</label>
                    <Input
                      type="password"
                      value={formData.password || ''}
                      onChange={e => setFormData({ ...formData, password: e.target.value })}
                      placeholder="密码"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button variant="secondary" onClick={onClose}>取消</Button>
                  <Button variant="primary" type="submit" loading={isLoading}>
                    {isEditMode ? '保存' : '添加'}
                  </Button>
                </div>
              </form>
            )}
      </div>
    </Modal>
  )
}

const ProxiesPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [statusFilter, setStatusFilter] = useState<CrawlHubProxyStatus | ''>('')
  const [sorting, setSorting] = useState<SortingState>([])

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectedProxy, setSelectedProxy] = useState<CrawlHubProxy | null>(null)

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useCrawlHubProxies({
    page,
    page_size: pageSize,
    status: statusFilter || undefined,
  })

  const createMutation = useCreateCrawlHubProxy()
  const updateMutation = useUpdateCrawlHubProxy()
  const deleteMutation = useDeleteCrawlHubProxy()
  const checkMutation = useCheckCrawlHubProxy()

  const handleCreate = async (formData: CrawlHubProxyCreate) => {
    try {
      await createMutation.mutateAsync(formData)
      Toast.notify({ type: 'success', message: '代理添加成功' })
      setShowCreateModal(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '添加失败' })
    }
  }

  const handleUpdate = async (formData: CrawlHubProxyUpdate) => {
    if (!editingId)
      return
    try {
      await updateMutation.mutateAsync({ id: editingId, data: formData })
      Toast.notify({ type: 'success', message: '代理更新成功' })
      setShowEditModal(false)
      setEditingId(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handleDelete = async () => {
    if (!selectedProxy)
      return
    try {
      await deleteMutation.mutateAsync(selectedProxy.id)
      Toast.notify({ type: 'success', message: '代理删除成功' })
      setShowDeleteModal(false)
      setSelectedProxy(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const handleCheck = async (proxy: CrawlHubProxy) => {
    try {
      await checkMutation.mutateAsync(proxy.id)
      Toast.notify({ type: 'success', message: '检测完成' })
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '检测失败' })
    }
  }

  const handleSortingChange = useCallback((newSorting: SortingState) => {
    setSorting(newSorting)
    setPage(1)
  }, [])

  const columns: ColumnDef<CrawlHubProxy>[] = useMemo(() => [
    {
      id: 'host',
      header: '代理地址',
      size: 200,
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <RiServerLine className="h-4 w-4 text-text-tertiary" />
          <span className="font-medium text-text-primary">
            {row.original.host}
            :
            {row.original.port}
          </span>
        </div>
      ),
      meta: {
        skeletonClassName: 'h-6 w-32',
      },
    },
    {
      id: 'protocol',
      header: '协议',
      size: 100,
      cell: ({ row }) => (
        <span className="inline-flex items-center rounded-md bg-background-section px-2 py-1 text-xs font-medium uppercase text-text-secondary">
          {row.original.protocol}
        </span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-16',
      },
    },
    {
      id: 'status',
      header: '状态',
      size: 100,
      cell: ({ row }) => (
        <StatusBadge
          status={row.original.status}
          statusConfig={{
            active: { label: '可用', color: 'bg-util-colors-green-green-500' },
            inactive: { label: '不可用', color: 'bg-util-colors-red-red-500' },
            cooldown: { label: '冷却中', color: 'bg-util-colors-yellow-yellow-500' },
          }}
        />
      ),
      meta: {
        skeletonClassName: 'h-6 w-16',
      },
    },
    {
      id: 'success_rate',
      header: '成功率',
      size: 100,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {(row.original.success_rate * 100).toFixed(1)}
          %
        </span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-16',
      },
    },
    {
      id: 'last_check_at',
      header: '最后检测',
      size: 160,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.last_check_at ? formatDateTime(row.original.last_check_at) : '-'}
        </span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-32',
      },
    },
    createActionColumn<CrawlHubProxy>({
      width: 140,
      actions: [
        {
          icon: RiRefreshLine,
          label: '检测',
          onClick: row => handleCheck(row),
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
            setSelectedProxy(row)
            setShowDeleteModal(true)
          },
          variant: 'danger',
        },
      ],
    }),
  ], [formatDateTime])

  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">代理池</h1>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <RiAddLine className="mr-1 h-4 w-4" />
          添加代理
        </Button>
      </div>

      <DataTableToolbar
        className="shrink-0"
        filterSlot={(
          <SimpleSelect
            className="w-32"
            defaultValue={statusFilter}
            items={statusOptions}
            onSelect={(item) => {
              setStatusFilter(item.value as CrawlHubProxyStatus | '')
              setPage(1)
            }}
          />
        )}
      />

      <DataTable
        columns={columns}
        data={data?.items || []}
        isLoading={isLoading}
        loadingRowCount={5}
        getRowId={row => row.id}
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

      <ProxyFormModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={data => handleCreate(data as CrawlHubProxyCreate)}
        isLoading={createMutation.isPending}
      />
      <ProxyFormModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setEditingId(null)
        }}
        proxyId={editingId}
        onSubmit={data => handleUpdate(data as CrawlHubProxyUpdate)}
        isLoading={updateMutation.isPending}
      />
      <Confirm
        isShow={showDeleteModal}
        onCancel={() => {
          setShowDeleteModal(false)
          setSelectedProxy(null)
        }}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认删除"
        content={`确定要删除代理 "${selectedProxy?.host}:${selectedProxy?.port}" 吗？`}
      />
    </>
  )
}

export default ProxiesPage
