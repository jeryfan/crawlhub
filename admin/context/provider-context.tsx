'use client'

import {
  createContext,
  useContext,
  useContextSelector,
} from 'use-context-selector'

type ProviderContextState = {
  enableBilling: boolean
}

const ProviderContext = createContext<ProviderContextState>({
  enableBilling: false,
})

export const useProviderContext = () => useContext(ProviderContext)

// Adding a dangling comma to avoid the generic parsing issue in tsx, see:
// https://github.com/microsoft/TypeScript/issues/15713
export const useProviderContextSelector = <T,>(
  selector: (state: ProviderContextState) => T,
): T => useContextSelector(ProviderContext, selector)

type ProviderContextProviderProps = {
  children: React.ReactNode
}
export const ProviderContextProvider = ({
  children,
}: ProviderContextProviderProps) => {
  return (
    <ProviderContext.Provider
      value={{
        enableBilling: false,
      }}
    >
      {children}
    </ProviderContext.Provider>
  )
}

export default ProviderContext
