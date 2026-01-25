import type { ReactNode } from 'react'
import * as React from 'react'
import { AppInitializer } from '@/app/components/app-initializer'
import AmplitudeProvider from '@/app/components/base/amplitude'
import GA, { GaType } from '@/app/components/base/ga'
import Zendesk from '@/app/components/base/zendesk'
import Header from '@/app/components/header'
import HeaderWrapper from '@/app/components/header/header-wrapper'
import Sidebar from '@/app/components/sidebar'
import { menuItems } from '@/app/components/sidebar/menu-config'
import { AppContextProvider } from '@/context/app-context'
import { BrandingProvider } from '@/context/branding-context'
import { EventEmitterContextProvider } from '@/context/event-emitter'
import { ModalContextProvider } from '@/context/modal-context'
import { ProviderContextProvider } from '@/context/provider-context'
import { SidebarProvider } from '@/context/sidebar-context'
import Splash from '../components/splash'

const Layout = ({ children }: { children: ReactNode }) => {
  return (
    <>
      <GA gaType={GaType.admin} />
      <AmplitudeProvider />
      <AppInitializer>
        <AppContextProvider>
          <EventEmitterContextProvider>
            <ProviderContextProvider>
              <ModalContextProvider>
                <BrandingProvider>
                  <SidebarProvider>
                    <div className="flex h-screen flex-col">
                      <HeaderWrapper>
                        <Header />
                      </HeaderWrapper>
                      <div className="flex flex-1 overflow-hidden">
                        <Sidebar menuItems={menuItems} />
                        <main className="flex h-full flex-1 flex-col overflow-hidden bg-background-body px-2 pt-2">
                          {children}
                        </main>
                      </div>
                    </div>
                  </SidebarProvider>
                </BrandingProvider>
                <Splash />
              </ModalContextProvider>
            </ProviderContextProvider>
          </EventEmitterContextProvider>
        </AppContextProvider>
        <Zendesk />
      </AppInitializer>
    </>
  )
}
export default Layout
