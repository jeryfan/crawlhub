'use client'

import type { ColumnDef, SortingState } from '@/app/components/base/table'
import type { ScriptType, Spider, SpiderCreate, SpiderUpdate } from '@/types/crawlhub'
import {
  RiAddLine,
  RiBugLine,
  RiCloseLine,
  RiDeleteBinLine,
  RiEditLine,
  RiPlayLine,
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
import Textarea from '@/app/components/base/textarea'
import Toast from '@/app/components/base/toast'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useCreateSpider,
  useDeleteSpider,
  useProjects,
  useRunSpider,
  useSpider,
  useSpiders,
  useUpdateSpider,
} from '@/service/use-crawlhub'

const scriptTypeOptions = [
  { value: 'httpx', name: 'httpx' },
  { value: 'scrapy', name: 'Scrapy' },
  { value: 'playwright', name: 'Playwright' },
]

type SpiderFormModalProps = {
  isOpen: boolean
  onClose: () => void
  spiderId?: string | null
  onSubmit: (data: SpiderCreate | SpiderUpdate) => void
  isLoading: boolean
}

const SpiderFormModal = ({ isOpen, onClose, spiderId, onSubmit, isLoading }: SpiderFormModalProps) => {
  const [formData, setFormData] = useState<SpiderCreate>({
    project_id: '',
    name: '',
    description: '',
    script_type: 'httpx',
  })

  const { data: spiderDetail, isLoading: isLoadingDetail } = useSpider(spiderId || '')
  const { data: projectsData } = useProjects({ page: 1, page_size: 100 })

  const projectOptions = useMemo(() => [
    { value: '', name: '请选择项目' },
    ...(projectsData?.items.map(p => ({ value: p.id, name: p.name })) || []),
  ], [projectsData])

  useEffect(() => {
    if (isOpen) {
      if (spiderDetail) {
        setFormData({
          project_id: spiderDetail.project_id,
          name: spiderDetail.name,
          description: spiderDetail.description || '',
          script_type: spiderDetail.script_type,
        })
      }
      else if (!spiderId) {
        setFormData({
          project_id: '',
          name: '',
          description: '',
          script_type: 'httpx',
        })
      }
    }
  }, [isOpen, spiderDetail, spiderId])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!spiderId && !formData.project_id) {
      Toast.notify({ type: 'error', message: '请选择项目' })
      return
    }
    onSubmit(formData)
  }

  const isEditMode = !!spiderId

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-md">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            {isEditMode ? '编辑爬虫' : '创建爬虫'}
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
                <Skeleton className="h-20 w-full" />
                <Skeleton className="ml-auto h-10 w-32" />
              </div>
            )
          : (
              <form onSubmit={handleSubmit} className="space-y-4">
                {!isEditMode && (
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">所属项目</label>
                    <SimpleSelect
                      className="w-full"
                      defaultValue={formData.project_id}
                      items={projectOptions}
                      onSelect={item => setFormData({ ...formData, project_id: item.value as string })}
                    />
                  </div>
                )}
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">爬虫名称</label>
                  <Input
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="请输入爬虫名称"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">脚本类型</label>
                  <SimpleSelect
                    className="w-full"
                    defaultValue={formData.script_type}
                    items={scriptTypeOptions}
                    onSelect={item => setFormData({ ...formData, script_type: item.value as ScriptType })}
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">描述</label>
                  <Textarea
                    value={formData.description || ''}
                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                    placeholder="请输入爬虫描述（可选）"
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

const SpidersPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectedSpider, setSelectedSpider] = useState<Spider | null>(null)

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useSpiders({
    page,
    page_size: pageSize,
    keyword: searchKeyword,
  })

  const createMutation = useCreateSpider()
  const updateMutation = useUpdateSpider()
  const deleteMutation = useDeleteSpider()
  const runMutation = useRunSpider()

  const handleSearch = useCallback(() => {
    setSearchKeyword(keyword)
    setPage(1)
  }, [keyword])

  const handleCreate = async (formData: SpiderCreate) => {
    try {
      await createMutation.mutateAsync(formData)
      Toast.notify({ type: 'success', message: '爬虫创建成功' })
      setShowCreateModal(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '创建失败' })
    }
  }

  const handleUpdate = async (formData: SpiderUpdate) => {
    if (!editingId)
      return
    try {
      await updateMutation.mutateAsync({ id: editingId, data: formData })
      Toast.notify({ type: 'success', message: '爬虫更新成功' })
      setShowEditModal(false)
      setEditingId(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handleDelete = async () => {
    if (!selectedSpider)
      return
    try {
      await deleteMutation.mutateAsync(selectedSpider.id)
      Toast.notify({ type: 'success', message: '爬虫删除成功' })
      setShowDeleteModal(false)
      setSelectedSpider(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const handleRun = async (spider: Spider) => {
    try {
      await runMutation.mutateAsync(spider.id)
      Toast.notify({ type: 'success', message: '任务已创建' })
    }
    catch {
      Toast.notify({ type: 'error', message: '执行失败' })
    }
  }

  const handleSortingChange = useCallback((newSorting: SortingState) => {
    setSorting(newSorting)
    setPage(1)
  }, [])

  const columns: ColumnDef<Spider>[] = useMemo(() => [
    {
      id: 'name',
      header: '爬虫名称',
      size: 200,
      enableSorting: true,
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <RiBugLine className="h-4 w-4 text-text-tertiary" />
          <span className="font-medium text-text-primary">{row.original.name}</span>
        </div>
      ),
      meta: {
        skeletonClassName: 'h-6 w-32',
      },
    },
    {
      id: 'script_type',
      header: '脚本类型',
      size: 120,
      cell: ({ row }) => (
        <span className="inline-flex items-center rounded-md bg-background-section px-2 py-1 text-xs font-medium text-text-secondary">
          {row.original.script_type}
        </span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-16',
      },
    },
    {
      id: 'is_active',
      header: '状态',
      size: 100,
      cell: ({ row }) => (
        <StatusBadge
          status={row.original.is_active ? 'active' : 'inactive'}
          statusConfig={{
            active: { label: '启用', color: 'bg-util-colors-green-green-500' },
            inactive: { label: '禁用', color: 'bg-util-colors-gray-gray-500' },
          }}
        />
      ),
      meta: {
        skeletonClassName: 'h-6 w-16',
      },
    },
    {
      id: 'description',
      header: '描述',
      size: 200,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.description || '-'}
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
    createActionColumn<Spider>({
      width: 140,
      actions: [
        {
          icon: RiPlayLine,
          label: '执行',
          onClick: row => handleRun(row),
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
            setSelectedSpider(row)
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
        <h1 className="text-2xl font-semibold text-text-primary">爬虫列表</h1>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <RiAddLine className="mr-1 h-4 w-4" />
          创建爬虫
        </Button>
      </div>

      <DataTableToolbar
        className="shrink-0"
        searchValue={keyword}
        searchPlaceholder="搜索爬虫名称"
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

      <SpiderFormModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={data => handleCreate(data as SpiderCreate)}
        isLoading={createMutation.isPending}
      />
      <SpiderFormModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setEditingId(null)
        }}
        spiderId={editingId}
        onSubmit={data => handleUpdate(data as SpiderUpdate)}
        isLoading={updateMutation.isPending}
      />
      <Confirm
        isShow={showDeleteModal}
        onCancel={() => {
          setShowDeleteModal(false)
          setSelectedSpider(null)
        }}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认删除"
        content={`确定要删除爬虫 "${selectedSpider?.name}" 吗？`}
      />
    </>
  )
}

export default SpidersPage
