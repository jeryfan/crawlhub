import { renderI18nObject } from '@/i18n-config'

export const useRenderI18nObject = () => {
  const language = 'zh_Hans'
  return (obj: Record<string, string>) => {
    return renderI18nObject(obj, language)
  }
}
