'use client'

import { RiAddLine, RiServerLine } from '@remixicon/react'
import Button from '@/app/components/base/button'

const ProxiesPage = () => {
  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">代理池</h1>
        <Button variant="primary">
          <RiAddLine className="mr-1 h-4 w-4" />
          添加代理
        </Button>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed border-divider-regular bg-background-section p-12">
        <RiServerLine className="mb-4 h-12 w-12 text-text-quaternary" />
        <p className="mb-2 text-lg font-medium text-text-secondary">暂无代理</p>
        <p className="text-sm text-text-tertiary">添加代理服务器以提高爬虫稳定性</p>
      </div>
    </>
  )
}

export default ProxiesPage
