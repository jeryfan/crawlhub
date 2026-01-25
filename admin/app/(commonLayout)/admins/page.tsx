'use client'

import type { ColumnDef, RowSelectionState, SortingState } from '@/app/components/base/table'
import type { AdminCreate, AdminListItem, AdminUpdate } from '@/types/platform'
import {
  RiAddLine,
  RiCloseLine,
  RiDeleteBinLine,
  RiEditLine,
  RiLockPasswordLine,
} from '@remixicon/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import Skeleton from '@/app/components/base/skeleton'
import StatusBadge from '@/app/components/base/status-badge'
import {
  AvatarCell,

  createActionColumn,
  DataTable,

  DataTableToolbar,
} from '@/app/components/base/table'
import Toast from '@/app/components/base/toast'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useAdmin,
  useAdmins,
  useCreateAdmin,
  useDeleteAdmin,
  useUpdateAdmin,
  useUpdateAdminPassword,
} from '@/service/use-platform'

type AdminFormModalProps = {
  isOpen: boolean
  onClose: () => void
  adminId?: string | null
  onSubmit: (data: AdminCreate | AdminUpdate) => Promise<void> | void
  isLoading: boolean
}

const AdminFormModal = ({ isOpen, onClose, adminId, onSubmit, isLoading }: AdminFormModalProps) => {
  const [formData, setFormData] = useState<AdminCreate>({
    name: '',
    email: '',
    password: '',
  })

  const { data: adminDetail, isLoading: isLoadingDetail } = useAdmin(adminId || '')

  useEffect(() => {
    if (isOpen) {
      if (adminDetail) {
        setFormData({
          name: adminDetail.name,
          email: adminDetail.email,
          password: '',
        })
      }
      else if (!adminId) {
        setFormData({
          name: '',
          email: '',
          password: '',
        })
      }
    }
  }, [isOpen, adminDetail, adminId])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const submitData = adminId
      ? { name: formData.name, email: formData.email }
      : formData
    onSubmit(submitData)
  }

  const isEditMode = !!adminId

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-md">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            {isEditMode ? '编辑管理员' : '创建管理员'}
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
                    placeholder="请输入名称"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">邮箱</label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                    placeholder="请输入邮箱"
                    required
                  />
                </div>
                {!isEditMode && (
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">密码</label>
                    <Input
                      type="password"
                      value={formData.password}
                      onChange={e => setFormData({ ...formData, password: e.target.value })}
                      placeholder="请输入密码（至少8位）"
                      required
                    />
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

type PasswordModalProps = {
  isOpen: boolean
  onClose: () => void
  onSubmit: (password: string) => void
  isLoading: boolean
}

const PasswordModal = ({ isOpen, onClose, onSubmit, isLoading }: PasswordModalProps) => {
  const [password, setPassword] = useState('')

  useEffect(() => {
    if (isOpen)
      setPassword('')
  }, [isOpen])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(password)
  }

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-sm">
      <div className="p-6">
        <h3 className="mb-4 text-lg font-semibold text-text-primary">重置密码</h3>
        <form onSubmit={handleSubmit}>
          <Input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="请输入新密码（至少8位）"
            required
          />
          <div className="mt-4 flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose}>取消</Button>
            <Button variant="primary" type="submit" loading={isLoading}>确认</Button>
          </div>
        </form>
      </div>
    </Modal>
  )
}

const AdminsPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectedAdmin, setSelectedAdmin] = useState<AdminListItem | null>(null)

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useAdmins({
    page,
    page_size: pageSize,
    keyword: searchKeyword,
    // 服务端排序参数
    ...(sorting.length > 0 && {
      sort_by: sorting[0].id,
      sort_order: sorting[0].desc ? 'desc' : 'asc',
    }),
  })

  const createMutation = useCreateAdmin()
  const updateMutation = useUpdateAdmin()
  const deleteMutation = useDeleteAdmin()
  const passwordMutation = useUpdateAdminPassword()

  const handleSearch = useCallback(() => {
    setSearchKeyword(keyword)
    setPage(1)
  }, [keyword])

  const handleCreate = async (formData: AdminCreate) => {
    try {
      await createMutation.mutateAsync(formData)
      Toast.notify({ type: 'success', message: '管理员创建成功' })
      setShowCreateModal(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '创建失败' })
    }
  }

  const handleUpdate = async (formData: AdminUpdate) => {
    if (!editingId)
      return
    try {
      await updateMutation.mutateAsync({ id: editingId, data: formData })
      Toast.notify({ type: 'success', message: '管理员更新成功' })
      setShowEditModal(false)
      setEditingId(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handleDelete = async () => {
    if (!selectedAdmin)
      return
    try {
      await deleteMutation.mutateAsync(selectedAdmin.id)
      Toast.notify({ type: 'success', message: '管理员删除成功' })
      setShowDeleteModal(false)
      setSelectedAdmin(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const handlePasswordReset = async (password: string) => {
    if (!selectedAdmin)
      return
    try {
      await passwordMutation.mutateAsync({ id: selectedAdmin.id, password })
      Toast.notify({ type: 'success', message: '密码已重置' })
      setShowPasswordModal(false)
      setSelectedAdmin(null)
    }
    catch {
      Toast.notify({ type: 'error', message: '重置失败' })
    }
  }

  const handleSortingChange = useCallback((newSorting: SortingState) => {
    setSorting(newSorting)
    setPage(1)
  }, [])

  // 定义表格列
  const columns: ColumnDef<AdminListItem>[] = useMemo(() => [
    {
      id: 'name',
      header: '管理员',
      size: 280,
      enableSorting: true,
      cell: ({ row }) => (
        <AvatarCell
          name={row.original.name}
          avatar={row.original.avatar_url}
          email={row.original.email}
        />
      ),
      meta: {
        skeletonClassName: 'h-10 w-48',
      },
    },
    {
      id: 'status',
      header: '状态',
      size: 100,
      cell: ({ row }) => <StatusBadge status={row.original.status} type="admin" />,
      meta: {
        skeletonClassName: 'h-6 w-16',
      },
    },
    {
      id: 'last_login_at',
      header: '最后登录',
      size: 160,
      enableSorting: true,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {formatDateTime(row.original.last_login_at)}
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
    createActionColumn<AdminListItem>({
      width: 120,
      actions: [
        {
          icon: RiLockPasswordLine,
          label: '重置密码',
          onClick: (row) => {
            setSelectedAdmin(row)
            setShowPasswordModal(true)
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
          icon: RiDeleteBinLine,
          label: '删除',
          onClick: (row) => {
            setSelectedAdmin(row)
            setShowDeleteModal(true)
          },
          variant: 'danger',
        },
      ],
    }),
  ], [])

  const selectedCount = Object.keys(rowSelection).length

  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">管理员管理</h1>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <RiAddLine className="mr-1 h-4 w-4" />
          创建管理员
        </Button>
      </div>

      <DataTableToolbar
        className="shrink-0"
        searchValue={keyword}
        searchPlaceholder="搜索管理员"
        onSearchChange={setKeyword}
        onSearch={handleSearch}
        selectedCount={selectedCount}
        bulkActionsSlot={
          selectedCount > 0 && (
            <Button
              variant="warning"
              size="small"
              onClick={() => {
                // 批量删除逻辑
                Toast.notify({ type: 'info', message: `已选择 ${selectedCount} 个管理员` })
              }}
            >
              <RiDeleteBinLine className="mr-1 h-4 w-4" />
              批量删除
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
        // 行选择
        enableRowSelection
        rowSelection={rowSelection}
        onRowSelectionChange={setRowSelection}
        // 排序
        enableSorting
        sorting={sorting}
        onSortingChange={handleSortingChange}
        stickyHeader
        // 分页
        pagination={{
          page,
          pageSize,
          total: data?.total || 0,
          onChange: setPage,
          onPageSizeChange: setPageSize,
        }}
      />

      <AdminFormModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={data => handleCreate(data as AdminCreate)}
        isLoading={createMutation.isPending}
      />
      <AdminFormModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setEditingId(null)
        }}
        adminId={editingId}
        onSubmit={data => handleUpdate(data as AdminUpdate)}
        isLoading={updateMutation.isPending}
      />
      <PasswordModal
        isOpen={showPasswordModal}
        onClose={() => {
          setShowPasswordModal(false)
          setSelectedAdmin(null)
        }}
        onSubmit={handlePasswordReset}
        isLoading={passwordMutation.isPending}
      />
      <Confirm
        isShow={showDeleteModal}
        onCancel={() => {
          setShowDeleteModal(false)
          setSelectedAdmin(null)
        }}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认删除"
        content={`确定要删除管理员 "${selectedAdmin?.name}" 吗？`}
      />
    </>
  )
}

export default AdminsPage
