// Proxy Route Types
export type ProxyRoute = {
  id: string
  path: string
  target_urls: string[]
  load_balance_mode: 'round_robin' | 'failover'
  methods: string
  status: 'enabled' | 'disabled'
  description: string | null
  timeout: number
  preserve_host: boolean
  enable_logging: boolean
  streaming: boolean
  created_by: string | null
  created_at: string
  updated_at: string
}

export type ProxyRouteCreate = {
  path: string
  target_urls: string[]
  load_balance_mode?: 'round_robin' | 'failover'
  methods?: string
  description?: string
  timeout?: number
  preserve_host?: boolean
  enable_logging?: boolean
  streaming?: boolean
}

export type ProxyRouteUpdate = {
  path?: string
  target_urls?: string[]
  load_balance_mode?: 'round_robin' | 'failover'
  methods?: string
  status?: 'enabled' | 'disabled'
  description?: string
  timeout?: number
  preserve_host?: boolean
  enable_logging?: boolean
  streaming?: boolean
}

export type ProxyRoutesQueryParams = {
  page?: number
  page_size?: number
  status?: string
}

export type ProxyRouteListResponse = {
  items: ProxyRoute[]
  total: number
  page: number
  page_size: number
}

// Proxy Log Types
export type ProxyLogRequest = {
  method: string
  path: string
  query_params: Record<string, any> | null
  headers: Record<string, string> | null
  body: any
  body_size: number
}

export type ProxyLogResponse = {
  status_code: number
  headers: Record<string, string> | null
  body: any
  body_size: number
}

export type ProxyLogEntry = {
  _id: string
  route_id: string
  route_path: string
  target_url: string
  request: ProxyLogRequest
  response: ProxyLogResponse | null
  status: 'pending' | 'completed' | 'error'
  latency_ms: number
  client_ip: string | null
  error: string | null
  created_at: string
  completed_at: string | null
}

export type ProxyLogsQueryParams = {
  page?: number
  page_size?: number
  route_id?: string
  route_path?: string
  status_code?: number
  client_ip?: string
  start_time?: string
  end_time?: string
  has_error?: boolean
}

export type ProxyLogListResponse = {
  items: ProxyLogEntry[]
  total: number
  page: number
  page_size: number
}

export type ProxyLogStatistics = {
  total_requests: number
  success_count: number
  error_count: number
  success_rate: number
  avg_latency_ms: number
  requests_by_route: Record<string, number>
  requests_by_status: Record<string, number>
}
