/* eslint-disable react-refresh/only-export-components */
import { createBrowserRouter, Navigate } from 'react-router-dom'

import { AppLayout } from '@/app/layouts/AppLayout'
import { RequireAuth } from '@/routes/guards/require-auth'
import { RequireRole } from '@/routes/guards/require-role'
import { DashboardPage } from '@/routes/pages/dashboard'
import { LoginPage } from '@/routes/pages/login'
import { NotFoundPage } from '@/routes/pages/not-found'
import { RegisterPage } from '@/routes/pages/register'

function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <div className="space-y-2 rounded-lg border bg-card p-6 shadow-sm">
      <h2 className="text-xl font-semibold">{title}</h2>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  )
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/app/dashboard" replace />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/app',
    element: <RequireAuth loadingFallback={<div>Cargando sesión…</div>} />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            index: true,
            element: <Navigate to="dashboard" replace />,
          },
          {
            path: 'dashboard',
            element: <DashboardPage />,
          },
          {
            path: 'my-reservations',
            element: (
              <PlaceholderPage
                title="Mis reservas"
                description="Lista de reservas del huésped autenticado."
              />
            ),
          },
          {
            path: 'new-reservation',
            element: (
              <PlaceholderPage
                title="Nueva reserva"
                description="Flujo para crear una reserva desde el portal de huéspedes."
              />
            ),
          },
          {
            path: 'my-payments',
            element: (
              <PlaceholderPage
                title="Mis pagos"
                description="Historial de pagos asociados al huésped autenticado."
              />
            ),
          },
          {
            path: 'profile',
            element: (
              <PlaceholderPage
                title="Perfil"
                description="Actualizar datos del usuario y huésped."
              />
            ),
          },
          {
            element: <RequireRole roles={['RECEPTIONIST', 'ADMIN']} />,
            children: [
              {
                path: 'reservations',
                element: (
                  <PlaceholderPage
                    title="Reservas"
                    description="Gestión de reservas para personal del hotel."
                  />
                ),
              },
              {
                path: 'payments',
                element: (
                  <PlaceholderPage
                    title="Pagos"
                    description="Listado y administración de pagos."
                  />
                ),
              },
              {
                path: 'guests',
                element: (
                  <PlaceholderPage
                    title="Huéspedes"
                    description="Gestión de perfiles de huéspedes."
                  />
                ),
              },
            ],
          },
          {
            element: <RequireRole roles="ADMIN" />,
            children: [
              {
                path: 'rooms',
                element: (
                  <PlaceholderPage
                    title="Habitaciones"
                    description="Administración de habitaciones y disponibilidad."
                  />
                ),
              },
              {
                path: 'users',
                element: (
                  <PlaceholderPage
                    title="Usuarios"
                    description="Gestión de usuarios del sistema."
                  />
                ),
              },
              {
                path: 'roles',
                element: (
                  <PlaceholderPage
                    title="Roles"
                    description="Configuración de roles y permisos."
                  />
                ),
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
])
