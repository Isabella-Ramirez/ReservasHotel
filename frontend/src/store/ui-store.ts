import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export type ThemePreference = 'light' | 'dark' | 'system'

interface UIState {
  theme: ThemePreference
  sidebarCollapsed: boolean
  setTheme: (theme: ThemePreference) => void
  setSidebarCollapsed: (collapsed: boolean) => void
  cycleTheme: () => void
  toggleSidebar: () => void
}

const fallbackStorage: Storage = {
  getItem: () => null,
  setItem: () => undefined,
  removeItem: () => undefined,
  clear: () => undefined,
  key: () => null,
  length: 0,
}

const storage =
  typeof window !== 'undefined'
    ? createJSONStorage(() => window.localStorage)
    : createJSONStorage(() => fallbackStorage)

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      theme: 'system',
      sidebarCollapsed: false,
      setTheme: (theme) => set({ theme }),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      cycleTheme: () => {
        const order: ThemePreference[] = ['light', 'dark', 'system']
        const current = get().theme
        const next = order[(order.indexOf(current) + 1) % order.length]
        set({ theme: next })
      },
      toggleSidebar: () => set({ sidebarCollapsed: !get().sidebarCollapsed }),
    }),
    {
      name: 'hotel.ui',
      storage,
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    },
  ),
)
