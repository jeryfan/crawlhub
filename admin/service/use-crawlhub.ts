/**
 * CrawlHub 爬虫管理 API 服务
 */

import type {
  CoderWorkspace,
  CoderWorkspaceStatusResponse,
  CrawlHubProxiesQueryParams,
  CrawlHubProxy,
  CrawlHubProxyBatchCreate,
  CrawlHubProxyCreate,
  CrawlHubProxyListResponse,
  CrawlHubProxyUpdate,
  CrawlHubTask,
  DataListResponse,
  DataPreviewResponse,
  DataQueryParams,
  DataSource,
  DataSourceCreate,
  DataSourceListResponse,
  DataSourcesQueryParams,
  DataSourceTestRequest,
  DataSourceUpdate,
  Deployment,
  DeploymentListResponse,
  DeployRequest,
  FileUploadResult,
  Project,
  ProjectCreate,
  ProjectListResponse,
  ProjectsQueryParams,
  ProjectUpdate,
  Spider,
  SpiderCreate,
  SpiderDataSourceAssoc,
  SpiderDataSourceCreate,
  SpiderDataSourceUpdate,
  SpiderListResponse,
  SpidersQueryParams,
  SpiderTemplate,
  SpiderUpdate,
  TaskListResponse,
  TaskLog,
  TasksQueryParams,
} from '@/types/crawlhub'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { del, get, post, put, upload } from './base'
import { API_PREFIX, CSRF_COOKIE_NAME, CSRF_HEADER_NAME } from '@/config'
import Cookies from 'js-cookie'

const NAME_SPACE = 'crawlhub'

// ============ Projects API ============

export const useProjects = (params?: ProjectsQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'projects', params],
    queryFn: () => get<ProjectListResponse>('/crawlhub/projects', { params }),
    select: data => data,
  })
}

export const useProject = (projectId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'projects', projectId],
    queryFn: () => get<Project>(`/crawlhub/projects/${projectId}`),
    select: data => data,
    enabled: !!projectId,
  })
}

export const useCreateProject = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: ProjectCreate) => post<Project>('/crawlhub/projects', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'projects'] })
    },
  })
}

export const useUpdateProject = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string, data: ProjectUpdate }) =>
      put<Project>(`/crawlhub/projects/${id}`, { body: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'projects'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'projects', variables.id] })
    },
  })
}

export const useDeleteProject = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => del(`/crawlhub/projects/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'projects'] })
    },
  })
}

// ============ Spiders API ============

export const useSpiders = (params?: SpidersQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'spiders', params],
    queryFn: () => get<SpiderListResponse>('/crawlhub/spiders', { params }),
    select: data => data,
  })
}

export const useSpider = (spiderId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'spiders', spiderId],
    queryFn: () => get<Spider>(`/crawlhub/spiders/${spiderId}`),
    select: data => data,
    enabled: !!spiderId,
  })
}

export const useSpiderTemplates = () => {
  return useQuery({
    queryKey: [NAME_SPACE, 'spiders', 'templates'],
    queryFn: () => get<SpiderTemplate[]>('/crawlhub/spiders/templates'),
    select: data => data,
  })
}

export const useCreateSpider = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: SpiderCreate) => post<Spider>('/crawlhub/spiders', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spiders'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'projects'] })
    },
  })
}

export const useUpdateSpider = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string, data: SpiderUpdate }) =>
      put<Spider>(`/crawlhub/spiders/${id}`, { body: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spiders'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spiders', variables.id] })
    },
  })
}

export const useDeleteSpider = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => del(`/crawlhub/spiders/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spiders'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'projects'] })
    },
  })
}

export const useRunSpider = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => post(`/crawlhub/spiders/${id}/run`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tasks'] })
    },
  })
}

// ============ Proxies API ============

export const useCrawlHubProxies = (params?: CrawlHubProxiesQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'proxies', params],
    queryFn: () => get<CrawlHubProxyListResponse>('/crawlhub/proxies', { params }),
    select: data => data,
  })
}

export const useCrawlHubProxy = (proxyId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'proxies', proxyId],
    queryFn: () => get<CrawlHubProxy>(`/crawlhub/proxies/${proxyId}`),
    select: data => data,
    enabled: !!proxyId,
  })
}

export const useCreateCrawlHubProxy = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CrawlHubProxyCreate) => post<CrawlHubProxy>('/crawlhub/proxies', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'proxies'] })
    },
  })
}

export const useBatchCreateCrawlHubProxies = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CrawlHubProxyBatchCreate) => post<CrawlHubProxy[]>('/crawlhub/proxies/batch', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'proxies'] })
    },
  })
}

export const useUpdateCrawlHubProxy = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string, data: CrawlHubProxyUpdate }) =>
      put<CrawlHubProxy>(`/crawlhub/proxies/${id}`, { body: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'proxies'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'proxies', variables.id] })
    },
  })
}

export const useDeleteCrawlHubProxy = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => del(`/crawlhub/proxies/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'proxies'] })
    },
  })
}

export const useCheckCrawlHubProxy = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => post(`/crawlhub/proxies/${id}/check`, {}),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'proxies'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'proxies', id] })
    },
  })
}

// ============ Coder Workspace API ============

export const useCreateOrGetWorkspace = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (spiderId: string) =>
      post<CoderWorkspace>(`/crawlhub/spiders/${spiderId}/workspace`, {}),
    onSuccess: (_, spiderId) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'workspace', spiderId] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spiders', spiderId] })
    },
  })
}

export const useWorkspaceStatus = (spiderId: string, options?: { enabled?: boolean, refetchInterval?: number | false }) => {
  const { enabled = true, refetchInterval = 5000 } = options || {}
  return useQuery({
    queryKey: [NAME_SPACE, 'workspace', spiderId],
    queryFn: () => get<CoderWorkspaceStatusResponse>(`/crawlhub/spiders/${spiderId}/workspace`),
    enabled: !!spiderId && enabled,
    refetchInterval,
  })
}

export const useStartWorkspace = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (spiderId: string) =>
      post(`/crawlhub/spiders/${spiderId}/workspace/start`, {}),
    onSuccess: (_, spiderId) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'workspace', spiderId] })
    },
  })
}

export const useStopWorkspace = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (spiderId: string) =>
      post(`/crawlhub/spiders/${spiderId}/workspace/stop`, {}),
    onSuccess: (_, spiderId) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'workspace', spiderId] })
    },
  })
}

export const useUploadToWorkspace = () => {
  return useMutation({
    mutationFn: ({ spiderId, file, path }: { spiderId: string, file: File, path?: string }) => {
      return new Promise<FileUploadResult>((resolve, reject) => {
        const xhr = new XMLHttpRequest()
        const formData = new FormData()
        formData.append('file', file)
        if (path)
          formData.append('path', path)

        upload(
          {
            xhr,
            data: formData,
          },
          false,
          `/crawlhub/spiders/${spiderId}/workspace/upload`,
        ).then((res) => {
          resolve(res as unknown as FileUploadResult)
        }).catch(reject)
      })
    },
  })
}

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

export const useDeleteDeployment = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spiderId, deploymentId }: { spiderId: string; deploymentId: string }) =>
      del(`/crawlhub/spiders/${spiderId}/deployments/${deploymentId}`),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'deployments', variables.spiderId] })
    },
  })
}

// ============ Tasks API ============

export const useTasks = (params?: TasksQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'tasks', params],
    queryFn: () => get<TaskListResponse>(`/crawlhub/tasks`, { params }),
    refetchInterval: (query) => {
      const hasActive = query.state.data?.items?.some(
        (t: CrawlHubTask) => t.status === 'pending' || t.status === 'running',
      )
      return hasActive ? 3000 : false
    },
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

// ============ DataSources API ============

export const useDataSources = (params?: DataSourcesQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'datasources', params],
    queryFn: () => get<DataSourceListResponse>('/crawlhub/datasources', { params }),
  })
}

export const useDataSource = (id: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'datasources', id],
    queryFn: () => get<DataSource>(`/crawlhub/datasources/${id}`),
    enabled: !!id,
  })
}

export const useCreateDataSource = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: DataSourceCreate) => post<DataSource>('/crawlhub/datasources', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'datasources'] })
    },
  })
}

export const useUpdateDataSource = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DataSourceUpdate }) =>
      put<DataSource>(`/crawlhub/datasources/${id}`, { body: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'datasources'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'datasources', variables.id] })
    },
  })
}

export const useDeleteDataSource = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => del(`/crawlhub/datasources/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'datasources'] })
    },
  })
}

export const useTestDataSourceConnection = () => {
  return useMutation({
    mutationFn: (id: string) => post<{ ok: boolean; message: string; latency_ms: number }>(`/crawlhub/datasources/${id}/test`, {}),
  })
}

export const useTestDataSourceParams = () => {
  return useMutation({
    mutationFn: (data: DataSourceTestRequest) => post<{ ok: boolean; message: string; latency_ms: number }>('/crawlhub/datasources/test', { body: data }),
  })
}

export const useStartDataSource = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => post(`/crawlhub/datasources/${id}/start`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'datasources'] })
    },
  })
}

export const useStopDataSource = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => post(`/crawlhub/datasources/${id}/stop`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'datasources'] })
    },
  })
}

// ============ Spider-DataSource Associations API ============

export const useSpiderDataSources = (spiderId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'spider-datasources', spiderId],
    queryFn: () => get<SpiderDataSourceAssoc[]>(`/crawlhub/spiders/${spiderId}/datasources`),
    enabled: !!spiderId,
  })
}

export const useAddSpiderDataSource = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spiderId, data }: { spiderId: string; data: SpiderDataSourceCreate }) =>
      post<SpiderDataSourceAssoc>(`/crawlhub/spiders/${spiderId}/datasources`, { body: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spider-datasources', variables.spiderId] })
    },
  })
}

export const useUpdateSpiderDataSource = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spiderId, assocId, data }: { spiderId: string; assocId: string; data: SpiderDataSourceUpdate }) =>
      put<SpiderDataSourceAssoc>(`/crawlhub/spiders/${spiderId}/datasources/${assocId}`, { body: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spider-datasources', variables.spiderId] })
    },
  })
}

export const useRemoveSpiderDataSource = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spiderId, assocId }: { spiderId: string; assocId: string }) =>
      del(`/crawlhub/spiders/${spiderId}/datasources/${assocId}`),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'spider-datasources', variables.spiderId] })
    },
  })
}
