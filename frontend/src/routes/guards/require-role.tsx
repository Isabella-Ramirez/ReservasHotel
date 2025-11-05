import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '@/app/providers/use-auth'
import type { RoleCode } from '@/features/auth/types'

interface RequireRoleProps {
  roles: RoleCode | RoleCode[]
  redirectTo?: string
}

export function RequireRole({ roles, redirectTo = '/app/dashboard' }: RequireRoleProps) {
  const location = useLocation()
  const { hasRole } = useAuth()

  if (!hasRole(roles)) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />
  }

  return <Outlet />
}
