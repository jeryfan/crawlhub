'use client'

import type { CoderWorkspaceStatus } from '@/types/crawlhub'
import {
  RiArrowLeftLine,
  RiCodeLine,
  RiDatabase2Line,
  RiExternalLinkLine,
  RiLoader4Line,
  RiPlayLine,
  RiRocketLine,
  RiSettings3Line,
  RiStopLine,
  RiTaskLine,
} from '@remixicon/react'
import { useParams, usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useCallback, useState } from 'react'
import Button from '@/app/components/base/button'
import Skeleton from '@/app/components/base/skeleton'
import Toast from '@/app/components/base/toast'
import {
  useCreateOrGetWorkspace,
  useSpider,
  useStartWorkspace,
  useStopWorkspace,
  useWorkspaceStatus,
} from '@/service/use-crawlhub'
import DataTab from './tabs/data-tab'
import DeploymentsTab from './tabs/deployments-tab'
import SettingsTab from './tabs/settings-tab'
import TasksTab from './tabs/tasks-tab'
import WorkspaceTab from './tabs/workspace-tab'

type TabKey = 'workspace' | 'deployments' | 'tasks' | 'data' | 'settings'

const tabsList: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: 'workspace', label: '开发', icon: <RiCodeLine className="h-4 w-4" /> },
  { key: 'deployments', label: '部署', icon: <RiRocketLine className="h-4 w-4" /> },
  { key: 'tasks', label: '任务', icon: <RiTaskLine className="h-4 w-4" /> },
  { key: 'data', label: '数据', icon: <RiDatabase2Line className="h-4 w-4" /> },
  { key: 'settings', label: '设置', icon: <RiSettings3Line className="h-4 w-4" /> },
]

const statusLabels: Record<CoderWorkspaceStatus, string> = {
  pending: '等待中',
  starting: '启动中',
  running: '运行中',
  stopping: '停止中',
  stopped: '已停止',
  failed: '失败',
  unknown: '未知',
}

const statusColors: Record<CoderWorkspaceStatus, string> = {
  pending: 'bg-yellow-500',
  starting: 'bg-blue-500',
  running: 'bg-green-500',
  stopping: 'bg-orange-500',
  stopped: 'bg-gray-500',
  failed: 'bg-red-500',
  unknown: 'bg-gray-400',
}

const SpiderDetailPage = () => {
  const params = useParams()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const spiderId = params.id as string

  // 从 URL 读取 tab 参数，保持刷新后状态
  const tabFromUrl = searchParams.get('tab') as TabKey | null
  const initialTab = tabFromUrl && tabsList.some(t => t.key === tabFromUrl) ? tabFromUrl : 'workspace'

  const [activeTab, setActiveTab] = useState<TabKey>(initialTab)
  const [mountedTabs, setMountedTabs] = useState<Set<TabKey>>(() => new Set([initialTab]))

  const handleTabChange = useCallback((tab: TabKey) => {
    setActiveTab(tab)
    setMountedTabs((prev) => {
      if (prev.has(tab))
        return prev
      return new Set([...prev, tab])
    })
    router.replace(`${pathname}?tab=${tab}`, { scroll: false })
  }, [pathname, router])

  const { data: spider, isLoading: isLoadingSpider } = useSpider(spiderId)
  const {
    data: workspaceStatus,
    isLoading: isLoadingStatus,
    refetch: refetchStatus,
  } = useWorkspaceStatus(spiderId, {
    enabled: !!spiderId && !!spider?.coder_workspace_id,
    refetchInterval: (data) => {
      if (!data)
        return 3000
      if (data.status === 'starting' || data.status === 'stopping' || data.status === 'pending')
        return 2000
      if (data.status === 'running' && !data.is_ready)
        return 2000
      if (data.code_sync_status === 'syncing')
        return 2000
      return 10000
    },
  })

  const createOrGetWorkspaceMutation = useCreateOrGetWorkspace()
  const startWorkspaceMutation = useStartWorkspace()
  const stopWorkspaceMutation = useStopWorkspace()

  const handleBack = () => {
    router.push('/crawlhub/spiders')
  }

  const handleStartWorkspace = async () => {
    if (!spider)
      return
    try {
      if (spider.coder_workspace_id) {
        await startWorkspaceMutation.mutateAsync(spiderId)
        Toast.notify({ type: 'success', message: '正在启动工作区...' })
      }
      else {
        await createOrGetWorkspaceMutation.mutateAsync(spiderId)
        Toast.notify({ type: 'success', message: '正在创建工作区...' })
      }
      refetchStatus()
    }
    catch {
      Toast.notify({ type: 'error', message: '操作失败' })
    }
  }

  const handleStopWorkspace = async () => {
    try {
      await stopWorkspaceMutation.mutateAsync(spiderId)
      Toast.notify({ type: 'success', message: '正在停止工作区...' })
      refetchStatus()
    }
    catch {
      Toast.notify({ type: 'error', message: '停止失败' })
    }
  }

  const isOperating = createOrGetWorkspaceMutation.isPending
    || startWorkspaceMutation.isPending
    || stopWorkspaceMutation.isPending

  const sourceLabels: Record<string, string> = {
    empty: '空项目',
    scrapy: 'Scrapy 项目',
    git: 'Git 仓库',
    upload: '上传文件',
  }

  if (isLoadingSpider) {
    return (
      <div className="flex h-full flex-col">
        <div className="mb-4 flex items-center gap-4">
          <Skeleton className="h-8 w-8" />
          <Skeleton className="h-8 w-48" />
        </div>
        <Skeleton className="flex-1" />
      </div>
    )
  }

  if (!spider) {
    return (
      <div className="flex h-full flex-col items-center justify-center">
        <p className="text-text-secondary">爬虫不存在</p>
        <Button variant="secondary" onClick={handleBack} className="mt-4">
          返回列表
        </Button>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-3 flex shrink-0 items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-text-tertiary hover:bg-state-base-hover hover:text-text-secondary"
          >
            <RiArrowLeftLine className="h-5 w-5" />
          </button>
          <h1 className="text-lg font-semibold text-text-primary">{spider.name}</h1>
          <span className="rounded bg-background-section px-1.5 py-0.5 text-xs text-text-tertiary">
            {sourceLabels[spider.source] || spider.source}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Workspace status indicator */}
          <div className="flex items-center gap-2 rounded-lg bg-background-section px-3 py-1.5">
            <span className="text-xs text-text-tertiary">工作区:</span>
            {isLoadingStatus && !workspaceStatus
              ? <Skeleton className="h-4 w-12" />
              : workspaceStatus
                ? (
                    <div className="flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${statusColors[workspaceStatus.status]}`} />
                      <span className="text-xs font-medium text-text-primary">
                        {workspaceStatus.status === 'running' && !workspaceStatus.is_ready
                          ? workspaceStatus.code_sync_status === 'syncing'
                            ? '同步中'
                            : '初始化中'
                          : statusLabels[workspaceStatus.status]}
                      </span>
                      {(workspaceStatus.status === 'starting' || workspaceStatus.status === 'stopping'
                        || (workspaceStatus.status === 'running' && !workspaceStatus.is_ready)) && (
                        <RiLoader4Line className="h-3 w-3 animate-spin text-text-tertiary" />
                      )}
                    </div>
                  )
                : <span className="text-xs text-text-tertiary">未创建</span>}
          </div>

          {/* Workspace controls (only on workspace tab) */}
          {activeTab === 'workspace' && (
            <>
              {workspaceStatus?.url && (
                <Button
                  variant="secondary-accent"
                  size="small"
                  onClick={() => window.open(workspaceStatus.url!, '_blank')}
                >
                  <RiExternalLinkLine className="mr-1 h-3.5 w-3.5" />
                  新窗口
                </Button>
              )}
              {(!workspaceStatus || workspaceStatus.status === 'stopped' || workspaceStatus.status === 'failed') && (
                <Button variant="primary" size="small" onClick={handleStartWorkspace} loading={isOperating}>
                  <RiPlayLine className="mr-1 h-3.5 w-3.5" />
                  {spider.coder_workspace_id ? '启动' : '创建工作区'}
                </Button>
              )}
              {workspaceStatus?.status === 'running' && (
                <Button variant="secondary" size="small" onClick={handleStopWorkspace} loading={isOperating}>
                  <RiStopLine className="mr-1 h-3.5 w-3.5" />
                  停止
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-3 flex shrink-0 gap-1 border-b border-divider-subtle">
        {tabsList.map(tab => (
          <button
            key={tab.key}
            onClick={() => handleTabChange(tab.key)}
            className={`flex items-center gap-1.5 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'border-text-accent text-text-accent'
                : 'border-transparent text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-0 flex-1">
        {mountedTabs.has('workspace') && (
          <div className={activeTab !== 'workspace' ? 'hidden' : 'h-full'}>
            <WorkspaceTab
              spider={spider}
              workspaceStatus={workspaceStatus}
              isLoadingStatus={isLoadingStatus}
              onStartWorkspace={handleStartWorkspace}
              isOperating={isOperating}
            />
          </div>
        )}
        {mountedTabs.has('deployments') && (
          <div className={activeTab !== 'deployments' ? 'hidden' : 'h-full'}>
            <DeploymentsTab spiderId={spiderId} spider={spider} />
          </div>
        )}
        {mountedTabs.has('tasks') && (
          <div className={activeTab !== 'tasks' ? 'hidden' : 'h-full'}>
            <TasksTab spiderId={spiderId} />
          </div>
        )}
        {mountedTabs.has('data') && (
          <div className={activeTab !== 'data' ? 'hidden' : 'h-full'}>
            <DataTab spiderId={spiderId} />
          </div>
        )}
        {mountedTabs.has('settings') && (
          <div className={activeTab !== 'settings' ? 'hidden' : 'h-full'}>
            <SettingsTab spiderId={spiderId} spider={spider} />
          </div>
        )}
      </div>
    </div>
  )
}

export default SpiderDetailPage
