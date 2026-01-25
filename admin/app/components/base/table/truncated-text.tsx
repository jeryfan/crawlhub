'use client'

import { useEffect, useRef, useState } from 'react'
import Tooltip from '@/app/components/base/tooltip'
import { cn } from '@/utils/classnames'

export type TruncatedTextProps = {
  /** 要显示的文本 */
  text: string | null | undefined
  /** 最大宽度，默认不限制 */
  maxWidth?: number | string
  /** 最大行数，默认1行 */
  maxLines?: 1 | 2 | 3
  /** 额外的 CSS 类名 */
  className?: string
  /** 文本颜色类名 */
  textClassName?: string
}

/**
 * 截断文本组件
 *
 * 当文本超出容器宽度时自动截断并显示省略号，鼠标悬停时通过 Tooltip 显示完整内容。
 *
 * @example
 * // 单行截断
 * <TruncatedText text={longText} />
 *
 * @example
 * // 最多2行
 * <TruncatedText text={longText} maxLines={2} />
 *
 * @example
 * // 指定最大宽度
 * <TruncatedText text={longText} maxWidth={200} />
 */
const TruncatedText = ({
  text,
  maxWidth,
  maxLines = 1,
  className,
  textClassName,
}: TruncatedTextProps) => {
  const textRef = useRef<HTMLSpanElement>(null)
  const [isTruncated, setIsTruncated] = useState(false)

  useEffect(() => {
    const checkTruncation = () => {
      if (textRef.current) {
        const { scrollWidth, clientWidth, scrollHeight, clientHeight }
          = textRef.current
        // 检查是否被截断（水平或垂直）
        setIsTruncated(
          scrollWidth > clientWidth || scrollHeight > clientHeight,
        )
      }
    }

    checkTruncation()

    // 监听窗口变化重新检测
    window.addEventListener('resize', checkTruncation)
    return () => window.removeEventListener('resize', checkTruncation)
  }, [text])

  if (!text)
    return <span className={cn('text-text-quaternary', textClassName)}>-</span>

  const lineClampClass = {
    1: 'line-clamp-1',
    2: 'line-clamp-2',
    3: 'line-clamp-3',
  }[maxLines]

  const content = (
    <span
      ref={textRef}
      className={cn('block', lineClampClass, textClassName, className)}
      style={{
        maxWidth: maxWidth
          ? typeof maxWidth === 'number'
            ? `${maxWidth}px`
            : maxWidth
          : undefined,
      }}
    >
      {text}
    </span>
  )

  if (isTruncated) {
    return (
      <Tooltip
        popupContent={
          <div className="max-w-xs whitespace-pre-wrap break-words">{text}</div>
        }
        asChild={false}
      >
        {content}
      </Tooltip>
    )
  }

  return content
}

export default TruncatedText
