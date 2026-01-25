'use client'

import type { ColumnDef, RowSelectionState, SortingState } from '@/app/components/base/table'
import type { SearchUserItem } from '@/service/use-platform'
import type { TenantCreate, TenantListItem, TenantMember, TenantUpdate } from '@/types/platform'
import {
  RiAddLine,
  RiCloseLine,
  RiDeleteBinLine,
  RiEditLine,
  RiGroupLine,
  RiSearchLine,
  RiUserAddLine,
} from '@remixicon/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import { PortalSelect, SimpleSelect } from '@/app/components/base/select'
import Skeleton from '@/app/components/base/skeleton'
import StatusBadge from '@/app/components/base/status-badge'
import {

  createActionColumn,
  DataTable,

  DataTableToolbar,
  TruncatedText,
} from '@/app/components/base/table'
import Toast from '@/app/components/base/toast'
import useTimestamp from '@/hooks/use-timestamp'
import {
  useBatchAddTenantMembers,
  useCreateTenant,
  useDeleteTenant,
  useRemoveTenantMember,
  useSearchUsersForTenant,
  useSubscriptionPlans,
  useTenant,
  useTenantDeletionImpact,
  useTenantMembers,
  useTenants,
  useUpdateTenant,
  useUpdateTenantMemberRole,
} from '@/service/use-platform'

type TenantFormModalProps = {
  isOpen: boolean
  onClose: () => void
  tenantId?: string | null
  onSubmit: (data: TenantCreate | TenantUpdate) => Promise<void> | void
  isLoading: boolean
}

const TenantFormModal = ({ isOpen, onClose, tenantId, onSubmit, isLoading }: TenantFormModalProps) => {
  const [formData, setFormData] = useState<TenantCreate & { status?: string }>({
    name: '',
    plan: 'basic',
    status: 'normal',
  })

  const { data: tenantDetail, isLoading: isLoadingDetail } = useTenant(tenantId || '')
  const { data: subscriptionPlans, isLoading: isLoadingPlans } = useSubscriptionPlans()

  // 生成计划选项
  const planOptions = useMemo(() => {
    if (!subscriptionPlans || subscriptionPlans.length === 0) {
      return [{ value: 'basic', name: 'Basic' }]
    }
    return subscriptionPlans.map(plan => ({
      value: plan.id,
      name: plan.name,
    }))
  }, [subscriptionPlans])

  useEffect(() => {
    if (isOpen) {
      if (tenantDetail) {
        setFormData({
          name: tenantDetail.name,
          plan: tenantDetail.plan || 'basic',
          status: tenantDetail.status || 'normal',
        })
      }
      else if (!tenantId) {
        setFormData({
          name: '',
          plan: 'basic',
          status: 'normal',
        })
      }
    }
  }, [isOpen, tenantDetail, tenantId])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  const isEditMode = !!tenantId

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-md">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            {isEditMode ? '编辑租户' : '创建租户'}
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
                  <label className="mb-1.5 block text-sm text-text-secondary">租户名称</label>
                  <Input
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="请输入租户名称"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm text-text-secondary">订阅计划</label>
                  {isLoadingPlans
                    ? <Skeleton className="h-10 w-full" />
                    : (
                        <PortalSelect
                          value={formData.plan}
                          items={planOptions}
                          onSelect={item => setFormData({ ...formData, plan: item.value as string })}
                          popupClassName="!z-[1001]"
                        />
                      )}
                </div>
                {isEditMode && (
                  <div>
                    <label className="mb-1.5 block text-sm text-text-secondary">状态</label>
                    <SimpleSelect
                      className="w-full"
                      value={formData.status}
                      items={[
                        { value: 'normal', name: '正常' },
                        { value: 'archive', name: '归档' },
                      ]}
                      onSelect={item => setFormData({ ...formData, status: item.value as string })}
                      notClearable
                    />
                  </div>
                )}
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

type MembersModalProps = {
  isOpen: boolean
  onClose: () => void
  tenantId: string
  tenantName: string
}

const roleOptions = [
  { value: 'owner', name: '所有者' },
  { value: 'admin', name: '管理员' },
  { value: 'editor', name: '编辑' },
  { value: 'normal', name: '普通成员' },
]

const MembersModal = ({ isOpen, onClose, tenantId, tenantName }: MembersModalProps) => {
  const { data: members, isLoading, refetch } = useTenantMembers(tenantId)
  const updateRoleMutation = useUpdateTenantMemberRole()
  const removeMemberMutation = useRemoveTenantMember()
  const [removingMemberId, setRemovingMemberId] = useState<string | null>(null)
  const [showAddMembersModal, setShowAddMembersModal] = useState(false)

  const handleRoleChange = async (memberId: string, newRole: string) => {
    try {
      await updateRoleMutation.mutateAsync({ tenantId, memberId, role: newRole })
      Toast.notify({ type: 'success', message: '角色已更新' })
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handleRemoveMember = async (memberId: string) => {
    try {
      await removeMemberMutation.mutateAsync({ tenantId, memberId })
      Toast.notify({ type: 'success', message: '成员已移除' })
      setRemovingMemberId(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '移除失败' })
    }
  }

  const handleAddMembersSuccess = () => {
    setShowAddMembersModal(false)
    refetch()
  }

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-lg">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            {tenantName}
            {' '}
            - 成员管理
          </h3>
          <div className="flex items-center gap-2">
            <Button variant="primary" size="small" onClick={() => setShowAddMembersModal(true)}>
              <RiUserAddLine className="mr-1 h-4 w-4" />
              添加成员
            </Button>
            <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
              <RiCloseLine className="h-5 w-5" />
            </button>
          </div>
        </div>
        {isLoading
          ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => <Skeleton key={i} className="h-14" />)}
              </div>
            )
          : members && members.length > 0
            ? (
                <div className="max-h-96 space-y-2 overflow-y-auto">
                  {members.map((member: TenantMember) => (
                    <div key={member.id} className="flex items-center justify-between rounded-lg bg-background-section p-3">
                      <div className="mr-3 min-w-0 flex-1">
                        <p className="truncate font-medium text-text-primary">{member.account_name}</p>
                        <p className="truncate text-sm text-text-tertiary">{member.account_email}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <PortalSelect
                          value={member.role}
                          items={roleOptions}
                          onSelect={item => handleRoleChange(member.id, item.value as string)}
                          triggerClassName="w-28 h-8"
                          popupClassName="!z-[100]"
                        />
                        <button
                          className="rounded p-1.5 text-text-tertiary hover:bg-state-destructive-hover hover:text-util-colors-red-red-500"
                          onClick={() => setRemovingMemberId(member.id)}
                          title="移除成员"
                        >
                          <RiDeleteBinLine className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )
            : (
                <div className="py-8 text-center text-text-tertiary">暂无成员</div>
              )}
        <div className="flex justify-end pt-4">
          <Button variant="secondary" onClick={onClose}>关闭</Button>
        </div>
      </div>

      {/* 确认移除成员弹窗 */}
      <Confirm
        isShow={!!removingMemberId}
        onCancel={() => setRemovingMemberId(null)}
        onConfirm={() => removingMemberId && handleRemoveMember(removingMemberId)}
        isLoading={removeMemberMutation.isPending}
        title="确认移除"
        content="确定要将该成员从工作区中移除吗？"
      />

      {/* 批量添加成员弹窗 */}
      {showAddMembersModal && (
        <AddMembersModal
          isOpen={showAddMembersModal}
          onClose={() => setShowAddMembersModal(false)}
          tenantId={tenantId}
          tenantName={tenantName}
          onSuccess={handleAddMembersSuccess}
        />
      )}
    </Modal>
  )
}

// 批量添加成员弹窗
type AddMembersModalProps = {
  isOpen: boolean
  onClose: () => void
  tenantId: string
  tenantName: string
  onSuccess: () => void
}

const AddMembersModal = ({ isOpen, onClose, tenantId, tenantName, onSuccess }: AddMembersModalProps) => {
  const [searchKeyword, setSearchKeyword] = useState('')
  const [submittedKeyword, setSubmittedKeyword] = useState('')
  const [selectedUsers, setSelectedUsers] = useState<SearchUserItem[]>([])
  const [selectedRole, setSelectedRole] = useState('normal')
  const [page, setPage] = useState(1)
  const [allResults, setAllResults] = useState<SearchUserItem[]>([])

  const { data: searchData, isLoading: isSearching, isFetching } = useSearchUsersForTenant(tenantId, submittedKeyword, page)
  const batchAddMutation = useBatchAddTenantMembers()

  // 重置状态
  useEffect(() => {
    if (isOpen) {
      setSearchKeyword('')
      setSubmittedKeyword('')
      setSelectedUsers([])
      setSelectedRole('normal')
      setPage(1)
      setAllResults([])
    }
  }, [isOpen])

  // 合并分页结果
  useEffect(() => {
    if (searchData?.items) {
      if (page === 1) {
        setAllResults(searchData.items)
      }
      else {
        setAllResults(prev => [...prev, ...searchData.items])
      }
    }
  }, [searchData, page])

  // 回车搜索
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && searchKeyword.trim()) {
      setPage(1)
      setAllResults([])
      setSubmittedKeyword(searchKeyword.trim())
    }
  }

  // 滚动加载更多
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget
    if (scrollHeight - scrollTop - clientHeight < 50 && searchData?.has_more && !isFetching) {
      setPage(prev => prev + 1)
    }
  }

  const handleSelectUser = (user: SearchUserItem) => {
    if (user.is_member)
      return
    if (selectedUsers.some(u => u.id === user.id)) {
      setSelectedUsers(selectedUsers.filter(u => u.id !== user.id))
    }
    else {
      setSelectedUsers([...selectedUsers, user])
    }
  }

  const handleRemoveSelected = (userId: string) => {
    setSelectedUsers(selectedUsers.filter(u => u.id !== userId))
  }

  const handleSubmit = async () => {
    if (selectedUsers.length === 0)
      return

    try {
      const result = await batchAddMutation.mutateAsync({
        tenantId,
        accountIds: selectedUsers.map(u => u.id),
        role: selectedRole,
      })
      Toast.notify({
        type: 'success',
        message: `成功添加 ${result.added} 个成员${result.skipped > 0 ? `，${result.skipped} 个已存在` : ''}`,
      })
      onSuccess()
    }
    catch {
      Toast.notify({ type: 'error', message: '添加失败' })
    }
  }

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-3xl !z-[1002]">
      <div className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            添加成员到
            {' '}
            {tenantName}
          </h3>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>

        {/* 左右布局 */}
        <div className="flex gap-4" style={{ height: '400px' }}>
          {/* 左侧：搜索区域 */}
          <div className="flex flex-1 flex-col">
            <div className="relative mb-3">
              <RiSearchLine className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
              <Input
                value={searchKeyword}
                onChange={e => setSearchKeyword(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入邮箱或用户名，按回车搜索"
                className="pl-9"
              />
            </div>

            <div
              className="flex-1 overflow-y-auto rounded-lg border border-divider-subtle"
              onScroll={handleScroll}
            >
              {!submittedKeyword
                ? (
                    <div className="flex h-full items-center justify-center text-text-tertiary">
                      输入关键词后按回车搜索
                    </div>
                  )
                : isSearching && page === 1
                  ? (
                      <div className="space-y-2 p-3">
                        {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-12" />)}
                      </div>
                    )
                  : allResults.length > 0
                    ? (
                        <div className="divide-y divide-divider-subtle">
                          {allResults.map((user) => {
                            const isSelected = selectedUsers.some(u => u.id === user.id)
                            return (
                              <div
                                key={user.id}
                                className={`flex cursor-pointer items-center justify-between p-3 transition-colors ${
                                  user.is_member
                                    ? 'cursor-not-allowed bg-background-section-burn opacity-60'
                                    : isSelected
                                      ? 'bg-state-accent-hover'
                                      : 'hover:bg-background-section'
                                }`}
                                onClick={() => handleSelectUser(user)}
                              >
                                <div className="min-w-0 flex-1">
                                  <p className="truncate font-medium text-text-primary">{user.name}</p>
                                  <p className="truncate text-sm text-text-tertiary">{user.email}</p>
                                </div>
                                {user.is_member
                                  ? <span className="shrink-0 text-xs text-text-tertiary">已是成员</span>
                                  : isSelected
                                    ? <span className="shrink-0 text-xs text-components-badge-blue">已选择</span>
                                    : null}
                              </div>
                            )
                          })}
                          {isFetching && page > 1 && (
                            <div className="p-3">
                              <Skeleton className="h-12" />
                            </div>
                          )}
                          {searchData && !searchData.has_more && allResults.length > 0 && (
                            <div className="py-3 text-center text-xs text-text-tertiary">
                              共
                              {' '}
                              {searchData.total}
                              {' '}
                              条结果
                            </div>
                          )}
                        </div>
                      )
                    : (
                        <div className="flex h-full items-center justify-center text-text-tertiary">
                          未找到匹配的用户
                        </div>
                      )}
            </div>
          </div>

          {/* 右侧：已选用户 */}
          <div className="flex w-64 flex-col rounded-lg border border-divider-subtle bg-background-section-burn">
            <div className="flex items-center justify-between border-b border-divider-subtle px-3 py-2">
              <span className="text-sm font-medium text-text-secondary">
                已选择 (
                {selectedUsers.length}
                )
              </span>
              {selectedUsers.length > 0 && (
                <button
                  onClick={() => setSelectedUsers([])}
                  className="text-xs text-text-tertiary hover:text-util-colors-red-red-500"
                >
                  清空
                </button>
              )}
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              {selectedUsers.length === 0
                ? (
                    <div className="flex h-full items-center justify-center text-sm text-text-tertiary">
                      点击左侧用户添加
                    </div>
                  )
                : (
                    <div className="space-y-1">
                      {selectedUsers.map(user => (
                        <div
                          key={user.id}
                          className="flex items-center justify-between rounded-md bg-background-default p-2"
                        >
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium text-text-primary">{user.name}</p>
                            <p className="truncate text-xs text-text-tertiary">{user.email}</p>
                          </div>
                          <button
                            onClick={() => handleRemoveSelected(user.id)}
                            className="ml-2 shrink-0 rounded p-1 text-text-tertiary hover:bg-state-destructive-hover hover:text-util-colors-red-red-500"
                          >
                            <RiCloseLine className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
            </div>
            {/* 角色选择 */}
            <div className="border-t border-divider-subtle p-3">
              <label className="mb-1.5 block text-xs text-text-tertiary">成员角色</label>
              <PortalSelect
                value={selectedRole}
                items={roleOptions}
                onSelect={item => setSelectedRole(item.value as string)}
                popupClassName="!z-[1003]"
                triggerClassName="w-full"
              />
            </div>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="mt-4 flex justify-end gap-3 border-t border-divider-subtle pt-4">
          <Button variant="secondary" onClick={onClose}>取消</Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            loading={batchAddMutation.isPending}
            disabled={selectedUsers.length === 0}
          >
            添加
            {' '}
            {selectedUsers.length > 0 ? `(${selectedUsers.length})` : ''}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// 删除租户弹窗
type DeleteTenantModalProps = {
  isOpen: boolean
  onClose: () => void
  tenant: TenantListItem | null
  onSuccess: () => void
}

const DeleteTenantModal = ({ isOpen, onClose, tenant, onSuccess }: DeleteTenantModalProps) => {
  const [step, setStep] = useState<'loading' | 'confirm' | 'final'>('loading')
  const [deleteOrphanUsers, setDeleteOrphanUsers] = useState(false)
  const [isDeleted, setIsDeleted] = useState(false)

  const { data: impact, isLoading, refetch } = useTenantDeletionImpact(isDeleted ? '' : (tenant?.id || ''))
  const deleteMutation = useDeleteTenant()

  // 重置状态
  useEffect(() => {
    if (isOpen && tenant) {
      setStep('loading')
      setDeleteOrphanUsers(false)
      setIsDeleted(false)
      refetch()
    }
  }, [isOpen, tenant, refetch])

  // 加载完成后判断步骤
  useEffect(() => {
    if (!isLoading && impact && step === 'loading') {
      if (impact.orphan_user_count > 0) {
        setStep('confirm')
      }
      else {
        setStep('final')
      }
    }
  }, [isLoading, impact, step])

  const handleDelete = async () => {
    if (!tenant)
      return

    try {
      setIsDeleted(true) // 先标记为已删除，阻止后续请求
      await deleteMutation.mutateAsync({
        id: tenant.id,
        deleteOrphanUsers,
      })
      Toast.notify({ type: 'success', message: '租户删除成功' })
      onSuccess()
      onClose()
    }
    catch {
      setIsDeleted(false) // 删除失败，恢复状态
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  if (!tenant)
    return null

  return (
    <Modal isShow={isOpen} onClose={onClose} className="!max-w-lg">
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">删除租户</h3>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-secondary">
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>

        {step === 'loading' && isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-3/4" />
          </div>
        )}

        {step === 'confirm' && impact && (
          <div className="space-y-4">
            <div className="rounded-lg bg-util-colors-warning-warning-50 p-3 text-sm text-util-colors-warning-warning-600">
              该租户有
              {' '}
              {impact.orphan_user_count}
              {' '}
              个用户只属于此工作区，删除后这些用户将没有任何工作区。
            </div>

            <div className="rounded-lg bg-background-section p-4">
              <p className="mb-3 text-sm font-medium text-text-primary">受影响的用户：</p>
              <div className="max-h-40 space-y-2 overflow-y-auto">
                {impact.orphan_users.map(user => (
                  <div key={user.id} className="flex items-center justify-between rounded bg-background-default-burn p-2 text-sm">
                    <div>
                      <span className="text-text-primary">{user.name}</span>
                      <span className="ml-2 text-text-tertiary">{user.email}</span>
                    </div>
                    <span className="text-xs text-text-tertiary">{user.role === 'owner' ? '所有者' : user.role}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-divider-subtle p-3">
              <p className="mb-3 text-sm text-text-secondary">请选择如何处理这些用户：</p>
              <div className="space-y-2">
                <label className="flex cursor-pointer items-start gap-3 rounded-lg p-2 hover:bg-background-section">
                  <input
                    type="radio"
                    name="orphanAction"
                    checked={!deleteOrphanUsers}
                    onChange={() => setDeleteOrphanUsers(false)}
                    className="mt-1"
                  />
                  <div>
                    <p className="font-medium text-text-primary">保留用户账户</p>
                    <p className="text-xs text-text-tertiary">用户账户保留，但将没有任何工作区</p>
                  </div>
                </label>
                <label className="flex cursor-pointer items-start gap-3 rounded-lg p-2 hover:bg-background-section">
                  <input
                    type="radio"
                    name="orphanAction"
                    checked={deleteOrphanUsers}
                    onChange={() => setDeleteOrphanUsers(true)}
                    className="mt-1"
                  />
                  <div>
                    <p className="font-medium text-util-colors-red-red-600">同时删除这些用户</p>
                    <p className="text-xs text-text-tertiary">用户账户将被永久删除</p>
                  </div>
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t border-divider-subtle pt-4">
              <Button variant="secondary" onClick={onClose}>取消</Button>
              <Button variant="warning" onClick={() => setStep('final')}>
                继续删除
              </Button>
            </div>
          </div>
        )}

        {step === 'final' && impact && (
          <div className="space-y-4">
            <p className="text-text-secondary">
              确定要删除租户
              {' '}
              <span className="font-medium text-text-primary">{tenant.name}</span>
              {' '}
              吗？
            </p>

            <div className="rounded-lg bg-background-section p-3 text-sm">
              <p className="mb-2 font-medium text-text-primary">删除影响：</p>
              <ul className="list-inside list-disc space-y-1 text-text-secondary">
                <li>
                  移除
                  {impact.member_count}
                  {' '}
                  个成员的关联
                </li>
                {impact.orphan_user_count > 0 && (
                  deleteOrphanUsers
                    ? (
                        <li className="text-util-colors-red-red-600">
                          删除
                          {impact.orphan_user_count}
                          {' '}
                          个孤儿用户账户
                        </li>
                      )
                    : (
                        <li>
                          {impact.orphan_user_count}
                          {' '}
                          个用户将没有任何工作区
                        </li>
                      )
                )}
                <li>删除租户及其所有数据</li>
              </ul>
            </div>

            <p className="text-sm text-util-colors-red-red-600">此操作不可撤销！</p>

            <div className="flex justify-end gap-3 border-t border-divider-subtle pt-4">
              <Button variant="secondary" onClick={() => impact.orphan_user_count > 0 ? setStep('confirm') : onClose()}>
                {impact.orphan_user_count > 0 ? '返回' : '取消'}
              </Button>
              <Button variant="warning" onClick={handleDelete} loading={deleteMutation.isPending}>
                确认删除
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}

const TenantsPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showMembersModal, setShowMembersModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectedTenant, setSelectedTenant] = useState<TenantListItem | null>(null)

  const { formatDateTime } = useTimestamp()

  const { data, isLoading, refetch } = useTenants({
    page,
    page_size: pageSize,
    keyword: searchKeyword,
    status: statusFilter || undefined,
    ...(sorting.length > 0 && {
      sort_by: sorting[0].id,
      sort_order: sorting[0].desc ? 'desc' : 'asc',
    }),
  })

  const createMutation = useCreateTenant()
  const updateMutation = useUpdateTenant()

  const handleSearch = useCallback(() => {
    setSearchKeyword(keyword)
    setPage(1)
  }, [keyword])

  const handleCreate = async (formData: TenantCreate) => {
    try {
      await createMutation.mutateAsync(formData)
      Toast.notify({ type: 'success', message: '租户创建成功' })
      setShowCreateModal(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '创建失败' })
    }
  }

  const handleUpdate = async (formData: TenantUpdate) => {
    if (!editingId)
      return
    try {
      await updateMutation.mutateAsync({ id: editingId, data: formData })
      Toast.notify({ type: 'success', message: '租户更新成功' })
      setShowEditModal(false)
      setEditingId(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handleSortingChange = useCallback((newSorting: SortingState) => {
    setSorting(newSorting)
    setPage(1)
  }, [])

  // 定义表格列
  const columns: ColumnDef<TenantListItem>[] = useMemo(() => [
    {
      id: 'name',
      header: '租户名称',
      enableSorting: true,
      cell: ({ row }) => (
        <TruncatedText text={row.original.name} textClassName="text-text-primary font-medium" />
      ),
      meta: {
        skeletonClassName: 'h-6 w-32',
      },
    },
    {
      id: 'plan',
      header: '计划',
      size: 100,
      cell: ({ row }) => (
        <span className="bg-components-badge-bg-gray rounded px-2 py-1 text-xs capitalize text-text-secondary">
          {row.original.plan}
        </span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-16',
      },
    },
    {
      id: 'member_count',
      header: '成员数',
      size: 100,
      enableSorting: true,
      cell: ({ row }) => (
        <span className="text-text-secondary">{row.original.member_count}</span>
      ),
      meta: {
        skeletonClassName: 'h-6 w-12',
      },
    },
    {
      id: 'status',
      header: '状态',
      size: 100,
      cell: ({ row }) => <StatusBadge status={row.original.status} type="tenant" />,
      meta: {
        skeletonClassName: 'h-6 w-16',
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
    createActionColumn<TenantListItem>({
      width: 120,
      actions: [
        {
          icon: RiGroupLine,
          label: '成员',
          onClick: (row) => {
            setSelectedTenant(row)
            setShowMembersModal(true)
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
            setSelectedTenant(row)
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
        <h1 className="text-2xl font-semibold text-text-primary">租户管理</h1>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <RiAddLine className="mr-1 h-4 w-4" />
          创建租户
        </Button>
      </div>

      <DataTableToolbar
        className="shrink-0"
        searchValue={keyword}
        searchPlaceholder="搜索租户"
        onSearchChange={setKeyword}
        onSearch={handleSearch}
        filterSlot={(
          <SimpleSelect
            className="w-32"
            defaultValue={statusFilter}
            items={[
              { value: '', name: '全部状态' },
              { value: 'normal', name: '正常' },
              { value: 'archive', name: '归档' },
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
                Toast.notify({ type: 'info', message: `已选择 ${selectedCount} 个租户` })
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

      <TenantFormModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={data => handleCreate(data as TenantCreate)}
        isLoading={createMutation.isPending}
      />
      <TenantFormModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setEditingId(null)
        }}
        tenantId={editingId}
        onSubmit={data => handleUpdate(data as TenantUpdate)}
        isLoading={updateMutation.isPending}
      />
      {showMembersModal && (
        <MembersModal
          isOpen={showMembersModal}
          onClose={() => {
            setShowMembersModal(false)
            setSelectedTenant(null)
          }}
          tenantId={selectedTenant?.id || ''}
          tenantName={selectedTenant?.name || ''}
        />
      )}
      {showDeleteModal && (
        <DeleteTenantModal
          isOpen={showDeleteModal}
          onClose={() => {
            setShowDeleteModal(false)
            setSelectedTenant(null)
          }}
          tenant={selectedTenant}
          onSuccess={() => {
            setShowDeleteModal(false)
            setSelectedTenant(null)
            refetch()
          }}
        />
      )}
    </>
  )
}

export default TenantsPage
