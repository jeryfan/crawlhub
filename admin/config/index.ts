import { DatasetAttr } from '@/types/feature'
import pkg from '../package.json'

const getBooleanConfig = (
  envVar: string | undefined,
  dataAttrKey: DatasetAttr,
  defaultValue: boolean = true,
) => {
  if (envVar !== undefined && envVar !== '')
    return envVar === 'true'
  const attrValue = globalThis.document?.body?.getAttribute(dataAttrKey)
  if (attrValue !== undefined && attrValue !== '')
    return attrValue === 'true'
  return defaultValue
}

const getNumberConfig = (
  envVar: string | undefined,
  dataAttrKey: DatasetAttr,
  defaultValue: number,
) => {
  if (envVar) {
    const parsed = Number.parseInt(envVar)
    if (!Number.isNaN(parsed) && parsed > 0)
      return parsed
  }

  const attrValue = globalThis.document?.body?.getAttribute(dataAttrKey)
  if (attrValue) {
    const parsed = Number.parseInt(attrValue)
    if (!Number.isNaN(parsed) && parsed > 0)
      return parsed
  }
  return defaultValue
}

const getStringConfig = (
  envVar: string | undefined,
  dataAttrKey: DatasetAttr,
  defaultValue: string,
) => {
  if (envVar)
    return envVar

  const attrValue = globalThis.document?.body?.getAttribute(dataAttrKey)
  if (attrValue)
    return attrValue
  return defaultValue
}

export const API_PREFIX = getStringConfig(
  process.env.NEXT_PUBLIC_API_PREFIX,
  DatasetAttr.DATA_API_PREFIX,
  'http://localhost:8000/platform/api',
)

export const IS_CE_EDITION = true
export const IS_CLOUD_EDITION = false

export const IS_DEV = process.env.NODE_ENV === 'development'
export const IS_PROD = process.env.NODE_ENV === 'production'

export const SUPPORT_MAIL_LOGIN = !!(
  process.env.NEXT_PUBLIC_SUPPORT_MAIL_LOGIN
  || globalThis.document?.body?.getAttribute('data-public-support-mail-login')
)

export const LOCALE_COOKIE_NAME = 'locale'

const COOKIE_DOMAIN = getStringConfig(
  process.env.NEXT_PUBLIC_COOKIE_DOMAIN,
  DatasetAttr.DATA_PUBLIC_COOKIE_DOMAIN,
  '',
).trim()
export const CSRF_COOKIE_NAME = () => {
  if (COOKIE_DOMAIN)
    return 'admin_csrf_token'
  const isSecure = API_PREFIX.startsWith('https://')
  return isSecure ? '__Host-admin_csrf_token' : 'admin_csrf_token'
}
export const CSRF_HEADER_NAME = 'X-CSRF-Token'
export const ACCESS_TOKEN_LOCAL_STORAGE_NAME = 'access_token'
export const PASSPORT_LOCAL_STORAGE_NAME = (appCode: string) => `passport-${appCode}`
export const PASSPORT_HEADER_NAME = 'X-App-Passport'

export const WEB_APP_SHARE_CODE_HEADER_NAME = 'X-App-Code'

export const DEFAULT_VALUE_MAX_LEN = 48
export const DEFAULT_PARAGRAPH_VALUE_MAX_LEN = 1000

export const zhRegex = /^[\u4E00-\u9FA5]$/m
export const emojiRegex = /^[\uD800-\uDBFF][\uDC00-\uDFFF]$/m
export const emailRegex = /^[\w.!#$%&'*+\-/=?^{|}~]+@([\w-]+\.)+[\w-]{2,}$/m
const MAX_ZN_VAR_NAME_LENGTH = 8
const MAX_EN_VAR_VALUE_LENGTH = 30
export const getMaxVarNameLength = (value: string) => {
  if (zhRegex.test(value))
    return MAX_ZN_VAR_NAME_LENGTH

  return MAX_EN_VAR_VALUE_LENGTH
}

export const MAX_VAR_KEY_LENGTH = 30

export const MAX_PROMPT_MESSAGE_LENGTH = 10

export const VAR_ITEM_TEMPLATE = {
  key: '',
  name: '',
  type: 'string',
  max_length: DEFAULT_VALUE_MAX_LEN,
  required: true,
}

export const appDefaultIconBackground = '#D5F5F6'

export const VAR_REGEX
  = /\{\{(#[\w-]{1,50}(\.\d+)?(\.[a-z_]\w{0,29}){1,10}#)\}\}/gi

export const resetReg = () => (VAR_REGEX.lastIndex = 0)

export const DISABLE_UPLOAD_IMAGE_AS_ICON
  = process.env.NEXT_PUBLIC_DISABLE_UPLOAD_IMAGE_AS_ICON === 'true'

export const GITHUB_ACCESS_TOKEN
  = process.env.NEXT_PUBLIC_GITHUB_ACCESS_TOKEN || ''

export const SUPPORT_INSTALL_LOCAL_FILE_EXTENSIONS = '.fastapipkg,.fastapibndl'
export const FULL_DOC_PREVIEW_LENGTH = 50

export const JSON_SCHEMA_MAX_DEPTH = 10

export const ALLOW_UNSAFE_DATA_SCHEME
  = process.env.NEXT_PUBLIC_ALLOW_UNSAFE_DATA_SCHEME === 'true'

export const ENABLE_SINGLE_DOLLAR_LATEX
  = process.env.NEXT_PUBLIC_ENABLE_SINGLE_DOLLAR_LATEX === 'true'

export const VALUE_SELECTOR_DELIMITER = '@@@'

export const validPassword = /^(?=.*[a-z])(?=.*\d)\S{8,}$/i

export const ZENDESK_WIDGET_KEY = getStringConfig(
  process.env.NEXT_PUBLIC_ZENDESK_WIDGET_KEY,
  DatasetAttr.NEXT_PUBLIC_ZENDESK_WIDGET_KEY,
  '',
)
export const ZENDESK_FIELD_IDS = {
  ENVIRONMENT: getStringConfig(
    process.env.NEXT_PUBLIC_ZENDESK_FIELD_ID_ENVIRONMENT,
    DatasetAttr.NEXT_PUBLIC_ZENDESK_FIELD_ID_ENVIRONMENT,
    '',
  ),
  VERSION: getStringConfig(
    process.env.NEXT_PUBLIC_ZENDESK_FIELD_ID_VERSION,
    DatasetAttr.NEXT_PUBLIC_ZENDESK_FIELD_ID_VERSION,
    '',
  ),
  EMAIL: getStringConfig(
    process.env.NEXT_PUBLIC_ZENDESK_FIELD_ID_EMAIL,
    DatasetAttr.NEXT_PUBLIC_ZENDESK_FIELD_ID_EMAIL,
    '',
  ),
  WORKSPACE_ID: getStringConfig(
    process.env.NEXT_PUBLIC_ZENDESK_FIELD_ID_WORKSPACE_ID,
    DatasetAttr.NEXT_PUBLIC_ZENDESK_FIELD_ID_WORKSPACE_ID,
    '',
  ),
  PLAN: getStringConfig(
    process.env.NEXT_PUBLIC_ZENDESK_FIELD_ID_PLAN,
    DatasetAttr.NEXT_PUBLIC_ZENDESK_FIELD_ID_PLAN,
    '',
  ),
}
export const APP_VERSION = pkg.version

export const PARTNER_STACK_CONFIG = {
  cookieName: 'partner_stack_info',
  saveCookieDays: 90,
}
