'use client'

import type { FC, ReactNode } from 'react'
import type { UserProfileResponse } from '@/models/common'
import { useQueryClient } from '@tanstack/react-query'
import { noop } from 'es-toolkit/compat'
import { useCallback, useEffect, useMemo } from 'react'
import { createContext, useContext, useContextSelector } from 'use-context-selector'
import { setUserId, setUserProperties } from '@/app/components/base/amplitude'
import MaintenanceNotice from '@/app/components/header/maintenance-notice'
import {
  useUserProfile,
} from '@/service/use-common'

export type AppContextValue = {
  userProfile: UserProfileResponse
  mutateUserProfile: VoidFunction
  useSelector: typeof useSelector
}

const userProfilePlaceholder = {
  id: '',
  name: '',
  email: '',
  avatar: '',
  avatar_url: '',
  is_password_set: false,
}

const AppContext = createContext<AppContextValue>({
  userProfile: userProfilePlaceholder,
  mutateUserProfile: noop,
  useSelector,
})

export function useSelector<T>(selector: (value: AppContextValue) => T): T {
  return useContextSelector(AppContext, selector)
}

export type AppContextProviderProps = {
  children: ReactNode
}

export const AppContextProvider: FC<AppContextProviderProps> = ({ children }) => {
  const queryClient = useQueryClient()
  const { data: userProfileResp } = useUserProfile()

  const userProfile = useMemo<UserProfileResponse>(() => userProfileResp?.profile || userProfilePlaceholder, [userProfileResp?.profile])

  const mutateUserProfile = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['common', 'user-profile'] })
  }, [queryClient])

  useEffect(() => {
    // Report user info to Amplitude when loaded
    if (userProfile?.id) {
      setUserId(userProfile.email)
      const properties: Record<string, any> = {
        email: userProfile.email,
        name: userProfile.name,
        has_password: userProfile.is_password_set,
      }
      setUserProperties(properties)
    }
  }, [userProfile])

  return (
    <AppContext.Provider value={{
      userProfile,
      mutateUserProfile,
      useSelector,
    }}
    >
      <div className="flex h-full flex-col overflow-y-auto">
        {globalThis.document?.body?.getAttribute('data-public-maintenance-notice') && <MaintenanceNotice />}
        <div className="relative flex grow flex-col overflow-y-auto overflow-x-hidden bg-background-body">
          {children}
        </div>
      </div>
    </AppContext.Provider>
  )
}

export const useAppContext = () => useContext(AppContext)

export default AppContext
