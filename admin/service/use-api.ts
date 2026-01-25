/**
 * API管理 API 服务
 */

import type {
  ApiKeyCreate,
  ApiKeyCreateResponse,
  ApiKeyDetail,
  ApiKeyListResponse,
  ApiKeyQueryParams,
  ApiKeyRegenerateResponse,
  ApiKeyUpdate,
  ApiUsageByEndpoint,
  ApiUsageListResponse,
  ApiUsageQueryParams,
  ApiUsageStatsParams,
  ApiUsageStatsResponse,
  ApiUsageTrendItem,
} from '@/types/api'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { del, get, patch, post, put } from './base'

const NAME_SPACE = 'api-management'

// ============ API Keys API ============
export const useApiKeys = (params?: ApiKeyQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'api-keys', params],
    queryFn: () => get<ApiKeyListResponse>('/api-keys', { params }),
    select: data => data,
  })
}

export const useApiKey = (keyId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'api-keys', keyId],
    queryFn: () => get<ApiKeyDetail>(`/api-keys/${keyId}`),
    select: data => data,
    enabled: !!keyId,
  })
}

export const useCreateApiKey = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: ApiKeyCreate) =>
      post<ApiKeyCreateResponse>('/api-keys', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'api-keys'] })
    },
  })
}

export const useUpdateApiKey = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string, data: ApiKeyUpdate }) =>
      put<ApiKeyDetail>(`/api-keys/${id}`, { body: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'api-keys'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'api-keys', variables.id] })
    },
  })
}

export const useRegenerateApiKey = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      post<ApiKeyRegenerateResponse>(`/api-keys/${id}/regenerate`, {}),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'api-keys'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'api-keys', id] })
    },
  })
}

export const useRevokeApiKey = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      patch<ApiKeyDetail>(`/api-keys/${id}/revoke`, {}),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'api-keys'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'api-keys', id] })
    },
  })
}

export const useDeleteApiKey = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => del(`/api-keys/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'api-keys'] })
    },
  })
}

// ============ API Usage API ============
export const useApiUsage = (params?: ApiUsageQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'api-usage', params],
    queryFn: () => get<ApiUsageListResponse>('/api-usage', { params }),
    select: data => data,
  })
}

export const useApiUsageStats = (params?: ApiUsageStatsParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'api-usage', 'stats', params],
    queryFn: () => get<ApiUsageStatsResponse>('/api-usage/stats', { params }),
    select: data => data,
  })
}

export const useApiUsageByEndpoint = (params?: ApiUsageStatsParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'api-usage', 'by-endpoint', params],
    queryFn: () => get<ApiUsageByEndpoint[]>('/api-usage/by-endpoint', { params }),
    select: data => data,
  })
}

export const useApiUsageTrends = (params?: ApiUsageStatsParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'api-usage', 'trends', params],
    queryFn: () => get<ApiUsageTrendItem[]>('/api-usage/trends', { params }),
    select: data => data,
  })
}

// 导出API使用数据
export const exportApiUsage = (params?: ApiUsageQueryParams) => {
  const queryString = new URLSearchParams(
    Object.entries(params || {}).filter(([_, v]) => v != null) as [string, string][],
  ).toString()
  const url = `/api-usage/export${queryString ? `?${queryString}` : ''}`
  // 这里需要使用完整URL，包含platform前缀
  return `/platform/api${url}`
}
