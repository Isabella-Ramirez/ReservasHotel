import { LogOut, Menu, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { useMemo } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '@/app/providers/use-auth'
import { ThemeToggle } from '@/components/ui/theme-toggle'
import { cn } from '@/lib/utils'
import { moduleAccess, type ModuleKey } from '@/routes/module-access'
import { useUIStore } from '@/store/ui-store'

const moduleConfig: Record<ModuleKey, { label: string; path: string }> = {
  dashboard: { label: 'Dashboard', path: 'dashboard' },
  myReservations: { label: 'Mis reservas', path: 'my-reservations' },
  newReservation: { label: 'Nueva reserva', path: 'new-reservation' },
  myPayments: { label: 'Mis pagos', path: 'my-payments' },
  profile: { label: 'Perfil', path: 'profile' },
  reservations: { label: 'Reservas', path: 'reservations' },
  payments: { label: 'Pagos', path: 'payments' },
  guests: { label: 'Huéspedes', path: 'guests' },
  rooms: { label: 'Habitaciones', path: 'rooms' },
  users: { label: 'Usuarios', path: 'users' },
  roles: { label: 'Roles', path: 'roles' },
}

export function AppLayout() {
  const { user, logout } = useAuth()
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed)
  const toggleSidebar = useUIStore((state) => state.toggleSidebar)

  const navigation = useMemo(() => {
    if (!user) return []
    const allowed = moduleAccess[user.role_code] ?? []
    return allowed
      .map((module) => ({ module, config: moduleConfig[module] }))
      .filter(
        (item): item is { module: ModuleKey; config: (typeof moduleConfig)[ModuleKey] } =>
          Boolean(item.config),
      )
      .map(({ module, config }) => ({ ...config, module }))
  }, [user])

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside
        className={cn(
          'hidden border-r bg-sidebar transition-all duration-200 ease-out lg:flex lg:flex-col',
          sidebarCollapsed ? 'w-20' : 'w-64',
        )}
      >
        <div className="flex items-center justify-between px-4 py-3">
          <span
            className={cn(
              'text-sm font-semibold text-sidebar-foreground',
              sidebarCollapsed && 'sr-only',
            )}
          >
            Navegación
          </span>
          <button
            type="button"
            onClick={toggleSidebar}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-sidebar-border text-sidebar-foreground/80 transition hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
          >
            {sidebarCollapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </button>
        </div>
        <nav className="flex-1 space-y-1 px-2 pb-4">
          {navigation.map(({ path, label }) => (
            <NavLink
              key={path}
              to={`/app/${path}`}
              end={path === 'dashboard'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition',
                  isActive
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground',
                  sidebarCollapsed && 'justify-center px-0',
                )
              }
            >
              <span className={cn(sidebarCollapsed && 'sr-only')}>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="border-b bg-background/80 px-4 py-4 backdrop-blur sm:px-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground transition hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 lg:hidden"
                aria-label="Abrir navegación"
              >
                <Menu className="h-4 w-4" />
              </button>
              <h1 className="text-lg font-semibold leading-none tracking-tight sm:text-xl">
                ReservasHotel
              </h1>
            </div>
            <div className="flex items-center gap-3">
              <ThemeToggle />
              {user && (
                <>
                  <div className="hidden flex-col text-right text-sm leading-tight sm:flex">
                    <span className="font-semibold">{user.full_name}</span>
                    <span className="text-xs uppercase text-muted-foreground">
                      {user.role_code}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={logout}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-destructive text-destructive-foreground transition hover:bg-destructive/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive focus-visible:ring-offset-2"
                    aria-label="Cerrar sesión"
                  >
                    <LogOut className="h-4 w-4" />
                  </button>
                </>
              )}
            </div>
          </div>
        </header>
        <main className="flex-1 bg-muted/30 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
