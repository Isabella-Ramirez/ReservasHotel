import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type PropsWithChildren, useState } from 'react'

/**
 * Wraps react-query provider and ensures a single QueryClient instance per app mount.
 */
export function AppQueryClientProvider({ children }: PropsWithChildren) {
  const [queryClient] = useState(() => {
    return new QueryClient({
      defaultOptions: {
        queries: {
          refetchOnWindowFocus: false,
          retry: 1,
        },
      },
    })
  })

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}
