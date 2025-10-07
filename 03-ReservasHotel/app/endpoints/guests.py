from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.guest import Guest, GuestCreate, GuestUpdate, GuestResponse
from app.models.reservation import Reservation, ReservationStatus

router = APIRouter(prefix="/guests", tags=["Guests"])


@router.post("", response_model=GuestResponse, status_code=status.HTTP_201_CREATED)
def create_guest(guest: GuestCreate, db: Session = Depends(get_db)) -> GuestResponse:
    """
    Crear un nuevo huésped en el sistema.

    Args:
        guest: Datos del huésped a crear
        db: Sesión de base de datos

    Returns:
        GuestResponse: Datos del huésped creado

    Raises:
        HTTPException: Si el email ya está registrado
    """
    existing = db.query(Guest).filter(Guest.email == guest.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    new_guest = Guest(**guest.model_dump())
    db.add(new_guest)
    db.commit()
    db.refresh(new_guest)
    return new_guest


@router.get("/", response_model=list[GuestResponse])
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
    guest_id: UUID, guest_update: GuestUpdate, db: Session = Depends(get_db)
) -> GuestResponse:
    """
    Actualizar los datos de un huésped existente.

    Args:
        guest_id: ID único del huésped
        guest_update: Datos a actualizar
        db: Sesión de base de datos

    Returns:
        GuestResponse: Datos actualizados del huésped

    Raises:
        HTTPException: Si el huésped no existe
    """
    guest = db.query(Guest).filter(Guest.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Huésped no encontrado")

    for key, value in guest_update.model_dump(exclude_unset=True).items():
        setattr(guest, key, value)

    db.commit()
    db.refresh(guest)
    return guest


@router.delete("/{guest_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_guest(guest_id: UUID, db: Session = Depends(get_db)) -> JSONResponse:
    """
    Eliminar un huésped del sistema.

    Verifica que el huésped no tenga reservas activas antes de eliminarlo.

    Args:
        guest_id: ID único del huésped
        db: Sesión de base de datos

    Returns:
        JSONResponse: Confirmación de eliminación

    Raises:
        HTTPException: Si el huésped no existe o tiene reservas activas
    """
    guest = db.query(Guest).filter(Guest.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Huésped no encontrado")

    reservation = (
        db.query(Reservation)
        .filter(
            Reservation.guest_id == guest_id,
            Reservation.status != ReservationStatus.CANCELLED,
            Reservation.status != ReservationStatus.CHECKED_OUT,
        )
        .first()
    )

    if reservation:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar el huésped con reservas activas",
        )

    db.delete(guest)
    db.commit()
    return JSONResponse(content={"detail": "Huésped eliminado correctamente"})
