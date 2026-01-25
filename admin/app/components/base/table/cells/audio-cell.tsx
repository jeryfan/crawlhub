'use client'

import { RiPauseFill, RiPlayFill, RiVolumeUpLine } from '@remixicon/react'
import { useEffect, useRef, useState } from 'react'
import { cn } from '@/utils/classnames'

export type AudioCellProps = {
  /** 音频 URL */
  src: string | null
  /** 标题（用于显示） */
  title?: string
  /** 额外的类名 */
  className?: string
}

/**
 * 音频单元格组件
 *
 * 用于表格中展示迷你音频播放器
 *
 * @example
 * <AudioCell
 *   src={row.original.audio_url}
 *   title={row.original.name}
 * />
 */
const AudioCell = ({ src, title, className }: AudioCellProps) => {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)

  useEffect(() => {
    const audio = audioRef.current
    if (!audio)
      return

    const handleLoadedMetadata = () => {
      setDuration(audio.duration)
    }

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime)
    }

    const handleEnded = () => {
      setIsPlaying(false)
      setCurrentTime(0)
    }

    audio.addEventListener('loadedmetadata', handleLoadedMetadata)
    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('ended', handleEnded)

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('ended', handleEnded)
    }
  }, [src])

  const togglePlay = () => {
    const audio = audioRef.current
    if (!audio)
      return

    if (isPlaying)
      audio.pause()
    else audio.play()

    setIsPlaying(!isPlaying)
  }

  const formatTime = (time: number) => {
    if (!Number.isFinite(time) || Number.isNaN(time))
      return '0:00'
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  if (!src) {
    return (
      <div
        className={cn(
          'flex items-center gap-2 rounded bg-background-section px-2 py-1.5 text-text-quaternary',
          className,
        )}
      >
        <RiVolumeUpLine className="h-4 w-4" />
        <span className="text-sm">-</span>
      </div>
    )
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <audio ref={audioRef} src={src} preload="metadata" />

      <button
        onClick={togglePlay}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-50 text-primary-600 transition-colors hover:bg-primary-100"
      >
        {isPlaying
          ? (
              <RiPauseFill className="h-4 w-4" />
            )
          : (
              <RiPlayFill className="h-4 w-4" />
            )}
      </button>

      <div className="min-w-0 flex-1">
        {title && (
          <div className="truncate text-sm text-text-secondary">{title}</div>
        )}
        <div className="flex items-center gap-2">
          <div className="h-1 flex-1 overflow-hidden rounded-full bg-background-section">
            <div
              className="h-full bg-primary-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="whitespace-nowrap text-xs text-text-quaternary">
            {formatTime(currentTime)}
            {' '}
            /
            {formatTime(duration)}
          </span>
        </div>
      </div>
    </div>
  )
}

export default AudioCell
