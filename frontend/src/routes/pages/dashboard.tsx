import { useMemo } from 'react'

import { useAuth } from '@/app/providers/use-auth'
import type { ModuleKey } from '@/routes/module-access'
import { moduleAccess } from '@/routes/module-access'

const roleHighlights: Record<
  ModuleKey,
  { title: string; description: string; cta?: string }
> = {
  dashboard: {
    title: 'Resumen general',
    description: 'Visión general de tu actividad dentro del hotel.',
  },
  myReservations: {
    title: 'Mis reservas',
    description: 'Consulta tus reservas actuales y pasadas.',
  },
  newReservation: {
    title: 'Nueva reserva',
    description: 'Genera rápidamente una nueva reserva.',
    cta: 'Crear reserva',
  },
  myPayments: {
    title: 'Mis pagos',
    description: 'Revisa el estado de tus pagos recientes.',
  },
  profile: {
    title: 'Perfil',
    description: 'Mantén tus datos de contacto siempre actualizados.',
  },
  reservations: {
    title: 'Reservas',
    description: 'Gestiona check-ins, check-outs y asignaciones.',
  },
  payments: {
    title: 'Pagos',
    description: 'Controla cobros, reembolsos y facturación.',
  },
  guests: {
    title: 'Huéspedes',
    description: 'Actualiza datos de huéspedes y preferencias.',
  },
  rooms: {
    title: 'Habitaciones',
    description: 'Administra disponibilidad y mantenimiento.',
  },
  users: {
    title: 'Usuarios',
    description: 'Gestiona cuentas del personal y sus permisos.',
  },
  roles: {
    title: 'Roles',
    description: 'Define la seguridad y accesos del sistema.',
  },
}

export function DashboardPage() {
  const { user } = useAuth()

  const cards = useMemo(() => {
    if (!user) return []
    const accessible = moduleAccess[user.role_code] ?? []
    return accessible
      .map((module) => ({ module, data: roleHighlights[module] }))
      .filter(
        (item): item is { module: ModuleKey; data: (typeof roleHighlights)[ModuleKey] } =>
          Boolean(item.data),
      )
      .map(({ module, data }) => ({
        key: module,
        ...data,
      }))
  }, [user])

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <p className="text-sm text-muted-foreground">Hola de nuevo,</p>
        <h2 className="text-3xl font-semibold tracking-tight">
          {user?.full_name ?? 'Usuario'}
        </h2>
        <p className="text-sm text-muted-foreground">
          {user?.role_code === 'GUEST'
            ? 'Revisa tus reservas y gestiona tus pagos fácilmente.'
            : 'Consulta el estado del hotel y gestiona operaciones diarias.'}
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.slice(0, 6).map(({ key, title, description, cta }) => (
          <div
            key={key}
            className="flex h-full flex-col justify-between rounded-lg border bg-card p-4 shadow-sm"
          >
            <div className="space-y-1">
              <h3 className="text-lg font-semibold">{title}</h3>
              <p className="text-sm text-muted-foreground">{description}</p>
            </div>
            {cta ? (
              <p className="pt-4 text-sm font-semibold text-primary">{cta}</p>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  )
}
