/**
 * Platform 管理后台类型定义
 */

// ============ 通用类型 ============
export type PaginatedResponse<T> = {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type ApiResponse<T = unknown> = {
  code: number
  msg: string
  data: T
}

// ============ 用户管理类型 ============
export type AccountListItem = {
  id: string
  name: string
  email: string
  avatar: string | null
  avatar_url: string | null
  status: string
  last_login_at: string | null
  last_login_ip: string | null
  created_at: string
}

export type AccountDetail = {
  interface_language: string | null
  timezone: string | null
  last_active_at: string | null
  initialized_at: string | null
  updated_at: string | null
} & AccountListItem

export type AccountCreate = {
  name: string
  email: string
  password?: string
  status?: string
  tenant_id?: string
  role?: string
  avatar?: string
}

export type AccountUpdate = {
  name?: string
  email?: string
  status?: string
  avatar?: string
  interface_language?: string
  timezone?: string
}

export type AccountTenant = {
  id: string
  name: string
  role: string
  current: boolean
  joined_at: string | null
  member_id: string
}

// ============ 管理员管理类型 ============
export type AdminListItem = {
  id: string
  name: string
  email: string
  avatar: string | null
  avatar_url: string | null
  status: string
  last_login_at: string | null
  last_login_ip: string | null
  created_at: string
}

export type AdminDetail = {
  timezone: string | null
  last_active_at: string | null
  initialized_at: string | null
  updated_at: string | null
} & AdminListItem

export type AdminCreate = {
  name: string
  email: string
  password: string
}

export type AdminUpdate = {
  name?: string
  email?: string
  status?: string
  avatar?: string
  timezone?: string
}

// ============ 租户管理类型 ============
export type TenantListItem = {
  id: string
  name: string
  plan: string
  status: string
  created_at: string
  member_count: number
}

export type TenantDetail = {
  encrypt_public_key: string | null
  custom_config: Record<string, unknown> | null
  updated_at: string | null
} & TenantListItem

export type TenantCreate = {
  name: string
  plan?: string
}

export type TenantUpdate = {
  name?: string
  plan?: string
  status?: string
  custom_config?: Record<string, unknown>
}

export type TenantMember = {
  id: string
  account_id: string
  account_name: string
  account_email: string
  role: string
  created_at: string
}

// ============ 邀请码管理类型 ============
export type InvitationCodeListItem = {
  id: string
  batch: string
  code: string
  status: string
  used_at: string | null
  used_by_tenant_id: string | null
  used_by_account_id: string | null
  created_at: string
}

export type InvitationCodeCreate = {
  batch: string
  count: number
}

export type InvitationCodeStats = {
  total: number
  unused: number
  used: number
  deprecated: number
  by_batch: Array<{ batch: string, count: number }>
}

// ============ Dashboard 类型 ============
export type DashboardStats = {
  total_accounts: number
  active_accounts: number
  new_accounts_today: number
  new_accounts_week: number
  total_admins: number
  active_admins: number
  total_tenants: number
  active_tenants: number
  total_invitation_codes: number
  used_invitation_codes: number
}

export type DashboardTrend = {
  date: string
  count: number
}

export type DashboardTrends = {
  account_trends: DashboardTrend[]
  tenant_trends: DashboardTrend[]
}

export type RecentAccount = {
  id: string
  name: string
  email: string
  status: string
  created_at: string
}

export type RecentTenant = {
  id: string
  name: string
  plan: string
  status: string
  created_at: string
}

export type SystemInfo = {
  python_version: string
  debug_mode: boolean
  database_type: string
}

// ============ 查询参数类型 ============
export type PaginationParams = {
  page?: number
  page_size?: number
  keyword?: string
}

export type AccountsQueryParams = {
  status?: string
} & PaginationParams

export type AdminsQueryParams = {
  status?: string
} & PaginationParams

export type TenantsQueryParams = {
  status?: string
  plan?: string
} & PaginationParams

export type InvitationCodesQueryParams = {
  batch?: string
  status?: string
} & PaginationParams

// ============ 系统设置类型 ============
export type GeneralSettingsTarget = 'web' | 'admin'

// 品牌配置
export type BrandingSettings = {
  enabled: boolean
  application_title: string
  login_page_logo: string
  workspace_logo: string
  favicon: string
  theme_color: string
}

export type BrandingSettingsUpdate = {
  enabled?: boolean
  application_title?: string
  login_page_logo?: string
  workspace_logo?: string
  favicon?: string
  theme_color?: string
}

// OAuth 提供商配置
export type OAuthProviderSettings = {
  enabled: boolean
  client_id: string
  client_secret: string
}

export type OAuthProviderSettingsUpdate = {
  enabled?: boolean
  client_id?: string
  client_secret?: string
}

// 微信登录配置
export type WechatOAuthSettings = {
  enabled: boolean
  app_id: string
  app_secret: string
}

export type WechatOAuthSettingsUpdate = {
  enabled?: boolean
  app_id?: string
  app_secret?: string
}

// 认证配置（仅 web 端）
export type AuthSettings = {
  enable_login: boolean
  enable_register: boolean
  enable_email_code_login: boolean
  github: OAuthProviderSettings
  google: OAuthProviderSettings
  wechat: WechatOAuthSettings
}

export type AuthSettingsUpdate = {
  enable_login?: boolean
  enable_register?: boolean
  enable_email_code_login?: boolean
  github?: OAuthProviderSettingsUpdate
  google?: OAuthProviderSettingsUpdate
  wechat?: WechatOAuthSettingsUpdate
}

// 基础配置（完整）
export type GeneralSettingsConfig = {
  branding: BrandingSettings
  auth: AuthSettings
}

export type GeneralSettingsConfigUpdate = {
  branding?: BrandingSettingsUpdate
  auth?: AuthSettingsUpdate
}

// 兼容旧类型
export type BrandingTarget = GeneralSettingsTarget
export type BrandingConfig = BrandingSettings
export type BrandingConfigUpdate = BrandingSettingsUpdate
