import { MonitorSmartphone, MoonStar, Sun } from 'lucide-react'

import { cn } from '@/lib/utils'
import { useUIStore } from '@/store/ui-store'

const iconMap = {
  light: Sun,
  dark: MoonStar,
  system: MonitorSmartphone,
} as const

export function ThemeToggle({ className }: { className?: string }) {
  const theme = useUIStore((state) => state.theme)
  const cycleTheme = useUIStore((state) => state.cycleTheme)
  const Icon = iconMap[theme]

  return (
    <button
      type="button"
      onClick={cycleTheme}
      className={cn(
        'inline-flex h-9 items-center justify-center rounded-md border border-border bg-background px-3 text-sm font-medium transition hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        className,
      )}
    >
      <Icon className="h-4 w-4" />
      {/* <span className="ml-2 hidden text-xs font-medium capitalize sm:inline">
        {theme === 'system' ? 'auto' : theme}
      </span> */}
    </button>
  )
}
