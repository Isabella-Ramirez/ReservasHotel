from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from app.database import test_connection
from app.endpoints import auth, guests, reservations, rooms, users
from app.middleware.auth_middleware import AuthMiddleware
from scripts.migrate_database import auto_setup_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestor de ciclo de vida de la aplicación.

    Maneja los eventos de startup y shutdown de forma moderna.

    """
    try:
        if test_connection():
            print("Conexión a la base de datos verificada.")
            auto_setup_database()
    except Exception as e:
        print(f"Error durante el inicio: {e}")

    yield

    print("Aplicación cerrándose...")


app = FastAPI(
    title="Hotel Reservations API",
    description="API para manejar reservas de hotel.",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)

"""
Agrega el middleware de autenticación a la aplicación FastAPI.
Este middleware protege los endpoints según las reglas definidas en AuthMiddleware.
"""
app.add_middleware(AuthMiddleware)

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(guests.router)
api_router.include_router(rooms.router)
api_router.include_router(reservations.router)

app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str | list[str]]:
    """
    Endpoint raíz de la API.

    Returns:
        dict: Mensaje de bienvenida y lista de endpoints disponibles
    """
    return {
        "message": "Bienvenido a la API de Reservas de Hotel. Visita /docs para ver la documentación.",
        "endpoints": ["/api/auth", "/api/guests", "/api/rooms", "/api/reservations"],
    }
