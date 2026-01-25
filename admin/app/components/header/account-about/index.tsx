'use client'
import type { AppVersionResponse } from '@/models/common'
import { RiCloseLine } from '@remixicon/react'
import dayjs from 'dayjs'
import Link from 'next/link'
import { useTranslation } from 'react-i18next'
import Button from '@/app/components/base/button'
import FastAPILogo from '@/app/components/base/logo/fastapi-logo'
import Modal from '@/app/components/base/modal'
import { IS_CE_EDITION } from '@/config'

import { useGlobalPublicStore } from '@/context/global-public-context'

type IAccountSettingProps = {
  versionInfo: AppVersionResponse
  onCancel: () => void
}

export default function AccountAbout({
  versionInfo,
  onCancel,
}: IAccountSettingProps) {
  const { t } = useTranslation()
  const isLatest = versionInfo.current_version === versionInfo.latest_version
  const systemFeatures = useGlobalPublicStore(s => s.systemFeatures)

  return (
    <Modal
      isShow
      onClose={onCancel}
      className="!w-[480px] !max-w-[480px] !px-6 !py-4"
    >
      <div className="relative">
        <div className="absolute right-0 top-0 flex h-8 w-8 cursor-pointer items-center justify-center" onClick={onCancel}>
          <RiCloseLine className="h-4 w-4 text-text-tertiary" />
        </div>
        <div className="flex flex-col items-center gap-4 py-8">
          {systemFeatures.branding.enabled && systemFeatures.branding.workspace_logo
            ? (
                <img
                  src={systemFeatures.branding.workspace_logo}
                  className="block h-7 w-auto object-contain"
                  alt="logo"
                />
              )
            : <FastAPILogo size="large" className="mx-auto" />}

          <div className="text-center text-xs font-normal text-text-tertiary">
            Version
            {versionInfo?.current_version}
          </div>
          <div className="flex flex-col items-center gap-2 text-center text-xs font-normal text-text-secondary">
            <div>
              ©
              {dayjs().year()}
              {' '}
              FastAPI Template, Contributors.
            </div>
            <div className="text-text-accent">
              {
                IS_CE_EDITION
                  ? <Link href="#" target="_blank" rel="noopener noreferrer">Open Source License</Link>
                  : (
                      <>
                        <Link href="https://fastapi-template.com/privacy" target="_blank" rel="noopener noreferrer">Privacy Policy</Link>
                        ,&nbsp;
                        <Link href="https://fastapi-template.com/terms" target="_blank" rel="noopener noreferrer">Terms of Service</Link>
                      </>
                    )
              }
            </div>
          </div>
        </div>
        <div className="-mx-8 mb-4 h-[0.5px] bg-divider-regular" />
        <div className="flex items-center justify-between">
          <div className="text-xs font-medium text-text-tertiary">
            {
              isLatest
                ? t('about.latestAvailable', { ns: 'common', version: versionInfo.latest_version })
                : t('about.nowAvailable', { ns: 'common', version: versionInfo.latest_version })
            }
          </div>
          <div className="flex items-center">
            <Button className="mr-2" size="small">
              <Link
                href="#"
                target="_blank"
                rel="noopener noreferrer"
              >
                {t('about.changeLog', { ns: 'common' })}
              </Link>
            </Button>
            {
              !isLatest && !IS_CE_EDITION && (
                <Button variant="primary" size="small">
                  <Link
                    href={versionInfo.release_notes}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {t('about.updateNow', { ns: 'common' })}
                  </Link>
                </Button>
              )
            }
          </div>
        </div>
      </div>
    </Modal>
  )
}
