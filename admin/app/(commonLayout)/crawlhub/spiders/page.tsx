'use client'

import { RiAddLine, RiBugLine } from '@remixicon/react'
import Button from '@/app/components/base/button'

const SpidersPage = () => {
  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">爬虫列表</h1>
        <Button variant="primary">
          <RiAddLine className="mr-1 h-4 w-4" />
          创建爬虫
        </Button>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed border-divider-regular bg-background-section p-12">
        <RiBugLine className="mb-4 h-12 w-12 text-text-quaternary" />
        <p className="mb-2 text-lg font-medium text-text-secondary">暂无爬虫</p>
        <p className="text-sm text-text-tertiary">创建爬虫并编写脚本开始抓取数据</p>
      </div>
    </>
  )
}

export default SpidersPage
