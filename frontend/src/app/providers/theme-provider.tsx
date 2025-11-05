import { useEffect, type PropsWithChildren } from 'react'

import { useUIStore, type ThemePreference } from '@/store/ui-store'

function resolveTheme(preference: ThemePreference, mediaQueryList: MediaQueryList | null) {
  if (preference === 'system') {
    return mediaQueryList?.matches ? 'dark' : 'light'
  }
  return preference
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const theme = useUIStore((state) => state.theme)

  useEffect(() => {
    if (typeof window === 'undefined') return undefined

    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const root = document.documentElement

    const applyTheme = () => {
      const resolved = resolveTheme(theme, media)
      root.classList.toggle('dark', resolved === 'dark')
      root.dataset.theme = resolved
    }

    applyTheme()

    if (theme === 'system') {
      media.addEventListener('change', applyTheme)
      return () => media.removeEventListener('change', applyTheme)
    }

    return undefined
  }, [theme])

  return <>{children}</>
}
