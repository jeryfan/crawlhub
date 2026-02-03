'use client'

import type { CoderWorkspaceStatus } from '@/types/crawlhub'
import {
  RiArrowLeftLine,
  RiExternalLinkLine,
  RiLoader4Line,
  RiPlayLine,
  RiRefreshLine,
  RiStopLine,
} from '@remixicon/react'
import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
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
  const spiderId = params.id as string

  const [showIframe, setShowIframe] = useState(false)

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
      return 10000
    },
  })

  const createOrGetWorkspaceMutation = useCreateOrGetWorkspace()
  const startWorkspaceMutation = useStartWorkspace()
  const stopWorkspaceMutation = useStopWorkspace()

  useEffect(() => {
    if (workspaceStatus?.is_ready && workspaceStatus?.url) {
      setShowIframe(true)
    }
  }, [workspaceStatus?.is_ready, workspaceStatus?.url])

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
      setShowIframe(false)
      refetchStatus()
    }
    catch {
      Toast.notify({ type: 'error', message: '停止失败' })
    }
  }

  const handleOpenInNewWindow = () => {
    if (workspaceStatus?.url) {
      window.open(workspaceStatus.url, '_blank')
    }
  }

  const handleRefresh = () => {
    refetchStatus()
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
      {/* Header - 紧凑的顶部栏 */}
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
          {/* 工作区状态 */}
          <div className="flex items-center gap-2 rounded-lg bg-background-section px-3 py-1.5">
            <span className="text-xs text-text-tertiary">工作区状态:</span>
            {isLoadingStatus && !workspaceStatus
              ? (
                  <Skeleton className="h-4 w-12" />
                )
              : workspaceStatus
                ? (
                    <div className="flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${statusColors[workspaceStatus.status]}`} />
                      <span className="text-xs font-medium text-text-primary">
                        {statusLabels[workspaceStatus.status]}
                      </span>
                      {(workspaceStatus.status === 'starting' || workspaceStatus.status === 'stopping') && (
                        <RiLoader4Line className="h-3 w-3 animate-spin text-text-tertiary" />
                      )}
                    </div>
                  )
                : (
                    <span className="text-xs text-text-tertiary">未创建</span>
                  )}
          </div>

          <Button
            variant="secondary-accent"
            size="small"
            onClick={handleRefresh}
            disabled={isLoadingStatus}
          >
            <RiRefreshLine className={`mr-1 h-3.5 w-3.5 ${isLoadingStatus ? 'animate-spin' : ''}`} />
            刷新状态
          </Button>

          {workspaceStatus?.url && (
            <Button variant="secondary-accent" size="small" onClick={handleOpenInNewWindow}>
              <RiExternalLinkLine className="mr-1 h-3.5 w-3.5" />
              新窗口打开
            </Button>
          )}

          {(!workspaceStatus || workspaceStatus.status === 'stopped' || workspaceStatus.status === 'failed') && (
            <Button
              variant="primary"
              size="small"
              onClick={handleStartWorkspace}
              loading={isOperating}
            >
              <RiPlayLine className="mr-1 h-3.5 w-3.5" />
              {spider.coder_workspace_id ? '启动' : '创建工作区'}
            </Button>
          )}

          {workspaceStatus?.status === 'running' && (
            <Button
              variant="secondary"
              size="small"
              onClick={handleStopWorkspace}
              loading={isOperating}
            >
              <RiStopLine className="mr-1 h-3.5 w-3.5" />
              停止工作区
            </Button>
          )}
        </div>
      </div>

      {/* Coder iframe - 占据剩余空间 */}
      <div className="flex-1 overflow-hidden rounded-xl border border-divider-subtle">
        {showIframe && workspaceStatus?.url
          ? (
              <iframe
                src={workspaceStatus.url}
                className="h-full w-full border-0"
                title="Coder Workspace"
                allow="clipboard-read; clipboard-write"
              />
            )
          : (
              <div className="flex h-full flex-col items-center justify-center bg-background-section">
                {workspaceStatus?.status === 'starting' || workspaceStatus?.status === 'pending'
                  ? (
                      <>
                        <RiLoader4Line className="h-10 w-10 animate-spin text-text-quaternary" />
                        <p className="mt-3 text-sm text-text-secondary">工作区正在启动中...</p>
                        <p className="mt-1 text-xs text-text-tertiary">首次启动可能需要几分钟</p>
                      </>
                    )
                  : workspaceStatus?.status === 'running' && !workspaceStatus?.is_ready
                    ? (
                        <>
                          <RiLoader4Line className="h-10 w-10 animate-spin text-text-quaternary" />
                          <p className="mt-3 text-sm text-text-secondary">正在初始化开发环境...</p>
                          <p className="mt-1 text-xs text-text-tertiary">安装依赖和配置环境中</p>
                        </>
                      )
                    : (
                        <>
                          <div className="mb-4 rounded-lg bg-background-default-dimm p-4 text-center">
                            <p className="text-xs text-text-tertiary">
                              {sourceLabels[spider.source] || spider.source}
                              {spider.git_repo && ` · ${spider.git_repo}`}
                            </p>
                          </div>
                          <p className="text-text-tertiary">工作区未启动</p>
                          <Button variant="primary" onClick={handleStartWorkspace} className="mt-3" loading={isOperating}>
                            <RiPlayLine className="mr-1 h-4 w-4" />
                            {spider.coder_workspace_id ? '启动工作区' : '创建工作区'}
                          </Button>
                        </>
                      )}
              </div>
            )}
      </div>
    </div>
  )
}

export default SpiderDetailPage
