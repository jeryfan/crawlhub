export type ApiKeyStatus = 'active' | 'disabled' | 'revoked'

export type ApiKeyListItem = {
  id: string
  name: string
  key_prefix: string
  tenant_id: string | null
  tenant_name: string | null
  whitelist: string[] | null
  status: ApiKeyStatus
  rpm: number | null
  rph: number | null
  balance: number | null
  expires_at: string | null
  last_used_at: string | null
  created_at: string
  updated_at: string | null
}

export type ApiKeyDetail = {
  created_by: string | null
  created_by_name: string | null
} & ApiKeyListItem

export type ApiKeyCreate = {
  name: string
  tenant_id?: string
  whitelist?: string[]
  rpm?: number
  rph?: number
  balance?: number
  expires_at?: string
}

export type ApiKeyUpdate = {
  name?: string
  whitelist?: string[]
  rpm?: number
  rph?: number
  balance?: number
  expires_at?: string
  status?: ApiKeyStatus
}

export type ApiKeyCreateResponse = {
  id: string
  name: string
  key: string
  key_prefix: string
  tenant_id: string | null
  whitelist: string[] | null
  status: ApiKeyStatus
  rpm: number | null
  rph: number | null
  balance: number | null
  expires_at: string | null
  created_at: string
}

export type ApiKeyRegenerateResponse = {
  id: string
  name: string
  key: string
  key_prefix: string
}

export type ApiKeyListResponse = {
  items: ApiKeyListItem[]
  total: number
  page: number
  page_size: number
}

export type ApiUsageItem = {
  id: string
  api_key_id: string
  api_key_name: string | null
  api_key_prefix: string | null
  tenant_id: string
  tenant_name: string | null
  endpoint: string
  method: string
  service_type: string
  latency_ms: number
  status_code: number
  error_message: string | null
  ip_address: string
  request_id: string | null
  created_at: string
}

export type ApiUsageListResponse = {
  items: ApiUsageItem[]
  total: number
  page: number
  page_size: number
}

export type ApiUsageStats = {
  total_requests: number
  avg_latency_ms: number
  total_errors: number
  error_rate: number
}

export type ApiUsageByEndpoint = {
  endpoint: string
  request_count: number
  avg_latency_ms: number
}

export type ApiUsageTrendItem = {
  period: string
  request_count: number
}

export type ApiUsageStatsResponse = {
  stats: ApiUsageStats
  by_endpoint: ApiUsageByEndpoint[] | null
  trends: ApiUsageTrendItem[] | null
}

export type ApiKeyQueryParams = {
  tenant_id?: string
  status?: string
  search?: string
  page?: number
  page_size?: number
}

export type ApiUsageQueryParams = {
  tenant_id?: string
  api_key_id?: string
  endpoint?: string
  service_type?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

export type ApiUsageStatsParams = {
  tenant_id?: string
  api_key_id?: string
  start_date?: string
  end_date?: string
  granularity?: 'day' | 'hour'
}
