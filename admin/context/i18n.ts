import type { Locale } from '@/i18n-config/language'
import { atom, useAtomValue, useSetAtom } from 'jotai'
import { useCallback } from 'react'
import { changeLanguage } from '@/i18n-config/i18next-config'
import { getDocLanguage, getLanguage, getPricingPageLanguage } from '@/i18n-config/language'

export const localeAtom = atom<Locale>('en-US')
export const useLocale = () => {
  return useAtomValue(localeAtom)
}

export const useSetLocale = () => {
  const setLocale = useSetAtom(localeAtom)
  return useCallback(async (locale: Locale, shouldReload = true) => {
    setLocale(locale)
    await changeLanguage(locale)
    if (shouldReload && typeof window !== 'undefined')
      window.location.reload()
  }, [setLocale])
}

export const useGetLanguage = () => {
  const locale = useLocale()

  return getLanguage(locale)
}
export const useGetPricingPageLanguage = () => {
  const locale = useLocale()

  return getPricingPageLanguage(locale)
}

export const defaultDocBaseUrl = ''
export const useDocLink = (baseUrl?: string): ((path?: string, pathMap?: { [index: string]: string }) => string) => {
  let baseDocUrl = baseUrl || defaultDocBaseUrl
  baseDocUrl = (baseDocUrl.endsWith('/')) ? baseDocUrl.slice(0, -1) : baseDocUrl
  const locale = useLocale()
  const docLanguage = getDocLanguage(locale)
  return (path?: string, pathMap?: { [index: string]: string }): string => {
    const pathUrl = path || ''
    let targetPath = (pathMap) ? pathMap[locale] || pathUrl : pathUrl
    targetPath = (targetPath.startsWith('/')) ? targetPath.slice(1) : targetPath
    return `${baseDocUrl}/${docLanguage}/${targetPath}`
  }
}

const I18NContext = {
  locale: 'en-US' as Locale,
  localeAtom,
  useLocale,
  useGetLanguage,
  setLocaleOnClient: async (_locale: Locale, _shouldReload = true) => {},
  i18n: {},
}

export default I18NContext
