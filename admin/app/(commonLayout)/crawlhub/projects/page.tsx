'use client'

import type { ColumnDef, SortingState } from '@/app/components/base/table'
import type { Project, ProjectCreate, ProjectUpdate } from '@/types/crawlhub'
import {
  RiAddLine,
  RiCloseLine,
  RiDeleteBinLine,
  RiEditLine,
  RiFolderLine,
} from '@remixicon/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
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
  useCreateProject,
  useDeleteProject,
  useProject,
  useProjects,
  useUpdateProject,
} from '@/service/use-crawlhub'

type ProjectFormModalProps = {
  isOpen: boolean
  onClose: () => void
  projectId?: string | null
  onSubmit: (data: ProjectCreate | ProjectUpdate) => void
  isLoading: boolean
}

const ProjectFormModal = ({ isOpen, onClose, projectId, onSubmit, isLoading }: ProjectFormModalProps) => {
  const [formData, setFormData] = useState<ProjectCreate>({
    name: '',
    description: '',
  })

  const { data: projectDetail, isLoading: isLoadingDetail } = useProject(projectId || '')

  useEffect(() => {
    if (isOpen) {
      if (projectDetail) {
        setFormData({
          name: projectDetail.name,
          description: projectDetail.description || '',
        })
      }
      else if (!projectId) {
        setFormData({
          name: '',
          description: '',
        })
      }
    }
  }, [isOpen, projectDetail, projectId])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  const isEditMode = !!projectId

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-md">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            {isEditMode ? '编辑项目' : '创建项目'}
          </h3>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>
        {isEditMode && isLoadingDetail
          ? (
              <div className="space-y-4">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="ml-auto h-10 w-32" />
              </div>
            )
          : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">项目名称</label>
                  <Input
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="请输入项目名称"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">项目描述</label>
                  <Textarea
                    value={formData.description || ''}
                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                    placeholder="请输入项目描述（可选）"
                    rows={3}
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

const ProjectsPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useProjects({
    page,
    page_size: pageSize,
    keyword: searchKeyword,
  })

  const createMutation = useCreateProject()
  const updateMutation = useUpdateProject()
  const deleteMutation = useDeleteProject()

  const handleSearch = useCallback(() => {
    setSearchKeyword(keyword)
    setPage(1)
  }, [keyword])

  const handleCreate = async (formData: ProjectCreate) => {
    try {
      await createMutation.mutateAsync(formData)
      Toast.notify({ type: 'success', message: '项目创建成功' })
      setShowCreateModal(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '创建失败' })
    }
  }

  const handleUpdate = async (formData: ProjectUpdate) => {
    if (!editingId)
      return
    try {
      await updateMutation.mutateAsync({ id: editingId, data: formData })
      Toast.notify({ type: 'success', message: '项目更新成功' })
      setShowEditModal(false)
      setEditingId(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handleDelete = async () => {
    if (!selectedProject)
      return
    try {
      await deleteMutation.mutateAsync(selectedProject.id)
      Toast.notify({ type: 'success', message: '项目删除成功' })
      setShowDeleteModal(false)
      setSelectedProject(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const handleSortingChange = useCallback((newSorting: SortingState) => {
    setSorting(newSorting)
    setPage(1)
  }, [])

  const columns: ColumnDef<Project>[] = useMemo(() => [
    {
      id: 'name',
      header: '项目名称',
      size: 200,
      enableSorting: true,
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <RiFolderLine className="h-4 w-4 text-text-tertiary" />
          <span className="font-medium text-text-primary">{row.original.name}</span>
        </div>
      ),
      meta: {
        skeletonClassName: 'h-6 w-32',
      },
    },
    {
      id: 'description',
      header: '描述',
      size: 300,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.description || '-'}
        </span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-48',
      },
    },
    {
      id: 'spider_count',
      header: '爬虫数量',
      size: 100,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.spider_count || 0}
        </span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-12',
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
    createActionColumn<Project>({
      width: 100,
      actions: [
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
            setSelectedProject(row)
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
        <h1 className="text-2xl font-semibold text-text-primary">项目管理</h1>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <RiAddLine className="mr-1 h-4 w-4" />
          创建项目
        </Button>
      </div>

      <DataTableToolbar
        className="shrink-0"
        searchValue={keyword}
        searchPlaceholder="搜索项目名称"
        onSearchChange={setKeyword}
        onSearch={handleSearch}
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

      <ProjectFormModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={data => handleCreate(data as ProjectCreate)}
        isLoading={createMutation.isPending}
      />
      <ProjectFormModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setEditingId(null)
        }}
        projectId={editingId}
        onSubmit={data => handleUpdate(data as ProjectUpdate)}
        isLoading={updateMutation.isPending}
      />
      <Confirm
        isShow={showDeleteModal}
        onCancel={() => {
          setShowDeleteModal(false)
          setSelectedProject(null)
        }}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认删除"
        content={`确定要删除项目 "${selectedProject?.name}" 吗？删除后该项目下的所有爬虫也将被删除。`}
      />
    </>
  )
}

export default ProjectsPage
