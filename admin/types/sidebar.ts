import type { ReactNode } from 'react'

export type MenuItem = {
  key: string
  label: string
  icon?: ReactNode
  path?: string
  children?: MenuItem[]
  badge?: string | number
  disabled?: boolean
}

export type SidebarState = {
  collapsed: boolean
  openKeys: string[]
  selectedKey: string
}

export type SidebarContextValue = {
  setCollapsed: (collapsed: boolean) => void
  toggleCollapsed: () => void
  setOpenKeys: (keys: string[]) => void
  toggleOpenKey: (key: string) => void
  setSelectedKey: (key: string) => void
} & SidebarState
