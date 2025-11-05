import { Link, Navigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/auth-provider'
import { LoginForm } from '@/features/auth/components/login-form'

export function LoginPage() {
  const { token, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Verificando sesión…</p>
      </div>
    )
  }

  if (token) {
    return <Navigate to="/app/dashboard" replace />
  }

  return (
    <section className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-4 py-12">
      <div className="space-y-6 rounded-lg border bg-card p-8 shadow">
        <header className="space-y-1 text-center">
          <h2 className="text-2xl font-semibold tracking-tight">Inicia sesión</h2>
          <p className="text-sm text-muted-foreground">
            Ingresa tus credenciales para administrar tus reservas.
          </p>
        </header>
        <LoginForm />
      </div>
      <p className="mt-6 text-center text-sm text-muted-foreground">
        ¿Aún no tienes cuenta?{' '}
        <Link to="/register" className="font-semibold text-primary hover:underline">
          Regístrate aquí
        </Link>
      </p>
    </section>
  )
}
