from fastapi import FastAPI

from app.database import test_connection
from app.endpoints import auth, guests, reservations, rooms
from scripts.migrate_database import auto_setup_database

app = FastAPI(
    title="Hotel Reservations API",
    description="API para manejar reservas de hotel.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(guests.router)
app.include_router(rooms.router)
app.include_router(reservations.router)


@app.on_event("startup")
async def startup() -> None:
    """
    Evento de inicio de la aplicación.

    Verifica la conexión a la base de datos y ejecuta la configuración automática.
    """
    try:
        if test_connection():
            print("Conexión a la base de datos verificada.")
            auto_setup_database()
    except Exception as e:
        print(f"Error durante el inicio: {e}")


@app.get("/")
async def root() -> dict[str, str | list[str]]:
    """
    Endpoint raíz de la API.

    Returns:
        dict: Mensaje de bienvenida y lista de endpoints disponibles
    """
    return {
        "message": "Bienvenido a la API de Reservas de Hotel. Visita /docs para ver la documentación.",
        "endpoints": ["/auth", "/guests", "/rooms", "/reservations"],
    }
