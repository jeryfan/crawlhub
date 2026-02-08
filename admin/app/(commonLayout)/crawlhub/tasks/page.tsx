'use client'

import type { ColumnDef } from '@/app/components/base/table'
import type { CrawlHubTask, CrawlHubTaskStatus } from '@/types/crawlhub'
import {
  RiCloseLine,
  RiEyeLine,
  RiRefreshLine,
  RiStopCircleLine,
} from '@remixicon/react'
import { useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Modal from '@/app/components/base/modal'
import { SimpleSelect } from '@/app/components/base/select'
import StatusBadge from '@/app/components/base/status-badge'
import {
  createActionColumn,
  DataTable,
  DataTableToolbar,
} from '@/app/components/base/table'
import Toast from '@/app/components/base/toast'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useCancelTask,
  useTaskLogs,
  useTasks,
} from '@/service/use-crawlhub'

const taskStatusConfig = {
  pending: { label: '等待中', color: 'bg-util-colors-yellow-yellow-500' },
  running: { label: '运行中', color: 'bg-util-colors-blue-blue-500' },
  completed: { label: '已完成', color: 'bg-util-colors-green-green-500' },
  failed: { label: '失败', color: 'bg-util-colors-red-red-500' },
  cancelled: { label: '已取消', color: 'bg-util-colors-gray-gray-500' },
}

const statusOptions = [
  { value: '', name: '全部状态' },
  { value: 'pending', name: '等待中' },
  { value: 'running', name: '运行中' },
  { value: 'completed', name: '已完成' },
  { value: 'failed', name: '失败' },
  { value: 'cancelled', name: '已取消' },
]

const TaskLogsModal = ({ taskId, onClose }: { taskId: string; onClose: () => void }) => {
  const { data: logs, isLoading } = useTaskLogs(taskId)

  return (
    <Modal isShow onClose={onClose} className="!max-w-2xl">
      <div className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">任务日志</h3>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>
        {isLoading
          ? <div className="py-8 text-center text-sm text-text-tertiary">加载中...</div>
          : (
              <div className="space-y-3">
                {logs?.stdout && (
                  <div>
                    <p className="mb-1 text-xs font-medium text-text-secondary">标准输出</p>
                    <pre className="max-h-60 overflow-auto rounded-lg bg-gray-900 p-3 text-xs text-green-400">
                      {logs.stdout}
                    </pre>
                  </div>
                )}
                {logs?.stderr && (
                  <div>
                    <p className="mb-1 text-xs font-medium text-text-secondary">错误输出</p>
                    <pre className="max-h-60 overflow-auto rounded-lg bg-gray-900 p-3 text-xs text-red-400">
                      {logs.stderr}
                    </pre>
                  </div>
                )}
                {!logs?.stdout && !logs?.stderr && (
                  <p className="py-8 text-center text-sm text-text-tertiary">
                    {logs?.message || '暂无日志'}
                  </p>
                )}
              </div>
            )}
      </div>
    </Modal>
  )
}

const TasksPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [viewingLogTaskId, setViewingLogTaskId] = useState<string | null>(null)

  const { formatDateTime } = useTimestamp()

  const queryParams = {
    page,
    page_size: pageSize,
    ...(statusFilter ? { status: statusFilter as CrawlHubTaskStatus } : {}),
  }

  const { data, isLoading, refetch } = useTasks(queryParams)
  const cancelMutation = useCancelTask()

  const handleCancel = async (taskId: string) => {
    try {
      await cancelMutation.mutateAsync(taskId)
      Toast.notify({ type: 'success', message: '任务已取消' })
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '取消失败' })
    }
  }

  const columns: ColumnDef<CrawlHubTask>[] = useMemo(() => [
    {
      id: 'id',
      header: '任务ID',
      size: 120,
      cell: ({ row }) => (
        <span className="font-mono text-xs text-text-secondary">
          {row.original.id.slice(0, 8)}...
        </span>
      ),
    },
    {
      id: 'spider_id',
      header: '爬虫ID',
      size: 120,
      cell: ({ row }) => (
        <span className="font-mono text-xs text-text-secondary">
          {row.original.spider_id.slice(0, 8)}...
        </span>
      ),
    },
    {
      id: 'status',
      header: '状态',
      size: 100,
      cell: ({ row }) => (
        <StatusBadge status={row.original.status} statusConfig={taskStatusConfig} />
      ),
    },
    {
      id: 'trigger_type',
      header: '触发',
      size: 80,
      cell: ({ row }) => (
        <span className="text-xs text-text-secondary">
          {row.original.trigger_type === 'schedule' ? '定时' : row.original.is_test ? '测试' : '手动'}
        </span>
      ),
    },
    {
      id: 'counts',
      header: '成功/失败/总计',
      size: 140,
      cell: ({ row }) => (
        <div className="text-xs text-text-secondary">
          <span className="text-green-600">{row.original.success_count}</span>
          {' / '}
          <span className="text-red-500">{row.original.failed_count}</span>
          {' / '}
          <span>{row.original.total_count}</span>
        </div>
      ),
    },
    {
      id: 'started_at',
      header: '开始时间',
      size: 160,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.started_at ? formatDateTime(row.original.started_at) : '-'}
        </span>
      ),
    },
    {
      id: 'error_message',
      header: '错误',
      size: 200,
      cell: ({ row }) => (
        <span className="text-xs text-red-500" title={row.original.error_message || ''}>
          {row.original.error_message
            ? (row.original.error_message.length > 40
                ? `${row.original.error_message.slice(0, 40)}...`
                : row.original.error_message)
            : '-'}
        </span>
      ),
    },
    createActionColumn<CrawlHubTask>({
      width: 120,
      actions: [
        {
          icon: RiEyeLine,
          label: '日志',
          onClick: (row) => setViewingLogTaskId(row.id),
        },
        {
          icon: RiStopCircleLine,
          label: '取消',
          onClick: (row) => handleCancel(row.id),
          visible: (row) => row.status === 'pending' || row.status === 'running',
          variant: 'danger',
        },
      ],
    }),
  ], [formatDateTime])

  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">任务管理</h1>
        <Button variant="ghost" size="small" onClick={() => refetch()}>
          <RiRefreshLine className="mr-1 h-3.5 w-3.5" />
          刷新
        </Button>
      </div>

      <DataTableToolbar
        className="shrink-0"
        filterSlot={
          <SimpleSelect
            className="w-32"
            defaultValue={statusFilter}
            items={statusOptions}
            onSelect={(item) => {
              setStatusFilter(item.value as string)
              setPage(1)
            }}
          />
        }
      />

      <DataTable
        columns={columns}
        data={data?.items || []}
        isLoading={isLoading}
        loadingRowCount={5}
        getRowId={row => row.id}
        stickyHeader
        pagination={{
          page,
          pageSize,
          total: data?.total || 0,
          onChange: setPage,
          onPageSizeChange: setPageSize,
        }}
      />

      {viewingLogTaskId && (
        <TaskLogsModal
          taskId={viewingLogTaskId}
          onClose={() => setViewingLogTaskId(null)}
        />
      )}
    </>
  )
}

export default TasksPage
