'use client'
import type { Locale } from '.'
import { camelCase, kebabCase } from 'es-toolkit/compat'
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import app from '../i18n/en-US/app.json'
import common from '../i18n/en-US/common.json'
import custom from '../i18n/en-US/custom.json'
import layout from '../i18n/en-US/layout.json'
import login from '../i18n/en-US/login.json'
import oauth from '../i18n/en-US/oauth.json'
import time from '../i18n/en-US/time.json'

// @keep-sorted
export const resources = {
  app,
  common,
  custom,
  layout,
  login,
  oauth,
  time,
}

export type KebabCase<S extends string> = S extends `${infer T}${infer U}`
  ? T extends Lowercase<T>
    ? `${T}${KebabCase<U>}`
    : `-${Lowercase<T>}${KebabCase<U>}`
  : S

export type CamelCase<S extends string> = S extends `${infer T}-${infer U}`
  ? `${T}${Capitalize<CamelCase<U>>}`
  : S

export type Resources = typeof resources
export type NamespaceCamelCase = keyof Resources
export type NamespaceKebabCase = KebabCase<NamespaceCamelCase>

const requireSilent = async (lang: Locale, namespace: NamespaceKebabCase) => {
  let res
  try {
    res = (await import(`../i18n/${lang}/${namespace}.json`)).default
  }
  catch {
    res = (await import(`../i18n/en-US/${namespace}.json`)).default
  }

  return res
}

const NAMESPACES = Object.keys(resources).map(kebabCase) as NamespaceKebabCase[]

// Load a single namespace for a language
export const loadNamespace = async (lang: Locale, ns: NamespaceKebabCase) => {
  const camelNs = camelCase(ns) as NamespaceCamelCase
  if (i18n.hasResourceBundle(lang, camelNs))
    return

  const resource = await requireSilent(lang, ns)
  i18n.addResourceBundle(lang, camelNs, resource, true, true)
}

// Load all namespaces for a language (used when switching language)
export const loadLangResources = async (lang: Locale) => {
  await Promise.all(
    NAMESPACES.map(ns => loadNamespace(lang, ns)),
  )
}

// Initial resources: load en-US namespaces for fallback/default locale
const getInitialTranslations = () => {
  return {
    'en-US': resources,
  }
}

if (!i18n.isInitialized) {
  i18n.use(initReactI18next).init({
    lng: undefined,
    fallbackLng: 'en-US',
    resources: getInitialTranslations(),
    defaultNS: 'common',
    ns: Object.keys(resources),
    keySeparator: false,
  })
}

export const changeLanguage = async (lng?: Locale) => {
  if (!lng)
    return
  await loadLangResources(lng)
  await i18n.changeLanguage(lng)
}

export default i18n
