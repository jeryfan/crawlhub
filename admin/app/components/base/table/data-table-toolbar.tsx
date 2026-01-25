'use client'

import type { ReactNode } from 'react'
import { RiSearchLine } from '@remixicon/react'
import { cn } from '@/utils/classnames'
import Button from '../button'
import Input from '../input'

export type DataTableToolbarProps = {
  /** 搜索值 */
  searchValue?: string
  /** 搜索占位符 */
  searchPlaceholder?: string
  /** 搜索值变化回调 */
  onSearchChange?: (value: string) => void
  /** 搜索提交回调（按回车或点击搜索按钮） */
  onSearch?: () => void
  /** 筛选器插槽 */
  filterSlot?: ReactNode
  /** 批量操作插槽 */
  bulkActionsSlot?: ReactNode
  /** 选中数量（用于显示批量操作） */
  selectedCount?: number
  /** 右侧操作插槽（如新建按钮） */
  actionSlot?: ReactNode
  /** 额外的 CSS 类名 */
  className?: string
}

/**
 * 数据表格工具栏组件
 *
 * 提供搜索、筛选、批量操作等功能的统一布局。
 *
 * @example
 * <DataTableToolbar
 *   searchValue={keyword}
 *   searchPlaceholder="搜索用户"
 *   onSearchChange={setKeyword}
 *   onSearch={handleSearch}
 *   filterSlot={
 *     <SimpleSelect items={statusOptions} onSelect={handleStatusFilter} />
 *   }
 *   actionSlot={
 *     <Button variant="primary" onClick={handleCreate}>
 *       <RiAddLine className="w-4 h-4 mr-1" />
 *       创建
 *     </Button>
 *   }
 *   selectedCount={selectedIds.length}
 *   bulkActionsSlot={
 *     <Button variant="warning" onClick={handleBulkDelete}>
 *       批量删除
 *     </Button>
 *   }
 * />
 */
const DataTableToolbar = ({
  searchValue,
  searchPlaceholder = '搜索...',
  onSearchChange,
  onSearch,
  filterSlot,
  bulkActionsSlot,
  selectedCount = 0,
  actionSlot,
  className,
}: DataTableToolbarProps) => {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter')
      onSearch?.()
  }

  return (
    <div className={cn('mb-4 flex items-center gap-4', className)}>
      {/* 搜索框 */}
      {onSearchChange && (
        <div className="relative max-w-md flex-1">
          <RiSearchLine className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-quaternary" />
          <Input
            className="pl-9"
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={e => onSearchChange(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
      )}

      {/* 筛选器 */}
      {filterSlot}

      {/* 搜索按钮 */}
      {onSearch && (
        <Button variant="secondary" onClick={onSearch}>
          搜索
        </Button>
      )}

      {/* 批量操作 */}
      {selectedCount > 0 && bulkActionsSlot && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-text-tertiary">
            已选
            {' '}
            {selectedCount}
            {' '}
            项
          </span>
          {bulkActionsSlot}
        </div>
      )}

      {/* 右侧操作 */}
      {actionSlot && <div className="ml-auto">{actionSlot}</div>}
    </div>
  )
}

export default DataTableToolbar
