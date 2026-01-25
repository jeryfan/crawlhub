'use client'

import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

const SettingsPage = () => {
  const router = useRouter()

  useEffect(() => {
    router.replace('/settings/general')
  }, [router])

  return null
}

export default SettingsPage
