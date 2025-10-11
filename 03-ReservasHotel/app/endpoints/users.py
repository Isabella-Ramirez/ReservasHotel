from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserCreate, UserResponse, UserUpdate
from app.tools.auth import get_password_hash, get_current_user_id
from app.tools.error_handlers import (
    handle_database_errors,
    validate_resource_exists,
    validate_unique_field,
    validate_not_self_action,
    validate_resource_not_deleted,
    get_custom_message,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@handle_database_errors
def create_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Crear un nuevo usuario.

    Args:
        user_data: Datos del usuario a crear
        request: Request object para obtener usuario del middleware
        db: Sesión de base de datos

    Returns:
        UserResponse: Usuario creado

    Raises:
        HTTPException: Si hay errores de validación, email duplicado o role_id inválido
    """
    current_user_id = get_current_user_id(request)

    validate_unique_field(
        db=db,
        model_class=User,
        field_name="email",
        field_value=user_data.email,
        error_message=get_custom_message("User", "email_unique"),
    )

    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role_id=user_data.role_id,
        is_active=user_data.is_active,
        created_by=current_user_id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=List[UserResponse])
@handle_database_errors
def get_users(
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    db: Session = Depends(get_db),
):
    """
    Obtener lista de usuarios con paginación y filtros opcionales.

    Args:
        is_active: Filtro opcional por estado activo del usuario
        db: Sesión de base de datos

    Returns:
        List[UserResponse]: Lista de usuarios
    """
    query = db.query(User)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    users = query.all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
@handle_database_errors
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Obtener un usuario por su ID.

    Args:
        user_id: ID del usuario a buscar
        db: Sesión de base de datos

    Returns:
        UserResponse: Usuario encontrado

    Raises:
        HTTPException: Si el usuario no existe
    """
    user = db.query(User).filter(User.id == user_id).first()
    return validate_resource_exists(user, get_custom_message("User", "not_found"))


@router.put("/{user_id}", response_model=UserResponse)
@handle_database_errors
def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Actualizar un usuario existente.

    Args:
        user_id: ID del usuario a actualizar
        user_data: Datos a actualizar del usuario
        request: Request object para obtener usuario del middleware
        db: Sesión de base de datos

    Returns:
        UserResponse: Usuario actualizado

    Raises:
        HTTPException: Si el usuario no existe, email duplicado o datos inválidos
    """
    current_user_id = get_current_user_id(request)

    user = db.query(User).filter(User.id == user_id).first()
    user = validate_resource_exists(user, get_custom_message("User", "not_found"))

    if user_data.email and user_data.email != user.email:
        validate_unique_field(
            db=db,
            model_class=User,
            field_name="email",
            field_value=user_data.email,
            exclude_id=user_id,
            error_message=get_custom_message("User", "email_unique"),
        )

    update_data = user_data.model_dump(exclude_unset=True)

    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))

    update_data["updated_by"] = current_user_id

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_database_errors
def delete_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Eliminar un usuario (soft delete - marcar como inactivo).

    Args:
        user_id: ID del usuario a eliminar
        request: Request object para obtener usuario del middleware
        db: Sesión de base de datos

    Raises:
        HTTPException: Si el usuario no existe, auto-eliminación o errores de BD
    """
    current_user_id = get_current_user_id(request)

    user = db.query(User).filter(User.id == user_id).first()
    user = validate_resource_exists(user, get_custom_message("User", "not_found"))

    validate_not_self_action(
        current_user_id=current_user_id,
        target_user_id=str(user.id),
        detail=get_custom_message("User", "self_delete"),
    )

    validate_resource_not_deleted(user, "usuario")

    current_time = datetime.now(timezone.utc)
    setattr(user, "is_active", False)
    setattr(user, "deleted_at", current_time)
    setattr(user, "updated_by", current_user_id)

    db.commit()
    return JSONResponse(content={"detail": "Usuario eliminado correctamente"})