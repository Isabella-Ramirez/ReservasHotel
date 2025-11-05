import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '@/app/providers/use-auth'

interface RequireAuthProps {
  redirectTo?: string
  loadingFallback?: React.ReactNode
}

export function RequireAuth({
  redirectTo = '/login',
  loadingFallback = null,
}: RequireAuthProps) {
  const location = useLocation()
  const { token, loading } = useAuth()

  if (loading) {
    return <>{loadingFallback}</>
  }

  if (!token) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />
  }

  return <Outlet />
}
