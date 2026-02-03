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
  FileUploadResult,
  Project,
  ProjectCreate,
  ProjectListResponse,
  ProjectsQueryParams,
  ProjectUpdate,
  Spider,
  SpiderCreate,
  SpiderListResponse,
  SpidersQueryParams,
  SpiderTemplate,
  SpiderUpdate,
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
  return useMutation({
    mutationFn: (spiderId: string) =>
      post<CoderWorkspace>(`/crawlhub/spiders/${spiderId}/workspace`, {}),
  })
}

export const useWorkspaceStatus = (spiderId: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'workspace', spiderId],
    queryFn: () => get<CoderWorkspaceStatusResponse>(`/crawlhub/spiders/${spiderId}/workspace`),
    enabled: !!spiderId && enabled,
    refetchInterval: 10000,
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
