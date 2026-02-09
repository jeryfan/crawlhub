'use client'

import type { DataSource, DataSourceType, SpiderDataSourceAssoc, SpiderDataSourceCreate } from '@/types/crawlhub'
import {
  RiAddLine,
  RiCloseLine,
  RiDatabase2Line,
  RiDeleteBinLine,
} from '@remixicon/react'
import { useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import Modal from '@/app/components/base/modal'
import { SimpleSelect } from '@/app/components/base/select'
import StatusBadge from '@/app/components/base/status-badge'
import Toast from '@/app/components/base/toast'
import {
  useAddSpiderDataSource,
  useDataSources,
  useRemoveSpiderDataSource,
  useSpiderDataSources,
  useUpdateSpiderDataSource,
} from '@/service/use-crawlhub'

type DataSourcesTabProps = {
  spiderId: string
}

const typeLabels: Record<DataSourceType, string> = {
  postgresql: 'PostgreSQL',
  mysql: 'MySQL',
  mongodb: 'MongoDB',
}

const typeBadgeColors: Record<DataSourceType, string> = {
  postgresql: 'bg-blue-100 text-blue-700',
  mysql: 'bg-orange-100 text-orange-700',
  mongodb: 'bg-green-100 text-green-700',
}

const DataSourcesTab = ({ spiderId }: DataSourcesTabProps) => {
  const [showAddModal, setShowAddModal] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [selectedAssoc, setSelectedAssoc] = useState<SpiderDataSourceAssoc | null>(null)

  // 关联列表
  const { data: assocList, isLoading, refetch } = useSpiderDataSources(spiderId)
  // 可用数据源列表（用于添加）
  const { data: allDataSources } = useDataSources({ page_size: 100 })

  const addMutation = useAddSpiderDataSource()
  const updateMutation = useUpdateSpiderDataSource()
  const removeMutation = useRemoveSpiderDataSource()

  // 添加表单状态
  const [selectedDsId, setSelectedDsId] = useState('')
  const [targetTable, setTargetTable] = useState('')

  const handleAdd = async () => {
    if (!selectedDsId || !targetTable)
      return
    try {
      await addMutation.mutateAsync({
        spiderId,
        data: { datasource_id: selectedDsId, target_table: targetTable },
      })
      Toast.notify({ type: 'success', message: '数据源关联添加成功' })
      setShowAddModal(false)
      setSelectedDsId('')
      setTargetTable('')
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '添加失败' })
    }
  }

  const handleToggle = async (assoc: SpiderDataSourceAssoc) => {
    try {
      await updateMutation.mutateAsync({
        spiderId,
        assocId: assoc.id,
        data: { is_enabled: !assoc.is_enabled },
      })
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '更新失败' })
    }
  }

  const handleRemove = async () => {
    if (!selectedAssoc)
      return
    try {
      await removeMutation.mutateAsync({ spiderId, assocId: selectedAssoc.id })
      Toast.notify({ type: 'success', message: '关联已移除' })
      setShowDeleteConfirm(false)
      setSelectedAssoc(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '移除失败' })
    }
  }

  const items = assocList || []

  // 过滤已关联的数据源
  const associatedIds = new Set(items.map(a => a.datasource_id))
  const availableDatasources = (allDataSources?.items || []).filter(ds => !associatedIds.has(ds.id))

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="mb-3 flex shrink-0 items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-text-tertiary">
            已关联 {items.length} 个数据源
          </span>
        </div>
        <Button variant="primary" size="small" onClick={() => setShowAddModal(true)}>
          <RiAddLine className="mr-1 h-3.5 w-3.5" />
          添加数据源
        </Button>
      </div>

      {/* Association List */}
      <div className="flex-1 overflow-auto">
        {isLoading
          ? (
              <div className="py-12 text-center text-sm text-text-tertiary">加载中...</div>
            )
          : items.length === 0
            ? (
                <div className="py-12 text-center">
                  <RiDatabase2Line className="mx-auto mb-3 h-12 w-12 text-text-quaternary" />
                  <p className="text-sm text-text-tertiary">暂未关联数据源</p>
                  <p className="mt-1 text-xs text-text-quaternary">添加数据源后，爬虫数据将自动写入外部数据库</p>
                </div>
              )
            : (
                <div className="space-y-2">
                  {items.map(assoc => (
                    <div
                      key={assoc.id}
                      className={`flex items-center justify-between rounded-lg border px-4 py-3 ${
                        assoc.is_enabled ? 'border-divider-subtle bg-background-default' : 'border-divider-subtle bg-background-section opacity-60'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <RiDatabase2Line className="h-5 w-5 text-text-tertiary" />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-text-primary">
                              {assoc.datasource_name || '未知数据源'}
                            </span>
                            {assoc.datasource_type && (
                              <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${typeBadgeColors[assoc.datasource_type]}`}>
                                {typeLabels[assoc.datasource_type]}
                              </span>
                            )}
                            {assoc.datasource_status && (
                              <StatusBadge
                                status={assoc.datasource_status}
                                statusConfig={{
                                  active: { label: '正常', color: 'bg-util-colors-green-green-500' },
                                  inactive: { label: '停用', color: 'bg-util-colors-grey-grey-500' },
                                  creating: { label: '创建中', color: 'bg-util-colors-blue-blue-500' },
                                  error: { label: '异常', color: 'bg-util-colors-red-red-500' },
                                }}
                              />
                            )}
                          </div>
                          <div className="text-xs text-text-tertiary">
                            目标表: <span className="font-mono">{assoc.target_table}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleToggle(assoc)}
                          className={`relative h-5 w-9 rounded-full transition-colors ${
                            assoc.is_enabled ? 'bg-components-button-primary-bg' : 'bg-components-toggle-bg'
                          }`}
                        >
                          <span
                            className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
                              assoc.is_enabled ? 'translate-x-4' : ''
                            }`}
                          />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedAssoc(assoc)
                            setShowDeleteConfirm(true)
                          }}
                          className="flex h-7 w-7 items-center justify-center rounded text-text-tertiary hover:bg-state-destructive-hover hover:text-text-destructive"
                        >
                          <RiDeleteBinLine className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
      </div>

      {/* Add Modal */}
      <Modal isShow={showAddModal} onClose={() => setShowAddModal(false)} className="!max-w-md">
        <div className="p-6">
          <div className="mb-6 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-text-primary">添加数据源</h3>
            <button onClick={() => setShowAddModal(false)} className="text-text-tertiary hover:text-text-secondary">
              <RiCloseLine className="h-5 w-5" />
            </button>
          </div>
          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">选择数据源</label>
              {availableDatasources.length > 0
                ? (
                    <SimpleSelect
                      className="w-full"
                      defaultValue={selectedDsId}
                      items={availableDatasources.map(ds => ({
                        value: ds.id,
                        name: `${ds.name} (${typeLabels[ds.type]})`,
                      }))}
                      onSelect={item => setSelectedDsId(item.value as string)}
                    />
                  )
                : (
                    <p className="text-sm text-text-tertiary">没有可用的数据源，请先创建数据源</p>
                  )}
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">目标表名 / 集合名</label>
              <Input
                value={targetTable}
                onChange={e => setTargetTable(e.target.value)}
                placeholder="例如: articles 或 spider_results"
              />
            </div>
            <div className="flex justify-end gap-3 pt-4">
              <Button variant="secondary" onClick={() => setShowAddModal(false)}>取消</Button>
              <Button
                variant="primary"
                onClick={handleAdd}
                disabled={!selectedDsId || !targetTable}
                loading={addMutation.isPending}
              >
                添加
              </Button>
            </div>
          </div>
        </div>
      </Modal>

      {/* Delete Confirm */}
      <Confirm
        isShow={showDeleteConfirm}
        onCancel={() => {
          setShowDeleteConfirm(false)
          setSelectedAssoc(null)
        }}
        onConfirm={handleRemove}
        isLoading={removeMutation.isPending}
        title="确认移除"
        content={`确定要移除数据源 "${selectedAssoc?.datasource_name}" 的关联吗？已写入的数据不会被删除。`}
      />
    </div>
  )
}

export default DataSourcesTab
