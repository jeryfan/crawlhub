'use client'

import type { FC } from 'react'
import type { MenuItem } from '@/types/sidebar'
import {
  RiArrowDownSLine,
  RiArrowRightSLine,
  RiContractLeftLine,
  RiContractRightLine,
} from '@remixicon/react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  PortalToFollowElem,
  PortalToFollowElemContent,
  PortalToFollowElemTrigger,
} from '@/app/components/base/portal-to-follow-elem'
import Tooltip from '@/app/components/base/tooltip'
import { useSidebar } from '@/context/sidebar-context'
import { cn } from '@/utils/classnames'

type SidebarProps = {
  menuItems: MenuItem[]
}

type MenuItemProps = {
  item: MenuItem
  level?: number
}

// 收起状态下的弹出子菜单
const CollapsedSubmenu: FC<{ item: MenuItem, children: React.ReactNode }> = ({
  item,
  children,
}) => {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  return (
    <PortalToFollowElem
      open={open}
      onOpenChange={setOpen}
      placement="right-start"
      offset={8}
    >
      <PortalToFollowElemTrigger
        asChild={false}
        onClick={() => setOpen(v => !v)}
      >
        {children}
      </PortalToFollowElemTrigger>
      <PortalToFollowElemContent className="z-[1000]">
        <div className="min-w-[180px] rounded-xl border border-components-panel-border bg-components-panel-bg p-1.5 shadow-lg">
          {/* 标题 */}
          <div className="px-3 py-2 text-xs font-medium text-text-tertiary">
            {item.label}
          </div>
          {/* 子菜单项 */}
          <div className="space-y-0.5">
            {item.children?.map((child) => {
              const isSelected = pathname === child.path
              return (
                <Link
                  key={child.key}
                  href={child.path || '#'}
                  onClick={() => setOpen(false)}
                  className={cn(
                    'flex items-center gap-2 rounded-lg px-3 py-2 text-[13px] font-medium',
                    'transition-colors duration-150',
                    isSelected
                      ? 'bg-state-accent-active text-text-accent'
                      : 'text-text-secondary hover:bg-state-base-hover hover:text-text-primary',
                  )}
                >
                  {child.icon && (
                    <span className="flex h-4 w-4 items-center justify-center">
                      {child.icon}
                    </span>
                  )}
                  <span>{child.label}</span>
                  {isSelected && (
                    <RiArrowRightSLine className="ml-auto h-4 w-4 text-text-accent" />
                  )}
                </Link>
              )
            })}
          </div>
        </div>
      </PortalToFollowElemContent>
    </PortalToFollowElem>
  )
}

// 子菜单展开动画组件
const ExpandableSection: FC<{ isOpen: boolean, children: React.ReactNode }> = ({
  isOpen,
  children,
}) => {
  const contentRef = useRef<HTMLDivElement>(null)
  const [height, setHeight] = useState<number | 'auto'>(0)

  useEffect(() => {
    if (isOpen) {
      const contentHeight = contentRef.current?.scrollHeight || 0
      setHeight(contentHeight)
      // 动画完成后设置为 auto，以便内容变化时能自适应
      const timer = setTimeout(() => setHeight('auto'), 200)
      return () => clearTimeout(timer)
    }
    else {
      // 先设置具体高度，再设置为 0，确保动画生效
      if (contentRef.current) {
        setHeight(contentRef.current.scrollHeight)
        requestAnimationFrame(() => {
          setHeight(0)
        })
      }
    }
  }, [isOpen])

  return (
    <div
      className="overflow-hidden transition-all duration-200 ease-out"
      style={{ height: typeof height === 'number' ? `${height}px` : height }}
    >
      <div ref={contentRef}>{children}</div>
    </div>
  )
}

const MenuItemComponent: FC<MenuItemProps> = ({ item, level = 0 }) => {
  const pathname = usePathname()
  const { collapsed, openKeys, toggleOpenKey } = useSidebar()
  const hasChildren = item.children && item.children.length > 0
  const isOpen = openKeys.includes(item.key)
  const isSelected = pathname === item.path
  const isChildSelected = item.children?.some(
    child =>
      pathname === child.path
      || child.children?.some(c => pathname === c.path),
  )
  const isActive = isSelected || isChildSelected

  const handleClick = useCallback(() => {
    if (hasChildren && !collapsed)
      toggleOpenKey(item.key)
  }, [hasChildren, collapsed, item.key, toggleOpenKey])

  const paddingLeft = collapsed ? 12 : 12 + level * 16

  // 根据层级调整样式
  const isChildItem = level > 0

  // 基础样式类
  const baseClasses = cn(
    'group relative flex cursor-pointer items-center gap-3',
    'transition-all duration-150 ease-out',
    'hover:bg-state-base-hover',
    isSelected && 'bg-state-accent-active',
    item.disabled && 'cursor-not-allowed opacity-50',
    // 父级菜单：较大圆角和内边距
    !isChildItem && 'rounded-lg px-3 py-2.5',
    // 子级菜单：较小圆角和内边距，更轻量
    isChildItem && 'rounded-md px-3 py-2',
  )

  // 菜单项内容（不带点击事件，由外层控制）
  const itemInner = (
    <>
      {/* 左侧选中指示条 - 仅父级菜单显示 */}
      {!isChildItem && (
        <div
          className={cn(
            'absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full',
            'transition-all duration-200 ease-out',
            isSelected
              ? 'bg-text-accent opacity-100'
              : 'bg-transparent opacity-0 group-hover:bg-divider-regular group-hover:opacity-50',
          )}
        />
      )}

      {item.icon && (
        <span
          className={cn(
            'flex shrink-0 items-center justify-center',
            'transition-colors duration-150',
            // 父级菜单图标较大
            !isChildItem && 'h-5 w-5',
            // 子级菜单图标较小
            isChildItem && 'h-4 w-4',
            isActive
              ? 'text-text-accent'
              : 'text-text-tertiary group-hover:text-text-secondary',
          )}
        >
          {item.icon}
        </span>
      )}
      {!collapsed && (
        <>
          <span
            className={cn(
              'flex-1 truncate font-medium',
              'transition-colors duration-150',
              // 父级菜单文字较大
              !isChildItem && 'text-[13px]',
              // 子级菜单文字较小
              isChildItem && 'text-[12px]',
              isActive
                ? 'text-text-accent'
                : 'text-text-secondary group-hover:text-text-primary',
            )}
          >
            {item.label}
          </span>
          {item.badge && (
            <span className="rounded-full bg-util-colors-blue-blue-500 px-1.5 py-0.5 text-xs font-medium text-white shadow-xs">
              {item.badge}
            </span>
          )}
          {hasChildren && (
            <RiArrowDownSLine
              className={cn(
                'h-4 w-4 text-text-quaternary transition-transform duration-200',
                isOpen && 'rotate-180',
              )}
            />
          )}
        </>
      )}
    </>
  )

  // 收起状态下带子菜单的处理
  if (collapsed && hasChildren) {
    return (
      <div>
        <CollapsedSubmenu item={item}>
          <div className={baseClasses} style={{ paddingLeft }}>
            {itemInner}
          </div>
        </CollapsedSubmenu>
      </div>
    )
  }

  // 收起状态下无子菜单的处理
  if (collapsed && !hasChildren) {
    return (
      <div>
        <Tooltip
          position="right"
          offset={12}
          popupContent={<span className="whitespace-nowrap">{item.label}</span>}
        >
          {item.path
            ? (
                <Link href={item.path} className="block">
                  <div className={baseClasses} style={{ paddingLeft }}>
                    {itemInner}
                  </div>
                </Link>
              )
            : (
                <div className={baseClasses} style={{ paddingLeft }}>
                  {itemInner}
                </div>
              )}
        </Tooltip>
      </div>
    )
  }

  // 展开状态
  if (item.disabled) {
    return (
      <div className={baseClasses} style={{ paddingLeft }}>
        {itemInner}
      </div>
    )
  }

  return (
    <div>
      {item.path && !hasChildren
        ? (
            <Link href={item.path} className="block">
              <div className={baseClasses} style={{ paddingLeft }}>
                {itemInner}
              </div>
            </Link>
          )
        : (
            <div
              className={baseClasses}
              style={{ paddingLeft }}
              onClick={handleClick}
            >
              {itemInner}
            </div>
          )}
      {hasChildren && (
        <ExpandableSection isOpen={isOpen}>
          <div className="relative mt-1 space-y-0.5 pb-1 pl-2">
            {/* 左侧连接线 */}
            <div className="absolute bottom-2 left-[18px] top-0 w-px bg-divider-subtle" />
            {item.children!.map(child => (
              <MenuItemComponent
                key={child.key}
                item={child}
                level={level + 1}
              />
            ))}
          </div>
        </ExpandableSection>
      )}
    </div>
  )
}

const Sidebar: FC<SidebarProps> = ({ menuItems }) => {
  const { collapsed, toggleCollapsed } = useSidebar()

  return (
    <aside
      className={cn(
        'relative flex h-full flex-col border-r border-divider-subtle bg-background-default-subtle',
        'transition-[width] duration-300 ease-out',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      {/* Menu */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden px-2 py-3">
        <div className="space-y-0.5">
          {menuItems.map(item => (
            <MenuItemComponent key={item.key} item={item} />
          ))}
        </div>
      </nav>

      {/* Collapse Toggle */}
      <div className="shrink-0 border-t border-divider-subtle p-2">
        <Tooltip
          position="right"
          offset={12}
          disabled={!collapsed}
          popupContent={<span className="whitespace-nowrap">展开侧边栏</span>}
        >
          <button
            onClick={toggleCollapsed}
            className={cn(
              'flex w-full items-center gap-2 rounded-lg px-3 py-2.5',
              'text-text-tertiary transition-all duration-150',
              'hover:bg-state-base-hover hover:text-text-secondary',
              collapsed ? 'justify-center' : 'justify-start',
            )}
          >
            {collapsed
              ? (
                  <RiContractRightLine className="h-[18px] w-[18px]" />
                )
              : (
                  <>
                    <RiContractLeftLine className="h-[18px] w-[18px]" />
                    <span className="text-[13px] font-medium">收起侧边栏</span>
                  </>
                )}
          </button>
        </Tooltip>
      </div>
    </aside>
  )
}

export default Sidebar
