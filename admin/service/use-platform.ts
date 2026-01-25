/**
 * Platform 管理后台 API 服务
 */

import type { SubscriptionPlanItem } from '@/types/billing'
import type {
  AccountCreate,
  AccountDetail,
  AccountListItem,
  AccountsQueryParams,
  AccountTenant,
  AccountUpdate,
  AdminCreate,
  AdminDetail,
  AdminListItem,
  AdminsQueryParams,
  AdminUpdate,
  DashboardStats,
  DashboardTrends,
  GeneralSettingsConfig,
  GeneralSettingsConfigUpdate,
  GeneralSettingsTarget,
  InvitationCodeCreate,
  InvitationCodeListItem,
  InvitationCodesQueryParams,
  InvitationCodeStats,
  PaginatedResponse,
  RecentAccount,
  RecentTenant,
  SystemInfo,
  TenantCreate,
  TenantDetail,
  TenantListItem,
  TenantMember,
  TenantsQueryParams,
  TenantUpdate,
} from '@/types/platform'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { del, get, patch, post, put } from './base'

const NAME_SPACE = 'platform'

// ============ Dashboard API ============
export const useDashboardStats = () => {
  return useQuery({
    queryKey: [NAME_SPACE, 'dashboard', 'stats'],
    queryFn: () => get<DashboardStats>('/dashboard/stats'),
    select: data => data,
  })
}

export const useDashboardTrends = (days: number = 30) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'dashboard', 'trends', days],
    queryFn: () => get<DashboardTrends>('/dashboard/trends', { params: { days } }),
    select: data => data,
  })
}

export const useRecentAccounts = (limit: number = 10) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'dashboard', 'recent-accounts', limit],
    queryFn: () => get<RecentAccount[]>('/dashboard/recent-accounts', { params: { limit } }),
    select: data => data,
  })
}

export const useRecentTenants = (limit: number = 10) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'dashboard', 'recent-tenants', limit],
    queryFn: () => get<RecentTenant[]>('/dashboard/recent-tenants', { params: { limit } }),
    select: data => data,
  })
}

export const useSystemInfo = () => {
  return useQuery({
    queryKey: [NAME_SPACE, 'dashboard', 'system-info'],
    queryFn: () => get<SystemInfo>('/dashboard/system-info'),
    select: data => data,
  })
}

// ============ Accounts API ============
export const useAccounts = (params?: AccountsQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'accounts', params],
    queryFn: () => get<PaginatedResponse<AccountListItem>>('/accounts', { params }),
    select: data => data,
  })
}

export const useAccount = (accountId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'accounts', accountId],
    queryFn: () => get<AccountDetail>(`/accounts/${accountId}`),
    select: data => data,
    enabled: !!accountId,
  })
}

export const useAccountTenants = (accountId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'accounts', accountId, 'tenants'],
    queryFn: () => get<AccountTenant[]>(`/accounts/${accountId}/tenants`),
    select: data => data,
    enabled: !!accountId,
  })
}

export const useAccountOwnedTenants = (accountId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'accounts', accountId, 'owned-tenants'],
    queryFn: () => get<{ id: string, name: string, member_count: number, created_at: string }[]>(`/accounts/${accountId}/owned-tenants`),
    select: data => data,
    enabled: !!accountId,
  })
}

export const useCreateAccount = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AccountCreate) => post<AccountDetail>('/accounts', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'accounts'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'dashboard'] })
    },
  })
}

export const useUpdateAccount = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string, data: AccountUpdate }) =>
      put<AccountDetail>(`/accounts/${id}`, { body: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'accounts'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'accounts', variables.id] })
    },
  })
}

export const useUpdateAccountStatus = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) =>
      patch<AccountDetail>(`/accounts/${id}/status`, { body: { status } }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'accounts'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'accounts', variables.id] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'dashboard'] })
    },
  })
}

export const useDeleteAccount = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, deleteOwnedTenants = false }: { id: string, deleteOwnedTenants?: boolean }) =>
      del(`/accounts/${id}?delete_owned_tenants=${deleteOwnedTenants}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'accounts'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'dashboard'] })
    },
  })
}

export const useUpdateAccountPassword = () => {
  return useMutation({
    mutationFn: ({ id, password }: { id: string, password: string }) =>
      patch(`/accounts/${id}/password`, { body: { password } }),
  })
}

// ============ Admins API ============
export const useAdmins = (params?: AdminsQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'admins', params],
    queryFn: () => get<PaginatedResponse<AdminListItem>>('/admins', { params }),
    select: data => data,
  })
}

export const useAdmin = (adminId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'admins', adminId],
    queryFn: () => get<AdminDetail>(`/admins/${adminId}`),
    select: data => data,
    enabled: !!adminId,
  })
}

export const useCreateAdmin = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AdminCreate) => post<AdminDetail>('/admins', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'admins'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'dashboard'] })
    },
  })
}

export const useUpdateAdmin = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string, data: AdminUpdate }) =>
      put<AdminDetail>(`/admins/${id}`, { body: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'admins'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'admins', variables.id] })
    },
  })
}

export const useUpdateAdminPassword = () => {
  return useMutation({
    mutationFn: ({ id, password }: { id: string, password: string }) =>
      patch(`/admins/${id}/password`, { body: { password } }),
  })
}

export const useUpdateAdminStatus = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) =>
      patch<AdminDetail>(`/admins/${id}/status?status=${status}`, {}),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'admins'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'admins', variables.id] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'dashboard'] })
    },
  })
}

export const useDeleteAdmin = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => del(`/admins/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'admins'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'dashboard'] })
    },
  })
}

// ============ Tenants API ============
export const useTenants = (params?: TenantsQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'tenants', params],
    queryFn: () => get<PaginatedResponse<TenantListItem>>('/tenants', { params }),
    select: data => data,
  })
}

export const useTenant = (tenantId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'tenants', tenantId],
    queryFn: () => get<TenantDetail>(`/tenants/${tenantId}`),
    select: data => data,
    enabled: !!tenantId,
  })
}

export const useTenantMembers = (tenantId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'tenants', tenantId, 'members'],
    queryFn: () => get<TenantMember[]>(`/tenants/${tenantId}/members`),
    select: data => data,
    enabled: !!tenantId,
  })
}

export const useCreateTenant = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: TenantCreate) => post<TenantDetail>('/tenants', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'dashboard'] })
    },
  })
}

export const useUpdateTenant = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string, data: TenantUpdate }) =>
      put<TenantDetail>(`/tenants/${id}`, { body: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants', variables.id] })
    },
  })
}

export const useUpdateTenantStatus = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) =>
      patch<TenantDetail>(`/tenants/${id}/status?status=${status}`, {}),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants', variables.id] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'dashboard'] })
    },
  })
}

export const useDeleteTenant = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, deleteOrphanUsers = false }: { id: string, deleteOrphanUsers?: boolean }) =>
      del(`/tenants/${id}?delete_orphan_users=${deleteOrphanUsers}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'accounts'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'dashboard'] })
    },
  })
}

export type TenantDeletionImpact = {
  tenant_id: string
  tenant_name: string
  member_count: number
  owner: { id: string, name: string, email: string } | null
  orphan_users: { id: string, name: string, email: string, role: string }[]
  orphan_user_count: number
}

export const useTenantDeletionImpact = (tenantId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'tenants', tenantId, 'deletion-impact'],
    queryFn: () => get<TenantDeletionImpact>(`/tenants/${tenantId}/deletion-impact`),
    select: data => data,
    enabled: !!tenantId,
  })
}

export const useAddTenantMember = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, accountId, role }: { tenantId: string, accountId: string, role: string }) =>
      post<TenantMember>(`/tenants/${tenantId}/members?account_id=${accountId}&role=${role}`, {}),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants', variables.tenantId, 'members'] })
    },
  })
}

export type SearchUserItem = {
  id: string
  name: string
  email: string
  avatar_url: string | null
  is_member: boolean
}

export type SearchUsersResponse = {
  items: SearchUserItem[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export const useSearchUsersForTenant = (tenantId: string, keyword: string, page: number = 1) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'tenants', tenantId, 'search-users', keyword, page],
    queryFn: () => get<SearchUsersResponse>(`/tenants/${tenantId}/search-users`, { params: { keyword, page } }),
    select: data => data,
    enabled: !!tenantId && !!keyword && keyword.length >= 1,
  })
}

export const useBatchAddTenantMembers = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, accountIds, role }: { tenantId: string, accountIds: string[], role: string }) =>
      post<{ added: number, skipped: number, invalid: number }>(`/tenants/${tenantId}/members/batch`, {
        body: { account_ids: accountIds, role },
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants', variables.tenantId, 'members'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants'] })
    },
  })
}

export const useUpdateTenantMemberRole = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, memberId, role }: { tenantId: string, memberId: string, role: string }) =>
      patch<TenantMember>(`/tenants/${tenantId}/members/${memberId}?role=${role}`, {}),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants', variables.tenantId, 'members'] })
    },
  })
}

export const useRemoveTenantMember = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, memberId }: { tenantId: string, memberId: string }) =>
      del(`/tenants/${tenantId}/members/${memberId}`),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants', variables.tenantId, 'members'] })
    },
  })
}

export const useTransferTenantOwnership = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, newOwnerId }: { tenantId: string, newOwnerId: string }) =>
      post(`/tenants/${tenantId}/transfer-ownership?new_owner_id=${newOwnerId}`, {}),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants', variables.tenantId] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tenants', variables.tenantId, 'members'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'accounts'] })
    },
  })
}

// ============ Invitation Codes API ============
export const useInvitationCodes = (params?: InvitationCodesQueryParams) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'invitation-codes', params],
    queryFn: () => get<PaginatedResponse<InvitationCodeListItem>>('/invitation-codes', { params }),
    select: data => data,
  })
}

export const useInvitationCode = (codeId: string) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'invitation-codes', codeId],
    queryFn: () => get<InvitationCodeListItem>(`/invitation-codes/${codeId}`),
    select: data => data,
    enabled: !!codeId,
  })
}

export const useInvitationCodeStats = () => {
  return useQuery({
    queryKey: [NAME_SPACE, 'invitation-codes', 'stats'],
    queryFn: () => get<InvitationCodeStats>('/invitation-codes/stats/summary'),
    select: data => data,
  })
}

export const useInvitationCodeBatches = () => {
  return useQuery({
    queryKey: [NAME_SPACE, 'invitation-codes', 'batches'],
    queryFn: () => get<string[]>('/invitation-codes/batches'),
    select: data => data,
  })
}

export const useCreateInvitationCodes = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: InvitationCodeCreate) =>
      post<InvitationCodeListItem[]>('/invitation-codes', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'invitation-codes'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'dashboard'] })
    },
  })
}

export const useDeprecateInvitationCodes = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) => post('/invitation-codes/deprecate', { body: { ids } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'invitation-codes'] })
    },
  })
}

export const useDeleteInvitationCode = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => del(`/invitation-codes/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'invitation-codes'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'dashboard'] })
    },
  })
}

// ============ Settings API ============
export const useGeneralSettings = (target: GeneralSettingsTarget = 'web') => {
  return useQuery({
    queryKey: [NAME_SPACE, 'settings', 'general', target],
    queryFn: () => get<GeneralSettingsConfig>(`/settings/general/${target}`),
    select: data => data,
  })
}

export const useUpdateGeneralSettings = (target: GeneralSettingsTarget = 'web') => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: GeneralSettingsConfigUpdate) =>
      put<GeneralSettingsConfig>(`/settings/general/${target}`, { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'settings', 'general', target] })
    },
  })
}

// ============ Subscription Plans API ============
export const useSubscriptionPlans = (includeInactive = false) => {
  return useQuery({
    queryKey: [NAME_SPACE, 'subscription-plans', { includeInactive }],
    queryFn: () => get<SubscriptionPlanItem[]>('/subscription-plans', {
      params: { include_inactive: includeInactive },
    }),
    select: data => data,
  })
}

// 兼容旧 API（deprecated）
/** @deprecated 使用 useGeneralSettings */
export const useBrandingConfig = useGeneralSettings
/** @deprecated 使用 useUpdateGeneralSettings */
export const useUpdateBrandingConfig = useUpdateGeneralSettings
