"""Utilidades para manejo consistente de errores en los endpoints."""

from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session


F = TypeVar("F", bound=Callable[..., Any])


CUSTOM_ERROR_MESSAGES: Dict[str, Dict[str, str]] = {
    "User": {
        "email_unique": "El correo ya está registrado",
        "role_fk": "El rol especificado no existe",
        "not_found": "Usuario no encontrado",
        "self_delete": "No puedes eliminar tu propia cuenta",
        "already_deleted": "El usuario ya está eliminado",
    },
    "Guest": {
        "email_unique": "Ya existe un huésped con este correo",
        "document_unique": "Ya existe un huésped con este documento",
        "not_found": "Huésped no encontrado",
        "already_deleted": "El huésped ya está eliminado",
    },
    "Room": {
        "room_number_unique": "Ya existe una habitación con este número",
        "room_type_fk": "El tipo de habitación especificado no existe",
        "not_found": "Habitación no encontrada",
        "already_deleted": "La habitación ya está eliminada",
    },
    "Reservation": {
        "code_unique": "Ya existe una reserva con este código",
        "guest_fk": "El huésped especificado no existe",
        "room_fk": "La habitación especificada no existe",
        "not_found": "Reserva no encontrada",
        "already_deleted": "La reserva ya está eliminada",
    },
    "Role": {
        "code_unique": "Ya existe un rol con este código",
        "not_found": "Rol no encontrado",
        "already_deleted": "El rol ya está eliminado",
    },
}


def get_custom_message(model_name: str, error_type: str) -> str:
    return CUSTOM_ERROR_MESSAGES.get(model_name, {}).get(
        error_type, "Error en la operación"
    )


_FK_MESSAGES = {
    "role_id": "El rol especificado no existe",
    "guest_id": "El huésped especificado no existe",
    "room_id": "La habitación especificada no existe",
}

_UNIQUE_MESSAGES = {
    "email": "El correo ya está registrado",
    "room_number": "Ya existe una habitación con este número",
    "code": "Ya existe un registro con este código",
}


def _handle_integrity_error(error: IntegrityError) -> HTTPException:
    message = str(error.orig).lower()

    if "foreign key" in message:
        for key, detail in _FK_MESSAGES.items():
            if key in message:
                return HTTPException(status.HTTP_400_BAD_REQUEST, detail)
        return HTTPException(status.HTTP_400_BAD_REQUEST, "El recurso referenciado no existe")

    if "unique" in message or "duplicate" in message:
        for key, detail in _UNIQUE_MESSAGES.items():
            if key in message:
                return HTTPException(status.HTTP_400_BAD_REQUEST, detail)
        return HTTPException(status.HTTP_400_BAD_REQUEST, "Ya existe un registro con estos datos")

    return HTTPException(status.HTTP_400_BAD_REQUEST, "Error de integridad de datos")


def _handle_data_error(error: DataError) -> HTTPException:
    message = str(error.orig).lower()

    if "uuid" in message or "invalid input syntax" in message:
        return HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de UUID inválido")
    if "date" in message or "timestamp" in message:
        return HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de fecha inválido")
    if "numeric" in message or "integer" in message:
        return HTTPException(status.HTTP_400_BAD_REQUEST, "Formato numérico inválido")

    return HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de datos inválido")


def _handle_value_error(error: ValueError) -> HTTPException:
    message = str(error).lower()

    if "uuid" in message or "badly formed hexadecimal" in message:
        return HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de UUID inválido")
    if "date" in message or "time" in message:
        return HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de fecha inválido")

    return HTTPException(status.HTTP_400_BAD_REQUEST, "Datos inválidos")


def _handle_validation_error(error: ValidationError) -> HTTPException:
    details = error.errors()
    if details:
        first = details[0]
        field = first.get("loc", ["campo"])[-1]
        error_type = first.get("type")

        if error_type == "missing":
            return HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"El campo '{field}' es obligatorio",
            )
        if error_type == "value_error.email":
            return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Formato de email inválido")
        if error_type == "value_error.uuid":
            return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Formato de UUID inválido")

    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Error de validación de datos")


def handle_database_errors(func: F) -> F:
    @wraps(func)
    def wrapper(*args, **kwargs):
        db: Optional[Session] = None

        for arg in args:
            if isinstance(arg, Session):
                db = arg
                break
        if not db:
            for value in kwargs.values():
                if isinstance(value, Session):
                    db = value
                    break

        try:
            return func(*args, **kwargs)
        except HTTPException:
            raise
        except IntegrityError as error:
            if db:
                db.rollback()
            raise _handle_integrity_error(error)
        except DataError as error:
            if db:
                db.rollback()
            raise _handle_data_error(error)
        except ValidationError as error:
            if db:
                db.rollback()
            raise _handle_validation_error(error)
        except ValueError as error:
            if db:
                db.rollback()
            raise _handle_value_error(error)
        except Exception:
            if db:
                db.rollback()
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Error interno del servidor",
            )

    return wrapper  # type: ignore[arg-type]


def validate_uuid_format(uuid_str: str, field_name: str = "ID") -> UUID:
    try:
        return UUID(uuid_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Formato de {field_name} inválido",
        )


def validate_resource_exists(resource: Any, detail: str = "Recurso no encontrado") -> Any:
    if not resource:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail)
    return resource


def validate_unique_field(
    db: Session,
    model_class: Any,
    field_name: str,
    field_value: Any,
    exclude_id: Optional[UUID] = None,
    error_message: Optional[str] = None,
    include_deleted: bool = False,
) -> None:
    if not field_value:
        return

    query = db.query(model_class)
    if include_deleted:
        query = query.execution_options(include_deleted=True)

    query = query.filter(getattr(model_class, field_name) == field_value)

    if exclude_id:
        query = query.filter(model_class.id != exclude_id)

    if query.first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            error_message or f"Ya existe un registro con este {field_name}",
        )


def validate_not_self_action(
    current_user_id: str, target_user_id: str, detail: str = "No puedes realizar esta acción sobre tu propia cuenta"
) -> None:
    if str(current_user_id) == str(target_user_id):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail,
        )


def validate_resource_not_deleted(resource: Any, resource_name: str = "recurso") -> Any:
    if getattr(resource, "is_active", True) is False:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"El {resource_name} ya está eliminado",
        )

    if getattr(resource, "deleted_at", None) is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"El {resource_name} ya está eliminado",
        )

    return resource
