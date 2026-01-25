/**
 * Proxy 代理管理 API 服务
 */

import type {
  ProxyLogEntry,
  ProxyLogListResponse,
  ProxyLogsQueryParams,
  ProxyLogStatistics,
  ProxyRoute,
  ProxyRouteCreate,
  ProxyRouteListResponse,
  ProxyRoutesQueryParams,
  ProxyRouteUpdate,
} from '@/types/proxy'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { del, get, post, put } from './base'

const NAME_SPACE = 'proxy'

// ============ Proxy Routes API ============

export const useProxyRoutes = (params?: ProxyRoutesQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'routes', params],
    queryFn: () => get<ProxyRouteListResponse>('/proxy/routes', { params }),
    select: data => data,
  })
}

export const useProxyRoute = (routeId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'routes', routeId],
    queryFn: () => get<ProxyRoute>(`/proxy/routes/${routeId}`),
    select: data => data,
    enabled: !!routeId,
  })
}

export const useCreateProxyRoute = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: ProxyRouteCreate) => post<ProxyRoute>('/proxy/routes', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'routes'] })
    },
  })
}

export const useUpdateProxyRoute = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string, data: ProxyRouteUpdate }) =>
      put<ProxyRoute>(`/proxy/routes/${id}`, { body: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'routes'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'routes', variables.id] })
    },
  })
}

export const useDeleteProxyRoute = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => del(`/proxy/routes/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'routes'] })
    },
  })
}

export const useToggleProxyRouteStatus = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => post<ProxyRoute>(`/proxy/routes/${id}/toggle`, {}),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'routes'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'routes', id] })
    },
  })
}

// ============ Proxy Logs API ============

export const useProxyLogs = (params?: ProxyLogsQueryParams, options?: { refetchInterval?: number | false }) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'logs', params],
    queryFn: () => get<ProxyLogListResponse>('/proxy/logs', { params }),
    select: data => data,
    refetchInterval: options?.refetchInterval,
  })
}

export const useProxyLog = (logId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'logs', logId],
    queryFn: () => get<ProxyLogEntry>(`/proxy/logs/${logId}`),
    select: data => data,
    enabled: !!logId,
  })
}

export const useProxyLogStatistics = (params?: {
  start_time?: string
  end_time?: string
  route_id?: string
}, options?: { refetchInterval?: number | false }) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'logs', 'statistics', params],
    queryFn: () => get<ProxyLogStatistics>('/proxy/logs/statistics', { params }),
    select: data => data,
    refetchInterval: options?.refetchInterval,
  })
}

export const useClearProxyLogs = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (routeId?: string) => del('/proxy/logs', { params: routeId ? { route_id: routeId } : undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'logs'] })
    },
  })
}
