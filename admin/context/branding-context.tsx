'use client'

import type { ReactNode } from 'react'
import type { BrandingSettings } from '@/types/platform'
import {
  createContext,

  useContext,
  useEffect,
} from 'react'
import { useGeneralSettings } from '@/service/use-platform'
import { basePath } from '@/utils/var'

type BrandingContextValue = {
  config: BrandingSettings | undefined
  isLoading: boolean
}

const defaultBranding: BrandingSettings = {
  enabled: false,
  application_title: 'FastAPI Template',
  login_page_logo: '',
  workspace_logo: '',
  favicon: '',
  theme_color: '#1570EF',
}

const BrandingContext = createContext<BrandingContextValue>({
  config: defaultBranding,
  isLoading: true,
})

export const useBranding = () => {
  const context = useContext(BrandingContext)
  if (!context)
    throw new Error('useBranding must be used within BrandingProvider')

  return context
}

type BrandingProviderProps = {
  children: ReactNode
}

export const BrandingProvider = ({ children }: BrandingProviderProps) => {
  const { data: config, isLoading } = useGeneralSettings('admin')

  const branding = config?.branding ?? defaultBranding

  // 动态更新 favicon
  useEffect(() => {
    if (isLoading)
      return

    const faviconUrl = branding.enabled && branding.favicon
      ? branding.favicon
      : `${basePath}/favicon.svg`

    const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
    if (link) {
      link.href = faviconUrl
    }
    else {
      const newLink = document.createElement('link')
      newLink.rel = 'icon'
      newLink.href = faviconUrl
      document.head.appendChild(newLink)
    }
  }, [isLoading, branding.enabled, branding.favicon])

  // 动态更新页面标题
  useEffect(() => {
    if (isLoading)
      return

    const title = branding.enabled && branding.application_title
      ? branding.application_title
      : 'FastAPI Template'

    if (!document.title || document.title === 'FastAPI Template')
      document.title = title
  }, [isLoading, branding.enabled, branding.application_title])

  return (
    <BrandingContext.Provider value={{ config: branding, isLoading }}>
      {children}
    </BrandingContext.Provider>
  )
}

export default BrandingProvider
