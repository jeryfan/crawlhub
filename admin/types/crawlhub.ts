// CrawlHub Types

// Script Type
export type ScriptType = 'httpx' | 'scrapy' | 'playwright'

// Project Types
export type Project = {
  id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
  spider_count?: number
}

export type ProjectCreate = {
  name: string
  description?: string
}

export type ProjectUpdate = {
  name?: string
  description?: string
}

export type ProjectsQueryParams = {
  page?: number
  page_size?: number
  keyword?: string
}

export type ProjectListResponse = {
  items: Project[]
  total: number
  page: number
  page_size: number
}

// Spider Types
export type Spider = {
  id: string
  project_id: string
  name: string
  description: string | null
  script_type: ScriptType
  script_content: string | null
  cron_expr: string | null
  is_active: boolean
  config: Record<string, any> | null
  created_at: string
  updated_at: string
}

export type SpiderCreate = {
  project_id: string
  name: string
  description?: string
  script_type: ScriptType
  script_content?: string
  cron_expr?: string
  is_active?: boolean
  config?: Record<string, any>
}

export type SpiderUpdate = {
  name?: string
  description?: string
  script_type?: ScriptType
  script_content?: string
  cron_expr?: string
  is_active?: boolean
  config?: Record<string, any>
}

export type SpidersQueryParams = {
  page?: number
  page_size?: number
  project_id?: string
  is_active?: boolean
  keyword?: string
}

export type SpiderListResponse = {
  items: Spider[]
  total: number
  page: number
  page_size: number
}

export type SpiderTemplate = {
  name: string
  script_type: ScriptType
  content: string
}

// Task Types (CrawlHub Task)
export type CrawlHubTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export type CrawlHubTask = {
  id: string
  spider_id: string
  status: CrawlHubTaskStatus
  progress: number
  total_count: number
  success_count: number
  failed_count: number
  started_at: string | null
  finished_at: string | null
  worker_id: string | null
  container_id: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export type TasksQueryParams = {
  page?: number
  page_size?: number
  spider_id?: string
  status?: CrawlHubTaskStatus
}

export type TaskListResponse = {
  items: CrawlHubTask[]
  total: number
  page: number
  page_size: number
}

// Proxy Types (CrawlHub Proxy Pool)
export type ProxyProtocol = 'http' | 'https' | 'socks5'
export type CrawlHubProxyStatus = 'active' | 'inactive' | 'cooldown'

export type CrawlHubProxy = {
  id: string
  host: string
  port: number
  protocol: ProxyProtocol
  username: string | null
  password: string | null
  status: CrawlHubProxyStatus
  last_check_at: string | null
  success_rate: number
  created_at: string
  updated_at: string
}

export type CrawlHubProxyCreate = {
  host: string
  port: number
  protocol?: ProxyProtocol
  username?: string
  password?: string
}

export type CrawlHubProxyBatchCreate = {
  proxies: CrawlHubProxyCreate[]
}

export type CrawlHubProxyUpdate = {
  host?: string
  port?: number
  protocol?: ProxyProtocol
  username?: string
  password?: string
  status?: CrawlHubProxyStatus
}

export type CrawlHubProxiesQueryParams = {
  page?: number
  page_size?: number
  status?: CrawlHubProxyStatus
  protocol?: ProxyProtocol
}

export type CrawlHubProxyListResponse = {
  items: CrawlHubProxy[]
  total: number
  page: number
  page_size: number
}
