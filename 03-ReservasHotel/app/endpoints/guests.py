from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.guest import Guest, GuestCreate, GuestUpdate, GuestResponse
from app.models.reservation import Reservation, ReservationStatus
from app.tools.auth import get_current_user_id

router = APIRouter(prefix="/guests", tags=["Guests"])


@router.post("", response_model=GuestResponse, status_code=status.HTTP_201_CREATED)
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
        HTTPException: Si el email ya está registrado
    """
    current_user_id = get_current_user_id(request)
    
    existing = db.query(Guest).filter(Guest.email == guest.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    new_guest = Guest(
        **guest.model_dump(),
        created_by=current_user_id,
        updated_by=current_user_id,
    )
    db.add(new_guest)
    db.commit()
    db.refresh(new_guest)
    return new_guest


@router.get("", response_model=list[GuestResponse])
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
    guest = db.query(Guest).filter(Guest.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Huésped no encontrado")
    return guest


@router.put("/{guest_id}", response_model=GuestResponse)
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
        HTTPException: Si el huésped no existe
    """
    current_user_id = get_current_user_id(request)
    
    guest = db.query(Guest).filter(Guest.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Huésped no encontrado")

    update_data = guest_update.model_dump(exclude_unset=True)
    update_data["updated_by"] = current_user_id

    for key, value in update_data.items():
        setattr(guest, key, value)

    db.commit()
    db.refresh(guest)
    return guest


@router.delete("/{guest_id}", status_code=status.HTTP_204_NO_CONTENT)
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
        HTTPException: Si el huésped no existe o tiene reservas activas
    """
    current_user_id = get_current_user_id(request)
    
    guest = db.query(Guest).filter(Guest.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Huésped no encontrado")

    reservation = (
        db.query(Reservation)
        .filter(
            Reservation.guest_id == guest_id,
            Reservation.status.notin_(
                [
                    ReservationStatus.CANCELLED.value,
                    ReservationStatus.CHECKED_OUT.value,
                ]
            ),
        )
        .first()
    )

    if reservation:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar el huésped con reservas activas",
        )

    current_time = datetime.now(timezone.utc)
    setattr(guest, "deleted_at", current_time)
    setattr(guest, "updated_by", current_user_id)

    db.commit()
    return JSONResponse(content={"detail": "Huésped eliminado correctamente"})
