'use client'

import type { DataQueryParams } from '@/types/crawlhub'
import {
  RiDeleteBinLine,
  RiDownloadLine,
  RiRefreshLine,
} from '@remixicon/react'
import { useState } from 'react'
import Button from '@/app/components/base/button'
import Confirm from '@/app/components/base/confirm'
import Input from '@/app/components/base/input'
import { SimpleSelect } from '@/app/components/base/select'
import Toast from '@/app/components/base/toast'
import { useDeleteData, useSpiderData } from '@/service/use-crawlhub'
import { API_PREFIX } from '@/config'

const DataPage = () => {
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [spiderIdFilter, setSpiderIdFilter] = useState('')
  const [searchSpiderId, setSearchSpiderId] = useState('')
  const [isTestFilter, setIsTestFilter] = useState<string>('all')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const params: DataQueryParams = {
    page,
    page_size: pageSize,
  }
  if (searchSpiderId) params.spider_id = searchSpiderId
  if (isTestFilter === 'test') params.is_test = true
  if (isTestFilter === 'prod') params.is_test = false

  const { data, isLoading, refetch } = useSpiderData(params)
  const deleteMutation = useDeleteData()

  const handleSearch = () => {
    setSearchSpiderId(spiderIdFilter)
    setPage(1)
  }

  const handleDelete = async () => {
    if (!searchSpiderId) {
      Toast.notify({ type: 'error', message: '请先指定爬虫ID' })
      return
    }
    try {
      await deleteMutation.mutateAsync({ spider_id: searchSpiderId })
      Toast.notify({ type: 'success', message: '数据已删除' })
      setShowDeleteConfirm(false)
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: '删除失败' })
    }
  }

  const handleExport = (format: 'json' | 'csv') => {
    const exportParams = new URLSearchParams()
    if (searchSpiderId) exportParams.set('spider_id', searchSpiderId)
    const url = `${API_PREFIX}/crawlhub/data/export/${format}?${exportParams.toString()}`
    window.open(url, '_blank')
  }

  const items = data?.items || []
  const fieldKeys = items.length > 0
    ? Object.keys(items[0]).filter(k => !k.startsWith('_'))
    : []

  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">数据管理</h1>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="small" onClick={() => handleExport('json')}>
            <RiDownloadLine className="mr-1 h-3.5 w-3.5" />
            导出 JSON
          </Button>
          <Button variant="ghost" size="small" onClick={() => handleExport('csv')}>
            <RiDownloadLine className="mr-1 h-3.5 w-3.5" />
            导出 CSV
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex shrink-0 items-center gap-3">
        <div className="flex items-center gap-2">
          <Input
            value={spiderIdFilter}
            onChange={e => setSpiderIdFilter(e.target.value)}
            placeholder="按爬虫ID筛选"
            wrapperClassName="!w-64"
          />
          <Button variant="secondary" size="small" onClick={handleSearch}>搜索</Button>
        </div>
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
        <span className="text-sm text-text-tertiary">共 {data?.total || 0} 条</span>
        <div className="ml-auto flex items-center gap-2">
          {searchSpiderId && (
            <Button
              variant="ghost"
              size="small"
              destructive
              onClick={() => setShowDeleteConfirm(true)}
            >
              <RiDeleteBinLine className="mr-1 h-3.5 w-3.5" />
              清空
            </Button>
          )}
          <Button variant="ghost" size="small" onClick={() => refetch()}>
            <RiRefreshLine className="mr-1 h-3.5 w-3.5" />
            刷新
          </Button>
        </div>
      </div>

      {/* Data Table */}
      <div className="flex-1 overflow-auto">
        {isLoading
          ? <div className="py-12 text-center text-sm text-text-tertiary">加载中...</div>
          : items.length === 0
            ? <div className="py-12 text-center text-sm text-text-tertiary">暂无数据</div>
            : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-divider-subtle bg-background-section">
                        {fieldKeys.map(key => (
                          <th
                            key={key}
                            className="whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-text-tertiary"
                          >
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item, i) => (
                        <tr key={i} className="border-b border-divider-subtle hover:bg-state-base-hover">
                          {fieldKeys.map(key => (
                            <td
                              key={key}
                              className="max-w-xs truncate whitespace-nowrap px-3 py-2 text-text-secondary"
                              title={String(item[key] ?? '')}
                            >
                              {typeof item[key] === 'object'
                                ? JSON.stringify(item[key])
                                : String(item[key] ?? '-')}
                            </td>
                          ))}
                        </tr>
                      ))}
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
            <Button variant="secondary" size="small" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
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

      <Confirm
        isShow={showDeleteConfirm}
        onCancel={() => setShowDeleteConfirm(false)}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
        title="确认清空数据"
        type="danger"
        content="确定要清空该爬虫的所有采集数据吗？此操作不可恢复。"
      />
    </>
  )
}

export default DataPage
