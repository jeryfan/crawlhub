# Frontend Pipeline UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add deployment management, task management, data preview, and test run UI to the CrawlHub admin frontend, completing the full spider lifecycle pipeline.

**Architecture:** Extend the existing Next.js 14+ admin frontend with 3 new pages (tasks, data, spider detail tabs) and enhanced spider detail page. All new pages follow the established DataTable + React Query pattern. The spider detail page is refactored from a single Coder iframe into a tabbed layout with: 开发 (workspace), 部署 (deployments), 任务 (tasks), 数据 (data preview).

**Tech Stack:** Next.js 15, React 19, TypeScript, TanStack React Query v5, TanStack React Table v8, @headlessui/react, @remixicon/react, Tailwind CSS

---

## Context

**Backend APIs already implemented:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /crawlhub/spiders/{id}/deployments` | POST | Deploy from workspace |
| `GET /crawlhub/spiders/{id}/deployments` | GET | List deployments (paginated) |
| `GET /crawlhub/spiders/{id}/deployments/{did}` | GET | Deployment detail |
| `POST /crawlhub/spiders/{id}/deployments/{did}/rollback` | POST | Rollback to version |
| `POST /crawlhub/spiders/{id}/workspace/restore` | POST | Restore code to workspace |
| `POST /crawlhub/spiders/{id}/test-run` | POST | SSE test run |
| `POST /crawlhub/spiders/{id}/run` | POST | Production run (Celery) |
| `GET /crawlhub/tasks` | GET | Task list (paginated, filter by spider_id/status) |
| `GET /crawlhub/tasks/{id}` | GET | Task detail |
| `GET /crawlhub/tasks/{id}/logs` | GET | Task logs |
| `POST /crawlhub/tasks/{id}/cancel` | POST | Cancel task |
| `GET /crawlhub/data` | GET | Data list (filter spider_id/task_id/is_test) |
| `GET /crawlhub/data/preview/{task_id}` | GET | Data preview |
| `GET /crawlhub/data/export/json` | GET | Export JSON |
| `GET /crawlhub/data/export/csv` | GET | Export CSV |
| `DELETE /crawlhub/data` | DELETE | Delete data |

**Existing frontend patterns:**
- API hooks: `admin/service/use-crawlhub.ts` — React Query hooks with namespace `crawlhub`
- Types: `admin/types/crawlhub.ts`
- Base components: `Button`, `Modal`, `Confirm`, `Input`, `SimpleSelect`, `DataTable`, `DataTableToolbar`, `StatusBadge`, `Skeleton`, `Toast`
- Icons: `@remixicon/react` (RiXxxLine pattern)
- Menu: `admin/app/components/sidebar/menu-config.tsx`
- API methods: `get<T>`, `post<T>`, `put<T>`, `del<T>` from `@/service/base`

**Key response wrapper pattern:**
All backend responses are wrapped in `ApiResponse({ data: ... })`. The `get<T>` function returns the unwrapped `data` field.

---

### Task 1: Add TypeScript Types for Deployments and Data

**Files:**
- Modify: `admin/types/crawlhub.ts`

**Step 1: Add deployment and data types**

Add these types after the existing `FileUploadResult` type at the end of the file:

```typescript
// Deployment Types
export type DeploymentStatus = 'active' | 'archived'

export type Deployment = {
  id: string
  spider_id: string
  version: number
  status: DeploymentStatus
  entry_point: string | null
  file_count: number
  archive_size: number
  deploy_note: string | null
  created_at: string
  updated_at: string
}

export type DeploymentListResponse = {
  items: Deployment[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type DeployRequest = {
  deploy_note?: string
}

// Data Types
export type DataQueryParams = {
  spider_id?: string
  task_id?: string
  is_test?: boolean
  page?: number
  page_size?: number
}

export type DataListResponse = {
  items: Record<string, any>[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type DataPreviewResponse = {
  items: Record<string, any>[]
  total: number
  field_stats: Record<string, {
    type: string
    non_null_count: number
    sample: any
  }>
}

// Task Log Types
export type TaskLog = {
  stdout: string
  stderr: string
  message?: string
}
```

Also update the `Spider` type to include `active_deployment_id`:

```typescript
export type Spider = {
  // ... existing fields ...
  active_deployment_id: string | null  // Add this line after coder_workspace_name
  webhook_url: string | null           // Add this line too
  // ...
}
```

And update `CrawlHubTask` to include the new fields:

```typescript
export type CrawlHubTask = {
  // ... existing fields ...
  is_test: boolean         // Add
  trigger_type: string     // Add
  retry_count: number      // Add
  max_retries: number      // Add
}
```

**Step 2: Verify types compile**

Run: `cd /Users/fanjunjie/Documents/repositories/personal/crawlhub/admin && npx tsc --noEmit --pretty 2>&1 | head -30`

---

### Task 2: Add API Hooks for Deployments, Tasks, Data

**Files:**
- Modify: `admin/service/use-crawlhub.ts`

**Step 1: Add imports for new types**

At the top of the file, update the import statement to include the new types:

```typescript
import type {
  // ... existing imports ...
  DataListResponse,
  DataPreviewResponse,
  DataQueryParams,
  Deployment,
  DeploymentListResponse,
  DeployRequest,
  TaskLog,
  TasksQueryParams,
  TaskListResponse,
  CrawlHubTask,
} from '@/types/crawlhub'
```

**Step 2: Add Deployment hooks**

Add after the Coder Workspace API section:

```typescript
// ============ Deployments API ============

export const useDeployments = (spiderId: string, params?: { page?: number; page_size?: number }) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'deployments', spiderId, params],
    queryFn: () => get<DeploymentListResponse>(`/crawlhub/spiders/${spiderId}/deployments`, { params }),
    enabled: !!spiderId,
  })
}

export const useDeployFromWorkspace = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spiderId, data }: { spiderId: string; data?: DeployRequest }) =>
      post<Deployment>(`/crawlhub/spiders/${spiderId}/deployments`, { body: data || {} }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'deployments', variables.spiderId] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spiders', variables.spiderId] })
    },
  })
}

export const useRollbackDeployment = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spiderId, deploymentId }: { spiderId: string; deploymentId: string }) =>
      post<Deployment>(`/crawlhub/spiders/${spiderId}/deployments/${deploymentId}/rollback`, {}),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'deployments', variables.spiderId] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spiders', variables.spiderId] })
    },
  })
}

export const useRestoreWorkspace = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spiderId, deploymentId }: { spiderId: string; deploymentId?: string }) =>
      post(`/crawlhub/spiders/${spiderId}/workspace/restore`, {
        body: deploymentId ? { deployment_id: deploymentId } : {},
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'workspace', variables.spiderId] })
    },
  })
}
```

**Step 3: Add Task hooks**

Add after the Deployments section:

```typescript
// ============ Tasks API ============

export const useTasks = (params?: TasksQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'tasks', params],
    queryFn: () => get<TaskListResponse>(`/crawlhub/tasks`, { params }),
  })
}

export const useTask = (taskId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'tasks', taskId],
    queryFn: () => get<CrawlHubTask>(`/crawlhub/tasks/${taskId}`),
    enabled: !!taskId,
  })
}

export const useTaskLogs = (taskId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'tasks', taskId, 'logs'],
    queryFn: () => get<TaskLog>(`/crawlhub/tasks/${taskId}/logs`),
    enabled: !!taskId,
  })
}

export const useCancelTask = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => post(`/crawlhub/tasks/${taskId}/cancel`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tasks'] })
    },
  })
}
```

**Step 4: Add Data hooks**

Add after the Tasks section:

```typescript
// ============ Data API ============

export const useSpiderData = (params?: DataQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'data', params],
    queryFn: () => get<DataListResponse>(`/crawlhub/data`, { params }),
  })
}

export const useDataPreview = (taskId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'data', 'preview', taskId],
    queryFn: () => get<DataPreviewResponse>(`/crawlhub/data/preview/${taskId}`),
    enabled: !!taskId,
  })
}

export const useDeleteData = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (params: { spider_id?: string; task_id?: string }) =>
      del(`/crawlhub/data?${new URLSearchParams(params as Record<string, string>).toString()}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'data'] })
    },
  })
}

export const useTestRunSpider = () => {
  return useMutation({
    mutationFn: (spiderId: string) => {
      // SSE 不走标准 fetch，返回 EventSource URL 信息
      return Promise.resolve({ spiderId })
    },
  })
}
```

**Step 5: Verify types compile**

Run: `cd /Users/fanjunjie/Documents/repositories/personal/crawlhub/admin && npx tsc --noEmit --pretty 2>&1 | head -30`

---

### Task 3: Add Sidebar Menu Entries for Tasks and Data

**Files:**
- Modify: `admin/app/components/sidebar/menu-config.tsx`

**Step 1: Add new menu items**

Add icon imports at the top:

```typescript
import {
  // ... existing imports ...
  RiTaskLine,
  RiDatabase2Line,
} from '@remixicon/react'
```

Add two children to the `crawlhub` menu group, after `crawlhub-proxies`:

```typescript
{
  key: 'crawlhub-tasks',
  label: '任务管理',
  icon: <RiTaskLine className="h-5 w-5" />,
  path: '/crawlhub/tasks',
},
{
  key: 'crawlhub-data',
  label: '数据管理',
  icon: <RiDatabase2Line className="h-5 w-5" />,
  path: '/crawlhub/data',
},
```

---

### Task 4: Refactor Spider Detail Page with Tabs

This is the most substantial task. The current spider detail page only shows a Coder workspace iframe. We need to refactor it into a tabbed layout with four tabs: 开发, 部署, 任务, 数据.

**Files:**
- Modify: `admin/app/(commonLayout)/crawlhub/spiders/[id]/page.tsx`

**Step 1: Rewrite the spider detail page with tab navigation**

Replace the entire file content. The new structure:

```typescript
'use client'

import type { CoderWorkspaceStatus } from '@/types/crawlhub'
import {
  RiArrowLeftLine,
  RiCodeLine,
  RiDatabase2Line,
  RiExternalLinkLine,
  RiLoader4Line,
  RiPlayLine,
  RiRefreshLine,
  RiRocketLine,
  RiStopLine,
  RiTaskLine,
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
import WorkspaceTab from './tabs/workspace-tab'
import DeploymentsTab from './tabs/deployments-tab'
import TasksTab from './tabs/tasks-tab'
import DataTab from './tabs/data-tab'

type TabKey = 'workspace' | 'deployments' | 'tasks' | 'data'

const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: 'workspace', label: '开发', icon: <RiCodeLine className="h-4 w-4" /> },
  { key: 'deployments', label: '部署', icon: <RiRocketLine className="h-4 w-4" /> },
  { key: 'tasks', label: '任务', icon: <RiTaskLine className="h-4 w-4" /> },
  { key: 'data', label: '数据', icon: <RiDatabase2Line className="h-4 w-4" /> },
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
  const spiderId = params.id as string

  const [activeTab, setActiveTab] = useState<TabKey>('workspace')

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
          {/* Workspace status indicator (always visible) */}
          <div className="flex items-center gap-2 rounded-lg bg-background-section px-3 py-1.5">
            <span className="text-xs text-text-tertiary">工作区:</span>
            {isLoadingStatus && !workspaceStatus
              ? <Skeleton className="h-4 w-12" />
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
                : <span className="text-xs text-text-tertiary">未创建</span>}
          </div>

          {/* Workspace controls for workspace tab */}
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
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
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
        {activeTab === 'workspace' && (
          <WorkspaceTab
            spider={spider}
            workspaceStatus={workspaceStatus}
            isLoadingStatus={isLoadingStatus}
            onStartWorkspace={handleStartWorkspace}
            isOperating={isOperating}
          />
        )}
        {activeTab === 'deployments' && (
          <DeploymentsTab spiderId={spiderId} spider={spider} />
        )}
        {activeTab === 'tasks' && (
          <TasksTab spiderId={spiderId} />
        )}
        {activeTab === 'data' && (
          <DataTab spiderId={spiderId} />
        )}
      </div>
    </div>
  )
}

export default SpiderDetailPage
```

---

### Task 5: Create Workspace Tab Component

Extract the existing Coder iframe into its own tab component.

**Files:**
- Create: `admin/app/(commonLayout)/crawlhub/spiders/[id]/tabs/workspace-tab.tsx`

```typescript
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
```

---

### Task 6: Create Deployments Tab Component

Deploy button, deployment history table, rollback, restore workspace.

**Files:**
- Create: `admin/app/(commonLayout)/crawlhub/spiders/[id]/tabs/deployments-tab.tsx`

```typescript
'use client'

import type { ColumnDef } from '@/app/components/base/table'
import type { Deployment, Spider } from '@/types/crawlhub'
import {
  RiArrowGoBackLine,
  RiLoader4Line,
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

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useDeployments(spiderId, { page, page_size: pageSize })
  const deployMutation = useDeployFromWorkspace()
  const rollbackMutation = useRollbackDeployment()
  const restoreMutation = useRestoreWorkspace()

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
    </div>
  )
}

export default DeploymentsTab
```

---

### Task 7: Create Tasks Tab Component

Shows tasks filtered by current spider, with logs viewer.

**Files:**
- Create: `admin/app/(commonLayout)/crawlhub/spiders/[id]/tabs/tasks-tab.tsx`

```typescript
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
      size: 200,
      cell: ({ row }) => (
        <span className="text-xs text-red-500" title={row.original.error_message || ''}>
          {row.original.error_message
            ? (row.original.error_message.length > 50
                ? `${row.original.error_message.slice(0, 50)}...`
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
```

---

### Task 8: Create Data Tab Component

Data preview with task filter, field stats, export.

**Files:**
- Create: `admin/app/(commonLayout)/crawlhub/spiders/[id]/tabs/data-tab.tsx`

```typescript
'use client'

import type { DataQueryParams } from '@/types/crawlhub'
import {
  RiDeleteBinLine,
  RiDownloadLine,
  RiRefreshLine,
} from '@remixicon/react'
import { useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import { SimpleSelect } from '@/app/components/base/select'
import Toast from '@/app/components/base/toast'
import { useDeleteData, useSpiderData } from '@/service/use-crawlhub'
import { API_PREFIX } from '@/config'

type DataTabProps = {
  spiderId: string
}

const DataTab = ({ spiderId }: DataTabProps) => {
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [isTestFilter, setIsTestFilter] = useState<string>('all')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const params: DataQueryParams = {
    spider_id: spiderId,
    page,
    page_size: pageSize,
  }
  if (isTestFilter === 'test') params.is_test = true
  if (isTestFilter === 'prod') params.is_test = false

  const { data, isLoading, refetch } = useSpiderData(params)
  const deleteMutation = useDeleteData()

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync({ spider_id: spiderId })
      Toast.notify({ type: 'success', message: '数据已删除' })
      setShowDeleteConfirm(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const handleExport = (format: 'json' | 'csv') => {
    const url = `${API_PREFIX}/crawlhub/data/export/${format}?spider_id=${spiderId}`
    window.open(url, '_blank')
  }

  // Determine columns from first data item
  const items = data?.items || []
  const fieldKeys = items.length > 0
    ? Object.keys(items[0]).filter(k => !k.startsWith('_'))
    : []

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="mb-3 flex shrink-0 items-center justify-between">
        <div className="flex items-center gap-2">
          <SimpleSelect
            className="w-32"
            defaultValue={isTestFilter}
            items={[
              { value: 'all', name: '全部' },
              { value: 'prod', name: '生产数据' },
              { value: 'test', name: '测试数据' },
            ]}
            onSelect={item => {
              setIsTestFilter(item.value as string)
              setPage(1)
            }}
          />
          <span className="text-sm text-text-tertiary">
            共 {data?.total || 0} 条
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="small" onClick={() => handleExport('json')}>
            <RiDownloadLine className="mr-1 h-3.5 w-3.5" />
            JSON
          </Button>
          <Button variant="ghost" size="small" onClick={() => handleExport('csv')}>
            <RiDownloadLine className="mr-1 h-3.5 w-3.5" />
            CSV
          </Button>
          <Button
            variant="ghost"
            size="small"
            destructive
            onClick={() => setShowDeleteConfirm(true)}
          >
            <RiDeleteBinLine className="mr-1 h-3.5 w-3.5" />
            清空
          </Button>
          <Button variant="ghost" size="small" onClick={() => refetch()}>
            <RiRefreshLine className="mr-1 h-3.5 w-3.5" />
            刷新
          </Button>
        </div>
      </div>

      {/* Data Table */}
      <div className="flex-1 overflow-auto">
        {isLoading
          ? (
              <div className="py-12 text-center text-sm text-text-tertiary">加载中...</div>
            )
          : items.length === 0
            ? (
                <div className="py-12 text-center text-sm text-text-tertiary">暂无数据</div>
              )
            : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-divider-subtle bg-background-section">
                        {fieldKeys.map(key => (
                          <th
                            key={key}
                            className="whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-text-tertiary"
                          >
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item, i) => (
                        <tr key={i} className="border-b border-divider-subtle hover:bg-state-base-hover">
                          {fieldKeys.map(key => (
                            <td
                              key={key}
                              className="max-w-xs truncate whitespace-nowrap px-3 py-2 text-text-secondary"
                              title={String(item[key] ?? '')}
                            >
                              {typeof item[key] === 'object'
                                ? JSON.stringify(item[key])
                                : String(item[key] ?? '-')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
      </div>

      {/* Pagination */}
      {(data?.total || 0) > pageSize && (
        <div className="mt-3 flex shrink-0 items-center justify-between border-t border-divider-subtle pt-3">
          <span className="text-xs text-text-tertiary">
            第 {page} / {data?.total_pages || 1} 页
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="small"
              disabled={page <= 1}
              onClick={() => setPage(p => p - 1)}
            >
              上一页
            </Button>
            <Button
              variant="secondary"
              size="small"
              disabled={page >= (data?.total_pages || 1)}
              onClick={() => setPage(p => p + 1)}
            >
              下一页
            </Button>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      <Confirm
        isShow={showDeleteConfirm}
        onCancel={() => setShowDeleteConfirm(false)}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认清空数据"
        type="danger"
        content="确定要清空此爬虫的所有采集数据吗？此操作不可恢复。"
      />
    </div>
  )
}

export default DataTab
```

---

### Task 9: Create Tasks List Page

Standalone page at `/crawlhub/tasks` for viewing all tasks across spiders.

**Files:**
- Create: `admin/app/(commonLayout)/crawlhub/tasks/page.tsx`

```typescript
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
```

---

### Task 10: Create Data Management Page

Standalone page at `/crawlhub/data` for viewing all data across spiders.

**Files:**
- Create: `admin/app/(commonLayout)/crawlhub/data/page.tsx`

```typescript
'use client'

import type { DataQueryParams } from '@/types/crawlhub'
import {
  RiDeleteBinLine,
  RiDownloadLine,
  RiRefreshLine,
} from '@remixicon/react'
import { useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import { SimpleSelect } from '@/app/components/base/select'
import Toast from '@/app/components/base/toast'
import { useDeleteData, useSpiderData } from '@/service/use-crawlhub'
import { API_PREFIX } from '@/config'

const DataPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [spiderIdFilter, setSpiderIdFilter] = useState('')
  const [searchSpiderId, setSearchSpiderId] = useState('')
  const [isTestFilter, setIsTestFilter] = useState<string>('all')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const params: DataQueryParams = {
    page,
    page_size: pageSize,
  }
  if (searchSpiderId) params.spider_id = searchSpiderId
  if (isTestFilter === 'test') params.is_test = true
  if (isTestFilter === 'prod') params.is_test = false

  const { data, isLoading, refetch } = useSpiderData(params)
  const deleteMutation = useDeleteData()

  const handleSearch = () => {
    setSearchSpiderId(spiderIdFilter)
    setPage(1)
  }

  const handleDelete = async () => {
    if (!searchSpiderId) {
      Toast.notify({ type: 'error', message: '请先指定爬虫ID' })
      return
    }
    try {
      await deleteMutation.mutateAsync({ spider_id: searchSpiderId })
      Toast.notify({ type: 'success', message: '数据已删除' })
      setShowDeleteConfirm(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const handleExport = (format: 'json' | 'csv') => {
    const exportParams = new URLSearchParams()
    if (searchSpiderId) exportParams.set('spider_id', searchSpiderId)
    const url = `${API_PREFIX}/crawlhub/data/export/${format}?${exportParams.toString()}`
    window.open(url, '_blank')
  }

  const items = data?.items || []
  const fieldKeys = items.length > 0
    ? Object.keys(items[0]).filter(k => !k.startsWith('_'))
    : []

  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">数据管理</h1>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="small" onClick={() => handleExport('json')}>
            <RiDownloadLine className="mr-1 h-3.5 w-3.5" />
            导出 JSON
          </Button>
          <Button variant="ghost" size="small" onClick={() => handleExport('csv')}>
            <RiDownloadLine className="mr-1 h-3.5 w-3.5" />
            导出 CSV
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex shrink-0 items-center gap-3">
        <div className="flex items-center gap-2">
          <Input
            value={spiderIdFilter}
            onChange={e => setSpiderIdFilter(e.target.value)}
            placeholder="按爬虫ID筛选"
            wrapperClassName="!w-64"
          />
          <Button variant="secondary" size="small" onClick={handleSearch}>搜索</Button>
        </div>
        <SimpleSelect
          className="w-32"
          defaultValue={isTestFilter}
          items={[
            { value: 'all', name: '全部' },
            { value: 'prod', name: '生产数据' },
            { value: 'test', name: '测试数据' },
          ]}
          onSelect={item => {
            setIsTestFilter(item.value as string)
            setPage(1)
          }}
        />
        <span className="text-sm text-text-tertiary">共 {data?.total || 0} 条</span>
        <div className="ml-auto flex items-center gap-2">
          {searchSpiderId && (
            <Button
              variant="ghost"
              size="small"
              destructive
              onClick={() => setShowDeleteConfirm(true)}
            >
              <RiDeleteBinLine className="mr-1 h-3.5 w-3.5" />
              清空
            </Button>
          )}
          <Button variant="ghost" size="small" onClick={() => refetch()}>
            <RiRefreshLine className="mr-1 h-3.5 w-3.5" />
            刷新
          </Button>
        </div>
      </div>

      {/* Data Table */}
      <div className="flex-1 overflow-auto">
        {isLoading
          ? <div className="py-12 text-center text-sm text-text-tertiary">加载中...</div>
          : items.length === 0
            ? <div className="py-12 text-center text-sm text-text-tertiary">暂无数据</div>
            : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-divider-subtle bg-background-section">
                        {fieldKeys.map(key => (
                          <th
                            key={key}
                            className="whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-text-tertiary"
                          >
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item, i) => (
                        <tr key={i} className="border-b border-divider-subtle hover:bg-state-base-hover">
                          {fieldKeys.map(key => (
                            <td
                              key={key}
                              className="max-w-xs truncate whitespace-nowrap px-3 py-2 text-text-secondary"
                              title={String(item[key] ?? '')}
                            >
                              {typeof item[key] === 'object'
                                ? JSON.stringify(item[key])
                                : String(item[key] ?? '-')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
      </div>

      {/* Pagination */}
      {(data?.total || 0) > pageSize && (
        <div className="mt-3 flex shrink-0 items-center justify-between border-t border-divider-subtle pt-3">
          <span className="text-xs text-text-tertiary">
            第 {page} / {data?.total_pages || 1} 页
          </span>
          <div className="flex gap-2">
            <Button variant="secondary" size="small" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
              上一页
            </Button>
            <Button
              variant="secondary"
              size="small"
              disabled={page >= (data?.total_pages || 1)}
              onClick={() => setPage(p => p + 1)}
            >
              下一页
            </Button>
          </div>
        </div>
      )}

      <Confirm
        isShow={showDeleteConfirm}
        onCancel={() => setShowDeleteConfirm(false)}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认清空数据"
        type="danger"
        content="确定要清空该爬虫的所有采集数据吗？此操作不可恢复。"
      />
    </>
  )
}

export default DataPage
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | TypeScript types | `types/crawlhub.ts` |
| 2 | API hooks | `service/use-crawlhub.ts` |
| 3 | Sidebar menu | `components/sidebar/menu-config.tsx` |
| 4 | Spider detail page tabs | `spiders/[id]/page.tsx` |
| 5 | Workspace tab | `spiders/[id]/tabs/workspace-tab.tsx` |
| 6 | Deployments tab | `spiders/[id]/tabs/deployments-tab.tsx` |
| 7 | Tasks tab | `spiders/[id]/tabs/tasks-tab.tsx` |
| 8 | Data tab | `spiders/[id]/tabs/data-tab.tsx` |
| 9 | Tasks list page | `tasks/page.tsx` |
| 10 | Data management page | `data/page.tsx` |
