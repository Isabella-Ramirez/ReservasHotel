from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.guest import Guest, GuestCreate, GuestResponse, GuestUpdate
from app.models.reservation import Reservation, ReservationGuest, ReservationStatus
from app.tools.auth import get_current_user_id
from app.tools.error_handlers import (
    get_custom_message,
    handle_database_errors,
    validate_resource_exists,
    validate_unique_field,
)

router = APIRouter(prefix="/guests", tags=["Guests"])

ACTIVE_RESERVATION_STATUSES: Sequence[ReservationStatus] = (
    ReservationStatus.PENDING,
    ReservationStatus.CONFIRMED,
    ReservationStatus.CHECKED_IN,
)


def _get_guest_or_404(db: Session, guest_id: UUID) -> Guest:
    guest = db.query(Guest).filter(Guest.id == guest_id).first()
    return validate_resource_exists(guest, get_custom_message("Guest", "not_found"))


@router.post("", response_model=GuestResponse, status_code=status.HTTP_201_CREATED)
@handle_database_errors
def create_guest(
    guest: GuestCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> GuestResponse:
    """
    Crear un nuevo huésped en el sistema.

    Args:
        guest: Datos del huésped a crear
        request: Request object para obtener usuario del middleware
        db: Sesión de base de datos

    Returns:
        GuestResponse: Datos del huésped creado

    Raises:
        HTTPException: Si los datos ya existen o hay errores de validación
    """
    current_user_uuid = UUID(str(get_current_user_id(request)))

    if guest.email:
        validate_unique_field(
            db=db,
            model_class=Guest,
            field_name="email",
            field_value=guest.email,
            error_message=get_custom_message("Guest", "email_unique"),
            include_deleted=True,
        )

    if guest.document_no:
        validate_unique_field(
            db=db,
            model_class=Guest,
            field_name="document_no",
            field_value=guest.document_no,
            error_message=get_custom_message("Guest", "document_unique"),
            include_deleted=True,
        )

    if guest.user_id:
        validate_unique_field(
            db=db,
            model_class=Guest,
            field_name="user_id",
            field_value=guest.user_id,
            error_message=get_custom_message("Guest", "user_unique"),
            include_deleted=True,
        )

    new_guest = Guest(
        **guest.model_dump(),
        created_by=current_user_uuid,
        updated_by=current_user_uuid,
    )
    db.add(new_guest)
    db.commit()
    db.refresh(new_guest)
    return new_guest

@router.get("", response_model=list[GuestResponse])
@handle_database_errors
def get_all_guests(db: Session = Depends(get_db)):
    """
    Obtener todos los huéspedes registrados.

    Args:
        db: Sesión de base de datos

    Returns:
        list[GuestResponse]: Lista de todos los huéspedes
    """
    guests = db.query(Guest).all()
    return guests

@router.get("/{guest_id}", response_model=GuestResponse)
@handle_database_errors
def get_guest(guest_id: UUID, db: Session = Depends(get_db)) -> GuestResponse:
    """
    Obtener un huésped específico por su ID.

    Args:
        guest_id: ID único del huésped
        db: Sesión de base de datos

    Returns:
        GuestResponse: Datos del huésped

    Raises:
        HTTPException: Si el huésped no existe
    """
    guest = _get_guest_or_404(db, guest_id)
    return guest


@router.put("/{guest_id}", response_model=GuestResponse)
@handle_database_errors
def update_guest(
    guest_id: UUID,
    guest_update: GuestUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> GuestResponse:
    """
    Actualizar los datos de un huésped existente.

    Args:
        guest_id: ID único del huésped
        guest_update: Datos a actualizar
        request: Request object para obtener usuario del middleware
        db: Sesión de base de datos

    Returns:
        GuestResponse: Datos actualizados del huésped

    Raises:
        HTTPException: Si el huésped no existe o los datos ya están en uso
    """
    current_user_uuid = UUID(str(get_current_user_id(request)))
    guest = _get_guest_or_404(db, guest_id)

    update_data = guest_update.model_dump(exclude_unset=True)
    update_data["updated_by"] = current_user_uuid

    if "email" in update_data and update_data["email"] != guest.email:
        validate_unique_field(
            db=db,
            model_class=Guest,
            field_name="email",
            field_value=update_data["email"],
            exclude_id=guest_id,
            error_message=get_custom_message("Guest", "email_unique"),
            include_deleted=True,
        )

    if "document_no" in update_data and update_data["document_no"] != guest.document_no:
        validate_unique_field(
            db=db,
            model_class=Guest,
            field_name="document_no",
            field_value=update_data["document_no"],
            exclude_id=guest_id,
            error_message=get_custom_message("Guest", "document_unique"),
            include_deleted=True,
        )

    if "user_id" in update_data and update_data["user_id"] != guest.user_id:
        validate_unique_field(
            db=db,
            model_class=Guest,
            field_name="user_id",
            field_value=update_data["user_id"],
            exclude_id=guest_id,
            error_message=get_custom_message("Guest", "user_unique"),
            include_deleted=True,
        )

    for key, value in update_data.items():
        setattr(guest, key, value)

    db.commit()
    db.refresh(guest)
    return guest

@router.delete("/{guest_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_database_errors
def delete_guest(
    guest_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Eliminar un huésped del sistema.

    Verifica que el huésped no tenga reservas activas antes de eliminarlo.

    Args:
        guest_id: ID único del huésped
        request: Request object para obtener usuario del middleware
        db: Sesión de base de datos

    Returns:
        JSONResponse: Confirmación de eliminación

    Raises:
        HTTPException: Si el huésped no existe, ya está eliminado o tiene reservas activas
    """
    current_user_uuid = UUID(str(get_current_user_id(request)))
    guest = _get_guest_or_404(db, guest_id)

    primary_reservation = (
        db.query(Reservation.id)
        .filter(
            Reservation.primary_guest_id == guest_id,
            Reservation.deleted_at.is_(None),
            Reservation.status.in_(list(ACTIVE_RESERVATION_STATUSES)),
        )
        .first()
    )

    companion_reservation = (
        db.query(ReservationGuest.reservation_id)
        .join(
            Reservation,
            Reservation.id == ReservationGuest.reservation_id,
        )
        .filter(
            ReservationGuest.guest_id == guest_id,
            Reservation.deleted_at.is_(None),
            Reservation.status.in_(list(ACTIVE_RESERVATION_STATUSES)),
        )
        .first()
    )

    if primary_reservation or companion_reservation:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar el huésped con reservas activas",
        )

    current_time = datetime.now(timezone.utc)
    setattr(guest, "deleted_at", current_time)
    setattr(guest, "updated_by", current_user_uuid)

    db.commit()
    return JSONResponse(content={"detail": "Huésped eliminado correctamente"})
