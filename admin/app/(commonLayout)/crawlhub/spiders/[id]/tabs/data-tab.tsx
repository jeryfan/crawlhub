'use client'

import type { DataQueryParams } from '@/types/crawlhub'
import {
  RiCloseLine,
  RiDeleteBinLine,
  RiDownloadLine,
  RiFileCopyLine,
  RiRefreshLine,
} from '@remixicon/react'
import copy from 'copy-to-clipboard'
import { useCallback, useEffect, useMemo, useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import { SimpleSelect } from '@/app/components/base/select'
import Toast from '@/app/components/base/toast'
import { useDeleteData, useSpiderData, useSpider } from '@/service/use-crawlhub'
import { API_PREFIX } from '@/config'

type DataTabProps = {
  spiderId: string
  isActive?: boolean
}

// ── Helpers ──

/** Flatten each item's `data` field into top-level keys for display. */
function flattenItem(item: Record<string, any>): Record<string, any> {
  const data = item.data
  if (data && typeof data === 'object' && !Array.isArray(data))
    return { ...data }
  return { data }
}

/** Collect unique data field keys across all items (stable order from first appearance). */
function collectDataKeys(items: Record<string, any>[]): string[] {
  const seen = new Set<string>()
  const keys: string[] = []
  for (const item of items) {
    const flat = flattenItem(item)
    for (const k of Object.keys(flat)) {
      if (!seen.has(k)) {
        seen.add(k)
        keys.push(k)
      }
    }
  }
  return keys
}

/** Format a cell value for the table. */
function formatCell(value: unknown): string {
  if (value === null || value === undefined)
    return '-'
  if (typeof value === 'object')
    return JSON.stringify(value)
  return String(value)
}

/** Render value with syntax-colored JSON. */
function JsonValue({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null)
    return <span className="text-text-quaternary">null</span>
  if (value === undefined)
    return <span className="text-text-quaternary">undefined</span>
  if (typeof value === 'boolean')
    return <span className="text-util-colors-orange-orange-600">{String(value)}</span>
  if (typeof value === 'number')
    return <span className="text-util-colors-blue-blue-600">{value}</span>
  if (typeof value === 'string') {
    // Show URLs as clickable links
    if (value.startsWith('http://') || value.startsWith('https://'))
      return <a href={value} target="_blank" rel="noreferrer" className="text-text-accent hover:underline break-all">&quot;{value}&quot;</a>
    return <span className="text-util-colors-green-green-600 break-all">&quot;{value}&quot;</span>
  }
  if (Array.isArray(value)) {
    if (value.length === 0)
      return <span className="text-text-tertiary">[]</span>
    return (
      <div className="pl-4">
        <span className="text-text-secondary">[</span>
        {value.map((v, i) => (
          <div key={i} className="pl-2">
            <JsonValue value={v} depth={depth + 1} />
            {i < value.length - 1 && <span className="text-text-quaternary">,</span>}
          </div>
        ))}
        <span className="text-text-secondary">]</span>
      </div>
    )
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (entries.length === 0)
      return <span className="text-text-tertiary">{'{}'}</span>
    return (
      <div className="pl-4">
        <span className="text-text-secondary">{'{'}</span>
        {entries.map(([k, v], i) => (
          <div key={k} className="pl-2">
            <span className="text-text-accent-secondary">&quot;{k}&quot;</span>
            <span className="text-text-quaternary">: </span>
            <JsonValue value={v} depth={depth + 1} />
            {i < entries.length - 1 && <span className="text-text-quaternary">,</span>}
          </div>
        ))}
        <span className="text-text-secondary">{'}'}</span>
      </div>
    )
  }
  return <span>{String(value)}</span>
}

// ── Detail Panel ──

function DetailPanel({ item, onClose }: { item: Record<string, any>; onClose: () => void }) {
  const [showRaw, setShowRaw] = useState(false)
  const flat = flattenItem(item)
  const jsonStr = JSON.stringify(showRaw ? item : flat, null, 2)

  const handleCopy = () => {
    copy(jsonStr)
    Toast.notify({ type: 'success', message: '已复制到剪贴板' })
  }

  return (
    <div className="flex h-full w-[420px] shrink-0 flex-col border-l border-divider-subtle bg-components-panel-bg">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-divider-subtle px-4 py-3">
        <h3 className="text-sm font-semibold text-text-primary">数据详情</h3>
        <div className="flex items-center gap-1">
          <button
            className="rounded-md p-1 hover:bg-state-base-hover"
            onClick={handleCopy}
            title="复制 JSON"
          >
            <RiFileCopyLine className="h-4 w-4 text-text-tertiary" />
          </button>
          <button
            className="rounded-md p-1 hover:bg-state-base-hover"
            onClick={onClose}
          >
            <RiCloseLine className="h-4 w-4 text-text-tertiary" />
          </button>
        </div>
      </div>

      {/* Metadata */}
      <div className="space-y-1 border-b border-divider-subtle px-4 py-3">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-text-quaternary w-16 shrink-0">Task ID</span>
          <span className="text-text-secondary font-mono truncate">{item.task_id}</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-text-quaternary w-16 shrink-0">类型</span>
          <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${item.is_test ? 'bg-util-colors-orange-orange-50 text-util-colors-orange-orange-600' : 'bg-util-colors-green-green-50 text-util-colors-green-green-600'}`}>
            {item.is_test ? '测试' : '生产'}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-text-quaternary w-16 shrink-0">采集时间</span>
          <span className="text-text-secondary">{item.created_at ? new Date(item.created_at).toLocaleString() : '-'}</span>
        </div>
      </div>

      {/* JSON Content */}
      <div className="flex items-center justify-between border-b border-divider-subtle px-4 py-2">
        <div className="flex items-center gap-1">
          <button
            className={`rounded px-2 py-1 text-xs ${!showRaw ? 'bg-components-button-secondary-bg text-text-primary font-medium' : 'text-text-tertiary hover:bg-state-base-hover'}`}
            onClick={() => setShowRaw(false)}
          >
            采集数据
          </button>
          <button
            className={`rounded px-2 py-1 text-xs ${showRaw ? 'bg-components-button-secondary-bg text-text-primary font-medium' : 'text-text-tertiary hover:bg-state-base-hover'}`}
            onClick={() => setShowRaw(true)}
          >
            完整记录
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-auto px-4 py-3">
        <div className="text-[13px] font-mono leading-relaxed text-text-secondary">
          <JsonValue value={showRaw ? item : flat} />
        </div>
      </div>
    </div>
  )
}

// ── Main Component ──

const DataTab = ({ spiderId, isActive }: DataTabProps) => {
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [isTestFilter, setIsTestFilter] = useState<string>('all')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [selectedItem, setSelectedItem] = useState<Record<string, any> | null>(null)

  const params: DataQueryParams = {
    spider_id: spiderId,
    page,
    page_size: pageSize,
  }
  if (isTestFilter === 'test') params.is_test = true
  if (isTestFilter === 'prod') params.is_test = false

  const { data, isLoading, refetch } = useSpiderData(params)
  const { data: spider } = useSpider(spiderId)
  const deleteMutation = useDeleteData()

  // 切换到此 tab 时刷新数据
  useEffect(() => {
    if (isActive)
      refetch()
  }, [isActive, refetch])

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync({ spider_id: spiderId })
      Toast.notify({ type: 'success', message: '数据已删除' })
      setShowDeleteConfirm(false)
      setSelectedItem(null)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const handleExport = (format: 'json' | 'csv') => {
    const url = `${API_PREFIX}/crawlhub/data/export/${format}?spider_id=${spiderId}`
    window.open(url, '_blank')
  }

  const items = data?.items || []
  const dataKeys = useMemo(() => collectDataKeys(items), [items])

  const handleRowClick = useCallback((item: Record<string, any>) => {
    setSelectedItem(prev => prev === item ? null : item)
  }, [])

  return (
    <div className="flex h-full">
      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Toolbar */}
        <div className="mb-3 flex shrink-0 items-center justify-between">
          <div className="flex items-center gap-2">
            <SimpleSelect
              className="w-32"
              defaultValue={isTestFilter}
              items={[
                { value: 'all', name: '全部' },
                { value: 'prod', name: '生产数据' },
                { value: 'test', name: '测试数据' },
              ]}
              onSelect={item => {
                setIsTestFilter(item.value as string)
                setPage(1)
              }}
            />
            <span className="text-sm text-text-tertiary">
              共 {data?.total || 0} 条
            </span>
            {spider?.start_url && (
              <span className="text-xs text-text-quaternary truncate max-w-[300px]" title={spider.start_url}>
                <a href={spider.start_url} target="_blank" rel="noreferrer" className="text-text-accent hover:underline">
                  {spider.start_url}
                </a>
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="small" onClick={() => handleExport('json')}>
              <RiDownloadLine className="mr-1 h-3.5 w-3.5" />
              JSON
            </Button>
            <Button variant="ghost" size="small" onClick={() => handleExport('csv')}>
              <RiDownloadLine className="mr-1 h-3.5 w-3.5" />
              CSV
            </Button>
            <Button
              variant="ghost"
              size="small"
              destructive
              onClick={() => setShowDeleteConfirm(true)}
            >
              <RiDeleteBinLine className="mr-1 h-3.5 w-3.5" />
              清空
            </Button>
            <Button variant="ghost" size="small" onClick={() => refetch()}>
              <RiRefreshLine className="mr-1 h-3.5 w-3.5" />
              刷新
            </Button>
          </div>
        </div>

        {/* Data Table */}
        <div className="flex-1 overflow-auto">
          {isLoading
            ? (
                <div className="py-12 text-center text-sm text-text-tertiary">加载中...</div>
              )
            : items.length === 0
              ? (
                  <div className="py-12 text-center text-sm text-text-tertiary">暂无数据</div>
                )
              : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-divider-subtle bg-background-section">
                          <th className="whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-text-tertiary">
                            类型
                          </th>
                          <th className="whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-text-tertiary">
                            Task ID
                          </th>
                          {dataKeys.map(key => (
                            <th
                              key={key}
                              className="whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-text-tertiary"
                            >
                              {key}
                            </th>
                          ))}
                          <th className="whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-text-tertiary">
                            采集时间
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {items.map((item, i) => {
                          const flat = flattenItem(item)
                          const isSelected = selectedItem === item
                          return (
                            <tr
                              key={i}
                              className={`border-b border-divider-subtle cursor-pointer transition-colors ${isSelected ? 'bg-state-accent-hover' : 'hover:bg-state-base-hover'}`}
                              onClick={() => handleRowClick(item)}
                            >
                              <td className="whitespace-nowrap px-3 py-2">
                                <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${item.is_test ? 'bg-util-colors-orange-orange-50 text-util-colors-orange-orange-600' : 'bg-util-colors-green-green-50 text-util-colors-green-green-600'}`}>
                                  {item.is_test ? '测试' : '生产'}
                                </span>
                              </td>
                              <td className="whitespace-nowrap px-3 py-2 text-xs text-text-tertiary font-mono" title={item.task_id}>
                                {item.task_id ? item.task_id.slice(0, 8) : '-'}
                              </td>
                              {dataKeys.map(key => {
                                const val = flat[key]
                                const display = formatCell(val)
                                const isLink = typeof val === 'string' && (val.startsWith('http://') || val.startsWith('https://'))
                                return (
                                  <td
                                    key={key}
                                    className="max-w-[240px] truncate whitespace-nowrap px-3 py-2 text-text-secondary"
                                    title={display}
                                  >
                                    {isLink
                                      ? (
                                          <a
                                            href={val}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="text-text-accent hover:underline"
                                            onClick={e => e.stopPropagation()}
                                          >
                                            {display}
                                          </a>
                                        )
                                      : display}
                                  </td>
                                )
                              })}
                              <td className="whitespace-nowrap px-3 py-2 text-xs text-text-quaternary">
                                {item.created_at ? new Date(item.created_at).toLocaleString() : '-'}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
        </div>

        {/* Pagination */}
        {(data?.total || 0) > pageSize && (
          <div className="mt-3 flex shrink-0 items-center justify-between border-t border-divider-subtle pt-3">
            <span className="text-xs text-text-tertiary">
              第 {page} / {data?.total_pages || 1} 页
            </span>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="small"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
              >
                上一页
              </Button>
              <Button
                variant="secondary"
                size="small"
                disabled={page >= (data?.total_pages || 1)}
                onClick={() => setPage(p => p + 1)}
              >
                下一页
              </Button>
            </div>
          </div>
        )}

        {/* Delete Confirm */}
        <Confirm
          isShow={showDeleteConfirm}
          onCancel={() => setShowDeleteConfirm(false)}
          onConfirm={handleDelete}
          isLoading={deleteMutation.isPending}
          title="确认清空数据"
          type="danger"
          content="确定要清空此爬虫的所有采集数据吗？此操作不可恢复。"
        />
      </div>

      {/* Detail Panel */}
      {selectedItem && (
        <DetailPanel
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
        />
      )}
    </div>
  )
}

export default DataTab
