import { RouterProvider } from 'react-router-dom'

import { AuthProvider } from '@/app/providers/auth-provider'
import { AppQueryClientProvider } from '@/app/providers/query-client-provider'
import { ThemeProvider } from '@/app/providers/theme-provider'
import { router } from '@/routes'

function App() {
  return (
    <AppQueryClientProvider>
      <AuthProvider>
        <ThemeProvider>
          <RouterProvider router={router} />
        </ThemeProvider>
      </AuthProvider>
    </AppQueryClientProvider>
  )
}

export default App
