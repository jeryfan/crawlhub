import type { ColumnDef } from '@tanstack/react-table'
import type { ComponentType } from 'react'
import { cn } from '@/utils/classnames'

/**
 * 操作项配置
 */
export type ActionItem<TData> = {
  /** 图标组件 */
  icon: ComponentType<{ className?: string }>
  /** 操作标签（用于 title） */
  label: string
  /** 点击回调 */
  onClick: (row: TData) => void
  /** 是否隐藏（可以是布尔值或根据行数据判断的函数） */
  hidden?: boolean | ((row: TData) => boolean)
  /** 变体：danger 会使用红色悬停效果 */
  variant?: 'default' | 'danger'
}

/**
 * 操作列配置
 */
export type ActionColumnConfig<TData> = {
  /** 操作项列表 */
  actions: ActionItem<TData>[]
  /** 列头文本 */
  header?: string
  /** 列宽度 */
  width?: number
  /** 是否固定在右侧（默认 true） */
  sticky?: boolean
}

/**
 * 创建操作列
 *
 * @example
 * const actionColumn = createActionColumn<User>({
 *   actions: [
 *     { icon: RiEyeLine, label: '查看', onClick: (row) => handleView(row) },
 *     { icon: RiEditLine, label: '编辑', onClick: (row) => handleEdit(row) },
 *     { icon: RiDeleteBinLine, label: '删除', onClick: (row) => handleDelete(row), variant: 'danger' },
 *   ]
 * })
 */
export function createActionColumn<TData>(
  config: ActionColumnConfig<TData>,
): ColumnDef<TData, unknown> {
  const { actions, header = '操作', width, sticky = false } = config

  return {
    id: '__actions__',
    header,
    size: width,
    cell: ({ row }) => (
      <div className="flex items-center justify-center gap-1">
        {actions.map((action, index) => {
          // 判断是否隐藏
          const isHidden
            = typeof action.hidden === 'function'
              ? action.hidden(row.original)
              : action.hidden

          if (isHidden)
            return null

          const Icon = action.icon
          const isDanger = action.variant === 'danger'

          return (
            <button
              key={index}
              className={cn(
                'rounded p-1.5 transition-colors',
                isDanger
                  ? 'text-text-tertiary hover:bg-state-destructive-hover hover:text-util-colors-red-red-500'
                  : 'text-text-tertiary hover:bg-state-base-hover hover:text-text-secondary',
              )}
              onClick={(e) => {
                e.stopPropagation()
                action.onClick(row.original)
              }}
              title={action.label}
            >
              <Icon className="h-4 w-4" />
            </button>
          )
        })}
      </div>
    ),
    meta: {
      headerClassName: 'text-right',
      cellClassName: 'text-right',
      skeletonClassName: 'h-6 w-20 ml-auto',
      sticky: sticky ? 'right' : undefined,
    },
  }
}
