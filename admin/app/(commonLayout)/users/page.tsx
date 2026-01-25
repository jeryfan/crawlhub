'use client'

import type { ColumnDef, RowSelectionState, SortingState } from '@/app/components/base/table'
import type { AccountCreate, AccountListItem, AccountTenant, AccountUpdate } from '@/types/platform'
import {
  RiAddLine,
  RiCloseLine,
  RiDeleteBinLine,
  RiEditLine,
  RiEyeLine,
  RiLockPasswordLine,
} from '@remixicon/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import AvatarEdit from '@/app/components/base/avatar-edit'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import { PortalSelect, SimpleSelect } from '@/app/components/base/select'
import Skeleton from '@/app/components/base/skeleton'
import StatusBadge from '@/app/components/base/status-badge'
import {
  AvatarCell,

  createActionColumn,
  DataTable,

  DataTableToolbar,
} from '@/app/components/base/table'
import Toast from '@/app/components/base/toast'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useAccount,
  useAccountOwnedTenants,
  useAccounts,
  useAccountTenants,
  useAddTenantMember,
  useCreateAccount,
  useDeleteAccount,
  useRemoveTenantMember,
  useTenantMembers,
  useTenants,
  useTransferTenantOwnership,
  useUpdateAccount,
  useUpdateAccountPassword,
  useUpdateTenantMemberRole,
} from '@/service/use-platform'
import { encryptPassword } from '@/utils/encryption'

const statusOptions = [
  { value: 'active', name: '活跃' },
  { value: 'pending', name: '待激活' },
  { value: 'banned', name: '禁用' },
  { value: 'uninitialized', name: '未初始化' },
  { value: 'closed', name: '已关闭' },
]

const roleOptions = [
  { value: 'admin', name: '管理员' },
  { value: 'editor', name: '编辑' },
  { value: 'normal', name: '普通成员' },
]

const tenantRoleOptions = [
  { value: 'owner', name: '所有者' },
  { value: 'admin', name: '管理员' },
  { value: 'editor', name: '编辑' },
  { value: 'normal', name: '普通成员' },
]

// 用户表单弹窗
type UserFormModalProps = {
  isOpen: boolean
  onClose: () => void
  userId?: string | null
  onSubmit: (data: AccountCreate | AccountUpdate) => void
  isLoading: boolean
}

const UserFormModal = ({ isOpen, onClose, userId, onSubmit, isLoading }: UserFormModalProps) => {
  const [formData, setFormData] = useState<AccountCreate & { avatar_url?: string | null }>({
    name: '',
    email: '',
    password: '',
    status: 'active',
    tenant_id: '',
    role: '',
    avatar: '',
    avatar_url: null,
  })

  const { data: userDetail, isLoading: isLoadingDetail } = useAccount(userId || '')
  const { data: tenantsData, refetch: refetchTenants } = useTenants({ page: 1, page_size: 100 })

  useEffect(() => {
    if (isOpen) {
      refetchTenants()
      if (userDetail) {
        setFormData({
          name: userDetail.name,
          email: userDetail.email,
          password: '',
          status: userDetail.status,
          tenant_id: '',
          role: '',
          avatar: userDetail.avatar || '',
          avatar_url: userDetail.avatar_url,
        })
      }
      else if (!userId) {
        setFormData({
          name: '',
          email: '',
          password: '',
          status: 'active',
          tenant_id: '',
          role: '',
          avatar: '',
          avatar_url: null,
        })
      }
    }
  }, [isOpen, userDetail, userId, refetchTenants])

  const tenantOptions = [
    { value: '', name: '不选择（自动创建新工作区）' },
    ...(tenantsData?.items.map(tenant => ({ value: tenant.id, name: tenant.name })) || []),
  ]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const submitData = userId
      ? { name: formData.name, email: formData.email, status: formData.status, avatar: formData.avatar || undefined }
      : { ...formData, avatar: formData.avatar || undefined }
    // 移除 avatar_url，只提交 avatar
    const { avatar_url, ...dataToSubmit } = submitData as typeof submitData & { avatar_url?: string | null }
    onSubmit(dataToSubmit)
  }

  const handleTenantChange = (tenantId: string) => {
    setFormData({
      ...formData,
      tenant_id: tenantId,
      role: tenantId ? (formData.role || 'normal') : '',
    })
  }

  const isEditMode = !!userId

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-md">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            {isEditMode ? '编辑用户' : '创建用户'}
          </h3>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>

        {isEditMode && isLoadingDetail
          ? (
              <div className="space-y-4">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="ml-auto h-10 w-32" />
              </div>
            )
          : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">头像</label>
                  <AvatarEdit
                    name={formData.name || ' '}
                    avatar={formData.avatar_url}
                    size={64}
                    onChange={(fileId) => {
                      setFormData({ ...formData, avatar: fileId || '', avatar_url: fileId ? undefined : null })
                    }}
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">用户名</label>
                  <Input
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="请输入用户名"
                    required
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">邮箱</label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                    placeholder="请输入邮箱"
                    required
                  />
                </div>

                {!isEditMode && (
                  <>
                    <div>
                      <label className="mb-1.5 block text-sm text-text-secondary">密码</label>
                      <Input
                        type="password"
                        value={formData.password || ''}
                        onChange={e => setFormData({ ...formData, password: e.target.value })}
                        placeholder="请输入密码（至少8位）"
                      />
                    </div>

                    <div>
                      <label className="mb-1.5 block text-sm text-text-secondary">工作区（租户）</label>
                      <SimpleSelect
                        className="w-full"
                        value={formData.tenant_id}
                        items={tenantOptions}
                        onSelect={item => handleTenantChange(item.value as string)}
                      />
                      <p className="mt-1 text-xs text-text-tertiary">
                        如果不选择工作区，系统将为该用户创建一个新的默认工作区。
                      </p>
                    </div>

                    {formData.tenant_id && (
                      <div>
                        <label className="mb-1.5 block text-sm text-text-secondary">角色</label>
                        <SimpleSelect
                          className="w-full"
                          value={formData.role || 'normal'}
                          items={roleOptions}
                          onSelect={item => setFormData({ ...formData, role: item.value as string })}
                        />
                        <p className="mt-1 text-xs text-text-tertiary">
                          用户在所选工作区中的角色权限。
                        </p>
                      </div>
                    )}
                  </>
                )}

                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">状态</label>
                  <SimpleSelect
                    className="w-full"
                    value={formData.status}
                    items={statusOptions}
                    onSelect={item => setFormData({ ...formData, status: item.value as string })}
                  />
                </div>

                <div className="flex justify-end gap-3 pt-4">
                  <Button variant="secondary" onClick={onClose}>取消</Button>
                  <Button variant="primary" type="submit" loading={isLoading}>
                    {isEditMode ? '保存' : '创建'}
                  </Button>
                </div>
              </form>
            )}
      </div>
    </Modal>
  )
}

// 用户详情弹窗
type UserDetailModalProps = {
  isOpen: boolean
  onClose: () => void
  user: AccountListItem | null
}

const UserDetailModal = ({ isOpen, onClose, user }: UserDetailModalProps) => {
  const [showAddTenantModal, setShowAddTenantModal] = useState(false)
  const [selectedTenantId, setSelectedTenantId] = useState('')
  const [selectedRole, setSelectedRole] = useState('normal')
  const [removingTenantId, setRemovingTenantId] = useState<string | null>(null)
  const { formatDateTime } = useTimestamp()

  const { data: userTenants, isLoading: tenantsLoading, refetch: refetchUserTenants } = useAccountTenants(user?.id || '')
  const { data: allTenants } = useTenants({ page: 1, page_size: 100 })

  const addMemberMutation = useAddTenantMember()
  const updateRoleMutation = useUpdateTenantMemberRole()
  const removeMemberMutation = useRemoveTenantMember()

  const availableTenants = useMemo(() => {
    if (!allTenants?.items || !userTenants)
      return []
    const joinedTenantIds = new Set(userTenants.map(t => t.id))
    return allTenants.items.filter(t => !joinedTenantIds.has(t.id))
  }, [allTenants, userTenants])

  const handleAddToTenant = async () => {
    if (!user || !selectedTenantId)
      return
    try {
      await addMemberMutation.mutateAsync({
        tenantId: selectedTenantId,
        accountId: user.id,
        role: selectedRole,
      })
      Toast.notify({ type: 'success', message: '已添加到工作区' })
      setShowAddTenantModal(false)
      setSelectedTenantId('')
      setSelectedRole('normal')
      refetchUserTenants()
    }
    catch {
      Toast.notify({ type: 'error', message: '添加失败' })
    }
  }

  const handleRoleChange = async (tenant: AccountTenant, newRole: string) => {
    if (!user)
      return
    try {
      await updateRoleMutation.mutateAsync({
        tenantId: tenant.id,
        memberId: tenant.member_id,
        role: newRole,
      })
      Toast.notify({ type: 'success', message: '角色已更新' })
      refetchUserTenants()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handleRemoveFromTenant = async () => {
    if (!user || !removingTenantId)
      return
    const tenant = userTenants?.find(t => t.id === removingTenantId)
    if (!tenant)
      return
    try {
      await removeMemberMutation.mutateAsync({
        tenantId: removingTenantId,
        memberId: tenant.member_id,
      })
      Toast.notify({ type: 'success', message: '已从工作区移除' })
      setRemovingTenantId(null)
      refetchUserTenants()
    }
    catch {
      Toast.notify({ type: 'error', message: '移除失败' })
    }
  }

  if (!user)
    return null

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-lg">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">用户详情</h3>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="bg-components-avatar-bg flex h-16 w-16 items-center justify-center rounded-full text-xl font-semibold text-text-primary">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-lg font-medium text-text-primary">{user.name}</p>
              <p className="text-text-tertiary">{user.email}</p>
            </div>
          </div>

          <div className="space-y-3 border-t border-divider-subtle pt-4">
            <div className="flex justify-between">
              <span className="text-text-tertiary">状态</span>
              <StatusBadge status={user.status} type="user" />
            </div>
            <div className="flex justify-between">
              <span className="text-text-tertiary">最后登录时间</span>
              <span className="text-text-secondary">{formatDateTime(user.last_login_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-tertiary">最后登录IP</span>
              <span className="text-text-secondary">{user.last_login_ip || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-tertiary">创建时间</span>
              <span className="text-text-secondary">{formatDateTime(user.created_at)}</span>
            </div>
          </div>

          {/* 工作区管理 */}
          <div className="border-t border-divider-subtle pt-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="font-medium text-text-primary">所属工作区</span>
              <Button
                variant="secondary-accent"
                size="small"
                onClick={() => setShowAddTenantModal(true)}
                disabled={availableTenants.length === 0}
              >
                添加到工作区
              </Button>
            </div>
            {tenantsLoading
              ? (
                  <div className="space-y-2">
                    {[1, 2].map(i => <Skeleton key={i} className="h-12" />)}
                  </div>
                )
              : userTenants && userTenants.length > 0
                ? (
                    <div className="max-h-48 space-y-2 overflow-y-auto">
                      {userTenants.map((tenant: AccountTenant) => (
                        <div key={tenant.id} className="flex items-center justify-between rounded-lg bg-background-section p-3">
                          <div className="mr-3 min-w-0 flex-1">
                            <p className="truncate font-medium text-text-primary">{tenant.name}</p>
                            {tenant.current && (
                              <span className="text-xs text-util-colors-blue-blue-600">当前工作区</span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <PortalSelect
                              value={tenant.role}
                              items={tenantRoleOptions}
                              onSelect={item => handleRoleChange(tenant, item.value as string)}
                              triggerClassName="w-24 h-8"
                              popupClassName="!z-[100]"
                            />
                            <button
                              className="rounded p-1.5 text-text-tertiary hover:bg-state-destructive-hover hover:text-util-colors-red-red-500"
                              onClick={() => setRemovingTenantId(tenant.id)}
                              title="从工作区移除"
                            >
                              <RiDeleteBinLine className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )
                : (
                    <div className="py-4 text-center text-sm text-text-tertiary">暂无关联工作区</div>
                  )}
          </div>
        </div>

        <div className="flex justify-end pt-6">
          <Button variant="secondary" onClick={onClose}>关闭</Button>
        </div>
      </div>

      {/* 添加到工作区弹窗 */}
      <Modal isShow={showAddTenantModal} onClose={() => setShowAddTenantModal(false)} className="!max-w-sm">
        <div className="p-6">
          <h3 className="mb-4 text-lg font-semibold text-text-primary">添加到工作区</h3>
          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">选择工作区</label>
              <SimpleSelect
                className="w-full"
                defaultValue={selectedTenantId}
                items={[
                  { value: '', name: '请选择工作区' },
                  ...availableTenants.map(t => ({ value: t.id, name: t.name })),
                ]}
                onSelect={item => setSelectedTenantId(item.value as string)}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">角色</label>
              <SimpleSelect
                className="w-full"
                defaultValue={selectedRole}
                items={tenantRoleOptions.filter(r => r.value !== 'owner')}
                onSelect={item => setSelectedRole(item.value as string)}
              />
            </div>
          </div>
          <div className="mt-6 flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowAddTenantModal(false)}>取消</Button>
            <Button
              variant="primary"
              onClick={handleAddToTenant}
              loading={addMemberMutation.isPending}
              disabled={!selectedTenantId}
            >
              确认添加
            </Button>
          </div>
        </div>
      </Modal>

      {/* 确认移除弹窗 */}
      <Confirm
        isShow={!!removingTenantId}
        onCancel={() => setRemovingTenantId(null)}
        onConfirm={handleRemoveFromTenant}
        isLoading={removeMemberMutation.isPending}
        title="确认移除"
        content="确定要将该用户从工作区中移除吗？"
      />
    </Modal>
  )
}

// 密码重置弹窗
type PasswordModalProps = {
  isOpen: boolean
  onClose: () => void
  onSubmit: (password: string) => void
  isLoading: boolean
}

const PasswordModal = ({ isOpen, onClose, onSubmit, isLoading }: PasswordModalProps) => {
  const [password, setPassword] = useState('')

  useEffect(() => {
    if (isOpen)
      setPassword('')
  }, [isOpen])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(password)
  }

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-sm">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">重置密码</h3>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <Input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="请输入新密码（至少8位）"
            required
          />
          <div className="mt-4 flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose}>取消</Button>
            <Button variant="primary" type="submit" loading={isLoading}>确认</Button>
          </div>
        </form>
      </div>
    </Modal>
  )
}

// 删除用户弹窗
type DeleteUserModalProps = {
  isOpen: boolean
  onClose: () => void
  user: AccountListItem | null
  onSuccess: () => void
}

type OwnedTenant = {
  id: string
  name: string
  member_count: number
}

type TenantAction = {
  tenantId: string
  action: 'transfer' | 'delete'
  newOwnerId?: string
}

const DeleteUserModal = ({ isOpen, onClose, user, onSuccess }: DeleteUserModalProps) => {
  const [step, setStep] = useState<'check' | 'handle' | 'confirm'>('check')
  const [ownedTenants, setOwnedTenants] = useState<OwnedTenant[]>([])
  const [tenantActions, setTenantActions] = useState<Record<string, TenantAction>>({})
  const [isDeleted, setIsDeleted] = useState(false)

  const { data: ownedTenantsData, isLoading: isLoadingOwned, refetch } = useAccountOwnedTenants(isDeleted ? '' : (user?.id || ''))

  const deleteMutation = useDeleteAccount()
  const transferMutation = useTransferTenantOwnership()

  // 重置状态
  useEffect(() => {
    if (isOpen && user) {
      setStep('check')
      setOwnedTenants([])
      setTenantActions({})
      setIsDeleted(false)
      refetch()
    }
  }, [isOpen, user, refetch])

  // 处理加载完成后的逻辑
  useEffect(() => {
    if (!isLoadingOwned && ownedTenantsData && step === 'check') {
      if (ownedTenantsData.length > 0) {
        setOwnedTenants(ownedTenantsData)
        // 默认所有租户都设为删除
        const actions: Record<string, TenantAction> = {}
        ownedTenantsData.forEach((t) => {
          actions[t.id] = { tenantId: t.id, action: 'delete' }
        })
        setTenantActions(actions)
        setStep('handle')
      }
      else {
        setStep('confirm')
      }
    }
  }, [isLoadingOwned, ownedTenantsData, step])

  const handleDelete = async () => {
    if (!user)
      return

    try {
      setIsDeleted(true) // 先标记为已删除，阻止后续请求

      // 如果有需要转让的租户，先处理转让
      const transferActions = Object.values(tenantActions).filter(a => a.action === 'transfer' && a.newOwnerId)
      for (const action of transferActions) {
        await transferMutation.mutateAsync({
          tenantId: action.tenantId,
          newOwnerId: action.newOwnerId!,
        })
      }

      // 删除用户（同时删除其拥有的租户）
      const hasTenantsToDelete = Object.values(tenantActions).some(a => a.action === 'delete')
      await deleteMutation.mutateAsync({
        id: user.id,
        deleteOwnedTenants: hasTenantsToDelete,
      })

      Toast.notify({ type: 'success', message: '用户删除成功' })
      onSuccess()
      onClose()
    }
    catch {
      setIsDeleted(false) // 删除失败，恢复状态
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const setTenantAction = (tenantId: string, action: 'transfer' | 'delete', newOwnerId?: string) => {
    setTenantActions(prev => ({
      ...prev,
      [tenantId]: { tenantId, action, newOwnerId },
    }))
  }

  const isProcessing = deleteMutation.isPending || transferMutation.isPending

  // 检查是否所有需要转让的租户都选择了新所有者
  const canProceed = Object.values(tenantActions).every(
    a => a.action === 'delete' || (a.action === 'transfer' && a.newOwnerId),
  )

  if (!user)
    return null

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-lg">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">删除用户</h3>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>

        {step === 'check' && isLoadingOwned && (
          <div className="space-y-3">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-3/4" />
          </div>
        )}

        {step === 'handle' && ownedTenants.length > 0 && (
          <div className="space-y-4">
            <div className="rounded-lg bg-util-colors-warning-warning-50 p-3 text-sm text-util-colors-warning-warning-600">
              该用户是以下
              {' '}
              {ownedTenants.length}
              {' '}
              个工作区的所有者，请选择如何处理：
            </div>

            <div className="max-h-64 space-y-3 overflow-y-auto">
              {ownedTenants.map(tenant => (
                <TenantActionItem
                  key={tenant.id}
                  tenant={tenant}
                  userId={user.id}
                  action={tenantActions[tenant.id]}
                  onActionChange={(action, newOwnerId) => setTenantAction(tenant.id, action, newOwnerId)}
                />
              ))}
            </div>

            <div className="flex justify-end gap-3 border-t border-divider-subtle pt-4">
              <Button variant="secondary" onClick={onClose}>取消</Button>
              <Button
                variant="warning"
                onClick={() => setStep('confirm')}
                disabled={!canProceed}
              >
                继续删除
              </Button>
            </div>
          </div>
        )}

        {step === 'confirm' && (
          <div className="space-y-4">
            <p className="text-text-secondary">
              确定要删除用户
              {' '}
              <span className="font-medium text-text-primary">{user.name}</span>
              {' '}
              吗？
            </p>

            {ownedTenants.length > 0 && (
              <div className="rounded-lg bg-background-section p-3 text-sm">
                <p className="mb-2 font-medium text-text-primary">将执行以下操作：</p>
                <ul className="list-inside list-disc space-y-1 text-text-secondary">
                  {Object.values(tenantActions).map((action) => {
                    const tenant = ownedTenants.find(t => t.id === action.tenantId)
                    if (!tenant)
                      return null
                    if (action.action === 'delete') {
                      return (
                        <li key={action.tenantId} className="text-util-colors-red-red-600">
                          删除工作区「
                          {tenant.name}
                          」及其所有数据
                        </li>
                      )
                    }
                    return (
                      <li key={action.tenantId}>
                        转让工作区「
                        {tenant.name}
                        」的所有权
                      </li>
                    )
                  })}
                  <li>删除用户账户</li>
                </ul>
              </div>
            )}

            <p className="text-sm text-util-colors-red-red-600">此操作不可撤销！</p>

            <div className="flex justify-end gap-3 border-t border-divider-subtle pt-4">
              <Button variant="secondary" onClick={() => ownedTenants.length > 0 ? setStep('handle') : onClose()}>
                {ownedTenants.length > 0 ? '返回' : '取消'}
              </Button>
              <Button variant="warning" onClick={handleDelete} loading={isProcessing}>
                确认删除
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}

// 租户操作项组件
type TenantActionItemProps = {
  tenant: OwnedTenant
  userId: string
  action: TenantAction
  onActionChange: (action: 'transfer' | 'delete', newOwnerId?: string) => void
}

const TenantActionItem = ({ tenant, userId, action, onActionChange }: TenantActionItemProps) => {
  const isTransfer = action?.action === 'transfer'
  const { data: members } = useTenantMembers(isTransfer ? tenant.id : '')

  // 过滤掉当前用户，只显示其他成员作为可转让对象
  const otherMembers = members?.filter(m => m.account_id !== userId) || []

  return (
    <div className="rounded-lg border border-divider-subtle">
      <div className="flex items-center justify-between p-3">
        <div>
          <p className="font-medium text-text-primary">{tenant.name}</p>
          <p className="text-xs text-text-tertiary">
            {tenant.member_count}
            {' '}
            个成员
          </p>
        </div>
        <div className="flex items-center gap-2">
          <PortalSelect
            value={action?.action || 'delete'}
            items={[
              { value: 'delete', name: '删除工作区' },
              { value: 'transfer', name: '转让所有权' },
            ]}
            onSelect={(item) => {
              const newAction = item.value as 'transfer' | 'delete'
              onActionChange(newAction, undefined)
            }}
            triggerClassName="w-32"
            popupClassName="!z-[100]"
          />
        </div>
      </div>

      {isTransfer && (
        <div className="border-t border-divider-subtle bg-background-section-burn p-3">
          {otherMembers.length === 0
            ? (
                <p className="text-sm text-util-colors-warning-warning-600">
                  该工作区没有其他成员，无法转让所有权。请选择删除工作区或先添加其他成员。
                </p>
              )
            : (
                <div>
                  <label className="mb-1.5 block text-xs text-text-tertiary">选择新所有者</label>
                  <PortalSelect
                    value={action.newOwnerId || ''}
                    items={[
                      { value: '', name: '请选择成员' },
                      ...otherMembers.map(m => ({ value: m.account_id, name: `${m.account_name} (${m.account_email})` })),
                    ]}
                    onSelect={item => onActionChange('transfer', item.value as string || undefined)}
                    triggerClassName="w-full"
                    popupClassName="!z-[100]"
                  />
                </div>
              )}
        </div>
      )}
    </div>
  )
}

const UsersPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectedUser, setSelectedUser] = useState<AccountListItem | null>(null)

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useAccounts({
    page,
    page_size: pageSize,
    keyword: searchKeyword,
    status: statusFilter || undefined,
    ...(sorting.length > 0 && {
      sort_by: sorting[0].id,
      sort_order: sorting[0].desc ? 'desc' : 'asc',
    }),
  })

  const createMutation = useCreateAccount()
  const updateMutation = useUpdateAccount()
  const passwordMutation = useUpdateAccountPassword()

  const handleSearch = useCallback(() => {
    setSearchKeyword(keyword)
    setPage(1)
  }, [keyword])

  const handleCreate = async (formData: AccountCreate) => {
    try {
      const submitData = {
        ...formData,
        password: formData.password ? encryptPassword(formData.password) : '',
      }
      await createMutation.mutateAsync(submitData)
      Toast.notify({ type: 'success', message: '用户创建成功' })
      setShowCreateModal(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '创建失败' })
    }
  }

  const handleUpdate = async (formData: AccountUpdate) => {
    if (!editingId)
      return
    try {
      await updateMutation.mutateAsync({ id: editingId, data: formData })
      Toast.notify({ type: 'success', message: '用户更新成功' })
      setShowEditModal(false)
      setEditingId(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handlePasswordReset = async (password: string) => {
    if (!selectedUser)
      return
    try {
      await passwordMutation.mutateAsync({ id: selectedUser.id, password: encryptPassword(password) })
      Toast.notify({ type: 'success', message: '密码已重置' })
      setShowPasswordModal(false)
      setSelectedUser(null)
    }
    catch {
      Toast.notify({ type: 'error', message: '重置失败' })
    }
  }

  const handleSortingChange = useCallback((newSorting: SortingState) => {
    setSorting(newSorting)
    setPage(1)
  }, [])

  // 定义表格列
  const columns: ColumnDef<AccountListItem>[] = useMemo(() => [
    {
      id: 'name',
      header: '用户',
      size: 280,
      enableSorting: true,
      cell: ({ row }) => (
        <AvatarCell
          name={row.original.name}
          avatar={row.original.avatar_url}
          email={row.original.email}
        />
      ),
      meta: {
        skeletonClassName: 'h-10 w-48',
      },
    },
    {
      id: 'status',
      header: '状态',
      size: 100,
      cell: ({ row }) => <StatusBadge status={row.original.status} type="user" />,
      meta: {
        skeletonClassName: 'h-6 w-16',
      },
    },
    {
      id: 'last_login_at',
      header: '最后登录',
      size: 160,
      enableSorting: true,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {formatDateTime(row.original.last_login_at)}
        </span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-32',
      },
    },
    {
      id: 'created_at',
      header: '创建时间',
      size: 160,
      enableSorting: true,
      cell: ({ row }) => (
        <span className="text-sm text-text-secondary">
          {formatDateTime(row.original.created_at)}
        </span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-32',
      },
    },
    createActionColumn<AccountListItem>({
      width: 140,
      actions: [
        {
          icon: RiEyeLine,
          label: '查看',
          onClick: (row) => {
            setSelectedUser(row)
            setShowDetailModal(true)
          },
        },
        {
          icon: RiLockPasswordLine,
          label: '重置密码',
          onClick: (row) => {
            setSelectedUser(row)
            setShowPasswordModal(true)
          },
        },
        {
          icon: RiEditLine,
          label: '编辑',
          onClick: (row) => {
            setEditingId(row.id)
            setShowEditModal(true)
          },
        },
        {
          icon: RiDeleteBinLine,
          label: '删除',
          onClick: (row) => {
            setSelectedUser(row)
            setShowDeleteModal(true)
          },
          variant: 'danger',
        },
      ],
    }),
  ], [])

  const selectedCount = Object.keys(rowSelection).length

  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">用户管理</h1>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <RiAddLine className="mr-1 h-4 w-4" />
          创建用户
        </Button>
      </div>

      <DataTableToolbar
        className="shrink-0"
        searchValue={keyword}
        searchPlaceholder="搜索用户名或邮箱"
        onSearchChange={setKeyword}
        onSearch={handleSearch}
        filterSlot={(
          <SimpleSelect
            className="w-32"
            defaultValue={statusFilter}
            items={[
              { value: '', name: '全部状态' },
              ...statusOptions,
            ]}
            onSelect={(item) => {
              setStatusFilter(item.value as string)
              setPage(1)
            }}
          />
        )}
        selectedCount={selectedCount}
        bulkActionsSlot={
          selectedCount > 0 && (
            <Button
              variant="warning"
              size="small"
              onClick={() => {
                Toast.notify({ type: 'info', message: `已选择 ${selectedCount} 个用户` })
              }}
            >
              <RiDeleteBinLine className="mr-1 h-4 w-4" />
              批量删除
            </Button>
          )
        }
      />

      <DataTable
        columns={columns}
        data={data?.items || []}
        isLoading={isLoading}
        loadingRowCount={5}
        getRowId={row => row.id}
        enableRowSelection
        rowSelection={rowSelection}
        onRowSelectionChange={setRowSelection}
        enableSorting
        sorting={sorting}
        onSortingChange={handleSortingChange}
        stickyHeader
        pagination={{
          page,
          pageSize,
          total: data?.total || 0,
          onChange: setPage,
          onPageSizeChange: setPageSize,
        }}
      />

      <UserFormModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={data => handleCreate(data as AccountCreate)}
        isLoading={createMutation.isPending}
      />

      <UserFormModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setEditingId(null)
        }}
        userId={editingId}
        onSubmit={data => handleUpdate(data as AccountUpdate)}
        isLoading={updateMutation.isPending}
      />

      {showDetailModal && (
        <UserDetailModal
          isOpen={showDetailModal}
          onClose={() => {
            setShowDetailModal(false)
            setSelectedUser(null)
          }}
          user={selectedUser}
        />
      )}

      {showDeleteModal && (
        <DeleteUserModal
          isOpen={showDeleteModal}
          onClose={() => {
            setShowDeleteModal(false)
            setSelectedUser(null)
          }}
          user={selectedUser}
          onSuccess={() => {
            setShowDeleteModal(false)
            setSelectedUser(null)
            refetch()
          }}
        />
      )}

      <PasswordModal
        isOpen={showPasswordModal}
        onClose={() => {
          setShowPasswordModal(false)
          setSelectedUser(null)
        }}
        onSubmit={handlePasswordReset}
        isLoading={passwordMutation.isPending}
      />
    </>
  )
}

export default UsersPage
