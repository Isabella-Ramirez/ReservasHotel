from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserCreate, UserResponse, UserUpdate
from app.tools.auth import get_current_user, get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Crear un nuevo usuario.

    Args:
        user_data: Datos del usuario a crear
        db: Sesión de base de datos
        current_user: Usuario autenticado actual

    Returns:
        UserResponse: Usuario creado

    Raises:
        HTTPException: Si el correo ya está registrado
    """
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya está registrado",
        )

    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role_id=user_data.role_id,
        is_active=user_data.is_active,
        created_by=current_user.id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=List[UserResponse])
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
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Actualizar un usuario existente.

    Args:
        user_id: ID del usuario a actualizar
        user_data: Datos a actualizar del usuario
        db: Sesión de base de datos
        current_user: Usuario autenticado actual

    Returns:
        UserResponse: Usuario actualizado

    Raises:
        HTTPException: Si el usuario no existe o el email ya está en uso
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    if user_data.email and user_data.email != user.email:
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo ya está registrado",
            )

    update_data = user_data.model_dump(exclude_unset=True)

    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))

    update_data["updated_by"] = current_user.id

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Eliminar un usuario (soft delete - marcar como inactivo).

    Args:
        user_id: ID del usuario a eliminar
        db: Sesión de base de datos
        current_user: Usuario autenticado actual

    Raises:
        HTTPException: Si el usuario no existe o si intenta eliminarse a sí mismo
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta",
        )

    setattr(user, "is_active", False)
    setattr(user, "updated_by", current_user.id)

    db.commit()
