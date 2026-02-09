'use client'

import type { ColumnDef } from '@/app/components/base/table'
import type { Deployment, Spider } from '@/types/crawlhub'
import {
  RiArrowGoBackLine,
  RiDeleteBinLine,
  RiRefreshLine,
  RiRocketLine,
  RiUploadLine,
} from '@remixicon/react'
import { useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import StatusBadge from '@/app/components/base/status-badge'
import { createActionColumn, DataTable } from '@/app/components/base/table'
import Toast from '@/app/components/base/toast'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useDeleteDeployment,
  useDeployFromWorkspace,
  useDeployments,
  useRestoreWorkspace,
  useRollbackDeployment,
} from '@/service/use-crawlhub'

type DeploymentsTabProps = {
  spiderId: string
  spider: Spider
}

const DeploymentsTab = ({ spiderId, spider }: DeploymentsTabProps) => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [showDeployModal, setShowDeployModal] = useState(false)
  const [deployNote, setDeployNote] = useState('')
  const [rollbackTarget, setRollbackTarget] = useState<Deployment | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Deployment | null>(null)

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useDeployments(spiderId, { page, page_size: pageSize })
  const deployMutation = useDeployFromWorkspace()
  const rollbackMutation = useRollbackDeployment()
  const restoreMutation = useRestoreWorkspace()
  const deleteMutation = useDeleteDeployment()

  const handleDeploy = async () => {
    try {
      await deployMutation.mutateAsync({
        spiderId,
        data: deployNote ? { deploy_note: deployNote } : undefined,
      })
      Toast.notify({ type: 'success', message: '部署成功' })
      setShowDeployModal(false)
      setDeployNote('')
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '部署失败' })
    }
  }

  const handleRollback = async () => {
    if (!rollbackTarget)
      return
    try {
      await rollbackMutation.mutateAsync({ spiderId, deploymentId: rollbackTarget.id })
      Toast.notify({ type: 'success', message: `已回滚到 v${rollbackTarget.version}` })
      setRollbackTarget(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '回滚失败' })
    }
  }

  const handleRestore = async () => {
    try {
      await restoreMutation.mutateAsync({ spiderId })
      Toast.notify({ type: 'success', message: '代码已恢复到工作区' })
    }
    catch {
      Toast.notify({ type: 'error', message: '恢复失败' })
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteMutation.mutateAsync({ spiderId, deploymentId: deleteTarget.id })
      Toast.notify({ type: 'success', message: `已删除 v${deleteTarget.version}` })
      setDeleteTarget(null)
      refetch()
    } catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const columns: ColumnDef<Deployment>[] = useMemo(() => [
    {
      id: 'version',
      header: '版本',
      size: 80,
      cell: ({ row }) => (
        <span className="font-mono font-medium text-text-primary">v{row.original.version}</span>
      ),
    },
    {
      id: 'status',
      header: '状态',
      size: 100,
      cell: ({ row }) => (
        <StatusBadge
          status={row.original.status}
          statusConfig={{
            active: { label: '活跃', color: 'bg-util-colors-green-green-500' },
            archived: { label: '归档', color: 'bg-util-colors-gray-gray-500' },
          }}
        />
      ),
    },
    {
      id: 'file_count',
      header: '文件数',
      size: 80,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">{row.original.file_count}</span>
      ),
    },
    {
      id: 'archive_size',
      header: '包大小',
      size: 100,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">{formatSize(row.original.archive_size)}</span>
      ),
    },
    {
      id: 'deploy_note',
      header: '备注',
      size: 200,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">{row.original.deploy_note || '-'}</span>
      ),
    },
    {
      id: 'created_at',
      header: '部署时间',
      size: 160,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">{formatDateTime(row.original.created_at)}</span>
      ),
    },
    createActionColumn<Deployment>({
      width: 100,
      actions: [
        {
          icon: RiArrowGoBackLine,
          label: '回滚',
          onClick: (row) => setRollbackTarget(row),
          visible: (row) => row.status !== 'active',
        },
        {
          icon: RiDeleteBinLine,
          label: '删除',
          onClick: (row) => setDeleteTarget(row),
          visible: (row) => row.status !== 'active',
          variant: 'danger',
        },
      ],
    }),
  ], [formatDateTime])

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="mb-3 flex shrink-0 items-center justify-between">
        <div className="flex items-center gap-2">
          <Button variant="primary" size="small" onClick={() => setShowDeployModal(true)}>
            <RiRocketLine className="mr-1 h-3.5 w-3.5" />
            部署
          </Button>
          {spider.active_deployment_id && (
            <Button
              variant="secondary"
              size="small"
              onClick={handleRestore}
              loading={restoreMutation.isPending}
            >
              <RiUploadLine className="mr-1 h-3.5 w-3.5" />
              恢复代码到工作区
            </Button>
          )}
        </div>
        <Button variant="ghost" size="small" onClick={() => refetch()}>
          <RiRefreshLine className="mr-1 h-3.5 w-3.5" />
          刷新
        </Button>
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={data?.items || []}
        isLoading={isLoading}
        loadingRowCount={3}
        getRowId={row => row.id}
        pagination={{
          page,
          pageSize,
          total: data?.total || 0,
          onChange: setPage,
          onPageSizeChange: setPageSize,
        }}
      />

      {/* Deploy Modal */}
      <Modal isShow={showDeployModal} onClose={() => setShowDeployModal(false)} className="!max-w-md">
        <div className="p-6">
          <h3 className="mb-4 text-lg font-semibold text-text-primary">部署到生产</h3>
          <p className="mb-4 text-sm text-text-secondary">
            将从工作区拉取当前代码，打包并创建新的部署版本。
          </p>
          <div className="mb-4">
            <label className="mb-1.5 block text-sm text-text-secondary">部署备注（可选）</label>
            <Input
              value={deployNote}
              onChange={e => setDeployNote(e.target.value)}
              placeholder="例如: 修复翻页逻辑"
            />
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowDeployModal(false)}>取消</Button>
            <Button variant="primary" onClick={handleDeploy} loading={deployMutation.isPending}>
              <RiRocketLine className="mr-1 h-3.5 w-3.5" />
              确认部署
            </Button>
          </div>
        </div>
      </Modal>

      {/* Rollback Confirm */}
      <Confirm
        isShow={!!rollbackTarget}
        onCancel={() => setRollbackTarget(null)}
        onConfirm={handleRollback}
        isLoading={rollbackMutation.isPending}
        title="确认回滚"
        content={`确定要回滚到 v${rollbackTarget?.version} 吗？当前活跃版本将被归档。`}
      />

      {/* Delete Confirm */}
      <Confirm
        isShow={!!deleteTarget}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认删除"
        content={`确定要删除 v${deleteTarget?.version} 吗？此操作不可恢复。`}
        type="danger"
      />
    </div>
  )
}

export default DeploymentsTab
