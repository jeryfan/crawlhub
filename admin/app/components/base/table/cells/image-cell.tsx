'use client'

import { RiImageLine } from '@remixicon/react'
import { useState } from 'react'
import { cn } from '@/utils/classnames'

export type ImageCellProps = {
  /** 图片 URL */
  src: string | null
  /** 替代文本 */
  alt?: string
  /** 图片大小 */
  size?: number | { width: number, height: number }
  /** 自定义占位符 */
  fallback?: React.ReactNode
  /** 点击回调（用于查看大图） */
  onClick?: () => void
  /** 额外的类名 */
  className?: string
}

/**
 * 图片单元格组件
 *
 * 用于表格中展示图片缩略图，支持点击查看大图
 *
 * @example
 * <ImageCell
 *   src={row.original.thumbnail_url}
 *   alt={row.original.name}
 *   onClick={() => openLightbox(row.original.image_url)}
 * />
 */
const ImageCell = ({
  src,
  alt,
  size = 40,
  fallback,
  onClick,
  className,
}: ImageCellProps) => {
  const [error, setError] = useState(false)

  const width = typeof size === 'number' ? size : size.width
  const height = typeof size === 'number' ? size : size.height

  // 无图片或加载失败时显示占位符
  if (!src || error) {
    return (
      <div
        className={cn(
          'flex items-center justify-center rounded bg-background-section',
          className,
        )}
        style={{ width, height }}
      >
        {fallback || <RiImageLine className="h-5 w-5 text-text-quaternary" />}
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={alt || ''}
      className={cn(
        'rounded object-cover',
        onClick && 'cursor-pointer transition-opacity hover:opacity-80',
        className,
      )}
      style={{ width, height }}
      onClick={onClick}
      onError={() => setError(true)}
    />
  )
}

export default ImageCell
