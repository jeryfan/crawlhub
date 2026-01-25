/**
 * 账单相关类型定义
 */

// 订阅计划
export enum SubscriptionPlan {
  BASIC = 'basic',
  PRO = 'pro',
  MAX = 'max',
}

// 充值订单状态
export enum RechargeOrderStatus {
  PENDING = 'pending',
  PAID = 'paid',
  CANCELLED = 'cancelled',
  EXPIRED = 'expired',
}

// 订阅订单状态
export enum SubscriptionOrderStatus {
  ACTIVE = 'active',
  EXPIRED = 'expired',
  CANCELLED = 'cancelled',
  PENDING = 'pending',
}

// 订阅订单类型
export enum SubscriptionOrderType {
  NEW = 'new',
  RENEW = 'renew',
  UPGRADE = 'upgrade',
  DOWNGRADE = 'downgrade',
}

// 余额变动类型
export enum BalanceLogType {
  RECHARGE = 'recharge',
  SUBSCRIBE = 'subscribe',
  REFUND = 'refund',
  ADMIN_ADJUST = 'admin_adjust',
  UPGRADE_CHARGE = 'upgrade_charge',
}

// 支付方式
export enum PaymentMethod {
  WECHAT = 'wechat',
  ALIPAY = 'alipay',
}

// 订阅计划项（用于管理端）
export type SubscriptionPlanItem = {
  id: string
  name: string
  price_monthly: number
  price_yearly: number
  discount_percent: number
  first_month_discount_percent: number
  first_month_discount_enabled: boolean
  team_members: number
  apps_limit: number
  api_rate_limit: number
  features: Record<string, any> | null
  description: string | null
  sort_order: number
  is_active: boolean
  is_default: boolean
}

// 创建订阅计划
export type SubscriptionPlanCreate = {
  id: string
  name: string
  price_monthly?: number
  price_yearly?: number
  discount_percent?: number
  first_month_discount_percent?: number
  first_month_discount_enabled?: boolean
  team_members?: number
  apps_limit?: number
  api_rate_limit?: number
  features?: Record<string, any> | null
  description?: string | null
  sort_order?: number
  is_active?: boolean
  is_default?: boolean
}

// 更新订阅计划
export type SubscriptionPlanUpdate = {
  name?: string
  price_monthly?: number
  price_yearly?: number
  discount_percent?: number
  first_month_discount_percent?: number
  first_month_discount_enabled?: boolean
  team_members?: number
  apps_limit?: number
  api_rate_limit?: number
  features?: Record<string, any> | null
  description?: string | null
  sort_order?: number
  is_active?: boolean
  is_default?: boolean
}

// 充值订单列表项
export type RechargeOrderItem = {
  id: string
  tenant_id: string
  tenant_name: string
  account_id?: string
  account_name?: string
  amount: number
  payment_method: PaymentMethod
  status: RechargeOrderStatus
  trade_no: string | null
  paid_at: string | null
  created_at: string
}

// 订阅订单列表项
export type SubscriptionOrderItem = {
  id: string
  tenant_id: string
  tenant_name: string
  account_id?: string
  account_name?: string
  plan: SubscriptionPlan
  price: number
  status: SubscriptionOrderStatus
  starts_at: string
  expires_at: string
  is_auto_renew: boolean
  order_type: SubscriptionOrderType
  billing_cycle: 'monthly' | 'yearly' | null
  previous_plan?: string
  created_at: string
}

// 余额变动记录
export type BalanceLogItem = {
  id: string
  tenant_id: string
  tenant_name: string
  type: BalanceLogType
  amount: number
  balance_before: number
  balance_after: number
  remark: string | null
  operator_id: string | null
  account_id?: string
  account_name?: string
  created_at: string
}

// 分页响应
export type PaginatedResponse<T> = {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 账单统计
export type BillingStats = {
  total_recharge_amount: number
  total_subscription_revenue: number
  active_subscriptions: number
  pending_orders: number
}

// 调整余额请求
export type AdjustBalanceRequest = {
  amount: number
  remark?: string
}

// 修改计划请求
export type ModifyPlanRequest = {
  plan: SubscriptionPlan
  expires_at?: string
}
