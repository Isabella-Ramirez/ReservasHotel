import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { zodResolver } from '@hookform/resolvers/zod'
import { useLocation, useNavigate } from 'react-router-dom'
import * as z from 'zod'
import { AxiosError } from 'axios'

import { useAuth } from '@/app/providers/use-auth'
import { Button } from '@/components/ui/button'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import type { AuthCredentials } from '@/features/auth/types'

const loginSchema = z.object({
  email: z.email('El correo electrónico no es válido').min(1, 'El correo electrónico es obligatorio'),
  password: z.string().min(1, 'La contraseña es obligatoria'),
})

type LoginFormValues = z.infer<typeof loginSchema>

interface LocationState {
  from?: {
    pathname?: string
  }
}

function getErrorMessage(error: unknown) {
  if (error instanceof AxiosError) {
    const message =
      typeof error.response?.data === 'object' && error.response?.data !== null
        ? // Attempt to extract a message field from backend responses
          (error.response.data as { message?: string }).message
        : undefined

    return message ?? 'Credenciales inválidas. Inténtalo nuevamente.'
  }

  return 'Ocurrió un error inesperado. Inténtalo nuevamente.'
}

export function LoginForm() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const [formError, setFormError] = useState<string | null>(null)

  const defaultValues: LoginFormValues = {
    email: '',
    password: '',
  }

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues,
    mode: 'onSubmit',
  })

  const mutation = useMutation({
    mutationFn: async (values: AuthCredentials) => {
      setFormError(null)
      return login(values)
    },
    onSuccess: () => {
      const state = location.state as LocationState | null
      const destination = state?.from?.pathname ?? '/app/dashboard'
      navigate(destination, { replace: true })
    },
    onError: (error) => {
      setFormError(getErrorMessage(error))
    },
  })

  const onSubmit = async (values: LoginFormValues) => {
    await mutation.mutateAsync(values)
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <div className="space-y-4">
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Correo electrónico</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="tu-correo@ejemplo.com"
                    type="email"
                    autoComplete="email"
                    disabled={mutation.isPending}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Contraseña</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    type="password"
                    autoComplete="current-password"
                    disabled={mutation.isPending}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {formError ? (
          <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {formError}
          </p>
        ) : null}

        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? 'Iniciando...' : 'Iniciar sesión'}
        </Button>
      </form>
    </Form>
  )
}
