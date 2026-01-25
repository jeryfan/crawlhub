'use client'

import Avatar from '@/app/components/base/avatar'
import { TruncatedText } from '@/app/components/base/table'
import { cn } from '@/utils/classnames'

export type AvatarCellProps = {
  /** 显示名称 */
  name: string
  /** 头像 URL */
  avatar: string | null
  /** 邮箱或副标题 */
  email?: string
  /** 头像大小 */
  size?: number
  /** 额外的容器类名 */
  className?: string
}

/**
 * 头像单元格组件
 *
 * 用于表格中展示用户/管理员信息，包含头像、名称和可选的邮箱
 *
 * @example
 * <AvatarCell
 *   name={row.original.name}
 *   avatar={row.original.avatar_url}
 *   email={row.original.email}
 * />
 */
const AvatarCell = ({
  name,
  avatar,
  email,
  size = 40,
  className,
}: AvatarCellProps) => {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <Avatar name={name} avatar={avatar} size={size} className="shrink-0" />
      <div className="min-w-0 flex-1">
        <TruncatedText
          text={name}
          textClassName="text-text-primary font-medium"
        />
        {email && (
          <TruncatedText
            text={email}
            textClassName="text-text-tertiary text-sm"
          />
        )}
      </div>
    </div>
  )
}

export default AvatarCell
