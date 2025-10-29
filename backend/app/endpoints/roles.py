from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.rbac import Role, RoleCreate, RoleResponse, RoleUpdate
from app.tools.auth import get_current_user_id
from app.tools.error_handlers import (
    get_custom_message,
    handle_database_errors,
    validate_resource_exists,
    validate_unique_field,
)

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
@handle_database_errors
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

    current_user_uuid = UUID(str(get_current_user_id(request)))

    validate_unique_field(
        db=db,
        model_class=Role,
        field_name="code",
        field_value=role_data.code,
        error_message=get_custom_message("Role", "code_unique"),
        include_deleted=True,
    )

    role = Role(
        code=role_data.code,
        name=role_data.name,
        created_by=current_user_uuid,
    )

    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("", response_model=list[RoleResponse])
@handle_database_errors
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
@handle_database_errors
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
    role = validate_resource_exists(role, get_custom_message("Role", "not_found"))
    return role


@router.put("/{role_id}", response_model=RoleResponse)
@handle_database_errors
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

    current_user_uuid = UUID(str(get_current_user_id(request)))

    role = db.query(Role).filter(Role.id == role_id).first()
    role = validate_resource_exists(role, get_custom_message("Role", "not_found"))

    update_data = role_data.model_dump(exclude_unset=True)

    if "code" in update_data and update_data["code"] != role.code:
        validate_unique_field(
            db=db,
            model_class=Role,
            field_name="code",
            field_value=update_data["code"],
            exclude_id=role_id,
            error_message=get_custom_message("Role", "code_unique"),
            include_deleted=True,
        )

    for field, value in update_data.items():
        setattr(role, field, value)

    setattr(role, "updated_by", current_user_uuid)

    db.commit()
    db.refresh(role)
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_database_errors
def delete_role(
    role_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Eliminar (soft delete) un rol.

    Marca `deleted_at` y registra la auditoría. Si el rol ya está eliminado
    responde con error.

    Args:
        role_id: ID del rol.
        request: Request para obtener el usuario autenticado.
        db: sesión de base de datos.

    Returns:
        None

    Raises:
        HTTPException: 404 si no existe el rol.
        HTTPException: 400 si el rol ya está eliminado.
    """

    current_user_uuid = UUID(str(get_current_user_id(request)))

    role = db.query(Role).filter(Role.id == role_id).first()
    role = validate_resource_exists(role, get_custom_message("Role", "not_found"))

    current_time = datetime.now(timezone.utc)
    setattr(role, "deleted_at", current_time)
    setattr(role, "updated_by", current_user_uuid)

    db.commit()
    return JSONResponse(content={"detail": "Rol eliminado correctamente"})
