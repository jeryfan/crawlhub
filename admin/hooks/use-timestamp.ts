'use client'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useCallback } from 'react'
import { useAppContext } from '@/context/app-context'

dayjs.extend(utc)
dayjs.extend(timezone)

const useTimestamp = () => {
  const { userProfile: { timezone } } = useAppContext()

  // 格式化 Unix 时间戳（自定义格式）
  const formatTime = useCallback((value: number, format: string) => {
    return dayjs.unix(value).tz(timezone).format(format)
  }, [timezone])

  // 格式化 ISO 日期字符串（自定义格式）
  const formatDate = useCallback((value: string, format: string) => {
    return dayjs(value).tz(timezone).format(format)
  }, [timezone])

  // 格式化日期时间 YYYY/MM/DD HH:mm
  const formatDateTime = useCallback((value: string | null | undefined): string => {
    if (!value)
      return '-'
    return dayjs(value).tz(timezone).format('YYYY/MM/DD HH:mm')
  }, [timezone])

  // 格式化日期 YYYY/MM/DD
  const formatDateOnly = useCallback((value: string | null | undefined): string => {
    if (!value)
      return '-'
    return dayjs(value).tz(timezone).format('YYYY/MM/DD')
  }, [timezone])

  // 格式化完整日期时间 YYYY/MM/DD HH:mm:ss
  const formatDateTimeFull = useCallback((value: string | null | undefined): string => {
    if (!value)
      return '-'
    return dayjs(value).tz(timezone).format('YYYY/MM/DD HH:mm:ss')
  }, [timezone])

  return {
    formatTime,
    formatDate,
    formatDateTime,
    formatDateOnly,
    formatDateTimeFull,
  }
}

export default useTimestamp
