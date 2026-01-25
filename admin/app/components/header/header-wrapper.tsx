'use client'
import * as React from 'react'
import { cn } from '@/utils/classnames'
import s from './index.module.css'

type HeaderWrapperProps = {
  children: React.ReactNode
}

const HeaderWrapper = ({ children }: HeaderWrapperProps) => {
  return (
    <div
      className={cn(
        'sticky left-0 right-0 top-0 z-[15] flex min-h-[56px] shrink-0 grow-0 basis-auto flex-col',
        s.header,
        'border-b border-divider-subtle',
      )}
    >
      {children}
    </div>
  )
}
export default HeaderWrapper
