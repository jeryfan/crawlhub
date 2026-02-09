'use client'

import type { ColumnDef, SortingState } from '@/app/components/base/table'
import type { DataSource, DataSourceCreate, DataSourceMode, DataSourceStatus, DataSourceType, DataSourceUpdate } from '@/types/crawlhub'
import {
  RiAddLine,
  RiCloseLine,
  RiDatabase2Line,
  RiDeleteBinLine,
  RiEditLine,
  RiLoader4Line,
  RiPlayLine,
  RiRefreshLine,
  RiStopLine,
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
  useCreateDataSource,
  useDataSource,
  useDataSources,
  useDeleteDataSource,
  useStartDataSource,
  useStopDataSource,
  useTestDataSourceConnection,
  useTestDataSourceParams,
  useUpdateDataSource,
} from '@/service/use-crawlhub'

const typeOptions = [
  { value: '', name: '全部类型' },
  { value: 'postgresql', name: 'PostgreSQL' },
  { value: 'mysql', name: 'MySQL' },
  { value: 'mongodb', name: 'MongoDB' },
]

const modeOptions = [
  { value: '', name: '全部模式' },
  { value: 'external', name: '外部连接' },
  { value: 'managed', name: '平台托管' },
]

const typeLabels: Record<DataSourceType, string> = {
  postgresql: 'PostgreSQL',
  mysql: 'MySQL',
  mongodb: 'MongoDB',
}

const typeBadgeColors: Record<DataSourceType, string> = {
  postgresql: 'bg-blue-100 text-blue-700',
  mysql: 'bg-orange-100 text-orange-700',
  mongodb: 'bg-green-100 text-green-700',
}

type DataSourceFormModalProps = {
  isOpen: boolean
  onClose: () => void
  datasourceId?: string | null
  onSubmit: (data: DataSourceCreate | DataSourceUpdate) => void
  isLoading: boolean
}

const DataSourceFormModal = ({ isOpen, onClose, datasourceId, onSubmit, isLoading }: DataSourceFormModalProps) => {
  const [mode, setMode] = useState<DataSourceMode>('external')
  const [formData, setFormData] = useState<DataSourceCreate>({
    name: '',
    type: 'postgresql',
    mode: 'external',
    host: '',
    port: 5432,
    username: '',
    password: '',
    database: '',
  })

  const { data: dsDetail, isLoading: isLoadingDetail } = useDataSource(datasourceId || '')

  const testMutation = useTestDataSourceParams()
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string; latency_ms: number } | null>(null)
  const [createDbIfNotExists, setCreateDbIfNotExists] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setTestResult(null)
      setCreateDbIfNotExists(false)
      if (dsDetail) {
        setMode(dsDetail.mode)
        setFormData({
          name: dsDetail.name,
          type: dsDetail.type,
          mode: dsDetail.mode,
          description: dsDetail.description || '',
          host: dsDetail.host || '',
          port: dsDetail.port || 5432,
          username: dsDetail.username || '',
          password: '',
          database: dsDetail.database || '',
        })
      }
      else if (!datasourceId) {
        setMode('external')
        setFormData({
          name: '',
          type: 'postgresql',
          mode: 'external',
          host: '',
          port: 5432,
          username: '',
          password: '',
          database: '',
        })
      }
    }
  }, [isOpen, dsDetail, datasourceId])

  const handleTypeChange = (type: DataSourceType) => {
    const defaultPorts: Record<DataSourceType, number> = {
      postgresql: 5432,
      mysql: 3306,
      mongodb: 27017,
    }
    setFormData({ ...formData, type, port: defaultPorts[type] })
  }

  const handleTestConnection = async () => {
    setTestResult(null)
    try {
      const result = await testMutation.mutateAsync({
        type: formData.type,
        host: formData.host || '',
        port: formData.port,
        username: formData.username,
        password: formData.password,
        database: formData.database,
        connection_options: undefined,
      })
      setTestResult(result)
    }
    catch {
      setTestResult({ ok: false, message: '测试请求失败', latency_ms: 0 })
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({ ...formData, mode, create_db_if_not_exists: createDbIfNotExists })
  }

  const isEditMode = !!datasourceId

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-lg">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            {isEditMode ? '编辑数据源' : '创建数据源'}
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
              </div>
            )
          : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">名称</label>
                  <Input
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="数据源名称"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">描述</label>
                  <Input
                    value={formData.description || ''}
                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                    placeholder="可选描述"
                  />
                </div>
                {!isEditMode && (
                  <>
                    <div>
                      <label className="mb-1.5 block text-sm text-text-secondary">模式</label>
                      <div className="flex gap-3">
                        <button
                          type="button"
                          onClick={() => setMode('external')}
                          className={`flex-1 rounded-lg border px-4 py-3 text-left transition-colors ${
                            mode === 'external'
                              ? 'border-components-button-primary-bg bg-components-button-primary-bg/5'
                              : 'border-divider-regular hover:border-divider-intense'
                          }`}
                        >
                          <div className="text-sm font-medium text-text-primary">外部连接</div>
                          <div className="text-xs text-text-tertiary">填写已有数据库连接信息</div>
                        </button>
                        <button
                          type="button"
                          onClick={() => setMode('managed')}
                          className={`flex-1 rounded-lg border px-4 py-3 text-left transition-colors ${
                            mode === 'managed'
                              ? 'border-components-button-primary-bg bg-components-button-primary-bg/5'
                              : 'border-divider-regular hover:border-divider-intense'
                          }`}
                        >
                          <div className="text-sm font-medium text-text-primary">平台托管</div>
                          <div className="text-xs text-text-tertiary">一键创建 Docker 数据库</div>
                        </button>
                      </div>
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm text-text-secondary">数据库类型</label>
                      <SimpleSelect
                        className="w-full"
                        defaultValue={formData.type}
                        items={[
                          { value: 'postgresql', name: 'PostgreSQL' },
                          { value: 'mysql', name: 'MySQL' },
                          { value: 'mongodb', name: 'MongoDB' },
                        ]}
                        onSelect={item => handleTypeChange(item.value as DataSourceType)}
                      />
                    </div>
                  </>
                )}
                {(mode === 'external' || isEditMode) && (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="mb-1.5 block text-sm text-text-secondary">主机地址</label>
                        <Input
                          value={formData.host || ''}
                          onChange={e => setFormData({ ...formData, host: e.target.value })}
                          placeholder="localhost"
                          required={mode === 'external'}
                        />
                      </div>
                      <div>
                        <label className="mb-1.5 block text-sm text-text-secondary">端口</label>
                        <Input
                          type="number"
                          value={formData.port || ''}
                          onChange={e => setFormData({ ...formData, port: Number.parseInt(e.target.value) || 5432 })}
                          placeholder="5432"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="mb-1.5 block text-sm text-text-secondary">用户名</label>
                        <Input
                          value={formData.username || ''}
                          onChange={e => setFormData({ ...formData, username: e.target.value })}
                          placeholder="用户名"
                        />
                      </div>
                      <div>
                        <label className="mb-1.5 block text-sm text-text-secondary">密码</label>
                        <Input
                          type="password"
                          value={formData.password || ''}
                          onChange={e => setFormData({ ...formData, password: e.target.value })}
                          placeholder="密码"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm text-text-secondary">数据库名</label>
                      <Input
                        value={formData.database || ''}
                        onChange={e => setFormData({ ...formData, database: e.target.value })}
                        placeholder="数据库名"
                      />
                    </div>
                  </>
                )}
                {/* Auto-create database checkbox */}
                {!isEditMode && mode === 'external' && (
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="create-db"
                      checked={createDbIfNotExists}
                      onChange={e => setCreateDbIfNotExists(e.target.checked)}
                      className="h-4 w-4 rounded border-divider-regular text-components-button-primary-bg focus:ring-components-button-primary-bg"
                    />
                    <label htmlFor="create-db" className="text-sm text-text-secondary">
                      数据库不存在时自动创建
                    </label>
                  </div>
                )}
                {/* Test connection button and result */}
                {(mode === 'external' || isEditMode) && (
                  <div className="space-y-2">
                    <Button
                      type="button"
                      variant="secondary"
                      size="small"
                      onClick={handleTestConnection}
                      disabled={!formData.host}
                      loading={testMutation.isPending}
                    >
                      测试连接
                    </Button>
                    {testResult && (
                      <div className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
                        testResult.ok
                          ? 'bg-green-50 text-green-700'
                          : 'bg-red-50 text-red-700'
                      }`}>
                        <span className={`h-2 w-2 rounded-full ${testResult.ok ? 'bg-green-500' : 'bg-red-500'}`} />
                        <span>{testResult.message}</span>
                        {testResult.ok && testResult.latency_ms > 0 && (
                          <span className="text-xs opacity-70">({testResult.latency_ms}ms)</span>
                        )}
                      </div>
                    )}
                  </div>
                )}
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

const DataSourcesPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [typeFilter, setTypeFilter] = useState<DataSourceType | ''>('')
  const [modeFilter, setModeFilter] = useState<DataSourceMode | ''>('')
  const [sorting, setSorting] = useState<SortingState>([])

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectedDs, setSelectedDs] = useState<DataSource | null>(null)

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useDataSources({
    page,
    page_size: pageSize,
    type: typeFilter || undefined,
    mode: modeFilter || undefined,
  })

  const createMutation = useCreateDataSource()
  const updateMutation = useUpdateDataSource()
  const deleteMutation = useDeleteDataSource()
  const testMutation = useTestDataSourceConnection()
  const startMutation = useStartDataSource()
  const stopMutation = useStopDataSource()

  const handleCreate = async (formData: DataSourceCreate) => {
    try {
      await createMutation.mutateAsync(formData)
      Toast.notify({ type: 'success', message: '数据源创建成功' })
      setShowCreateModal(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '创建失败' })
    }
  }

  const handleUpdate = async (formData: DataSourceUpdate) => {
    if (!editingId)
      return
    try {
      await updateMutation.mutateAsync({ id: editingId, data: formData })
      Toast.notify({ type: 'success', message: '数据源更新成功' })
      setShowEditModal(false)
      setEditingId(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handleDelete = async () => {
    if (!selectedDs)
      return
    try {
      await deleteMutation.mutateAsync(selectedDs.id)
      Toast.notify({ type: 'success', message: '数据源删除成功' })
      setShowDeleteConfirm(false)
      setSelectedDs(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败，可能仍有爬虫关联' })
    }
  }

  const handleTest = async (ds: DataSource) => {
    try {
      const result = await testMutation.mutateAsync(ds.id)
      if (result.ok)
        Toast.notify({ type: 'success', message: `连接成功 (${result.latency_ms}ms)` })
      else
        Toast.notify({ type: 'error', message: `连接失败: ${result.message}` })
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '测试失败' })
    }
  }

  const handleStart = async (ds: DataSource) => {
    try {
      await startMutation.mutateAsync(ds.id)
      Toast.notify({ type: 'success', message: '容器已启动' })
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '启动失败' })
    }
  }

  const handleStop = async (ds: DataSource) => {
    try {
      await stopMutation.mutateAsync(ds.id)
      Toast.notify({ type: 'success', message: '容器已停止' })
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '停止失败' })
    }
  }

  const handleSortingChange = useCallback((newSorting: SortingState) => {
    setSorting(newSorting)
    setPage(1)
  }, [])

  const columns: ColumnDef<DataSource>[] = useMemo(() => [
    {
      id: 'name',
      header: '名称',
      size: 200,
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <RiDatabase2Line className="h-4 w-4 text-text-tertiary" />
          <div>
            <div className="font-medium text-text-primary">{row.original.name}</div>
            {row.original.description && (
              <div className="text-xs text-text-tertiary">{row.original.description}</div>
            )}
          </div>
        </div>
      ),
      meta: { skeletonClassName: 'h-8 w-40' },
    },
    {
      id: 'type',
      header: '类型',
      size: 120,
      cell: ({ row }) => (
        <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${typeBadgeColors[row.original.type]}`}>
          {typeLabels[row.original.type]}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-20' },
    },
    {
      id: 'mode',
      header: '模式',
      size: 100,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.mode === 'managed' ? '平台托管' : '外部连接'}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-16' },
    },
    {
      id: 'status',
      header: '状态',
      size: 100,
      cell: ({ row }) => (
        <StatusBadge
          status={row.original.status}
          statusConfig={{
            active: { label: '正常', color: 'bg-util-colors-green-green-500' },
            inactive: { label: '停用', color: 'bg-util-colors-grey-grey-500' },
            creating: { label: '创建中', color: 'bg-util-colors-blue-blue-500' },
            error: { label: '异常', color: 'bg-util-colors-red-red-500' },
          }}
        />
      ),
      meta: { skeletonClassName: 'h-6 w-16' },
    },
    {
      id: 'connection',
      header: '连接地址',
      size: 200,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.host
            ? `${row.original.host}:${row.original.port || ''}`
            : '-'}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-32' },
    },
    {
      id: 'last_check_at',
      header: '最后检查',
      size: 160,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.last_check_at ? formatDateTime(row.original.last_check_at) : '-'}
        </span>
      ),
      meta: { skeletonClassName: 'h-6 w-32' },
    },
    createActionColumn<DataSource>({
      width: 160,
      actions: [
        {
          icon: RiRefreshLine,
          label: '测试',
          onClick: row => handleTest(row),
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
            setSelectedDs(row)
            setShowDeleteConfirm(true)
          },
          variant: 'danger',
        },
      ],
    }),
  ], [formatDateTime])

  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">数据源</h1>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <RiAddLine className="mr-1 h-4 w-4" />
          创建数据源
        </Button>
      </div>

      <DataTableToolbar
        className="shrink-0"
        filterSlot={(
          <div className="flex items-center gap-2">
            <SimpleSelect
              className="w-32"
              defaultValue={typeFilter}
              items={typeOptions}
              onSelect={(item) => {
                setTypeFilter(item.value as DataSourceType | '')
                setPage(1)
              }}
            />
            <SimpleSelect
              className="w-32"
              defaultValue={modeFilter}
              items={modeOptions}
              onSelect={(item) => {
                setModeFilter(item.value as DataSourceMode | '')
                setPage(1)
              }}
            />
          </div>
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

      <DataSourceFormModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={data => handleCreate(data as DataSourceCreate)}
        isLoading={createMutation.isPending}
      />
      <DataSourceFormModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setEditingId(null)
        }}
        datasourceId={editingId}
        onSubmit={data => handleUpdate(data as DataSourceUpdate)}
        isLoading={updateMutation.isPending}
      />
      <Confirm
        isShow={showDeleteConfirm}
        onCancel={() => {
          setShowDeleteConfirm(false)
          setSelectedDs(null)
        }}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认删除"
        content={`确定要删除数据源 "${selectedDs?.name}" 吗？${selectedDs?.mode === 'managed' ? '关联的 Docker 容器也将被删除。' : ''}`}
      />
    </>
  )
}

export default DataSourcesPage
