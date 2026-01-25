import data from './languages'

export type Item = {
  value: number | string
  name: string
  example: string
}

export type I18nText = Record<typeof LanguagesSupported[number], string>

export const languages = data.languages

// for compatibility
export type Locale = 'ja_JP' | 'zh_Hans' | 'en_US' | (typeof languages[number])['value']

export const LanguagesSupported: Locale[] = languages.filter(item => item.supported).map(item => item.value)

export const getLanguage = (locale: Locale): Locale => {
  if (['zh-Hans', 'ja-JP'].includes(locale))
    return locale.replace('-', '_') as Locale

  return LanguagesSupported[0].replace('-', '_') as Locale
}

const DOC_LANGUAGE: Record<string, string> = {
  'zh-Hans': 'zh-hans',
  'ja-JP': 'ja-jp',
  'en-US': 'en',
}

export const localeMap: Record<Locale, string> = {
  'en-US': 'en',
  'en_US': 'en',
  'zh-Hans': 'zh-cn',
  'zh_Hans': 'zh-cn',
  'zh-Hant': 'zh-tw',
  'pt-BR': 'pt-br',
  'es-ES': 'es',
  'fr-FR': 'fr',
  'de-DE': 'de',
  'ja-JP': 'ja',
  'ja_JP': 'ja',
  'ko-KR': 'ko',
  'ru-RU': 'ru',
  'it-IT': 'it',
  'th-TH': 'th',
  'id-ID': 'id',
  'uk-UA': 'uk',
  'vi-VN': 'vi',
  'ro-RO': 'ro',
  'pl-PL': 'pl',
  'hi-IN': 'hi',
  'tr-TR': 'tr',
  'fa-IR': 'fa',
  'sl-SI': 'sl',
  'ar-TN': 'ar',
}

export const getDocLanguage = (locale: string) => {
  return DOC_LANGUAGE[locale] || 'en'
}

const PRICING_PAGE_LANGUAGE: Record<string, string> = {
  'ja-JP': 'jp',
}

export const getPricingPageLanguage = (locale: string) => {
  return PRICING_PAGE_LANGUAGE[locale] || ''
}

export const NOTICE_I18N = {
  title: {
    en_US: 'Important Notice',
    zh_Hans: '重要公告',
    zh_Hant: '重要公告',
    pt_BR: 'Aviso Importante',
    es_ES: 'Aviso Importante',
    fr_FR: 'Avis important',
    de_DE: 'Wichtiger Hinweis',
    ja_JP: '重要なお知らせ',
    ko_KR: '중요 공지',
    ru_RU: 'Важное Уведомление',
    it_IT: 'Avviso Importante',
    th_TH: 'ประกาศสำคัญ',
    id_ID: 'Pengumuman Penting',
    uk_UA: 'Важливе повідомлення',
    vi_VN: 'Thông báo quan trọng',
    ro_RO: 'Anunț Important',
    pl_PL: 'Ważne ogłoszenie',
    hi_IN: 'महत्वपूर्ण सूचना',
    tr_TR: 'Önemli Duyuru',
    fa_IR: 'هشدار مهم',
    sl_SI: 'Pomembno obvestilo',
    ar_TN: 'إشعار مهم',
  },
  desc: {
    en_US: '',
    zh_Hans: '',
    pt_BR: '',
    es_ES: '',
    fr_FR: '',
    de_DE: '',
    ja_JP: '',
    ko_KR: '',
    pl_PL: '',
    uk_UA: '',
    ru_RU: '',
    vi_VN: '',
    id_ID: '',
    tr_TR: '',
    fa_IR: '',
    sl_SI: '',
    th_TH: '',
    ar_TN: '',
  },
  href: '#',
}
