'use client'

import type { FC, ReactNode } from 'react'
import type { SidebarContextValue } from '@/types/sidebar'
import { usePathname } from 'next/navigation'
import {
  createContext,

  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'

const SIDEBAR_COLLAPSED_KEY = 'sidebar-collapsed'
const COLLAPSE_BREAKPOINT = 1024

const SidebarContext = createContext<SidebarContextValue | null>(null)

export const useSidebar = () => {
  const context = useContext(SidebarContext)
  if (!context)
    throw new Error('useSidebar must be used within a SidebarProvider')

  return context
}

type SidebarProviderProps = {
  children: ReactNode
}

export const SidebarProvider: FC<SidebarProviderProps> = ({ children }) => {
  const pathname = usePathname()

  const [collapsed, setCollapsedState] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
      return stored ? JSON.parse(stored) : false
    }
    return false
  })

  const [openKeys, setOpenKeys] = useState<string[]>([])
  const [selectedKey, setSelectedKey] = useState<string>('')

  // Auto collapse on small screens
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < COLLAPSE_BREAKPOINT)
        setCollapsedState(true)
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Sync selected key with pathname
  useEffect(() => {
    setSelectedKey(pathname)
  }, [pathname])

  const setCollapsed = useCallback((value: boolean) => {
    setCollapsedState(value)
    if (typeof window !== 'undefined')
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, JSON.stringify(value))
  }, [])

  const toggleCollapsed = useCallback(() => {
    setCollapsed(!collapsed)
  }, [collapsed, setCollapsed])

  const toggleOpenKey = useCallback((key: string) => {
    setOpenKeys(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key],
    )
  }, [])

  return (
    <SidebarContext.Provider
      value={{
        collapsed,
        openKeys,
        selectedKey,
        setCollapsed,
        toggleCollapsed,
        setOpenKeys,
        toggleOpenKey,
        setSelectedKey,
      }}
    >
      {children}
    </SidebarContext.Provider>
  )
}

export default SidebarContext
