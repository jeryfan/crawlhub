// CrawlHub Types

// Project Source - 项目来源类型
export type ProjectSource = 'empty' | 'scrapy' | 'git' | 'upload'

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
  script_content: string | null
  cron_expr: string | null
  is_active: boolean
  entry_point: string | null
  source: ProjectSource
  git_repo: string | null
  coder_workspace_id: string | null
  coder_workspace_name: string | null
  active_deployment_id: string | null
  code_sync_status: string | null
  webhook_url: string | null
  // 执行配置
  timeout_seconds: number | null
  max_items: number | null
  memory_limit_mb: number | null
  requirements_txt: string | null
  env_vars: string | null
  // 代理与限速
  proxy_enabled: boolean | null
  rate_limit_rps: number | null
  autothrottle_enabled: boolean | null
  // 数据去重
  dedup_enabled: boolean | null
  dedup_fields: string | null
  created_at: string
  updated_at: string
}

export type SpiderCreate = {
  project_id: string
  name: string
  description?: string
  script_content?: string
  cron_expr?: string
  is_active?: boolean
  entry_point?: string
  source?: ProjectSource
  git_repo?: string
}

export type SpiderUpdate = {
  name?: string
  description?: string
  script_content?: string
  cron_expr?: string
  is_active?: boolean
  entry_point?: string
  source?: ProjectSource
  git_repo?: string
  webhook_url?: string
  timeout_seconds?: number | null
  max_items?: number | null
  memory_limit_mb?: number | null
  requirements_txt?: string | null
  env_vars?: string | null
  proxy_enabled?: boolean | null
  rate_limit_rps?: number | null
  autothrottle_enabled?: boolean | null
  dedup_enabled?: boolean | null
  dedup_fields?: string | null
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

// Spider Template
export type SpiderTemplate = {
  name: string
  source: ProjectSource
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
  is_test: boolean
  trigger_type: string
  retry_count: number
  max_retries: number
  // 扩展字段
  error_category: string | null
  last_heartbeat: string | null
  items_per_second: number | null
  peak_memory_mb: number | null
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

// Coder Workspace Types
export type CoderWorkspaceStatus = 'pending' | 'starting' | 'running' | 'stopping' | 'stopped' | 'failed' | 'unknown'
export type CoderAgentStatus = 'connecting' | 'connected' | 'disconnected' | 'timeout'

export type CoderWorkspace = {
  id: string
  name: string
  status: CoderWorkspaceStatus
  url: string | null
  created_at: string | null
}

export type CoderWorkspaceStatusResponse = {
  status: CoderWorkspaceStatus
  agent_status: CoderAgentStatus | null
  url: string | null
  last_used_at: string | null
  build_status: string | null
  build_job: string | null
  is_ready: boolean
  apps_ready: boolean
  code_sync_status: string | null
}

export type FileUploadResult = {
  success: boolean
  files_count: number
  uploaded_files: string[]
  errors?: string[]
}

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
