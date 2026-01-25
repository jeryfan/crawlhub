import { cn } from '@/utils/classnames'

/**
 * 状态徽章配置项
 */
export type StatusConfig = {
  label: string
  color: string
}

/**
 * 预设状态配置
 */
const presetConfigs: Record<string, Record<string, StatusConfig>> = {
  'user': {
    active: { label: '活跃', color: 'bg-util-colors-green-green-500' },
    pending: { label: '待激活', color: 'bg-util-colors-yellow-yellow-500' },
    banned: { label: '禁用', color: 'bg-util-colors-red-red-500' },
    uninitialized: { label: '未初始化', color: 'bg-util-colors-gray-gray-500' },
    closed: { label: '已关闭', color: 'bg-util-colors-gray-gray-500' },
  },
  'admin': {
    active: { label: '活跃', color: 'bg-util-colors-green-green-500' },
    pending: { label: '待激活', color: 'bg-util-colors-yellow-yellow-500' },
    banned: { label: '禁用', color: 'bg-util-colors-red-red-500' },
  },
  'tenant': {
    normal: { label: '正常', color: 'bg-util-colors-green-green-500' },
    archive: { label: '归档', color: 'bg-util-colors-gray-gray-500' },
  },
  'invitation-code': {
    unused: { label: '未使用', color: 'bg-util-colors-green-green-500' },
    used: { label: '已使用', color: 'bg-util-colors-blue-blue-500' },
    deprecated: { label: '已作废', color: 'bg-util-colors-gray-gray-500' },
  },
}

export type StatusBadgeProps = {
  /** 状态值 */
  status: string
  /** 预设类型，使用预设的状态配置 */
  type?: 'user' | 'admin' | 'tenant' | 'invitation-code'
  /** 自定义状态配置，优先级高于 type */
  statusConfig?: Record<string, StatusConfig>
  /** 额外的 CSS 类名 */
  className?: string
}

/**
 * 状态徽章组件
 *
 * 用于显示各种状态的标识，支持预设类型和自定义配置。
 *
 * @example
 * // 使用预设类型
 * <StatusBadge status="active" type="user" />
 *
 * @example
 * // 使用自定义配置
 * <StatusBadge
 *   status="success"
 *   statusConfig={{
 *     success: { label: '成功', color: 'bg-green-500' },
 *     failed: { label: '失败', color: 'bg-red-500' },
 *   }}
 * />
 */
const StatusBadge = ({
  status,
  type,
  statusConfig,
  className,
}: StatusBadgeProps) => {
  // 获取状态配置：优先使用自定义配置，其次使用预设配置
  const configs = statusConfig || (type ? presetConfigs[type] : {})
  const config = configs[status] || {
    label: status,
    color: 'bg-util-colors-gray-gray-500',
  }

  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', config.color)} />
      <span className="text-sm text-text-secondary">{config.label}</span>
    </span>
  )
}

export default StatusBadge
