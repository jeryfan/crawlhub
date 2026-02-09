'use client'

import type { Spider, SpiderUpdate } from '@/types/crawlhub'
import {
  RiSaveLine,
} from '@remixicon/react'
import { useEffect, useState } from 'react'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import Toast from '@/app/components/base/toast'
import { useUpdateSpider } from '@/service/use-crawlhub'

type SettingsTabProps = {
  spiderId: string
  spider: Spider
}

const SettingsTab = ({ spiderId, spider }: SettingsTabProps) => {
  const updateMutation = useUpdateSpider()

  // 执行配置
  const [timeoutSeconds, setTimeoutSeconds] = useState<string>(String(spider.timeout_seconds ?? 300))
  const [maxItems, setMaxItems] = useState<string>(spider.max_items ? String(spider.max_items) : '')
  const [memoryLimitMb, setMemoryLimitMb] = useState<string>(spider.memory_limit_mb ? String(spider.memory_limit_mb) : '')
  const [entryPoint, setEntryPoint] = useState<string>(spider.entry_point ?? 'main:run')

  // 依赖管理
  const [requirementsTxt, setRequirementsTxt] = useState<string>(spider.requirements_txt ?? '')

  // 环境变量
  const [envVarsText, setEnvVarsText] = useState<string>(() => {
    if (!spider.env_vars) return ''
    try {
      const parsed = JSON.parse(spider.env_vars)
      return Object.entries(parsed).map(([k, v]) => `${k}=${v}`).join('\n')
    } catch {
      return spider.env_vars
    }
  })

  // 代理配置
  const [proxyEnabled, setProxyEnabled] = useState<boolean>(spider.proxy_enabled ?? false)
  const [rateLimitRps, setRateLimitRps] = useState<string>(spider.rate_limit_rps ? String(spider.rate_limit_rps) : '')
  const [autothrottleEnabled, setAutothrottleEnabled] = useState<boolean>(spider.autothrottle_enabled ?? false)

  // 数据配置
  const [dedupEnabled, setDedupEnabled] = useState<boolean>(spider.dedup_enabled ?? false)
  const [dedupFields, setDedupFields] = useState<string>(spider.dedup_fields ?? '')

  // 通知配置
  const [webhookUrl, setWebhookUrl] = useState<string>(spider.webhook_url ?? '')

  // Sync state when spider prop changes
  useEffect(() => {
    setTimeoutSeconds(String(spider.timeout_seconds ?? 300))
    setMaxItems(spider.max_items ? String(spider.max_items) : '')
    setMemoryLimitMb(spider.memory_limit_mb ? String(spider.memory_limit_mb) : '')
    setEntryPoint(spider.entry_point ?? 'main:run')
    setRequirementsTxt(spider.requirements_txt ?? '')
    setProxyEnabled(spider.proxy_enabled ?? false)
    setRateLimitRps(spider.rate_limit_rps ? String(spider.rate_limit_rps) : '')
    setAutothrottleEnabled(spider.autothrottle_enabled ?? false)
    setDedupEnabled(spider.dedup_enabled ?? false)
    setDedupFields(spider.dedup_fields ?? '')
    setWebhookUrl(spider.webhook_url ?? '')
    if (spider.env_vars) {
      try {
        const parsed = JSON.parse(spider.env_vars)
        setEnvVarsText(Object.entries(parsed).map(([k, v]) => `${k}=${v}`).join('\n'))
      } catch {
        setEnvVarsText(spider.env_vars)
      }
    } else {
      setEnvVarsText('')
    }
  }, [spider])

  const handleSave = async () => {
    // Parse env vars from KEY=VALUE format to JSON
    let envVarsJson: string | null = null
    if (envVarsText.trim()) {
      const envObj: Record<string, string> = {}
      for (const line of envVarsText.split('\n')) {
        const trimmed = line.trim()
        if (!trimmed || trimmed.startsWith('#')) continue
        const eqIdx = trimmed.indexOf('=')
        if (eqIdx > 0) {
          envObj[trimmed.slice(0, eqIdx).trim()] = trimmed.slice(eqIdx + 1).trim()
        }
      }
      envVarsJson = JSON.stringify(envObj)
    }

    const data: SpiderUpdate = {
      entry_point: entryPoint || null,
      timeout_seconds: timeoutSeconds ? parseInt(timeoutSeconds) || 300 : null,
      max_items: maxItems ? parseInt(maxItems) || null : null,
      memory_limit_mb: memoryLimitMb ? parseInt(memoryLimitMb) || null : null,
      requirements_txt: requirementsTxt || null,
      env_vars: envVarsJson,
      proxy_enabled: proxyEnabled,
      rate_limit_rps: rateLimitRps ? parseFloat(rateLimitRps) || null : null,
      autothrottle_enabled: autothrottleEnabled,
      dedup_enabled: dedupEnabled,
      dedup_fields: dedupFields || null,
      webhook_url: webhookUrl || null,
    }

    try {
      await updateMutation.mutateAsync({ id: spiderId, data })
      Toast.notify({ type: 'success', message: '设置已保存' })
    } catch {
      Toast.notify({ type: 'error', message: '保存失败' })
    }
  }

  return (
    <div className="h-full overflow-y-auto pb-8">
      <div className="mx-auto max-w-2xl space-y-6">
        {/* Save button */}
        <div className="flex justify-end">
          <Button variant="primary" size="small" onClick={handleSave} loading={updateMutation.isPending}>
            <RiSaveLine className="mr-1 h-3.5 w-3.5" />
            保存设置
          </Button>
        </div>

        {/* 执行配置 */}
        <section className="rounded-xl border border-divider-subtle bg-components-panel-bg p-4">
          <h3 className="mb-3 text-sm font-semibold text-text-primary">执行配置</h3>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs text-text-secondary">超时时间(秒)</label>
                <Input
                  value={timeoutSeconds}
                  onChange={e => setTimeoutSeconds(e.target.value)}
                  placeholder="300"
                  type="number"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-text-secondary">最大采集条数</label>
                <Input
                  value={maxItems}
                  onChange={e => setMaxItems(e.target.value)}
                  placeholder="不限制"
                  type="number"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs text-text-secondary">内存限制(MB)</label>
                <Input
                  value={memoryLimitMb}
                  onChange={e => setMemoryLimitMb(e.target.value)}
                  placeholder="不限制"
                  type="number"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-text-secondary">入口点</label>
                <Input
                  value={entryPoint}
                  onChange={e => setEntryPoint(e.target.value)}
                  placeholder="main:run"
                />
              </div>
            </div>
          </div>
        </section>

        {/* 依赖管理 */}
        <section className="rounded-xl border border-divider-subtle bg-components-panel-bg p-4">
          <h3 className="mb-3 text-sm font-semibold text-text-primary">依赖管理</h3>
          <div>
            <label className="mb-1 block text-xs text-text-secondary">requirements.txt</label>
            <textarea
              className="w-full rounded-lg border border-divider-regular bg-components-input-bg-normal px-3 py-2 font-mono text-xs text-text-primary placeholder:text-text-quaternary focus:border-components-input-border-active focus:outline-none"
              rows={4}
              value={requirementsTxt}
              onChange={e => setRequirementsTxt(e.target.value)}
              placeholder="requests==2.31.0&#10;beautifulsoup4>=4.12"
            />
          </div>
        </section>

        {/* 环境变量 */}
        <section className="rounded-xl border border-divider-subtle bg-components-panel-bg p-4">
          <h3 className="mb-3 text-sm font-semibold text-text-primary">环境变量</h3>
          <div>
            <label className="mb-1 block text-xs text-text-secondary">每行一个 KEY=VALUE</label>
            <textarea
              className="w-full rounded-lg border border-divider-regular bg-components-input-bg-normal px-3 py-2 font-mono text-xs text-text-primary placeholder:text-text-quaternary focus:border-components-input-border-active focus:outline-none"
              rows={4}
              value={envVarsText}
              onChange={e => setEnvVarsText(e.target.value)}
              placeholder="API_KEY=your_key&#10;BASE_URL=https://example.com"
            />
          </div>
        </section>

        {/* 代理配置 */}
        <section className="rounded-xl border border-divider-subtle bg-components-panel-bg p-4">
          <h3 className="mb-3 text-sm font-semibold text-text-primary">代理配置</h3>
          <div className="space-y-3">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={proxyEnabled}
                onChange={e => setProxyEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm text-text-primary">启用代理</span>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs text-text-secondary">请求频率限制(次/秒)</label>
                <Input
                  value={rateLimitRps}
                  onChange={e => setRateLimitRps(e.target.value)}
                  placeholder="不限制"
                  type="number"
                />
              </div>
              <div className="flex items-end pb-1">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={autothrottleEnabled}
                    onChange={e => setAutothrottleEnabled(e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                  <span className="text-sm text-text-primary">自动限速 (Scrapy)</span>
                </label>
              </div>
            </div>
          </div>
        </section>

        {/* 数据配置 */}
        <section className="rounded-xl border border-divider-subtle bg-components-panel-bg p-4">
          <h3 className="mb-3 text-sm font-semibold text-text-primary">数据配置</h3>
          <div className="space-y-3">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={dedupEnabled}
                onChange={e => setDedupEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm text-text-primary">启用去重</span>
            </label>
            {dedupEnabled && (
              <div>
                <label className="mb-1 block text-xs text-text-secondary">去重字段(逗号分隔)</label>
                <Input
                  value={dedupFields}
                  onChange={e => setDedupFields(e.target.value)}
                  placeholder="url,title"
                />
              </div>
            )}
          </div>
        </section>

        {/* 通知配置 */}
        <section className="rounded-xl border border-divider-subtle bg-components-panel-bg p-4">
          <h3 className="mb-3 text-sm font-semibold text-text-primary">通知配置</h3>
          <div>
            <label className="mb-1 block text-xs text-text-secondary">Webhook URL</label>
            <Input
              value={webhookUrl}
              onChange={e => setWebhookUrl(e.target.value)}
              placeholder="https://example.com/webhook"
            />
          </div>
        </section>
      </div>
    </div>
  )
}

export default SettingsTab
