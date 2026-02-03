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
  project_type: ProjectType
  entry_point: string | null
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
  project_type?: ProjectType
  entry_point?: string
  config?: Record<string, any>
}

export type SpiderUpdate = {
  name?: string
  description?: string
  script_type?: ScriptType
  script_content?: string
  cron_expr?: string
  is_active?: boolean
  project_type?: ProjectType
  entry_point?: string
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

// Project Type
export type ProjectType = 'single_file' | 'multi_file'

// Spider File Types
export type SpiderFile = {
  id: string
  spider_id: string
  file_path: string
  storage_key: string
  file_size: number
  content_type: string
  created_at: string
  updated_at: string
}

export type SpiderFileTreeNode = {
  id: string | null
  name: string
  path: string
  is_dir: boolean
  children: SpiderFileTreeNode[]
  file_size?: number
}

export type SpiderFileContent = {
  id: string
  file_path: string
  content: string
  content_type: string
}

// Code Session Types (deprecated, replaced by Coder Workspace)
export type CodeSessionStatus = 'pending' | 'starting' | 'ready' | 'syncing' | 'stopped' | 'failed'

export type CodeSession = {
  id: string
  spider_id: string
  status: CodeSessionStatus
  url: string | null
  token: string | null
  created_at: string
  expires_at: string
}

export type CodeSessionStatusResponse = {
  id: string
  status: CodeSessionStatus
  last_active_at: string
  expires_at: string
}

export type CodeSessionSyncResult = {
  success: boolean
  files_synced: number
  message: string | null
}

// Coder Workspace Types
export type CoderWorkspaceStatus = 'pending' | 'starting' | 'running' | 'stopping' | 'stopped' | 'failed' | 'unknown'

export type CoderWorkspace = {
  id: string
  name: string
  status: CoderWorkspaceStatus
  url: string | null
  created_at: string | null
}

export type CoderWorkspaceStatusResponse = {
  status: CoderWorkspaceStatus
  url: string | null
  last_used_at: string | null
}

export type FileUploadResult = {
  success: boolean
  files_count: number
  uploaded_files: string[]
  errors?: string[]
}
