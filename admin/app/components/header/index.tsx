'use client'

import Link from 'next/link'
import FastAPILogo from '@/app/components/base/logo/fastapi-logo'
import { useBranding } from '@/context/branding-context'
import useBreakpoints, { MediaType } from '@/hooks/use-breakpoints'
import AccountDropdown from './account-dropdown'

const Header = () => {
  const media = useBreakpoints()
  const isMobile = media === MediaType.mobile
  const { config } = useBranding()

  // 使用配置的 Logo 或默认 Logo
  const renderLogo = (size: 'small' | 'medium') => {
    if (config?.enabled && config.workspace_logo) {
      return (
        <img
          src={config.workspace_logo}
          alt={config.application_title || '管理后台'}
          className={size === 'small' ? 'h-6' : 'h-8'}
        />
      )
    }
    return <FastAPILogo size={size} />
  }

  if (isMobile) {
    return (
      <div className="flex items-center justify-between px-4 py-2">
        <Link href="/dashboard">
          {renderLogo('small')}
        </Link>
        <AccountDropdown />
      </div>
    )
  }

  return (
    <div className="flex h-[56px] items-center justify-between px-4">
      <Link href="/dashboard" className="flex items-center">
        {renderLogo('medium')}
      </Link>
      <div className="flex items-center gap-2">
        {/* <EnvNav /> */}
        <AccountDropdown />
      </div>
    </div>
  )
}

export default Header
