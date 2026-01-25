'use client'

import type { ColumnDef, RowSelectionState, SortingState } from '@/app/components/base/table'
import type { ApiKeyCreate, ApiKeyListItem, ApiKeyUpdate } from '@/types/api'
import {
  RiAddLine,
  RiCloseLine,
  RiDeleteBinLine,
  RiEditLine,
  RiFileCopyLine,
  RiForbidLine,
  RiRefreshLine,
} from '@remixicon/react'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import DatePicker from '@/app/components/base/date-and-time-picker/date-picker'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import { SimpleSelect } from '@/app/components/base/select'
import Skeleton from '@/app/components/base/skeleton'
import {

  createActionColumn,
  DataTable,

  DataTableToolbar,
} from '@/app/components/base/table'
import Textarea from '@/app/components/base/textarea'
import Toast from '@/app/components/base/toast'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useApiKey,
  useApiKeys,
  useCreateApiKey,
  useDeleteApiKey,
  useRegenerateApiKey,
  useRevokeApiKey,
  useUpdateApiKey,
} from '@/service/use-api'
import { useTenants } from '@/service/use-platform'

const statusOptions = [
  { value: 'active', name: '启用' },
  { value: 'disabled', name: '禁用' },
]

type ApiKeyFormModalProps = {
  isOpen: boolean
  onClose: () => void
  keyId?: string | null
  onSubmit: (data: ApiKeyCreate | ApiKeyUpdate) => Promise<void> | void
  isLoading: boolean
}

const ApiKeyFormModal = ({ isOpen, onClose, keyId, onSubmit, isLoading }: ApiKeyFormModalProps) => {
  const [formData, setFormData] = useState<ApiKeyCreate>({
    name: '',
    tenant_id: '',
    whitelist: undefined,
    rpm: undefined,
    rph: undefined,
    balance: undefined,
    expires_at: undefined,
  })
  const [whitelistInput, setWhitelistInput] = useState('')

  const { data: keyDetail, isLoading: isLoadingDetail } = useApiKey(keyId || '')
  const { data: tenantsData } = useTenants({ page: 1, page_size: 100 })

  const tenantOptions = useMemo(() => {
    return tenantsData?.items?.map(t => ({ value: t.id, name: t.name })) || []
  }, [tenantsData])

  useEffect(() => {
    if (isOpen) {
      if (keyDetail) {
        const ipList = keyDetail.whitelist || []
        setFormData({
          name: keyDetail.name,
          tenant_id: keyDetail.tenant_id ?? '',
          whitelist: ipList.length > 0 ? ipList : undefined,
          rpm: keyDetail.rpm || undefined,
          rph: keyDetail.rph || undefined,
          balance: keyDetail.balance || undefined,
          expires_at: keyDetail.expires_at || undefined,
        })
        setWhitelistInput(ipList.join('\n'))
      }
      else if (!keyId) {
        setFormData({
          name: '',
          tenant_id: '',
          whitelist: undefined,
          rpm: undefined,
          rph: undefined,
          balance: undefined,
          expires_at: undefined,
        })
        setWhitelistInput('')
      }
    }
  }, [isOpen, keyDetail, keyId])

  const handleWhitelistChange = (value: string) => {
    setWhitelistInput(value)
    const ips = value.split('\n').map(s => s.trim()).filter(Boolean)
    setFormData({ ...formData, whitelist: ips.length > 0 ? ips : undefined })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const submitData = keyId
      ? {
          name: formData.name,
          whitelist: formData.whitelist,
          rpm: formData.rpm,
          rph: formData.rph,
          balance: formData.balance,
          expires_at: formData.expires_at,
        }
      : formData
    onSubmit(submitData)
  }

  const isEditMode = !!keyId

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-lg">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            {isEditMode ? '编辑 API Key' : '创建 API Key'}
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
                  <label className="mb-1.5 block text-sm text-text-secondary">名称</label>
                  <Input
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="请输入 API Key 名称"
                    required
                  />
                </div>
                {!isEditMode && (
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">租户（可选）</label>
                    <SimpleSelect
                      items={tenantOptions}
                      defaultValue={formData.tenant_id}
                      onSelect={item => setFormData({ ...formData, tenant_id: item.value as string })}
                      placeholder="选择租户（留空为全局 API Key）"
                    />
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">RPM (每分钟限制)</label>
                    <Input
                      type="number"
                      value={formData.rpm?.toString() || ''}
                      onChange={e => setFormData({
                        ...formData,
                        rpm: e.target.value ? Number.parseInt(e.target.value) : undefined,
                      })}
                      placeholder="留空不限制"
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">RPH (每小时限制)</label>
                    <Input
                      type="number"
                      value={formData.rph?.toString() || ''}
                      onChange={e => setFormData({
                        ...formData,
                        rph: e.target.value ? Number.parseInt(e.target.value) : undefined,
                      })}
                      placeholder="留空不限制"
                    />
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">余额</label>
                  <Input
                    type="number"
                    value={formData.balance?.toString() || ''}
                    onChange={e => setFormData({
                      ...formData,
                      balance: e.target.value ? Number.parseFloat(e.target.value) : undefined,
                    })}
                    placeholder="留空不限制"
                  />
                  <p className="mt-1 text-xs text-text-tertiary">
                    用于付费场景的账户余额
                  </p>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">IP 白名单</label>
                  <Textarea
                    value={whitelistInput}
                    onChange={e => handleWhitelistChange(e.target.value)}
                    placeholder="一行一个IP地址，留空允许所有IP"
                    rows={3}
                  />
                  <p className="mt-1 text-xs text-text-tertiary">
                    支持单个IP或CIDR格式，如: 192.168.1.1 或 10.0.0.0/8
                  </p>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">过期时间</label>
                  <DatePicker
                    value={formData.expires_at ? dayjs(formData.expires_at) : undefined}
                    onChange={(date) => {
                      setFormData({
                        ...formData,
                        expires_at: date ? date.toISOString() : undefined,
                      })
                    }}
                    onClear={() => {
                      setFormData({
                        ...formData,
                        expires_at: undefined,
                      })
                    }}
                    placeholder="选择过期时间（留空永不过期）"
                    needTimePicker
                    popupZIndexClassname="z-[100]"
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

type KeyDisplayModalProps = {
  isOpen: boolean
  onClose: () => void
  apiKey: string | null | undefined
  keyName: string
}

const KeyDisplayModal = ({ isOpen, onClose, apiKey, keyName }: KeyDisplayModalProps) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    if (apiKey) {
      navigator.clipboard.writeText(apiKey)
      setCopied(true)
      Toast.notify({ type: 'success', message: '已复制到剪贴板' })
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-lg">
      <div className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">API Key 创建成功</h3>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>
        <div className="mb-3 rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
          请立即复制并妥善保存此 API Key，关闭后将无法再次查看完整密钥。
        </div>
        <div className="mb-2 text-sm text-text-secondary">
          名称:
          {' '}
          {keyName}
        </div>
        <div className="rounded-lg border border-divider-regular bg-background-section p-3">
          <code className="block break-all text-sm text-text-primary">{apiKey}</code>
        </div>
        <div className="mt-4 flex justify-end gap-3">
          <Button variant="secondary" onClick={handleCopy}>
            <RiFileCopyLine className="mr-1 h-4 w-4" />
            {copied ? '已复制' : '复制 API Key'}
          </Button>
          <Button variant="primary" onClick={onClose}>我已保存</Button>
        </div>
      </div>
    </Modal>
  )
}

const ApiKeysPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [sorting, setSorting] = useState<SortingState>([])
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showRevokeModal, setShowRevokeModal] = useState(false)
  const [showRegenerateModal, setShowRegenerateModal] = useState(false)
  const [showKeyModal, setShowKeyModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectedKey, setSelectedKey] = useState<ApiKeyListItem | null>(null)
  const [newApiKey, setNewApiKey] = useState<string | null>(null)
  const [newKeyName, setNewKeyName] = useState('')

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useApiKeys({
    page,
    page_size: pageSize,
    search: searchKeyword || undefined,
    status: statusFilter || undefined,
  })

  const createMutation = useCreateApiKey()
  const updateMutation = useUpdateApiKey()
  const deleteMutation = useDeleteApiKey()
  const revokeMutation = useRevokeApiKey()
  const regenerateMutation = useRegenerateApiKey()

  const handleSearch = useCallback(() => {
    setSearchKeyword(keyword)
    setPage(1)
  }, [keyword])

  const handleCreate = async (formData: ApiKeyCreate) => {
    try {
      const result = await createMutation.mutateAsync(formData)
      setNewApiKey(result.key)
      setNewKeyName(result.name)
      setShowCreateModal(false)
      setShowKeyModal(true)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '创建失败' })
    }
  }

  const handleUpdate = async (formData: ApiKeyUpdate) => {
    if (!editingId)
      return
    try {
      await updateMutation.mutateAsync({ id: editingId, data: formData })
      Toast.notify({ type: 'success', message: 'API Key 更新成功' })
      setShowEditModal(false)
      setEditingId(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handleDelete = async () => {
    if (!selectedKey)
      return
    try {
      await deleteMutation.mutateAsync(selectedKey.id)
      Toast.notify({ type: 'success', message: 'API Key 删除成功' })
      setShowDeleteModal(false)
      setSelectedKey(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const handleRevoke = async () => {
    if (!selectedKey)
      return
    try {
      await revokeMutation.mutateAsync(selectedKey.id)
      Toast.notify({ type: 'success', message: 'API Key 已吊销' })
      setShowRevokeModal(false)
      setSelectedKey(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '吊销失败' })
    }
  }

  const handleRegenerate = async () => {
    if (!selectedKey)
      return
    try {
      const result = await regenerateMutation.mutateAsync(selectedKey.id)
      setNewApiKey(result.key)
      setNewKeyName(result.name)
      setShowRegenerateModal(false)
      setShowKeyModal(true)
      setSelectedKey(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '重新生成失败' })
    }
  }

  const handleSortingChange = useCallback((newSorting: SortingState) => {
    setSorting(newSorting)
    setPage(1)
  }, [])

  const getStatusBadge = (status: string, expiresAt: string | null) => {
    if (expiresAt && new Date(expiresAt) < new Date())
      return <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">已过期</span>

    const statusMap: Record<string, { bg: string, text: string, label: string }> = {
      active: { bg: 'bg-green-100', text: 'text-green-700', label: '启用' },
      disabled: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: '禁用' },
      revoked: { bg: 'bg-red-100', text: 'text-red-700', label: '已吊销' },
    }
    const config = statusMap[status] || statusMap.active
    return (
      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    )
  }

  const formatRateLimits = (rpm: number | null, rph: number | null) => {
    if (!rpm && !rph)
      return '无限制'
    const parts = []
    if (rpm)
      parts.push(`${rpm}/min`)
    if (rph)
      parts.push(`${rph}/hour`)
    return parts.join(', ')
  }

  const columns: ColumnDef<ApiKeyListItem>[] = useMemo(() => [
    {
      id: 'name',
      header: '名称',
      size: 200,
      cell: ({ row }) => (
        <div>
          <div className="font-medium text-text-primary">{row.original.name}</div>
          <div className="text-xs text-text-tertiary">
            {row.original.key_prefix}
            ...
          </div>
        </div>
      ),
    },
    {
      id: 'tenant',
      header: '租户',
      size: 150,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">{row.original.tenant_name || '-'}</span>
      ),
    },
    {
      id: 'status',
      header: '状态',
      size: 100,
      cell: ({ row }) => getStatusBadge(row.original.status, row.original.expires_at),
    },
    {
      id: 'expires_at',
      header: '过期时间',
      size: 160,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.expires_at ? formatDateTime(row.original.expires_at) : '永不过期'}
        </span>
      ),
    },
    {
      id: 'rate_limits',
      header: '速率限制',
      size: 140,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {formatRateLimits(row.original.rpm, row.original.rph)}
        </span>
      ),
    },
    {
      id: 'balance',
      header: '余额',
      size: 100,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.balance != null ? `¥${row.original.balance.toFixed(2)}` : '-'}
        </span>
      ),
    },
    {
      id: 'last_used_at',
      header: '最后使用',
      size: 160,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.last_used_at ? formatDateTime(row.original.last_used_at) : '从未使用'}
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
    createActionColumn<ApiKeyListItem>({
      width: 140,
      sticky: true,
      actions: [
        {
          icon: RiRefreshLine,
          label: '重新生成',
          onClick: (row) => {
            setSelectedKey(row)
            setShowRegenerateModal(true)
          },
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
          icon: RiForbidLine,
          label: '吊销',
          onClick: (row) => {
            setSelectedKey(row)
            setShowRevokeModal(true)
          },
          hidden: row => row.status === 'revoked',
        },
        {
          icon: RiDeleteBinLine,
          label: '删除',
          onClick: (row) => {
            setSelectedKey(row)
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
        <h1 className="text-2xl font-semibold text-text-primary">API Key 管理</h1>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <RiAddLine className="mr-1 h-4 w-4" />
          创建 API Key
        </Button>
      </div>

      <DataTableToolbar
        className="shrink-0"
        searchValue={keyword}
        searchPlaceholder="搜索 API Key"
        onSearchChange={setKeyword}
        onSearch={handleSearch}
        selectedCount={selectedCount}
        filterSlot={(
          <SimpleSelect
            items={[{ value: '', name: '全部状态' }, ...statusOptions]}
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

      <ApiKeyFormModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={data => handleCreate(data as ApiKeyCreate)}
        isLoading={createMutation.isPending}
      />
      <ApiKeyFormModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setEditingId(null)
        }}
        keyId={editingId}
        onSubmit={data => handleUpdate(data as ApiKeyUpdate)}
        isLoading={updateMutation.isPending}
      />
      <KeyDisplayModal
        isOpen={showKeyModal}
        onClose={() => {
          setShowKeyModal(false)
          setNewApiKey(null)
          setNewKeyName('')
        }}
        apiKey={newApiKey}
        keyName={newKeyName}
      />
      <Confirm
        isShow={showDeleteModal}
        onCancel={() => {
          setShowDeleteModal(false)
          setSelectedKey(null)
        }}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认删除"
        content={`确定要删除 API Key "${selectedKey?.name}" 吗？删除后无法恢复。`}
      />
      <Confirm
        isShow={showRevokeModal}
        onCancel={() => {
          setShowRevokeModal(false)
          setSelectedKey(null)
        }}
        onConfirm={handleRevoke}
        isLoading={revokeMutation.isPending}
        title="确认吊销"
        content={`确定要吊销 API Key "${selectedKey?.name}" 吗？吊销后将无法使用此密钥。`}
      />
      <Confirm
        isShow={showRegenerateModal}
        onCancel={() => {
          setShowRegenerateModal(false)
          setSelectedKey(null)
        }}
        onConfirm={handleRegenerate}
        isLoading={regenerateMutation.isPending}
        title="确认重新生成"
        content={`确定要重新生成 API Key "${selectedKey?.name}" 吗？原密钥将立即失效。`}
      />
    </>
  )
}

export default ApiKeysPage
