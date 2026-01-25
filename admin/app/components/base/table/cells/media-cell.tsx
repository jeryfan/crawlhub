'use client'

import AudioCell from './audio-cell'
import ImageCell from './image-cell'
import VideoCell from './video-cell'

export type MediaType = 'image' | 'audio' | 'video'

export type MediaCellProps = {
  /** 媒体类型 */
  type: MediaType
  /** 媒体 URL */
  src: string | null
  /** 图片替代文本或音频/视频标题 */
  title?: string
  /** 封面图（仅视频） */
  poster?: string
  /** 大小（图片/视频） */
  size?: number | { width: number, height: number }
  /** 点击回调（仅图片） */
  onClick?: () => void
  /** 额外的类名 */
  className?: string
}

/**
 * 通用媒体单元格组件
 *
 * 根据媒体类型自动选择渲染组件
 *
 * @example
 * // 自动根据类型渲染
 * <MediaCell
 *   type={row.original.media_type}
 *   src={row.original.media_url}
 *   title={row.original.name}
 * />
 *
 * @example
 * // 图片类型
 * <MediaCell type="image" src={imageUrl} onClick={() => openLightbox()} />
 *
 * @example
 * // 视频类型
 * <MediaCell type="video" src={videoUrl} poster={thumbnailUrl} />
 */
const MediaCell = ({
  type,
  src,
  title,
  poster,
  size,
  onClick,
  className,
}: MediaCellProps) => {
  switch (type) {
    case 'image':
      return (
        <ImageCell
          src={src}
          alt={title}
          size={size}
          onClick={onClick}
          className={className}
        />
      )

    case 'audio':
      return (
        <AudioCell
          src={src}
          title={title}
          className={className}
        />
      )

    case 'video':
      return (
        <VideoCell
          src={src}
          poster={poster}
          title={title}
          size={size}
          className={className}
        />
      )

    default:
      return null
  }
}

export default MediaCell
