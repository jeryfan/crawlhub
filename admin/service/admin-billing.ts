import type {
  AdjustBalanceRequest,
  BalanceLogItem,
  BillingStats,
  ModifyPlanRequest,
  PaginatedResponse,
  RechargeOrderItem,
  SubscriptionOrderItem,
  SubscriptionPlanCreate,
  SubscriptionPlanItem,
  SubscriptionPlanUpdate,
} from '@/types/billing'
import { del, get, patch, post, put } from './base'

/**
 * 获取充值订单列表
 */
export const fetchRechargeOrders = (params: {
  page?: number
  page_size?: number
  tenant_id?: string
  status?: string
}) => {
  return get<PaginatedResponse<RechargeOrderItem>>('/recharge-orders', { params })
}

/**
 * 获取订阅订单列表
 */
export const fetchSubscriptionOrders = (params: {
  page?: number
  page_size?: number
  tenant_id?: string
  status?: string
}) => {
  return get<PaginatedResponse<SubscriptionOrderItem>>('/subscription-orders', { params })
}

/**
 * 获取余额变动记录
 */
export const fetchBalanceLogs = (params: {
  page?: number
  page_size?: number
  tenant_id?: string
  type?: string
}) => {
  return get<PaginatedResponse<BalanceLogItem>>('/balance-logs', { params })
}

/**
 * 调整租户余额
 */
export const adjustTenantBalance = (tenantId: string, data: AdjustBalanceRequest) => {
  return patch<{ balance: number }>(`/tenants/${tenantId}/balance`, { body: data })
}

/**
 * 修改租户计划
 */
export const modifyTenantPlan = (tenantId: string, data: ModifyPlanRequest) => {
  return patch<{ plan: string, plan_expires_at: string | null }>(`/tenants/${tenantId}/plan`, { body: data })
}

/**
 * 获取账单统计
 */
export const fetchBillingStats = () => {
  return get<BillingStats>('/billing/stats')
}

// ============ 订阅计划管理 ============

/**
 * 获取所有订阅计划
 */
export const fetchSubscriptionPlans = (includeInactive = false) => {
  return get<SubscriptionPlanItem[]>('/subscription-plans', {
    params: { include_inactive: includeInactive },
  })
}

/**
 * 获取单个订阅计划
 */
export const fetchSubscriptionPlan = (planId: string) => {
  return get<SubscriptionPlanItem>(`/subscription-plans/${planId}`)
}

/**
 * 创建订阅计划
 */
export const createSubscriptionPlan = (data: SubscriptionPlanCreate) => {
  return post<SubscriptionPlanItem>('/subscription-plans', { body: data })
}

/**
 * 更新订阅计划
 */
export const updateSubscriptionPlan = (planId: string, data: SubscriptionPlanUpdate) => {
  return put<SubscriptionPlanItem>(`/subscription-plans/${planId}`, { body: data })
}

/**
 * 删除订阅计划
 */
export const deleteSubscriptionPlan = (planId: string) => {
  return del<{ msg: string }>(`/subscription-plans/${planId}`)
}

/**
 * 初始化默认订阅计划
 */
export const initDefaultPlans = () => {
  return post<{ msg: string }>('/subscription-plans/init-default')
}
