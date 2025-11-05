import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="mx-auto flex h-full max-w-lg flex-col items-center justify-center space-y-6 text-center">
      <div className="space-y-2">
        <h2 className="text-4xl font-bold">404</h2>
        <p className="text-sm text-muted-foreground">
          La página que buscas no existe o ha sido movida.
        </p>
      </div>
      <Link
        to="/app/dashboard"
        className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition hover:bg-primary/90"
      >
        Volver al dashboard
      </Link>
    </div>
  )
}
