'use client'

import type { Dispatch, SetStateAction } from 'react'
import type { AccountSettingTab } from '@/app/components/header/account-setting/constants'
import type { ApiBasedExtension } from '@/models/common'
import { noop } from 'es-toolkit/compat'
import dynamic from 'next/dynamic'

import { useSearchParams } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import {
  createContext,
  useContext,
  useContextSelector,
} from 'use-context-selector'
import {
  ACCOUNT_SETTING_MODAL_ACTION,
  DEFAULT_ACCOUNT_SETTING_TAB,
  isValidAccountSettingTab,
} from '@/app/components/header/account-setting/constants'
import { removeSpecificQueryParam } from '@/utils'

const AccountSetting = dynamic(
  () => import('@/app/components/header/account-setting'),
  {
    ssr: false,
  },
)
const ApiBasedExtensionModal = dynamic(() => import('@/app/components/header/account-setting/api-based-extension-page/modal'), {
  ssr: false,
})

export type ModalState<T> = {
  payload: T
  onCancelCallback?: () => void
  onSaveCallback?: (newPayload?: T, formValues?: Record<string, any>) => void
  onRemoveCallback?: (newPayload?: T, formValues?: Record<string, any>) => void
  onEditCallback?: (newPayload: T) => void
  onValidateBeforeSaveCallback?: (newPayload: T) => boolean
  isEditMode?: boolean
}

export type ModalContextState = {
  setShowAccountSettingModal: Dispatch<
    SetStateAction<ModalState<AccountSettingTab> | null>
  >
  setShowApiBasedExtensionModal: Dispatch<SetStateAction<ModalState<ApiBasedExtension> | null>>
}

const ModalContext = createContext<ModalContextState>({
  setShowAccountSettingModal: noop,
  setShowApiBasedExtensionModal: noop,
})

export const useModalContext = () => useContext(ModalContext)

// Adding a dangling comma to avoid the generic parsing issue in tsx, see:
// https://github.com/microsoft/TypeScript/issues/15713
export const useModalContextSelector = <T,>(
  selector: (state: ModalContextState) => T,
): T => useContextSelector(ModalContext, selector)

type ModalContextProviderProps = {
  children: React.ReactNode
}
export const ModalContextProvider = ({
  children,
}: ModalContextProviderProps) => {
  const searchParams = useSearchParams()

  const [showAccountSettingModal, setShowAccountSettingModal]
    = useState<ModalState<AccountSettingTab> | null>(() => {
      if (searchParams.get('action') === ACCOUNT_SETTING_MODAL_ACTION) {
        const tabParam = searchParams.get('tab')
        const tab = isValidAccountSettingTab(tabParam)
          ? tabParam
          : DEFAULT_ACCOUNT_SETTING_TAB
        return { payload: tab }
      }
      return null
    })
  const [showApiBasedExtensionModal, setShowApiBasedExtensionModal] = useState<ModalState<ApiBasedExtension> | null>(null)
  const handleCancelAccountSettingModal = () => {
    removeSpecificQueryParam('action')
    removeSpecificQueryParam('tab')
    setShowAccountSettingModal(null)
    if (showAccountSettingModal?.onCancelCallback)
      showAccountSettingModal?.onCancelCallback()
  }

  const handleAccountSettingTabChange = useCallback(
    (tab: AccountSettingTab) => {
      setShowAccountSettingModal((prev) => {
        if (!prev)
          return { payload: tab }
        if (prev.payload === tab)
          return prev
        return { ...prev, payload: tab }
      })
    },
    [setShowAccountSettingModal],
  )

  useEffect(() => {
    if (typeof window === 'undefined')
      return
    const url = new URL(window.location.href)
    if (!showAccountSettingModal?.payload) {
      if (url.searchParams.get('action') !== ACCOUNT_SETTING_MODAL_ACTION)
        return
      url.searchParams.delete('action')
      url.searchParams.delete('tab')
      window.history.replaceState(null, '', url.toString())
      return
    }
    url.searchParams.set('action', ACCOUNT_SETTING_MODAL_ACTION)
    url.searchParams.set('tab', showAccountSettingModal.payload)
    window.history.replaceState(null, '', url.toString())
  }, [showAccountSettingModal])

  const handleSaveApiBasedExtension = (newApiBasedExtension: ApiBasedExtension) => {
    if (showApiBasedExtensionModal?.onSaveCallback)
      showApiBasedExtensionModal.onSaveCallback(newApiBasedExtension)
    setShowApiBasedExtensionModal(null)
  }

  return (
    <ModalContext.Provider
      value={{
        setShowAccountSettingModal,
        setShowApiBasedExtensionModal,
      }}
    >
      <>
        {children}
        {!!showAccountSettingModal && (
          <AccountSetting
            activeTab={showAccountSettingModal.payload}
            onCancel={handleCancelAccountSettingModal}
            onTabChange={handleAccountSettingTabChange}
          />
        )}
        {
          !!showApiBasedExtensionModal && (
            <ApiBasedExtensionModal
              data={showApiBasedExtensionModal.payload}
              onCancel={() => setShowApiBasedExtensionModal(null)}
              onSave={handleSaveApiBasedExtension}
            />
          )
        }
      </>
    </ModalContext.Provider>
  )
}

export default ModalContext
