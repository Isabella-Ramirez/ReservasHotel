from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import test_connection
from app.endpoints import auth, guests, reservations, roles, rooms, users
from app.middleware.auth_middleware import AuthMiddleware
from app.tools.error_handlers import format_validation_error
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


def custom_openapi() -> dict:
    """Inject a Bearer security scheme so Swagger shows the authorize button."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    security_scheme = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})[
        "BearerAuth"
    ] = security_scheme
    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

"""
Agrega el middleware de autenticación a la aplicación FastAPI.
Este middleware protege los endpoints según las reglas definidas en AuthMiddleware.
"""

origins = [
    "http://localhost:3000",
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(guests.router)
api_router.include_router(rooms.router)
api_router.include_router(reservations.router)

app.include_router(api_router)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    status_code, detail = format_validation_error(exc)
    return JSONResponse(status_code=status_code, content={"detail": detail})


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
