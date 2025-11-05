export function RegisterPage() {
  return (
    <section className="mx-auto flex w-full max-w-md flex-col space-y-6 rounded-lg border bg-card p-8 shadow">
      <header className="space-y-1 text-center">
        <h2 className="text-2xl font-semibold tracking-tight">Crea una cuenta</h2>
        <p className="text-sm text-muted-foreground">
          Regístrate para administrar tus reservas y pagos.
        </p>
      </header>
      <div className="rounded bg-muted/50 p-4 text-center text-sm text-muted-foreground">
        Aquí irá el formulario de registro.
      </div>
    </section>
  )
}
