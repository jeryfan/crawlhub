'use client'

import type {
  AuthSettings,
  BrandingSettings,
  GeneralSettingsConfigUpdate,
  GeneralSettingsTarget,
  OAuthProviderSettings,
  WechatOAuthSettings,
} from '@/types/platform'
import {
  RiCheckLine,
  RiComputerLine,
  RiGithubFill,
  RiGoogleFill,
  RiLockLine,
  RiMailLine,
  RiPaletteLine,
  RiSettings3Line,
  RiUserAddLine,
  RiUserLine,
  RiWechatFill,
} from '@remixicon/react'
import { useCallback, useEffect, useState } from 'react'
import Button from '@/app/components/base/button'
import CroppedImageUploadField from '@/app/components/base/image-uploader/cropped-image-upload-field'
import Input from '@/app/components/base/input'
import Switch from '@/app/components/base/switch'
import Toast from '@/app/components/base/toast'
import {
  useGeneralSettings,
  useUpdateGeneralSettings,
} from '@/service/use-platform'
import { cn } from '@/utils/classnames'

type TabItem = {
  key: GeneralSettingsTarget
  label: string
  icon: React.ReactNode
}

const tabs: TabItem[] = [
  { key: 'web', label: '用户端', icon: <RiUserLine className="h-4 w-4" /> },
  {
    key: 'admin',
    label: '管理端',
    icon: <RiComputerLine className="h-4 w-4" />,
  },
]

const themePresets = [
  { color: '#1570EF', name: '经典蓝' },
  { color: '#7C3AED', name: '优雅紫' },
  { color: '#059669', name: '自然绿' },
  { color: '#DC2626', name: '活力红' },
  { color: '#D97706', name: '温暖橙' },
  { color: '#0891B2', name: '清新青' },
  { color: '#4F46E5', name: '靛蓝' },
  { color: '#DB2777', name: '玫红' },
]

const defaultOAuth: OAuthProviderSettings = {
  enabled: false,
  client_id: '',
  client_secret: '',
}

const defaultWechat: WechatOAuthSettings = {
  enabled: false,
  app_id: '',
  app_secret: '',
}

const defaultBranding: BrandingSettings = {
  enabled: false,
  application_title: '',
  login_page_logo: '',
  workspace_logo: '',
  favicon: '',
  theme_color: '#1570EF',
}

const defaultAuth: AuthSettings = {
  enable_login: true,
  enable_register: true,
  enable_email_code_login: true,
  github: { ...defaultOAuth },
  google: { ...defaultOAuth },
  wechat: { ...defaultWechat },
}

type GeneralFormProps = {
  target: GeneralSettingsTarget
  onStateChange?: (state: { hasChanges: boolean, isPending: boolean }) => void
  registerActions?: (actions: {
    submit: () => void
    reset: () => void
  }) => void
}

const GeneralForm = ({
  target,
  onStateChange,
  registerActions,
}: GeneralFormProps) => {
  const { data: config, isLoading } = useGeneralSettings(target)
  const { mutate: updateConfig, isPending } = useUpdateGeneralSettings(target)

  const [branding, setBranding] = useState<BrandingSettings>(defaultBranding)
  const [auth, setAuth] = useState<AuthSettings>(defaultAuth)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    if (config) {
      setBranding(config.branding)
      setAuth(config.auth)
    }
  }, [config])

  useEffect(() => {
    if (!config)
      return
    const b = config.branding
    const a = config.auth
    const brandingChanged
      = branding.enabled !== b.enabled
        || branding.application_title !== b.application_title
        || branding.login_page_logo !== b.login_page_logo
        || branding.workspace_logo !== b.workspace_logo
        || branding.favicon !== b.favicon
        || branding.theme_color !== b.theme_color
    const authChanged
      = target === 'web'
        && (auth.enable_login !== a.enable_login
          || auth.enable_register !== a.enable_register
          || auth.enable_email_code_login !== a.enable_email_code_login
          || auth.github.enabled !== a.github.enabled
          || auth.github.client_id !== a.github.client_id
          || auth.github.client_secret !== a.github.client_secret
          || auth.google.enabled !== a.google.enabled
          || auth.google.client_id !== a.google.client_id
          || auth.google.client_secret !== a.google.client_secret
          || auth.wechat.enabled !== a.wechat.enabled
          || auth.wechat.app_id !== a.wechat.app_id
          || auth.wechat.app_secret !== a.wechat.app_secret)
    setHasChanges(brandingChanged || authChanged)
  }, [branding, auth, config, target])

  const handleSubmit = useCallback(() => {
    const data: GeneralSettingsConfigUpdate = { branding }
    if (target === 'web')
      data.auth = auth

    updateConfig(data, {
      onSuccess: () => {
        Toast.notify({ type: 'success', message: '保存成功' })
        setHasChanges(false)
      },
      onError: (error: Error) => {
        Toast.notify({ type: 'error', message: error.message || '保存失败' })
      },
    })
  }, [branding, auth, target, updateConfig])

  const handleReset = useCallback(() => {
    if (config) {
      setBranding(config.branding)
      setAuth(config.auth)
    }
  }, [config])

  useEffect(() => {
    onStateChange?.({ hasChanges, isPending })
  }, [hasChanges, isPending, onStateChange])

  useEffect(() => {
    registerActions?.({ submit: handleSubmit, reset: handleReset })
  }, [registerActions, handleSubmit, handleReset])

  if (isLoading) {
    return (
      <div className="space-y-5">
        {[1, 2, 3].map(i => (
          <div
            key={i}
            className="animate-pulse rounded-2xl border border-divider-subtle bg-components-panel-bg p-5"
          >
            <div className="h-4 w-24 rounded bg-divider-regular" />
            <div className="mt-3 h-10 rounded-lg bg-divider-subtle" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Branding toggle card */}
      <div
        className={cn(
          'rounded-2xl border p-5 transition-all duration-300',
          branding.enabled
            ? 'border-components-button-primary-bg/50 bg-gradient-to-br from-state-accent-hover to-background-body'
            : 'border-divider-subtle bg-components-panel-bg hover:border-divider-regular',
        )}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'flex h-10 w-10 items-center justify-center rounded-xl transition-colors',
                branding.enabled
                  ? 'bg-components-button-primary-bg text-white'
                  : 'bg-background-default-burn text-text-quaternary',
              )}
            >
              <RiPaletteLine className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-text-primary">
                自定义品牌
              </p>
              <p className="mt-0.5 text-xs text-text-tertiary">
                自定义应用名称、Logo 和主题色
              </p>
            </div>
          </div>
          <Switch
            size="md"
            defaultValue={branding.enabled}
            onChange={v => setBranding({ ...branding, enabled: v })}
          />
        </div>

        {branding.enabled && (
          <div className="mt-5 space-y-5 border-t border-divider-subtle pt-5">
            <div>
              <p className="mb-2 text-[13px] font-medium text-text-secondary">
                应用名称
              </p>
              <Input
                value={branding.application_title}
                onChange={e =>
                  setBranding({
                    ...branding,
                    application_title: e.target.value,
                  })}
                placeholder="请输入应用名称"
              />
            </div>
            <div>
              <p className="mb-3 text-[13px] font-medium text-text-secondary">
                Logo 配置
              </p>
              <div className="grid grid-cols-3 gap-4">
                <CroppedImageUploadField
                  label="登录页 Logo"
                  description="展示在登录页面顶部"
                  aspectHint="高度 32-40px"
                  value={branding.login_page_logo || ''}
                  onChange={url =>
                    setBranding({ ...branding, login_page_logo: url })}
                />
                <CroppedImageUploadField
                  label={target === 'admin' ? '侧边栏 Logo' : '工作区 Logo'}
                  description={
                    target === 'admin' ? '展示在侧边导航栏' : '展示在工作区顶部'
                  }
                  aspectHint="高度 22-32px"
                  value={branding.workspace_logo || ''}
                  onChange={url =>
                    setBranding({ ...branding, workspace_logo: url })}
                />
                <CroppedImageUploadField
                  label="Favicon"
                  description="浏览器标签页图标"
                  aspectHint="32×32px"
                  cropShape="round"
                  allowShapeSelection
                  value={branding.favicon || ''}
                  onChange={url => setBranding({ ...branding, favicon: url })}
                />
              </div>
            </div>
            <div>
              <p className="mb-3 text-[13px] font-medium text-text-secondary">
                主题色
              </p>
              <div className="mb-3 grid grid-cols-4 gap-2">
                {themePresets.map(preset => (
                  <button
                    key={preset.color}
                    type="button"
                    className={cn(
                      'group flex flex-col items-center gap-1.5 rounded-xl border p-2.5 transition-all',
                      branding.theme_color === preset.color
                        ? 'border-components-button-primary-bg/50 bg-state-accent-hover'
                        : 'border-transparent bg-background-default-subtle hover:border-divider-regular',
                    )}
                    onClick={() =>
                      setBranding({ ...branding, theme_color: preset.color })}
                  >
                    <div
                      className="flex h-7 w-7 items-center justify-center rounded-full shadow-sm"
                      style={{ backgroundColor: preset.color }}
                    >
                      {branding.theme_color === preset.color && (
                        <RiCheckLine className="h-3.5 w-3.5 text-white" />
                      )}
                    </div>
                    <span className="text-[10px] text-text-tertiary">
                      {preset.name}
                    </span>
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-3 rounded-xl bg-background-default-subtle p-3">
                <input
                  type="color"
                  value={branding.theme_color}
                  onChange={e =>
                    setBranding({ ...branding, theme_color: e.target.value })}
                  className="h-9 w-12 cursor-pointer rounded-lg border border-divider-regular bg-transparent p-0.5"
                />
                <Input
                  value={branding.theme_color}
                  onChange={e =>
                    setBranding({ ...branding, theme_color: e.target.value })}
                  placeholder="#1570EF"
                  className="!h-9 flex-1 font-mono text-sm uppercase"
                />
                <div
                  className="h-9 w-9 rounded-lg"
                  style={{ backgroundColor: branding.theme_color }}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {target === 'web' && (
        <>
          {/* Login/Register/Email Code toggles */}
          <div className="rounded-2xl border border-divider-subtle bg-components-panel-bg p-5">
            <p className="mb-4 text-[13px] font-semibold text-text-primary">
              登录注册
            </p>
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-xl bg-background-default-subtle p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-util-colors-blue-blue-500 text-white">
                    <RiLockLine className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      允许登录
                    </p>
                    <p className="text-xs text-text-tertiary">
                      关闭后用户将无法登录
                    </p>
                  </div>
                </div>
                <Switch
                  size="md"
                  defaultValue={auth.enable_login}
                  onChange={v => setAuth({ ...auth, enable_login: v })}
                />
              </div>
              <div className="flex items-center justify-between rounded-xl bg-background-default-subtle p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-util-colors-green-green-500 text-white">
                    <RiUserAddLine className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      允许注册
                    </p>
                    <p className="text-xs text-text-tertiary">
                      关闭后新用户无法注册
                    </p>
                  </div>
                </div>
                <Switch
                  size="md"
                  defaultValue={auth.enable_register}
                  onChange={v => setAuth({ ...auth, enable_register: v })}
                />
              </div>
              <div className="flex items-center justify-between rounded-xl bg-background-default-subtle p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-util-colors-violet-violet-500 text-white">
                    <RiMailLine className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      验证码登录
                    </p>
                    <p className="text-xs text-text-tertiary">
                      允许用户使用邮箱验证码登录
                    </p>
                  </div>
                </div>
                <Switch
                  size="md"
                  defaultValue={auth.enable_email_code_login}
                  onChange={v =>
                    setAuth({ ...auth, enable_email_code_login: v })}
                />
              </div>
            </div>
          </div>

          {/* GitHub OAuth */}
          <div
            className={cn(
              'rounded-2xl border p-5 transition-all',
              auth.github.enabled
                ? 'border-gray-300 bg-gradient-to-br from-gray-50 to-background-body'
                : 'border-divider-subtle bg-components-panel-bg hover:border-divider-regular',
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-900 text-white">
                  <RiGithubFill className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-text-primary">
                    GitHub 登录
                  </p>
                  <p className="mt-0.5 text-xs text-text-tertiary">
                    允许用户使用 GitHub 账号登录
                  </p>
                </div>
              </div>
              <Switch
                size="md"
                defaultValue={auth.github.enabled}
                onChange={v =>
                  setAuth({ ...auth, github: { ...auth.github, enabled: v } })}
              />
            </div>
            {auth.github.enabled && (
              <div className="mt-5 space-y-4 border-t border-divider-subtle pt-5">
                {(!auth.github.client_id || !auth.github.client_secret) && (
                  <div className="rounded-lg bg-state-warning-hover p-3 text-xs text-state-warning-solid">
                    请填写 Client ID 和 Client Secret 后 GitHub
                    登录才会在用户端生效
                  </div>
                )}
                <div>
                  <p className="mb-2 text-[13px] font-medium text-text-secondary">
                    Client ID
                  </p>
                  <Input
                    value={auth.github.client_id}
                    onChange={e =>
                      setAuth({
                        ...auth,
                        github: { ...auth.github, client_id: e.target.value },
                      })}
                    placeholder="请输入 GitHub Client ID"
                  />
                </div>
                <div>
                  <p className="mb-2 text-[13px] font-medium text-text-secondary">
                    Client Secret
                  </p>
                  <Input
                    type="password"
                    value={auth.github.client_secret}
                    onChange={e =>
                      setAuth({
                        ...auth,
                        github: {
                          ...auth.github,
                          client_secret: e.target.value,
                        },
                      })}
                    placeholder="请输入 GitHub Client Secret"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Google OAuth */}
          <div
            className={cn(
              'rounded-2xl border p-5 transition-all',
              auth.google.enabled
                ? 'border-blue-300 bg-gradient-to-br from-blue-50 to-background-body'
                : 'border-divider-subtle bg-components-panel-bg hover:border-divider-regular',
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-sm">
                  <RiGoogleFill className="h-5 w-5 text-[#4285F4]" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-text-primary">
                    Google 登录
                  </p>
                  <p className="mt-0.5 text-xs text-text-tertiary">
                    允许用户使用 Google 账号登录
                  </p>
                </div>
              </div>
              <Switch
                size="md"
                defaultValue={auth.google.enabled}
                onChange={v =>
                  setAuth({ ...auth, google: { ...auth.google, enabled: v } })}
              />
            </div>
            {auth.google.enabled && (
              <div className="mt-5 space-y-4 border-t border-divider-subtle pt-5">
                {(!auth.google.client_id || !auth.google.client_secret) && (
                  <div className="rounded-lg bg-state-warning-hover p-3 text-xs text-state-warning-solid">
                    请填写 Client ID 和 Client Secret 后 Google
                    登录才会在用户端生效
                  </div>
                )}
                <div>
                  <p className="mb-2 text-[13px] font-medium text-text-secondary">
                    Client ID
                  </p>
                  <Input
                    value={auth.google.client_id}
                    onChange={e =>
                      setAuth({
                        ...auth,
                        google: { ...auth.google, client_id: e.target.value },
                      })}
                    placeholder="请输入 Google Client ID"
                  />
                </div>
                <div>
                  <p className="mb-2 text-[13px] font-medium text-text-secondary">
                    Client Secret
                  </p>
                  <Input
                    type="password"
                    value={auth.google.client_secret}
                    onChange={e =>
                      setAuth({
                        ...auth,
                        google: {
                          ...auth.google,
                          client_secret: e.target.value,
                        },
                      })}
                    placeholder="请输入 Google Client Secret"
                  />
                </div>
              </div>
            )}
          </div>

          {/* WeChat OAuth */}
          <div
            className={cn(
              'rounded-2xl border p-5 transition-all',
              auth.wechat.enabled
                ? 'border-green-300 bg-gradient-to-br from-green-50 to-background-body'
                : 'border-divider-subtle bg-components-panel-bg hover:border-divider-regular',
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#07C160] text-white">
                  <RiWechatFill className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-text-primary">
                    微信登录
                  </p>
                  <p className="mt-0.5 text-xs text-text-tertiary">
                    允许用户使用微信扫码登录
                  </p>
                </div>
              </div>
              <Switch
                size="md"
                defaultValue={auth.wechat.enabled}
                onChange={v =>
                  setAuth({ ...auth, wechat: { ...auth.wechat, enabled: v } })}
              />
            </div>
            {auth.wechat.enabled && (
              <div className="mt-5 space-y-4 border-t border-divider-subtle pt-5">
                {(!auth.wechat.app_id || !auth.wechat.app_secret) && (
                  <div className="rounded-lg bg-state-warning-hover p-3 text-xs text-state-warning-solid">
                    请填写 App ID 和 App Secret 后微信登录才会在用户端生效
                  </div>
                )}
                <div>
                  <p className="mb-2 text-[13px] font-medium text-text-secondary">
                    App ID
                  </p>
                  <Input
                    value={auth.wechat.app_id}
                    onChange={e =>
                      setAuth({
                        ...auth,
                        wechat: { ...auth.wechat, app_id: e.target.value },
                      })}
                    placeholder="请输入微信 App ID"
                  />
                </div>
                <div>
                  <p className="mb-2 text-[13px] font-medium text-text-secondary">
                    App Secret
                  </p>
                  <Input
                    type="password"
                    value={auth.wechat.app_secret}
                    onChange={e =>
                      setAuth({
                        ...auth,
                        wechat: { ...auth.wechat, app_secret: e.target.value },
                      })}
                    placeholder="请输入微信 App Secret"
                  />
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

const GeneralSettingsPage = () => {
  const [activeTab, setActiveTab] = useState<GeneralSettingsTarget>('web')
  const [formState, setFormState] = useState({
    hasChanges: false,
    isPending: false,
  })
  const [formActions, setFormActions] = useState<{
    submit: () => void
    reset: () => void
  } | null>(null)

  return (
    <div className="flex h-full flex-col bg-background-body">
      <div className="flex-1 overflow-auto">
        <div className="mx-auto max-w-3xl px-6 py-8 pb-6">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-components-button-primary-bg to-util-colors-indigo-indigo-600 shadow-lg">
              <RiSettings3Line className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-text-primary">基础配置</h1>
              <p className="mt-0.5 text-sm text-text-tertiary">
                品牌展示、登录注册和第三方登录设置
              </p>
            </div>
          </div>

          <div className="mb-6 flex gap-1 rounded-2xl border border-divider-subtle bg-components-panel-bg p-1.5">
            {tabs.map(tab => (
              <button
                key={tab.key}
                type="button"
                className={cn(
                  'relative flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-medium transition-all',
                  activeTab === tab.key
                    ? 'bg-background-body text-text-primary shadow-sm'
                    : 'text-text-tertiary hover:bg-background-default-subtle hover:text-text-secondary',
                )}
                onClick={() => setActiveTab(tab.key)}
              >
                <span
                  className={cn(
                    activeTab === tab.key && 'text-components-button-primary-bg',
                  )}
                >
                  {tab.icon}
                </span>
                {tab.label}
              </button>
            ))}
          </div>

          <GeneralForm
            key={activeTab}
            target={activeTab}
            onStateChange={useCallback(
              (s: { hasChanges: boolean, isPending: boolean }) =>
                setFormState(s),
              [],
            )}
            registerActions={useCallback(
              (a: { submit: () => void, reset: () => void }) =>
                setFormActions(a),
              [],
            )}
          />
        </div>
      </div>

      <div
        className={cn(
          'shrink-0 border-t bg-background-body transition-all',
          formState.hasChanges
            ? 'border-components-button-primary-bg/30 shadow-[0_-4px_20px_rgba(0,0,0,0.08)]'
            : 'border-divider-subtle',
        )}
      >
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            {formState.hasChanges && (
              <>
                <div className="h-2 w-2 animate-pulse rounded-full bg-state-warning-solid" />
                <span className="text-xs text-text-tertiary">
                  有未保存的更改
                </span>
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="secondary"
              onClick={() => formActions?.reset()}
              disabled={!formState.hasChanges || formState.isPending}
            >
              重置
            </Button>
            <Button
              variant="primary"
              onClick={() => formActions?.submit()}
              loading={formState.isPending}
              disabled={!formState.hasChanges}
              className="min-w-[100px]"
            >
              保存配置
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GeneralSettingsPage
