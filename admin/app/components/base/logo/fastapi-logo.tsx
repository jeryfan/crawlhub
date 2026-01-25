'use client'
import type { FC } from 'react'
import useTheme from '@/hooks/use-theme'
import { cn } from '@/utils/classnames'
import { basePath } from '@/utils/var'

export type LogoStyle = 'default' | 'monochromeWhite'

export const logoPathMap: Record<LogoStyle, string> = {
  default: '/logo/logo.svg',
  monochromeWhite: '/logo/logo-monochrome-white.svg',
}

export type LogoSize = 'large' | 'medium' | 'small'

export const logoSizeMap: Record<LogoSize, string> = {
  large: 'w-20 h-7',
  medium: 'w-16 h-[22px]',
  small: 'w-12 h-4',
}

type AppLogoProps = {
  style?: LogoStyle
  size?: LogoSize
  className?: string
}

const AppLogo: FC<AppLogoProps> = ({
  style = 'default',
  size = 'medium',
  className,
}) => {
  const { theme } = useTheme()
  const themedStyle
    = theme === 'dark' && style === 'default' ? 'monochromeWhite' : style

  return (
    <img
      src={`${basePath}${logoPathMap[themedStyle]}`}
      className={cn('block object-contain', logoSizeMap[size], className)}
      alt="FastAPI Template"
    />
  )
}

// Keep FastAPILogo as alias for backward compatibility
export { AppLogo as FastAPILogo }
export default AppLogo
