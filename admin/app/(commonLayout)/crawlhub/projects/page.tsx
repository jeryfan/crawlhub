'use client'

import { RiAddLine, RiFolderLine } from '@remixicon/react'
import Button from '@/app/components/base/button'

const ProjectsPage = () => {
  return (
    <>
      <div className="mb-6 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">项目管理</h1>
        <Button variant="primary">
          <RiAddLine className="mr-1 h-4 w-4" />
          创建项目
        </Button>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed border-divider-regular bg-background-section p-12">
        <RiFolderLine className="mb-4 h-12 w-12 text-text-quaternary" />
        <p className="mb-2 text-lg font-medium text-text-secondary">暂无项目</p>
        <p className="text-sm text-text-tertiary">创建第一个爬虫项目开始使用</p>
      </div>
    </>
  )
}

export default ProjectsPage
