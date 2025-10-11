from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.guest import Guest
from app.models.reservation import (
    Reservation,
    ReservationCreate,
    ReservationUpdate,
    ReservationResponse,
    ReservationStatus,
)
from app.models.room import Room, RoomType, RoomStatus
from app.tools.auth import get_current_user_id
from app.tools.error_handlers import (
    handle_database_errors,
    validate_resource_exists,
    validate_resource_not_deleted,
    get_custom_message,
)

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.post(
    "", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED
)
@handle_database_errors
def create_reservation(
    reservation: ReservationCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> ReservationResponse:
    """
    Crear una nueva reserva en el sistema.

    Valida que el huésped y la habitación existan, calcula el costo total
    automáticamente y marca la habitación como ocupada.

    Args:
        reservation: Datos de la reserva a crear
        db: Sesión de base de datos

    Returns:
        ReservationResponse: Datos de la reserva creada

    Raises:
        HTTPException: Si el huésped no existe, la habitación no está disponible
                      o las fechas no son válidas
    """
    current_user_id = get_current_user_id(request)

    guest = db.query(Guest).filter(Guest.id == reservation.guest_id).first()
    guest = validate_resource_exists(guest, get_custom_message("Guest", "not_found"))
    validate_resource_not_deleted(guest, "huésped")

    room = db.query(Room).filter(Room.id == reservation.room_id).first()
    room = validate_resource_exists(room, get_custom_message("Room", "not_found"))
    validate_resource_not_deleted(room, "habitación")

    if str(room.status) != (RoomStatus.AVAILABLE.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Habitación no disponible")

    nights = (reservation.check_out_date - reservation.check_in_date).days
    if nights <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Las fechas de reserva no son válidas")

    room_type = db.query(RoomType).filter(RoomType.id == room.room_type_id).first()
    room_type = validate_resource_exists(
        room_type,
        get_custom_message("Room", "room_type_fk"),
    )

    db.refresh(room_type)
    base_rate = getattr(room_type, "base_rate")
    total = nights * float(base_rate)

    new_reservation = Reservation(
        guest_id=reservation.guest_id,
        room_id=reservation.room_id,
        check_in_date=reservation.check_in_date,
        check_out_date=reservation.check_out_date,
        total_amount=total,
        status=ReservationStatus.CONFIRMED.value,
        created_by=current_user_id,
        updated_by=current_user_id,
    )

    for key, value in {
        "status": RoomStatus.OCCUPIED.value,
        "updated_by": current_user_id,
    }.items():
        setattr(room, key, value)

    db.add(new_reservation)
    db.commit()
    db.refresh(new_reservation)

    return new_reservation


@router.get("", response_model=list[ReservationResponse])
@handle_database_errors
def get_reservations(db: Session = Depends(get_db)):
    """
    Obtener todas las reservas del sistema.

    Args:
        db: Sesión de base de datos

    Returns:
        list[ReservationResponse]: Lista de todas las reservas
    """
    reservations = db.query(Reservation).all()
    return reservations or []


@router.get("/{reservation_id}", response_model=ReservationResponse)
@handle_database_errors
def get_reservation(
    reservation_id: UUID,
    db: Session = Depends(get_db),
) -> ReservationResponse:
    """
    Obtener una reserva específica por su ID.

    Args:
        reservation_id: ID único de la reserva
        db: Sesión de base de datos

    Returns:
        ReservationResponse: Datos de la reserva

    Raises:
        HTTPException: Si la reserva no existe
    """
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    reservation = validate_resource_exists(reservation, get_custom_message("Reservation", "not_found"))
    return reservation


@router.put("/{reservation_id}/cancel", response_model=ReservationResponse)
@handle_database_errors
def cancel_reservation(
    reservation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ReservationResponse:
    """
    Cancelar una reserva existente.

    Cambia el estado de la reserva a CANCELLED y libera la habitación.

    Args:
        reservation_id: ID único de la reserva
        request: Request object para obtener usuario del middleware
        db: Sesión de base de datos

    Returns:
        ReservationResponse: Datos de la reserva cancelada

    Raises:
        HTTPException: Si la reserva no existe o ya está cancelada
    """
    current_user_id = get_current_user_id(request)
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    reservation = validate_resource_exists(reservation, get_custom_message("Reservation", "not_found"))
    validate_resource_not_deleted(reservation, "reserva")

    db.refresh(reservation)

    if str(reservation.status) == ReservationStatus.CANCELLED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La reserva ya está cancelada")

    for key, value in {
        "status": ReservationStatus.CANCELLED.value,
        "updated_by": current_user_id,
    }.items():
        setattr(reservation, key, value)

    room = db.query(Room).filter(Room.id == reservation.room_id).first()
    if room:
        for key, value in {
            "status": RoomStatus.AVAILABLE.value,
            "updated_by": current_user_id,
        }.items():
            setattr(room, key, value)

    db.commit()
    db.refresh(reservation)
    return reservation


@router.put("/{reservation_id}", response_model=ReservationResponse)
@handle_database_errors
def update_reservation(
    reservation_id: UUID,
    reservation_update: ReservationUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> ReservationResponse:
    """
    Actualizar una reserva existente.

    Permite modificar los datos de la reserva y recalcula automáticamente
    el costo total si se cambian las fechas.

    Args:
        reservation_id: ID único de la reserva
        reservation_update: Datos a actualizar
        request: Request object para obtener usuario del middleware
        db: Sesión de base de datos

    Returns:
        ReservationResponse: Datos actualizados de la reserva

    Raises:
        HTTPException: Si la reserva no existe o las fechas no son válidas
    """
    current_user_id = get_current_user_id(request)
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    reservation = validate_resource_exists(reservation, get_custom_message("Reservation", "not_found"))
    validate_resource_not_deleted(reservation, "reserva")

    update_data = reservation_update.model_dump(exclude_unset=True)
    new_check_in = update_data.get("check_in_date", reservation.check_in_date)
    new_check_out = update_data.get("check_out_date", reservation.check_out_date)
    if ("check_in_date" in update_data or "check_out_date" in update_data) and new_check_in and new_check_out:
        nights = (new_check_out - new_check_in).days
        if nights <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Las fechas de reserva no son válidas")

    for key, value in update_data.items():
        setattr(reservation, key, value)

    if ("check_in_date" in update_data or "check_out_date" in update_data) and new_check_in and new_check_out:
        nights = (reservation.check_out_date - reservation.check_in_date).days
        room = db.query(Room).filter(Room.id == reservation.room_id).first()
        if room:
            room_type = db.query(RoomType).filter(RoomType.id == room.room_type_id).first()
            if room_type:
                db.refresh(room_type)
                base_rate = getattr(room_type, "base_rate")
                reservation.total_amount = nights * float(base_rate)

    setattr(reservation, "updated_by", current_user_id)

    db.commit()
    db.refresh(reservation)
    return reservation


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_database_errors
def delete_reservation(
    reservation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Eliminar una reserva del sistema.

    Libera la habitación si la reserva estaba confirmada antes de eliminarla.

    Args:
        reservation_id: ID único de la reserva
        request: Request object para obtener usuario del middleware
        db: Sesión de base de datos

    Raises:
        HTTPException: Si la reserva no existe
    """
    current_user_id = get_current_user_id(request)
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    reservation = validate_resource_exists(reservation, get_custom_message("Reservation", "not_found"))
    validate_resource_not_deleted(reservation, "reserva")

    db.refresh(reservation)

    if str(reservation.status) == ReservationStatus.CONFIRMED.value:
        room = db.query(Room).filter(Room.id == reservation.room_id).first()
        if room:
            for key, value in {
                "status": RoomStatus.AVAILABLE.value,
                "updated_by": current_user_id,
            }.items():
                setattr(room, key, value)

    current_time = datetime.now(timezone.utc)
    for key, value in {
        "status": ReservationStatus.CANCELLED.value,
        "deleted_at": current_time,
        "updated_by": current_user_id,
    }.items():
        setattr(reservation, key, value)

    db.commit()
    return JSONResponse(content={"detail": "Reserva eliminada correctamente"})
