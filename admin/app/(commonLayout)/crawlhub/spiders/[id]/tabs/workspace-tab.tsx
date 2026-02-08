'use client'

import type { CoderWorkspaceStatusResponse, Spider } from '@/types/crawlhub'
import { RiLoader4Line, RiPlayLine } from '@remixicon/react'
import { useEffect, useState } from 'react'
import Button from '@/app/components/base/button'

type WorkspaceTabProps = {
  spider: Spider
  workspaceStatus: CoderWorkspaceStatusResponse | undefined
  isLoadingStatus: boolean
  onStartWorkspace: () => void
  isOperating: boolean
}

const sourceLabels: Record<string, string> = {
  empty: '空项目',
  scrapy: 'Scrapy 项目',
  git: 'Git 仓库',
  upload: '上传文件',
}

const WorkspaceTab = ({ spider, workspaceStatus, isLoadingStatus, onStartWorkspace, isOperating }: WorkspaceTabProps) => {
  const [showIframe, setShowIframe] = useState(false)

  useEffect(() => {
    if (workspaceStatus?.is_ready && workspaceStatus?.url)
      setShowIframe(true)
    else
      setShowIframe(false)
  }, [workspaceStatus?.is_ready, workspaceStatus?.url])

  return (
    <div className="h-full overflow-hidden rounded-xl border border-divider-subtle">
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
                        <Button variant="primary" onClick={onStartWorkspace} className="mt-3" loading={isOperating}>
                          <RiPlayLine className="mr-1 h-4 w-4" />
                          {spider.coder_workspace_id ? '启动工作区' : '创建工作区'}
                        </Button>
                      </>
                    )}
            </div>
          )}
    </div>
  )
}

export default WorkspaceTab
