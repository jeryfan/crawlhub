'use client'

import type { ColumnDef } from '@/app/components/base/table'
import type { CrawlHubTask } from '@/types/crawlhub'
import {
  RiCloseLine,
  RiEyeLine,
  RiPlayLine,
  RiRefreshLine,
  RiStopCircleLine,
} from '@remixicon/react'
import { useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Modal from '@/app/components/base/modal'
import StatusBadge from '@/app/components/base/status-badge'
import { createActionColumn, DataTable } from '@/app/components/base/table'
import Toast from '@/app/components/base/toast'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useCancelTask,
  useRunSpider,
  useTaskLogs,
  useTasks,
} from '@/service/use-crawlhub'

type TasksTabProps = {
  spiderId: string
}

const taskStatusConfig = {
  pending: { label: '等待中', color: 'bg-util-colors-yellow-yellow-500' },
  running: { label: '运行中', color: 'bg-util-colors-blue-blue-500' },
  completed: { label: '已完成', color: 'bg-util-colors-green-green-500' },
  failed: { label: '失败', color: 'bg-util-colors-red-red-500' },
  cancelled: { label: '已取消', color: 'bg-util-colors-gray-gray-500' },
}

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
                      {logs.stdout || '(空)'}
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

const TasksTab = ({ spiderId }: TasksTabProps) => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [viewingLogTaskId, setViewingLogTaskId] = useState<string | null>(null)

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useTasks({ spider_id: spiderId, page, page_size: pageSize })
  const runMutation = useRunSpider()
  const cancelMutation = useCancelTask()

  const handleRun = async () => {
    try {
      await runMutation.mutateAsync(spiderId)
      Toast.notify({ type: 'success', message: '任务已提交' })
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '执行失败' })
    }
  }

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
      id: 'status',
      header: '状态',
      size: 100,
      cell: ({ row }) => (
        <StatusBadge status={row.original.status} statusConfig={taskStatusConfig} />
      ),
    },
    {
      id: 'trigger_type',
      header: '触发方式',
      size: 90,
      cell: ({ row }) => (
        <span className="text-xs text-text-secondary">
          {row.original.trigger_type === 'schedule' ? '定时' : row.original.is_test ? '测试' : '手动'}
        </span>
      ),
    },
    {
      id: 'progress',
      header: '进度',
      size: 120,
      cell: ({ row }) => {
        const task = row.original
        if (task.status !== 'running' && task.progress === 0) return <span className="text-xs text-text-tertiary">-</span>
        return (
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-16 rounded-full bg-background-section">
              <div
                className="h-full rounded-full bg-util-colors-blue-blue-500 transition-all"
                style={{ width: `${Math.min(100, task.progress)}%` }}
              />
            </div>
            <span className="text-xs text-text-secondary">{task.progress}%</span>
          </div>
        )
      },
    },
    {
      id: 'counts',
      header: '数据量',
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
      id: 'finished_at',
      header: '结束时间',
      size: 160,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {row.original.finished_at ? formatDateTime(row.original.finished_at) : '-'}
        </span>
      ),
    },
    {
      id: 'error_message',
      header: '错误信息',
      size: 240,
      cell: ({ row }) => {
        const task = row.original
        if (!task.error_message) return <span className="text-xs text-text-tertiary">-</span>
        const categoryLabels: Record<string, { label: string; color: string }> = {
          network: { label: '网络', color: 'bg-orange-100 text-orange-700' },
          auth: { label: '认证', color: 'bg-red-100 text-red-700' },
          parse: { label: '解析', color: 'bg-yellow-100 text-yellow-700' },
          system: { label: '系统', color: 'bg-gray-100 text-gray-700' },
        }
        const cat = task.error_category ? categoryLabels[task.error_category] : null
        return (
          <div className="flex items-center gap-1.5">
            {cat && (
              <span className={`shrink-0 rounded px-1 py-0.5 text-[10px] font-medium ${cat.color}`}>
                {cat.label}
              </span>
            )}
            <span className="truncate text-xs text-red-500" title={task.error_message}>
              {task.error_message.length > 40
                ? `${task.error_message.slice(0, 40)}...`
                : task.error_message}
            </span>
          </div>
        )
      },
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
    <div className="flex h-full flex-col">
      <div className="mb-3 flex shrink-0 items-center justify-between">
        <Button variant="primary" size="small" onClick={handleRun} loading={runMutation.isPending}>
          <RiPlayLine className="mr-1 h-3.5 w-3.5" />
          执行爬虫
        </Button>
        <Button variant="ghost" size="small" onClick={() => refetch()}>
          <RiRefreshLine className="mr-1 h-3.5 w-3.5" />
          刷新
        </Button>
      </div>

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

      {viewingLogTaskId && (
        <TaskLogsModal
          taskId={viewingLogTaskId}
          onClose={() => setViewingLogTaskId(null)}
        />
      )}
    </div>
  )
}

export default TasksTab
