/**
 * CrawlHub 爬虫管理 API 服务
 */

import type {
  CrawlHubProxy,
  CrawlHubProxiesQueryParams,
  CrawlHubProxyBatchCreate,
  CrawlHubProxyCreate,
  CrawlHubProxyListResponse,
  CrawlHubProxyUpdate,
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
import { del, get, post, put } from './base'

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
