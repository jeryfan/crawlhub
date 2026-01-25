'use client'
import type { FC } from 'react'
import { cn } from '@/utils/classnames'
import { basePath } from '@/utils/var'

type LogoSiteProps = {
  className?: string
}

const LogoSite: FC<LogoSiteProps> = ({ className }) => {
  return (
    <img
      src={`${basePath}/logo/logo.svg`}
      className={cn('block h-[22px] w-auto', className)}
      alt="FastAPI Template"
    />
  )
}

export default LogoSite
