from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.post(
    "/", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED
)
def create_reservation(
    reservation: ReservationCreate, db: Session = Depends(get_db)
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
    guest = db.query(Guest).filter(Guest.id == reservation.guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Huésped no encontrado")

    room = (
        db.query(Room)
        .filter(Room.id == reservation.room_id, Room.status == RoomStatus.AVAILABLE)
        .first()
    )
    if not room:
        raise HTTPException(status_code=400, detail="Habitación no disponible")

    nights = (reservation.check_out_date - reservation.check_in_date).days
    if nights <= 0:
        raise HTTPException(
            status_code=400, detail="Las fechas de reserva no son válidas"
        )

    room_type = db.query(RoomType).filter(RoomType.id == room.room_type_id).first()
    if not room_type:
        raise HTTPException(status_code=400, detail="Tipo de habitación no encontrado")

    db.refresh(room_type)
    base_rate = getattr(room_type, "base_rate")
    total = nights * float(base_rate)

    new_reservation = Reservation(
        guest_id=reservation.guest_id,
        room_id=reservation.room_id,
        check_in_date=reservation.check_in_date,
        check_out_date=reservation.check_out_date,
        total_amount=total,
        status=ReservationStatus.CONFIRMED,
    )

    db.query(Room).filter(Room.id == reservation.room_id).update(
        {"status": RoomStatus.OCCUPIED.value}
    )

    db.add(new_reservation)
    db.commit()
    db.refresh(new_reservation)

    return new_reservation


@router.get("", response_model=list[ReservationResponse])
def get_reservations(db: Session = Depends(get_db)):
    """
    Obtener todas las reservas del sistema.

    Args:
        db: Sesión de base de datos

    Returns:
        list[ReservationResponse]: Lista de todas las reservas
    """
    return db.query(Reservation).all()


@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation(
    reservation_id: UUID, db: Session = Depends(get_db)
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
    if not reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return reservation


@router.put("/{reservation_id}/cancel", response_model=ReservationResponse)
def cancel_reservation(
    reservation_id: UUID, db: Session = Depends(get_db)
) -> ReservationResponse:
    """
    Cancelar una reserva existente.

    Cambia el estado de la reserva a CANCELLED y libera la habitación.

    Args:
        reservation_id: ID único de la reserva
        db: Sesión de base de datos

    Returns:
        ReservationResponse: Datos de la reserva cancelada

    Raises:
        HTTPException: Si la reserva no existe o ya está cancelada
    """
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    db.refresh(reservation)

    if str(reservation.status) == ReservationStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="La reserva ya está cancelada")

    db.query(Reservation).filter(Reservation.id == reservation_id).update(
        {"status": ReservationStatus.CANCELLED.value}
    )

    room = db.query(Room).filter(Room.id == reservation.room_id).first()
    if room:
        db.query(Room).filter(Room.id == reservation.room_id).update(
            {"status": RoomStatus.AVAILABLE.value}
        )

    db.commit()
    db.refresh(reservation)
    return reservation


@router.put("/{reservation_id}", response_model=ReservationResponse)
def update_reservation(
    reservation_id: UUID,
    reservation_update: ReservationUpdate,
    db: Session = Depends(get_db),
) -> ReservationResponse:
    """
    Actualizar una reserva existente.

    Permite modificar los datos de la reserva y recalcula automáticamente
    el costo total si se cambian las fechas.

    Args:
        reservation_id: ID único de la reserva
        reservation_update: Datos a actualizar
        db: Sesión de base de datos

    Returns:
        ReservationResponse: Datos actualizados de la reserva

    Raises:
        HTTPException: Si la reserva no existe o las fechas no son válidas
    """
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    update_data = reservation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(reservation, key, value)

    db.flush()
    db.refresh(reservation)

    if "check_in_date" in update_data or "check_out_date" in update_data:
        nights = (reservation.check_out_date - reservation.check_in_date).days
        if nights <= 0:
            raise HTTPException(
                status_code=400, detail="Las fechas de reserva no son válidas"
            )
        room = db.query(Room).filter(Room.id == reservation.room_id).first()
        if room:
            room_type = (
                db.query(RoomType).filter(RoomType.id == room.room_type_id).first()
            )
            if room_type:
                db.refresh(room_type)
                base_rate = getattr(room_type, "base_rate")
                reservation.total_amount = nights * float(base_rate)

    db.commit()
    db.refresh(reservation)
    return reservation


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reservation(
    reservation_id: UUID, db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Eliminar una reserva del sistema.

    Libera la habitación si la reserva estaba confirmada antes de eliminarla.

    Args:
        reservation_id: ID único de la reserva
        db: Sesión de base de datos

    Returns:
        JSONResponse: Confirmación de eliminación

    Raises:
        HTTPException: Si la reserva no existe
    """
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    db.refresh(reservation)

    if str(reservation.status) == ReservationStatus.CONFIRMED.value:
        room = db.query(Room).filter(Room.id == reservation.room_id).first()
        if room:
            db.query(Room).filter(Room.id == reservation.room_id).update(
                {"status": RoomStatus.AVAILABLE.value}
            )

    db.delete(reservation)
    db.commit()
    return JSONResponse(content={"detail": "Reserva eliminada correctamente"})
