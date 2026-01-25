'use client'

import { RiCloseLine, RiPlayFill, RiVideoLine } from '@remixicon/react'
import { useRef, useState } from 'react'
import Modal from '@/app/components/base/modal'
import { cn } from '@/utils/classnames'

export type VideoCellProps = {
  /** 视频 URL */
  src: string | null
  /** 封面图 URL */
  poster?: string
  /** 标题 */
  title?: string
  /** 缩略图大小 */
  size?: number | { width: number, height: number }
  /** 额外的类名 */
  className?: string
}

/**
 * 视频单元格组件
 *
 * 用于表格中展示视频缩略图，点击打开视频播放器弹窗
 *
 * @example
 * <VideoCell
 *   src={row.original.video_url}
 *   poster={row.original.thumbnail_url}
 *   title={row.original.name}
 * />
 */
const VideoCell = ({
  src,
  poster,
  title,
  size = 60,
  className,
}: VideoCellProps) => {
  const [showModal, setShowModal] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  const width = typeof size === 'number' ? size : size.width
  const height = typeof size === 'number' ? size : size.height

  const handleCloseModal = () => {
    setShowModal(false)
    // 关闭时暂停视频
    if (videoRef.current)
      videoRef.current.pause()
  }

  if (!src) {
    return (
      <div
        className={cn(
          'flex items-center justify-center rounded bg-background-section',
          className,
        )}
        style={{ width, height }}
      >
        <RiVideoLine className="h-5 w-5 text-text-quaternary" />
      </div>
    )
  }

  return (
    <>
      <div
        className={cn(
          'group relative cursor-pointer overflow-hidden rounded',
          className,
        )}
        style={{ width, height }}
        onClick={() => setShowModal(true)}
      >
        {poster
          ? (
              <img
                src={poster}
                alt={title || 'Video thumbnail'}
                className="h-full w-full object-cover"
              />
            )
          : (
              <div className="flex h-full w-full items-center justify-center bg-background-section">
                <RiVideoLine className="h-6 w-6 text-text-quaternary" />
              </div>
            )}

        {/* 播放按钮遮罩 */}
        <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 transition-opacity group-hover:opacity-100">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/90">
            <RiPlayFill className="h-4 w-4 text-gray-900" />
          </div>
        </div>
      </div>

      {/* 视频播放弹窗 */}
      <Modal
        isShow={showModal}
        onClose={handleCloseModal}
        className="!max-w-4xl"
      >
        <div className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="truncate text-lg font-semibold text-text-primary">
              {title || '视频播放'}
            </h3>
            <button
              onClick={handleCloseModal}
              className="text-text-tertiary hover:text-text-secondary"
            >
              <RiCloseLine className="h-5 w-5" />
            </button>
          </div>

          <video
            ref={videoRef}
            src={src}
            poster={poster}
            controls
            autoPlay
            className="w-full rounded"
            style={{ maxHeight: '70vh' }}
          >
            您的浏览器不支持视频播放
          </video>
        </div>
      </Modal>
    </>
  )
}

export default VideoCell
