import type { AdjustBalanceRequest, ModifyPlanRequest } from '@/types/billing'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  adjustTenantBalance,
  fetchBalanceLogs,
  fetchBillingStats,
  fetchRechargeOrders,
  fetchSubscriptionOrders,
  modifyTenantPlan,
} from './admin-billing'

const NAMESPACE = 'admin-billing'

/**
 * 获取充值订单列表
 */
export const useRechargeOrders = (params: {
  page?: number
  page_size?: number
  tenant_id?: string
  status?: string
}) => {
  return useQuery({
    queryKey: [NAMESPACE, 'recharge-orders', params],
    queryFn: () => fetchRechargeOrders(params),
  })
}

/**
 * 获取订阅订单列表
 */
export const useSubscriptionOrders = (params: {
  page?: number
  page_size?: number
  tenant_id?: string
  status?: string
}) => {
  return useQuery({
    queryKey: [NAMESPACE, 'subscription-orders', params],
    queryFn: () => fetchSubscriptionOrders(params),
  })
}

/**
 * 获取余额变动记录
 */
export const useBalanceLogs = (params: {
  page?: number
  page_size?: number
  tenant_id?: string
  type?: string
}) => {
  return useQuery({
    queryKey: [NAMESPACE, 'balance-logs', params],
    queryFn: () => fetchBalanceLogs(params),
  })
}

/**
 * 调整租户余额
 */
export const useAdjustTenantBalance = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: [NAMESPACE, 'adjust-balance'],
    mutationFn: ({ tenantId, data }: { tenantId: string, data: AdjustBalanceRequest }) =>
      adjustTenantBalance(tenantId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAMESPACE] })
      queryClient.invalidateQueries({ queryKey: ['platform', 'tenants'] })
    },
  })
}

/**
 * 修改租户计划
 */
export const useModifyTenantPlan = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: [NAMESPACE, 'modify-plan'],
    mutationFn: ({ tenantId, data }: { tenantId: string, data: ModifyPlanRequest }) =>
      modifyTenantPlan(tenantId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAMESPACE] })
      queryClient.invalidateQueries({ queryKey: ['platform', 'tenants'] })
    },
  })
}

/**
 * 获取账单统计
 */
export const useBillingStats = () => {
  return useQuery({
    queryKey: [NAMESPACE, 'stats'],
    queryFn: fetchBillingStats,
  })
}
