from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.rbac import Role, RoleCreate, RoleResponse, RoleUpdate
from app.tools.auth import get_current_user_id

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role_data: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> RoleResponse:
    """Crear un rol con código único.

    Valida que el código no esté en uso y guarda el rol con datos de auditoría.

    Args:
        role_data: datos para crear el rol.
        request: Request para obtener el usuario autenticado.
        db: sesión de base de datos.

    Returns:
        RoleResponse: rol creado.

    Raises:
        HTTPException: 400 si el código del rol ya está en uso.
    """

    current_user_id = get_current_user_id(request)

    existing = (
        db.query(Role)
        .execution_options(include_deleted=True)
        .filter(Role.code == role_data.code)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código del rol ya está en uso",
        )

    role = Role(
        code=role_data.code,
        name=role_data.name,
        created_by=current_user_id,
    )

    db.add(role)
    db.commit()
    db.refresh(role)
    return RoleResponse.model_validate(role)


@router.get("", response_model=List[RoleResponse])
def list_roles(
    include_deleted: bool = Query(
        False,
        description="Indica si se deben incluir roles eliminados",
    ),
    db: Session = Depends(get_db),
):
    """Listar roles.

    Devuelve los roles ordenados por nombre. Opcionalmente incluye roles
    eliminados lógicamente.

    Args:
        include_deleted: si True incluye roles con `deleted_at` definido.
        db: sesión de base de datos.

    Returns:
        List[RoleResponse]: lista de roles.
    """

    query = db.query(Role)

    if include_deleted:
        query = query.execution_options(include_deleted=True)

    roles = query.order_by(Role.name.asc()).all()
    return roles


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
) -> RoleResponse:
    """Obtener un rol por su identificador.

    Args:
        role_id: ID del rol.
        db: sesión de base de datos.

    Returns:
        RoleResponse: rol encontrado.

    Raises:
        HTTPException: 404 si no existe el rol.
    """

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )
    return RoleResponse.model_validate(role)


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> RoleResponse:
    """Actualizar un rol existente.

    Aplica solo los campos enviados y registra el usuario que realiza la
    modificación. No permite actualizar roles eliminados.

    Args:
        role_id: ID del rol a actualizar.
        role_data: campos a actualizar.
        request: Request para obtener el usuario autenticado.
        db: sesión de base de datos.

    Returns:
        RoleResponse: rol actualizado.

    Raises:
        HTTPException: 404 si no existe el rol.
        HTTPException: 400 si el rol está eliminado.
    """

    current_user_id = get_current_user_id(request)

    role = (
        db.query(Role)
        .execution_options(include_deleted=True)
        .filter(Role.id == role_id)
        .first()
    )
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )

    if role.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No es posible actualizar un rol eliminado",
        )

    update_data = role_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(role, field, value)

    setattr(role, "updated_by", current_user_id)

    db.commit()
    db.refresh(role)
    return RoleResponse.model_validate(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    """Eliminar (soft delete) un rol.

    Marca `deleted_at` y registra la auditoría. Si el rol ya está eliminado
    no realiza ninguna acción.

    Args:
        role_id: ID del rol.
        request: Request para obtener el usuario autenticado.
        db: sesión de base de datos.

    Returns:
        None

    Raises:
        HTTPException: 404 si no existe el rol.
    """

    current_user_id = get_current_user_id(request)

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )

    if role.deleted_at is not None:
        return

    current_time = datetime.now(timezone.utc)
    setattr(role, "deleted_at", current_time)
    setattr(role, "updated_by", current_user_id)

    db.commit()
    return None