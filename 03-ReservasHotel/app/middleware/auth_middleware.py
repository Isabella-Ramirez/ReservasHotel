"""
Middleware de autenticación para la API de Reservas de Hotel.

Este middleware intercepta todas las requests y aplica autenticación
según las reglas definidas para cada endpoint.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable
import re

from app.tools.auth import verify_token
from app.database import get_db
from app.models.user import User


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware que maneja la autenticación automáticamente.
    
    Reglas de protección:
    - GET en rutas públicas: Sin autenticación
    - POST, PUT, DELETE: Requieren autenticación
    - Rutas específicas: Configuración personalizada
    """
    
    def __init__(self, app):
        """
        Inicializa el middleware de autenticación con las rutas públicas, protegidas y métodos protegidos.
        Args:
            app: Instancia de la aplicación FastAPI.
        """
        super().__init__(app)
        
        self.public_paths = {
            "/",
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/api/auth/login",
        }
        self.protected_paths = {
            "/api/auth/me",
            "/api/rooms",
            "/api/guests", 
            "/api/reservations",
            "/api/users"
        }
        self.protected_methods = {"POST", "PUT", "DELETE", "PATCH"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Intercepta la request y aplica las reglas de autenticación.
        """
        path = request.url.path
        method = request.method
        
        if self._requires_auth(path, method):
            try:
                token = self._extract_token(request)
                if not token:
                    return self._unauthorized_response("Token de autorización requerido")
                payload = verify_token(token)
                user_id = payload.get("user")
                if not user_id:
                    return self._unauthorized_response("Token inválido")
                if not self._is_user_valid(user_id):
                    return self._unauthorized_response("Usuario no autorizado")
                request.state.user_id = user_id
                request.state.user_payload = payload
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail},
                    headers=e.headers
                )
            except Exception as e:
                return self._unauthorized_response("Error de autenticación")
       
        response = await call_next(request)
        return response

    def _requires_auth(self, path: str, method: str) -> bool:
        """
        Determina si una ruta requiere autenticación basado en las reglas.
        """
        if path in self.public_paths:
            return False
        if any(path.startswith(protected) for protected in self.protected_paths):
            return True
        return method in self.protected_methods

    def _extract_token(self, request: Request) -> str | None:
        """
        Obtiene el token JWT del encabezado Authorization de la solicitud.
        Args:
            request: Objeto Request de FastAPI.
        Returns:
            El token JWT como cadena, o None si no se encuentra o el formato es incorrecto.
        """
        """
        Extrae el token JWT del header Authorization.
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
            
        
        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
            
        return parts[1]

    def _is_user_valid(self, user_id: str) -> bool:
        """
        Verifica si el usuario existe y está activo en la base de datos.
        Args:
            user_id: ID del usuario a verificar.
        Returns:
            True si el usuario existe y está activo, False en caso contrario.
        """
        """
        Verifica que el usuario existe y está activo en la base de datos.
        """
        try:
            db = next(get_db())
            user = db.query(User).filter(User.id == user_id).first()
            if not user or user.is_active is False:
                return False
            return True
        except Exception:
            return False
        finally:
            if 'db' in locals():
                db.close()

    def _unauthorized_response(self, message: str) -> JSONResponse:
        """
        Genera una respuesta JSON de error 401 para solicitudes no autorizadas.
        Args:
            message: Mensaje de error a mostrar.
        Returns:
            JSONResponse con el código 401 y el mensaje proporcionado.
        """
        """
        Crea una respuesta de error 401.
        """
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": message},
            headers={"WWW-Authenticate": "Bearer"}
        )




