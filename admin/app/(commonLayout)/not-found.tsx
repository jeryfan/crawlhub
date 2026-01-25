'use client'

import { RiArrowLeftLine, RiHome4Line } from '@remixicon/react'
import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="flex h-full flex-col items-center justify-center">
      <div className="text-center">
        <h1 className="text-8xl font-bold text-text-tertiary">404</h1>
        <h2 className="mt-4 text-2xl font-semibold text-text-primary">
          页面未找到
        </h2>
        <p className="mt-2 text-text-tertiary">
          抱歉，您访问的页面不存在或已被移除
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <button
            onClick={() => window.history.back()}
            className="inline-flex items-center gap-2 rounded-lg border border-divider-regular px-4 py-2 text-sm font-medium text-text-secondary transition-colors hover:bg-state-base-hover"
          >
            <RiArrowLeftLine className="h-4 w-4" />
            返回上页
          </button>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700"
          >
            <RiHome4Line className="h-4 w-4" />
            回到首页
          </Link>
        </div>
      </div>
    </div>
  )
}
