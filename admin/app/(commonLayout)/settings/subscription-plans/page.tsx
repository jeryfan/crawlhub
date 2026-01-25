'use client'

import type {
  SubscriptionPlanCreate,
  SubscriptionPlanItem,
  SubscriptionPlanUpdate,
} from '@/types/billing'
import {
  RiAddLine,
  RiDeleteBinLine,
  RiEditLine,
  RiPriceTag3Line,
  RiRefreshLine,
  RiStarLine,
} from '@remixicon/react'
import { useCallback, useEffect, useState } from 'react'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import Switch from '@/app/components/base/switch'
import Toast from '@/app/components/base/toast'
import {
  createSubscriptionPlan,
  deleteSubscriptionPlan,
  fetchSubscriptionPlans,
  initDefaultPlans,
  updateSubscriptionPlan,
} from '@/service/admin-billing'
import { cn } from '@/utils/classnames'

const NUM_INFINITE = 0

const formatQuota = (value: number): string => {
  if (value === NUM_INFINITE)
    return '无限制'
  return value.toLocaleString()
}

type PlanFormData = {
  id: string
  name: string
  price_monthly: string
  price_yearly: string
  discount_percent: string
  first_month_discount_percent: string
  first_month_discount_enabled: boolean
  team_members: string
  apps_limit: string
  api_rate_limit: string
  description: string
  sort_order: string
  is_active: boolean
  is_default: boolean
}

const defaultFormData: PlanFormData = {
  id: '',
  name: '',
  price_monthly: '0',
  price_yearly: '0',
  discount_percent: '0',
  first_month_discount_percent: '0',
  first_month_discount_enabled: false,
  team_members: '1',
  apps_limit: '10',
  api_rate_limit: '100',
  description: '',
  sort_order: '0',
  is_active: true,
  is_default: false,
}

const SubscriptionPlansPage = () => {
  const [plans, setPlans] = useState<SubscriptionPlanItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showInactive, setShowInactive] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [editingPlan, setEditingPlan] = useState<SubscriptionPlanItem | null>(
    null,
  )
  const [formData, setFormData] = useState<PlanFormData>(defaultFormData)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [deleteConfirmPlan, setDeleteConfirmPlan]
    = useState<SubscriptionPlanItem | null>(null)

  const loadPlans = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await fetchSubscriptionPlans(showInactive)
      setPlans(data)
    }
    catch (error) {
      Toast.notify({
        type: 'error',
        message: '加载订阅计划失败',
      })
    }
    finally {
      setIsLoading(false)
    }
  }, [showInactive])

  useEffect(() => {
    loadPlans()
  }, [loadPlans])

  const handleInitDefault = async () => {
    try {
      const result = await initDefaultPlans()
      Toast.notify({
        type: 'success',
        message: result.msg || '初始化成功',
      })
      loadPlans()
    }
    catch (error) {
      Toast.notify({
        type: 'error',
        message: '初始化失败',
      })
    }
  }

  const handleOpenModal = (plan?: SubscriptionPlanItem) => {
    if (plan) {
      setEditingPlan(plan)
      // 根据月付和年付价格自动计算折扣
      const originalYearlyPrice = plan.price_monthly * 12
      const calculatedDiscount
        = originalYearlyPrice > 0
          ? Math.round((1 - plan.price_yearly / originalYearlyPrice) * 100)
          : 0
      setFormData({
        id: plan.id,
        name: plan.name,
        price_monthly: String(plan.price_monthly),
        price_yearly: String(plan.price_yearly),
        discount_percent: String(Math.max(0, calculatedDiscount)),
        first_month_discount_percent: String(
          plan.first_month_discount_percent || 0,
        ),
        first_month_discount_enabled:
          plan.first_month_discount_enabled || false,
        team_members: String(plan.team_members),
        apps_limit: String(plan.apps_limit),
        api_rate_limit: String(plan.api_rate_limit),
        description: plan.description || '',
        sort_order: String(plan.sort_order),
        is_active: plan.is_active,
        is_default: plan.is_default,
      })
    }
    else {
      setEditingPlan(null)
      setFormData(defaultFormData)
    }
    setShowModal(true)
  }

  const handleCloseModal = () => {
    setShowModal(false)
    setEditingPlan(null)
    setFormData(defaultFormData)
  }

  const handleSubmit = async () => {
    if (!formData.id.trim() || !formData.name.trim()) {
      Toast.notify({
        type: 'error',
        message: '请填写计划ID和名称',
      })
      return
    }

    setIsSubmitting(true)
    try {
      if (editingPlan) {
        const updateData: SubscriptionPlanUpdate = {
          name: formData.name,
          price_monthly: Number(formData.price_monthly),
          price_yearly: Number(formData.price_yearly),
          discount_percent: Number(formData.discount_percent),
          first_month_discount_percent: Number(
            formData.first_month_discount_percent,
          ),
          first_month_discount_enabled: formData.first_month_discount_enabled,
          team_members: Number(formData.team_members),
          apps_limit: Number(formData.apps_limit),
          api_rate_limit: Number(formData.api_rate_limit),
          description: formData.description || null,
          sort_order: Number(formData.sort_order),
          is_active: formData.is_active,
          is_default: formData.is_default,
        }
        await updateSubscriptionPlan(editingPlan.id, updateData)
        Toast.notify({
          type: 'success',
          message: '更新成功',
        })
      }
      else {
        const createData: SubscriptionPlanCreate = {
          id: formData.id,
          name: formData.name,
          price_monthly: Number(formData.price_monthly),
          price_yearly: Number(formData.price_yearly),
          discount_percent: Number(formData.discount_percent),
          first_month_discount_percent: Number(
            formData.first_month_discount_percent,
          ),
          first_month_discount_enabled: formData.first_month_discount_enabled,
          team_members: Number(formData.team_members),
          apps_limit: Number(formData.apps_limit),
          api_rate_limit: Number(formData.api_rate_limit),
          description: formData.description || null,
          sort_order: Number(formData.sort_order),
          is_active: formData.is_active,
          is_default: formData.is_default,
        }
        await createSubscriptionPlan(createData)
        Toast.notify({
          type: 'success',
          message: '创建成功',
        })
      }
      handleCloseModal()
      loadPlans()
    }
    catch (error: any) {
      Toast.notify({
        type: 'error',
        message: error.message || '操作失败',
      })
    }
    finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (plan: SubscriptionPlanItem) => {
    try {
      await deleteSubscriptionPlan(plan.id)
      Toast.notify({
        type: 'success',
        message: '删除成功',
      })
      setDeleteConfirmPlan(null)
      loadPlans()
    }
    catch (error: any) {
      Toast.notify({
        type: 'error',
        message: error.message || '删除失败',
      })
    }
  }

  return (
    <div className="flex h-full flex-col bg-background-body">
      <div className="flex-1 overflow-auto">
        <div className="mx-auto max-w-4xl px-6 py-8">
          {/* Header */}
          <div className="mb-8">
            <div className="mb-2 flex items-center gap-3">
              <div className="relative">
                <div className="shadow-components-button-primary-bg/25 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-components-button-primary-bg to-util-colors-indigo-indigo-600 shadow-lg">
                  <RiPriceTag3Line className="h-6 w-6 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-xl font-bold text-text-primary">
                  订阅计划管理
                </h1>
                <p className="mt-0.5 text-sm text-text-tertiary">
                  配置系统的订阅等级和配额限制
                </p>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <label className="flex cursor-pointer items-center gap-2 text-sm text-text-secondary">
                <Switch
                  size="md"
                  defaultValue={showInactive}
                  onChange={setShowInactive}
                />
                显示未激活计划
              </label>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                onClick={handleInitDefault}
                className="gap-1"
              >
                <RiRefreshLine className="h-4 w-4" />
                初始化默认计划
              </Button>
              <Button
                variant="primary"
                onClick={() => handleOpenModal()}
                className="gap-1"
              >
                <RiAddLine className="h-4 w-4" />
                新建计划
              </Button>
            </div>
          </div>

          {/* Plans List */}
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div
                  key={i}
                  className="animate-pulse rounded-2xl border border-divider-subtle bg-components-panel-bg p-6"
                >
                  <div className="flex items-center justify-between">
                    <div className="h-6 w-32 rounded bg-divider-regular" />
                    <div className="h-8 w-20 rounded bg-divider-subtle" />
                  </div>
                  <div className="mt-4 grid grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map(j => (
                      <div
                        key={j}
                        className="h-16 rounded-lg bg-divider-subtle"
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : plans.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-divider-regular bg-components-panel-bg p-12 text-center">
              <RiPriceTag3Line className="mx-auto h-12 w-12 text-text-quaternary" />
              <p className="mt-4 text-sm text-text-tertiary">暂无订阅计划</p>
              <p className="mt-1 text-xs text-text-quaternary">
                点击"初始化默认计划"快速创建基础计划
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {plans.map(plan => (
                <div
                  key={plan.id}
                  className={cn(
                    'group rounded-2xl border bg-components-panel-bg p-6 transition-all hover:shadow-md',
                    plan.is_default
                      ? 'border-components-button-primary-bg/50'
                      : plan.is_active
                        ? 'border-divider-subtle hover:border-divider-regular'
                        : 'bg-background-default-dimm border-divider-subtle opacity-60',
                  )}
                >
                  {/* Plan Header */}
                  <div className="mb-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          'flex h-10 w-10 items-center justify-center rounded-xl',
                          plan.is_default
                            ? 'bg-components-button-primary-bg text-white'
                            : 'bg-background-default-burn text-text-tertiary',
                        )}
                      >
                        {plan.is_default
                          ? (
                              <RiStarLine className="h-5 w-5" />
                            )
                          : (
                              <RiPriceTag3Line className="h-5 w-5" />
                            )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-semibold text-text-primary">
                            {plan.name}
                          </h3>
                          <span className="rounded bg-background-default-subtle px-2 py-0.5 font-mono text-xs text-text-tertiary">
                            {plan.id}
                          </span>
                          {plan.is_default && (
                            <span className="bg-components-button-primary-bg/10 rounded-full px-2 py-0.5 text-xs font-medium text-components-button-primary-bg">
                              默认
                            </span>
                          )}
                          {!plan.is_active && (
                            <span className="rounded-full bg-state-warning-hover px-2 py-0.5 text-xs font-medium text-state-warning-solid">
                              未激活
                            </span>
                          )}
                        </div>
                        {plan.description && (
                          <p className="mt-0.5 text-xs text-text-tertiary">
                            {plan.description}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
                      <Button
                        variant="ghost"
                        size="small"
                        onClick={() => handleOpenModal(plan)}
                        className="gap-1"
                      >
                        <RiEditLine className="h-4 w-4" />
                        编辑
                      </Button>
                      <Button
                        variant="ghost"
                        size="small"
                        onClick={() => setDeleteConfirmPlan(plan)}
                        className="gap-1 text-state-destructive-solid hover:bg-state-destructive-hover"
                      >
                        <RiDeleteBinLine className="h-4 w-4" />
                        删除
                      </Button>
                    </div>
                  </div>

                  {/* Plan Details */}
                  <div className="grid grid-cols-6 gap-3">
                    <div className="rounded-xl bg-background-default-subtle p-3">
                      <p className="text-xs text-text-quaternary">月付价格</p>
                      <p className="mt-1 text-lg font-semibold text-text-primary">
                        ¥
                        {plan.price_monthly}
                      </p>
                    </div>
                    <div className="rounded-xl bg-background-default-subtle p-3">
                      <p className="text-xs text-text-quaternary">年付价格</p>
                      <p className="mt-1 text-lg font-semibold text-text-primary">
                        ¥
                        {plan.price_yearly}
                        {plan.discount_percent > 0 && (
                          <span className="ml-1 text-xs font-normal text-state-success-solid">
                            -
                            {plan.discount_percent}
                            %
                          </span>
                        )}
                      </p>
                    </div>
                    <div className="rounded-xl bg-background-default-subtle p-3">
                      <p className="text-xs text-text-quaternary">首月折扣</p>
                      <p className="mt-1 text-lg font-semibold text-text-primary">
                        {plan.first_month_discount_enabled
                          && plan.first_month_discount_percent > 0
                          ? (
                              <span className="text-state-success-solid">
                                -
                                {plan.first_month_discount_percent}
                                %
                              </span>
                            )
                          : (
                              <span className="text-text-quaternary">-</span>
                            )}
                      </p>
                    </div>
                    <div className="rounded-xl bg-background-default-subtle p-3">
                      <p className="text-xs text-text-quaternary">团队成员</p>
                      <p className="mt-1 text-lg font-semibold text-text-primary">
                        {formatQuota(plan.team_members)}
                      </p>
                    </div>
                    <div className="rounded-xl bg-background-default-subtle p-3">
                      <p className="text-xs text-text-quaternary">应用数量</p>
                      <p className="mt-1 text-lg font-semibold text-text-primary">
                        {formatQuota(plan.apps_limit)}
                      </p>
                    </div>
                    <div className="rounded-xl bg-background-default-subtle p-3">
                      <p className="text-xs text-text-quaternary">API 限速</p>
                      <p className="mt-1 text-lg font-semibold text-text-primary">
                        {plan.api_rate_limit === NUM_INFINITE
                          ? '无限制'
                          : `${plan.api_rate_limit}/分`}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create/Edit Modal */}
      <Modal
        isShow={showModal}
        onClose={handleCloseModal}
        className="!w-[560px] !p-0"
      >
        <div className="border-b border-divider-subtle px-6 py-4">
          <h3 className="text-lg font-semibold text-text-primary">
            {editingPlan ? '编辑订阅计划' : '新建订阅计划'}
          </h3>
        </div>
        <div className="max-h-[60vh] overflow-y-auto px-6 py-4">
          <div className="space-y-4">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">
                  计划 ID
                  {' '}
                  <span className="text-state-destructive-solid">*</span>
                </label>
                <Input
                  value={formData.id}
                  onChange={e =>
                    setFormData({ ...formData, id: e.target.value })}
                  placeholder="如: basic, pro, max"
                  disabled={!!editingPlan}
                  className="font-mono"
                />
                <p className="mt-1 text-xs text-text-quaternary">
                  唯一标识符，创建后不可修改
                </p>
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">
                  计划名称
                  {' '}
                  <span className="text-state-destructive-solid">*</span>
                </label>
                <Input
                  value={formData.name}
                  onChange={e =>
                    setFormData({ ...formData, name: e.target.value })}
                  placeholder="如: 基础版, 专业版"
                />
              </div>
            </div>

            {/* Pricing */}
            <div className="rounded-xl border border-divider-subtle p-4">
              <h4 className="mb-3 text-sm font-medium text-text-primary">
                定价设置
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1.5 block text-xs text-text-tertiary">
                    月付价格 (¥)
                  </label>
                  <Input
                    type="number"
                    value={formData.price_monthly}
                    onChange={(e) => {
                      const monthlyPrice = e.target.value
                      const yearlyPrice = Number(formData.price_yearly)
                      const originalYearlyPrice = Number(monthlyPrice) * 12
                      const discount
                        = originalYearlyPrice > 0
                          ? Math.round(
                              (1 - yearlyPrice / originalYearlyPrice) * 100,
                            )
                          : 0
                      setFormData({
                        ...formData,
                        price_monthly: monthlyPrice,
                        discount_percent: String(Math.max(0, discount)),
                      })
                    }}
                    min="0"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs text-text-tertiary">
                    年付价格 (¥)
                  </label>
                  <Input
                    type="number"
                    value={formData.price_yearly}
                    onChange={(e) => {
                      const yearlyPrice = e.target.value
                      const monthlyPrice = Number(formData.price_monthly)
                      const originalYearlyPrice = monthlyPrice * 12
                      const discount
                        = originalYearlyPrice > 0
                          ? Math.round(
                              (1 - Number(yearlyPrice) / originalYearlyPrice)
                              * 100,
                            )
                          : 0
                      setFormData({
                        ...formData,
                        price_yearly: yearlyPrice,
                        discount_percent: String(Math.max(0, discount)),
                      })
                    }}
                    min="0"
                  />
                </div>
              </div>
              {Number(formData.price_monthly) > 0 && (
                <div className="mt-3 rounded-lg bg-background-default-subtle p-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-text-tertiary">
                      年付原价（月付×12）
                    </span>
                    <span className="text-text-secondary">
                      ¥
                      {(Number(formData.price_monthly) * 12).toFixed(0)}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-xs">
                    <span className="text-text-tertiary">年付折扣</span>
                    <span
                      className={cn(
                        'font-medium',
                        Number(formData.discount_percent) > 0
                          ? 'text-state-success-solid'
                          : 'text-text-quaternary',
                      )}
                    >
                      {Number(formData.discount_percent) > 0
                        ? `省 ${formData.discount_percent}%`
                        : '无折扣'}
                    </span>
                  </div>
                  {Number(formData.discount_percent) > 0 && (
                    <div className="mt-1.5 flex items-center justify-between text-xs">
                      <span className="text-text-tertiary">用户节省</span>
                      <span className="font-medium text-state-success-solid">
                        ¥
                        {(
                          Number(formData.price_monthly) * 12
                          - Number(formData.price_yearly)
                        ).toFixed(0)}
                        /年
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* First Month Discount */}
            <div className="rounded-xl border border-divider-subtle p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-text-primary">
                    首月折扣
                  </h4>
                  <p className="mt-0.5 text-xs text-text-quaternary">
                    仅对月付新用户首次订阅生效
                  </p>
                </div>
                <Switch
                  size="md"
                  defaultValue={formData.first_month_discount_enabled}
                  onChange={value =>
                    setFormData({
                      ...formData,
                      first_month_discount_enabled: value,
                    })}
                />
              </div>
              {formData.first_month_discount_enabled && (
                <div className="mt-3">
                  <label className="mb-1.5 block text-xs text-text-tertiary">
                    首月折扣 (%)
                  </label>
                  <Input
                    type="number"
                    value={formData.first_month_discount_percent}
                    onChange={e =>
                      setFormData({
                        ...formData,
                        first_month_discount_percent: e.target.value,
                      })}
                    min="0"
                    max="100"
                    placeholder="如：20 表示首月 8 折"
                  />
                  {Number(formData.first_month_discount_percent) > 0
                    && Number(formData.price_monthly) > 0 && (
                    <p className="mt-2 text-xs text-state-success-solid">
                      首月价格：¥
                      {(
                        Number(formData.price_monthly)
                        * (1
                          - Number(formData.first_month_discount_percent) / 100)
                      ).toFixed(2)}
                      （原价 ¥
                      {formData.price_monthly}
                      ）
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Quotas */}
            <div className="rounded-xl border border-divider-subtle p-4">
              <h4 className="mb-3 text-sm font-medium text-text-primary">
                配额限制
              </h4>
              <p className="mb-3 text-xs text-text-quaternary">
                设置为 0 表示无限制
              </p>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="mb-1.5 block text-xs text-text-tertiary">
                    团队成员
                  </label>
                  <Input
                    type="number"
                    value={formData.team_members}
                    onChange={e =>
                      setFormData({ ...formData, team_members: e.target.value })}
                    min="0"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs text-text-tertiary">
                    应用数量
                  </label>
                  <Input
                    type="number"
                    value={formData.apps_limit}
                    onChange={e =>
                      setFormData({ ...formData, apps_limit: e.target.value })}
                    min="0"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs text-text-tertiary">
                    API 限速 (次/分)
                  </label>
                  <Input
                    type="number"
                    value={formData.api_rate_limit}
                    onChange={e =>
                      setFormData({
                        ...formData,
                        api_rate_limit: e.target.value,
                      })}
                    min="0"
                  />
                </div>
              </div>
            </div>

            {/* Other Settings */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">
                  描述
                </label>
                <Input
                  value={formData.description}
                  onChange={e =>
                    setFormData({ ...formData, description: e.target.value })}
                  placeholder="计划描述（可选）"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">
                  排序
                </label>
                <Input
                  type="number"
                  value={formData.sort_order}
                  onChange={e =>
                    setFormData({ ...formData, sort_order: e.target.value })}
                  min="0"
                />
              </div>
            </div>

            {/* Switches */}
            <div className="flex items-center gap-6">
              <label className="flex cursor-pointer items-center gap-2 text-sm text-text-secondary">
                <Switch
                  size="md"
                  defaultValue={formData.is_active}
                  onChange={value =>
                    setFormData({ ...formData, is_active: value })}
                />
                激活状态
              </label>
              <label className="flex cursor-pointer items-center gap-2 text-sm text-text-secondary">
                <Switch
                  size="md"
                  defaultValue={formData.is_default}
                  onChange={value =>
                    setFormData({ ...formData, is_default: value })}
                />
                设为默认计划
              </label>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-3 border-t border-divider-subtle px-6 py-4">
          <Button variant="secondary" onClick={handleCloseModal}>
            取消
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            loading={isSubmitting}
            disabled={!formData.id.trim() || !formData.name.trim()}
          >
            {editingPlan ? '保存' : '创建'}
          </Button>
        </div>
      </Modal>

      {/* Delete Confirm Modal */}
      <Modal
        isShow={!!deleteConfirmPlan}
        onClose={() => setDeleteConfirmPlan(null)}
        className="!w-[400px] !p-6"
      >
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-state-destructive-hover">
          <RiDeleteBinLine className="h-6 w-6 text-state-destructive-solid" />
        </div>
        <h3 className="mb-2 text-lg font-semibold text-text-primary">
          确认删除
        </h3>
        <p className="mb-6 text-sm text-text-tertiary">
          确定要删除订阅计划
          {' '}
          <span className="font-medium text-text-secondary">
            {deleteConfirmPlan?.name}
          </span>
          {' '}
          吗？ 此操作不可撤销。
        </p>
        <div className="flex items-center justify-end gap-3">
          <Button
            variant="secondary"
            onClick={() => setDeleteConfirmPlan(null)}
          >
            取消
          </Button>
          <Button
            variant="warning"
            onClick={() => deleteConfirmPlan && handleDelete(deleteConfirmPlan)}
          >
            确认删除
          </Button>
        </div>
      </Modal>
    </div>
  )
}

export default SubscriptionPlansPage
