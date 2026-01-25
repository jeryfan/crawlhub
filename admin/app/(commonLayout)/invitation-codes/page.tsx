'use client'

import type { ColumnDef, RowSelectionState, SortingState } from '@/app/components/base/table'
import type { InvitationCodeCreate, InvitationCodeListItem } from '@/types/platform'
import {
  RiAddLine,
  RiCloseLine,
  RiDeleteBinLine,
  RiProhibitedLine,
} from '@remixicon/react'
import { useCallback, useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import { SimpleSelect } from '@/app/components/base/select'
import StatusBadge from '@/app/components/base/status-badge'
import {

  createActionColumn,
  DataTable,

  DataTableToolbar,
  TruncatedText,
} from '@/app/components/base/table'
import Toast from '@/app/components/base/toast'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useCreateInvitationCodes,
  useDeleteInvitationCode,
  useDeprecateInvitationCodes,
  useInvitationCodeBatches,
  useInvitationCodes,
  useInvitationCodeStats,
} from '@/service/use-platform'

type CreateModalProps = {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: InvitationCodeCreate) => void
  isLoading: boolean
}

const CreateModal = ({ isOpen, onClose, onSubmit, isLoading }: CreateModalProps) => {
  const [formData, setFormData] = useState<InvitationCodeCreate>({
    batch: '',
    count: 10,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-md">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">批量创建邀请码</h3>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm text-text-secondary">批次名称</label>
            <Input
              value={formData.batch}
              onChange={e => setFormData({ ...formData, batch: e.target.value })}
              placeholder="请输入批次名称"
              required
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-text-secondary">数量</label>
            <Input
              type="number"
              value={formData.count}
              onChange={e => setFormData({ ...formData, count: Number.parseInt(e.target.value) || 10 })}
              min={1}
              max={1000}
              required
            />
            <p className="mt-1 text-xs text-text-quaternary">最多可创建 1000 个</p>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <Button variant="secondary" onClick={onClose}>取消</Button>
            <Button variant="primary" type="submit" loading={isLoading}>创建</Button>
          </div>
        </form>
      </div>
    </Modal>
  )
}

const InvitationCodesPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [batchFilter, setBatchFilter] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showDeprecateModal, setShowDeprecateModal] = useState(false)
  const [selectedCode, setSelectedCode] = useState<InvitationCodeListItem | null>(null)

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useInvitationCodes({
    page,
    page_size: pageSize,
    keyword: searchKeyword,
    status: statusFilter || undefined,
    batch: batchFilter || undefined,
    ...(sorting.length > 0 && {
      sort_by: sorting[0].id,
      sort_order: sorting[0].desc ? 'desc' : 'asc',
    }),
  })
  const { data: stats } = useInvitationCodeStats()
  const { data: batches } = useInvitationCodeBatches()

  const createMutation = useCreateInvitationCodes()
  const deleteMutation = useDeleteInvitationCode()
  const deprecateMutation = useDeprecateInvitationCodes()

  const handleSearch = useCallback(() => {
    setSearchKeyword(keyword)
    setPage(1)
  }, [keyword])

  const handleCreate = async (formData: InvitationCodeCreate) => {
    try {
      await createMutation.mutateAsync(formData)
      Toast.notify({ type: 'success', message: '邀请码创建成功' })
      setShowCreateModal(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '创建失败' })
    }
  }

  const handleDelete = async () => {
    if (!selectedCode)
      return
    try {
      await deleteMutation.mutateAsync(selectedCode.id)
      Toast.notify({ type: 'success', message: '邀请码删除成功' })
      setShowDeleteModal(false)
      setSelectedCode(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const handleDeprecate = async () => {
    const selectedIds = Object.keys(rowSelection)
    if (selectedIds.length === 0)
      return
    try {
      await deprecateMutation.mutateAsync(selectedIds)
      Toast.notify({ type: 'success', message: '邀请码已作废' })
      setShowDeprecateModal(false)
      setRowSelection({})
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

  // 自定义行选择逻辑：只能选择未使用的邀请码
  const handleRowSelectionChange = useCallback((newSelection: RowSelectionState) => {
    // 过滤掉非 unused 状态的选择
    const filteredSelection: RowSelectionState = {}
    const items = data?.items || []

    Object.keys(newSelection).forEach((id) => {
      const item = items.find(i => i.id === id)
      if (item && item.status === 'unused')
        filteredSelection[id] = true
    })

    setRowSelection(filteredSelection)
  }, [data?.items])

  // 定义表格列
  const columns: ColumnDef<InvitationCodeListItem>[] = useMemo(() => [
    {
      id: 'code',
      header: '邀请码',
      size: 200,
      cell: ({ row }) => (
        <code className="rounded bg-background-section px-2 py-1 font-mono text-sm text-text-primary">
          {row.original.code}
        </code>
      ),
      meta: {
        skeletonClassName: 'h-6 w-24',
      },
    },
    {
      id: 'batch',
      header: '批次',
      size: 150,
      enableSorting: true,
      cell: ({ row }) => (
        <TruncatedText text={row.original.batch} textClassName="text-text-secondary" />
      ),
      meta: {
        skeletonClassName: 'h-6 w-20',
      },
    },
    {
      id: 'status',
      header: '状态',
      size: 100,
      cell: ({ row }) => <StatusBadge status={row.original.status} type="invitation-code" />,
      meta: {
        skeletonClassName: 'h-6 w-16',
      },
    },
    {
      id: 'used_at',
      header: '使用时间',
      size: 160,
      enableSorting: true,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {formatDateTime(row.original.used_at)}
        </span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-32',
      },
    },
    {
      id: 'created_at',
      header: '创建时间',
      size: 160,
      enableSorting: true,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {formatDateTime(row.original.created_at)}
        </span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-32',
      },
    },
    createActionColumn<InvitationCodeListItem>({
      width: 80,
      actions: [
        {
          icon: RiDeleteBinLine,
          label: '删除',
          onClick: (row) => {
            setSelectedCode(row)
            setShowDeleteModal(true)
          },
          variant: 'danger',
        },
      ],
    }),
  ], [])

  const selectedCount = Object.keys(rowSelection).length

  // 判断行是否可选（只有 unused 状态的可选）
  const getRowClassName = useCallback((row: InvitationCodeListItem) => {
    if (row.status !== 'unused')
      return 'opacity-60'

    return ''
  }, [])

  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">邀请码管理</h1>
        <div className="flex items-center gap-3">
          {stats && (
            <div className="text-sm text-text-tertiary">
              总计
              {' '}
              {stats.total}
              {' '}
              | 未使用
              {' '}
              {stats.unused}
              {' '}
              | 已使用
              {' '}
              {stats.used}
            </div>
          )}
          <Button variant="primary" onClick={() => setShowCreateModal(true)}>
            <RiAddLine className="mr-1 h-4 w-4" />
            批量创建
          </Button>
        </div>
      </div>

      <DataTableToolbar
        className="shrink-0"
        searchValue={keyword}
        searchPlaceholder="搜索邀请码"
        onSearchChange={setKeyword}
        onSearch={handleSearch}
        filterSlot={(
          <>
            <SimpleSelect
              className="w-32"
              defaultValue={statusFilter}
              items={[
                { value: '', name: '全部状态' },
                { value: 'unused', name: '未使用' },
                { value: 'used', name: '已使用' },
                { value: 'deprecated', name: '已作废' },
              ]}
              onSelect={(item) => {
                setStatusFilter(item.value as string)
                setPage(1)
              }}
            />
            <SimpleSelect
              className="w-32"
              defaultValue={batchFilter}
              items={[
                { value: '', name: '全部批次' },
                ...(batches?.map(batch => ({ value: batch, name: batch })) || []),
              ]}
              onSelect={(item) => {
                setBatchFilter(item.value as string)
                setPage(1)
              }}
            />
          </>
        )}
        selectedCount={selectedCount}
        bulkActionsSlot={
          selectedCount > 0 && (
            <Button
              variant="warning"
              size="small"
              onClick={() => setShowDeprecateModal(true)}
            >
              <RiProhibitedLine className="mr-1 h-4 w-4" />
              批量作废 (
              {selectedCount}
              )
            </Button>
          )
        }
      />

      <DataTable
        columns={columns}
        data={data?.items || []}
        isLoading={isLoading}
        loadingRowCount={5}
        getRowId={row => row.id}
        enableRowSelection
        rowSelection={rowSelection}
        onRowSelectionChange={handleRowSelectionChange}
        rowClassName={getRowClassName}
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

      <CreateModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreate}
        isLoading={createMutation.isPending}
      />
      <Confirm
        isShow={showDeleteModal}
        onCancel={() => {
          setShowDeleteModal(false)
          setSelectedCode(null)
        }}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认删除"
        content={`确定要删除邀请码 "${selectedCode?.code}" 吗？`}
      />
      <Confirm
        isShow={showDeprecateModal}
        onCancel={() => setShowDeprecateModal(false)}
        onConfirm={handleDeprecate}
        isLoading={deprecateMutation.isPending}
        title="批量作废"
        content={`确定要作废选中的 ${selectedCount} 个邀请码吗？`}
      />
    </>
  )
}

export default InvitationCodesPage
