// TypeScript type definitions for FastAPI's i18next configuration
// This file is auto-generated. Do not edit manually.
// To regenerate, run: pnpm run gen:i18n-types
import 'react-i18next'

// Extract types from translation files using typeof import pattern

type AppAnnotationMessages = typeof import('../i18n/en-US/app-annotation').default
type AppApiMessages = typeof import('../i18n/en-US/app-api').default
type AppDebugMessages = typeof import('../i18n/en-US/app-debug').default
type AppLogMessages = typeof import('../i18n/en-US/app-log').default
type AppOverviewMessages = typeof import('../i18n/en-US/app-overview').default
type AppMessages = typeof import('../i18n/en-US/app').default
type BillingMessages = typeof import('../i18n/en-US/billing').default
type CommonMessages = typeof import('../i18n/en-US/common').default
type CustomMessages = typeof import('../i18n/en-US/custom').default
type EducationMessages = typeof import('../i18n/en-US/education').default
type ExploreMessages = typeof import('../i18n/en-US/explore').default
type LayoutMessages = typeof import('../i18n/en-US/layout').default
type LoginMessages = typeof import('../i18n/en-US/login').default
type OauthMessages = typeof import('../i18n/en-US/oauth').default
type RegisterMessages = typeof import('../i18n/en-US/register').default
type RunLogMessages = typeof import('../i18n/en-US/run-log').default
type ShareMessages = typeof import('../i18n/en-US/share').default
type TimeMessages = typeof import('../i18n/en-US/time').default

// Complete type structure that matches i18next-config.ts camelCase conversion
export type Messages = {
  appAnnotation: AppAnnotationMessages
  appApi: AppApiMessages
  appDebug: AppDebugMessages
  appLog: AppLogMessages
  appOverview: AppOverviewMessages
  app: AppMessages
  billing: BillingMessages
  common: CommonMessages
  custom: CustomMessages
  education: EducationMessages
  explore: ExploreMessages
  layout: LayoutMessages
  login: LoginMessages
  oauth: OauthMessages
  register: RegisterMessages
  runLog: RunLogMessages
  share: ShareMessages
  time: TimeMessages
}

// Utility type to flatten nested object keys into dot notation
type FlattenKeys<T> = T extends object
  ? {
      [K in keyof T]: T[K] extends object
        ? `${K & string}.${FlattenKeys<T[K]> & string}`
        : `${K & string}`
    }[keyof T]
  : never

export type ValidTranslationKeys = FlattenKeys<Messages>

// Extend react-i18next with FastAPI's type structure
declare module 'react-i18next' {
  type CustomTypeOptions = {
    defaultNS: 'translation'
    resources: {
      translation: Messages
    }
  }
}

// Extend i18next for complete type safety
declare module 'i18next' {
  type CustomTypeOptions = {
    defaultNS: 'translation'
    resources: {
      translation: Messages
    }
  }
}
