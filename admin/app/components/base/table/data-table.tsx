'use client'

import type { ColumnDef, RowSelectionState, SortingState } from '@tanstack/react-table'
import type { ReactNode } from 'react'
import { RiArrowDownSLine, RiArrowUpSLine } from '@remixicon/react'
import {

  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useCallback, useMemo } from 'react'
import { cn } from '@/utils/classnames'
import Checkbox from '../checkbox'
import Pagination from '../pagination'
import Skeleton from '../skeleton'

// 扩展 ColumnDef 的 meta 类型
declare module '@tanstack/react-table' {
  // eslint-disable-next-line unused-imports/no-unused-vars, ts/consistent-type-definitions
  interface ColumnMeta<TData, TValue> {
    headerClassName?: string
    cellClassName?: string
    skeletonClassName?: string
    /** 固定列位置 */
    sticky?: 'left' | 'right'
  }
}

/**
 * 分页配置
 */
export type PaginationConfig = {
  /** 当前页码（从 1 开始） */
  page: number
  /** 每页条数 */
  pageSize: number
  /** 总条数 */
  total: number
  /** 页码改变回调 */
  onChange: (page: number) => void
  /** 每页条数改变回调 */
  onPageSizeChange?: (size: number) => void
}

/**
 * DataTable 组件属性
 */
export type DataTableProps<TData> = {
  /** 列定义 */
  columns: ColumnDef<TData, unknown>[]
  /** 数据源 */
  data: TData[]
  /** 是否加载中 */
  isLoading?: boolean
  /** 加载时显示的骨架屏行数 */
  loadingRowCount?: number
  /** 空数据时显示的文本 */
  emptyText?: string
  /** 空数据时显示的图标 */
  emptyIcon?: ReactNode

  // 行选择
  /** 是否启用行选择 */
  enableRowSelection?: boolean
  /** 行选择状态 */
  rowSelection?: RowSelectionState
  /** 行选择改变回调 */
  onRowSelectionChange?: (selection: RowSelectionState) => void
  /** 获取行 ID 的函数 */
  getRowId?: (row: TData) => string

  // 服务端排序
  /** 是否启用排序 */
  enableSorting?: boolean
  /** 排序状态 */
  sorting?: SortingState
  /** 排序改变回调（服务端排序） */
  onSortingChange?: (sorting: SortingState) => void

  // 分页
  /** 分页配置 */
  pagination?: PaginationConfig

  // 事件
  /** 行点击回调 */
  onRowClick?: (row: TData) => void

  // 样式
  /** 容器类名 */
  className?: string
  /** 表头类名 */
  headerClassName?: string
  /** 行类名（可以是字符串或根据行数据返回类名的函数） */
  rowClassName?: string | ((row: TData) => string)
  /** 是否使用固定表头（表头固定，内容区域滚动） */
  stickyHeader?: boolean
  /** 表格最大高度（仅在 stickyHeader 为 true 时生效），默认自动填充父容器 */
  maxHeight?: string | number
}

/**
 * 增强的 DataTable 组件
 *
 * 支持行选择、服务端排序、分页等功能，采用简洁的设计风格。
 */
function DataTable<TData>({
  columns,
  data,
  isLoading = false,
  loadingRowCount = 5,
  emptyText = '暂无数据',
  emptyIcon,
  // 行选择
  enableRowSelection = false,
  rowSelection = {},
  onRowSelectionChange,
  getRowId,
  // 排序
  enableSorting = false,
  sorting = [],
  onSortingChange,
  // 分页
  pagination,
  // 事件
  onRowClick,
  // 样式
  className,
  headerClassName,
  rowClassName,
  stickyHeader = false,
  maxHeight,
}: DataTableProps<TData>) {
  // 处理排序点击
  const handleSortingChange = useCallback(
    (columnId: string) => {
      if (!onSortingChange)
        return

      const existingSort = sorting.find(s => s.id === columnId)

      if (!existingSort) {
        // 第一次点击：升序
        onSortingChange([{ id: columnId, desc: false }])
      }
      else if (!existingSort.desc) {
        // 第二次点击：降序
        onSortingChange([{ id: columnId, desc: true }])
      }
      else {
        // 第三次点击：取消排序
        onSortingChange([])
      }
    },
    [sorting, onSortingChange],
  )

  // 处理全选
  const handleSelectAllChange = useCallback(() => {
    if (!onRowSelectionChange)
      return

    const allSelected = data.every((row, index) => {
      const rowId = getRowId ? getRowId(row) : String(index)
      return rowSelection[rowId]
    })

    if (allSelected) {
      // 取消全选
      onRowSelectionChange({})
    }
    else {
      // 全选
      const newSelection: RowSelectionState = {}
      data.forEach((row, index) => {
        const rowId = getRowId ? getRowId(row) : String(index)
        newSelection[rowId] = true
      })
      onRowSelectionChange(newSelection)
    }
  }, [data, rowSelection, onRowSelectionChange, getRowId])

  // 处理单行选择
  const handleRowSelectChange = useCallback(
    (rowId: string) => {
      if (!onRowSelectionChange)
        return

      const newSelection = { ...rowSelection }
      if (newSelection[rowId])
        delete newSelection[rowId]
      else newSelection[rowId] = true

      onRowSelectionChange(newSelection)
    },
    [rowSelection, onRowSelectionChange],
  )

  // 计算全选状态
  const selectAllState = useMemo(() => {
    if (data.length === 0)
      return { checked: false, indeterminate: false }

    const selectedCount = data.filter((row, index) => {
      const rowId = getRowId ? getRowId(row) : String(index)
      return rowSelection[rowId]
    }).length

    return {
      checked: selectedCount === data.length,
      indeterminate: selectedCount > 0 && selectedCount < data.length,
    }
  }, [data, rowSelection, getRowId])

  // 构建最终的列定义（包含选择列）
  const finalColumns = useMemo(() => {
    if (!enableRowSelection)
      return columns

    const selectionColumn: ColumnDef<TData, unknown> = {
      id: '__selection__',
      size: 48,
      header: () => (
        <Checkbox
          checked={selectAllState.checked}
          indeterminate={selectAllState.indeterminate}
          onCheck={handleSelectAllChange}
        />
      ),
      cell: ({ row }) => {
        const rowId = getRowId ? getRowId(row.original) : row.id
        return (
          <Checkbox
            checked={!!rowSelection[rowId]}
            onCheck={(e) => {
              e.stopPropagation()
              handleRowSelectChange(rowId)
            }}
          />
        )
      },
      meta: {
        skeletonClassName: 'h-4 w-4',
      },
    }

    return [selectionColumn, ...columns]
  }, [
    enableRowSelection,
    columns,
    selectAllState,
    handleSelectAllChange,
    rowSelection,
    handleRowSelectChange,
    getRowId,
  ])

  const table = useReactTable({
    data,
    columns: finalColumns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: getRowId
      ? (row, index) => getRowId(row) ?? String(index)
      : undefined,
    manualSorting: true,
    manualPagination: true,
    state: {
      sorting,
      rowSelection,
    },
  })

  const getRowClassName = (row: TData) => {
    if (typeof rowClassName === 'function')
      return rowClassName(row)

    return rowClassName
  }

  // 渲染排序图标
  const renderSortIcon = (columnId: string) => {
    const sort = sorting.find(s => s.id === columnId)

    return (
      <span className="ml-1 inline-flex flex-col -space-y-1">
        <RiArrowUpSLine
          className={cn(
            'h-3.5 w-3.5',
            sort && !sort.desc ? 'text-text-primary' : 'text-text-quaternary',
          )}
        />
        <RiArrowDownSLine
          className={cn(
            'h-3.5 w-3.5',
            sort && sort.desc ? 'text-text-primary' : 'text-text-quaternary',
          )}
        />
      </span>
    )
  }

  return (
    <div className={cn('flex w-full flex-col', stickyHeader && 'min-h-0 flex-1', className)}>
      <div
        className={cn('overflow-x-auto', stickyHeader && 'flex-1 overflow-y-auto')}
        style={maxHeight ? { maxHeight: typeof maxHeight === 'number' ? `${maxHeight}px` : maxHeight } : undefined}
      >
        <table className="w-full table-fixed bg-transparent">
          {/* 定义列宽 */}
          <colgroup>
            {finalColumns.map((column, index) => (
              <col
                key={index}
                style={{
                  width: column.size ? `${column.size}px` : undefined,
                }}
              />
            ))}
          </colgroup>
          <thead className={cn(
            'bg-background-section',
            stickyHeader && 'sticky top-0 z-[1]',
            headerClassName,
          )}
          >
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const canSort = enableSorting && header.column.getCanSort()
                  const isSortable
                    = canSort && header.column.id !== '__selection__'

                  return (
                    <th
                      key={header.id}
                      className={cn(
                        'px-4 py-3 text-left text-sm font-medium text-text-tertiary',
                        isSortable
                        && 'cursor-pointer select-none hover:text-text-secondary',
                        header.column.columnDef.meta?.headerClassName,
                        // Sticky 列样式
                        header.column.columnDef.meta?.sticky === 'right'
                        && 'sticky right-0 z-10 bg-background-section',
                        header.column.columnDef.meta?.sticky === 'left'
                        && 'sticky left-0 z-10 bg-background-section',
                      )}
                      style={{ width: header.column.columnDef.size }}
                      onClick={
                        isSortable
                          ? () => handleSortingChange(header.column.id)
                          : undefined
                      }
                    >
                      <div className="flex items-center">
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                        {isSortable && renderSortIcon(header.column.id)}
                      </div>
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>
          <tbody className="bg-transparent">
            {isLoading ? (
              // Loading skeleton rows
              Array.from({ length: loadingRowCount }).map((_, i) => (
                <tr
                  key={`skeleton-${i}`}
                  className="border-t border-divider-subtle"
                >
                  {finalColumns.map((column, j) => (
                    <td
                      key={`skeleton-${i}-${j}`}
                      className={cn(
                        'px-4 py-2',
                        // Sticky 列样式
                        column.meta?.sticky === 'right'
                        && 'sticky right-0 bg-white',
                        column.meta?.sticky === 'left'
                        && 'sticky left-0 bg-white',
                      )}
                    >
                      <Skeleton
                        className={cn(
                          'h-6',
                          column.meta?.skeletonClassName || 'w-24',
                        )}
                      />
                    </td>
                  ))}
                </tr>
              ))
            ) : table.getRowModel().rows.length > 0 ? (
              // Data rows
              table.getRowModel().rows.map((row) => {
                const rowId = getRowId ? getRowId(row.original) : row.id
                const isSelected = rowSelection[rowId]

                return (
                  <tr
                    key={row.id}
                    className={cn(
                      'group/row border-t border-divider-subtle transition-colors hover:bg-state-base-hover',
                      onRowClick && 'cursor-pointer',
                      isSelected && 'bg-state-accent-hover',
                      getRowClassName(row.original),
                    )}
                    onClick={() => onRowClick?.(row.original)}
                  >
                    {row.getVisibleCells().map(cell => (
                      <td
                        key={cell.id}
                        className={cn(
                          'px-4 py-2',
                          cell.column.columnDef.meta?.cellClassName,
                          // Sticky 列样式
                          cell.column.columnDef.meta?.sticky === 'right'
                          && 'sticky right-0 z-10 bg-white',
                          cell.column.columnDef.meta?.sticky === 'left'
                          && 'sticky left-0 z-10 bg-white',
                        )}
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </td>
                    ))}
                  </tr>
                )
              })
            ) : (
              // Empty state
              <tr>
                <td
                  colSpan={finalColumns.length}
                  className="px-4 py-12 text-center text-text-tertiary"
                >
                  <div className="flex flex-col items-center gap-2">
                    {emptyIcon}
                    <span>{emptyText}</span>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 分页 */}
      {pagination && pagination.total > pagination.pageSize && (
        <div className="flex shrink-0 justify-end">
          <Pagination
            current={pagination.page - 1}
            onChange={page => pagination.onChange(page + 1)}
            total={pagination.total}
            limit={pagination.pageSize}
            onLimitChange={pagination.onPageSizeChange}
          />
        </div>
      )}
    </div>
  )
}

export { DataTable }
export type { ColumnDef, RowSelectionState, SortingState }
