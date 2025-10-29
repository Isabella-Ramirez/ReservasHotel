from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional, Sequence
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.guest import Guest
from app.models.reservation import (
    Reservation,
    ReservationCreate,
    ReservationGuest,
    ReservationResponse,
    ReservationStatus,
    ReservationUpdate,
)
from app.models.room import Room, RoomStatus, RoomType
from app.tools.auth import get_current_user_id
from app.tools.error_handlers import (
    get_custom_message,
    handle_database_errors,
    validate_resource_exists,
)

router = APIRouter(prefix="/reservations", tags=["Reservations"])

ACTIVE_RESERVATION_STATUSES: Sequence[ReservationStatus] = (
    ReservationStatus.PENDING,
    ReservationStatus.CONFIRMED,
    ReservationStatus.CHECKED_IN,
)
TWO_DECIMALS = Decimal("0.01")


def _generate_reservation_code(db: Session) -> str:
    """Genera un localizador único para la reserva."""
    while True:
        candidate = uuid4().hex[:8].upper()
        exists = (
            db.query(Reservation.id)
            .filter(Reservation.code == candidate)
            .execution_options(include_deleted=True)
            .first()
        )
        if not exists:
            return candidate


def _normalize_guests(
    db: Session, primary_guest_id: UUID, companion_guest_ids: Iterable[UUID]
) -> list[UUID]:
    """Valida y normaliza la lista de huéspedes asociados a la reserva."""
    unique_ids: list[UUID] = []
    for guest_id in [primary_guest_id, *companion_guest_ids]:
        if guest_id not in unique_ids:
            unique_ids.append(guest_id)

    guests = (
        db.query(Guest)
        .filter(
            Guest.id.in_(unique_ids),
            Guest.deleted_at.is_(None),
        )
        .all()
    )

    if len(guests) != len(unique_ids):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Alguno de los huéspedes asociados no existe",
        )

    return unique_ids


def _room_has_conflict(
    db: Session,
    room_id: UUID,
    check_in: date,
    check_out: date,
    exclude_reservation_id: Optional[UUID] = None,
) -> bool:
    """Verifica si la habitación tiene traslapo de fechas con otra reserva activa."""
    query = db.query(Reservation.id).filter(
        Reservation.room_id == room_id,
        Reservation.deleted_at.is_(None),
        Reservation.status.in_(list(ACTIVE_RESERVATION_STATUSES)),
        Reservation.check_out_date > check_in,
        Reservation.check_in_date < check_out,
    )

    if exclude_reservation_id:
        query = query.filter(Reservation.id != exclude_reservation_id)

    return query.first() is not None


def _find_available_room(
    db: Session,
    room_type_id: UUID,
    check_in: date,
    check_out: date,
) -> Optional[Room]:
    """Busca la primera habitación disponible del tipo indicado para el rango de fechas."""
    candidate_rooms = (
        db.query(Room)
        .filter(
            Room.room_type_id == room_type_id,
            Room.deleted_at.is_(None),
            Room.status == RoomStatus.AVAILABLE,
        )
        .order_by(Room.room_number.asc())
        .all()
    )

    for candidate in candidate_rooms:
        if not _room_has_conflict(
            db,
            candidate.id,
            check_in,
            check_out,
        ):
            return candidate

    return None


def _sync_guest_links(
    reservation: Reservation, guest_ids: list[UUID], primary_guest_id: UUID
) -> None:
    """Sincroniza los huéspedes asociados a la reserva."""
    existing = {link.guest_id: link for link in reservation.guest_links}

    for link in list(reservation.guest_links):
        if link.guest_id not in guest_ids:
            reservation.guest_links.remove(link)

    for guest_id in guest_ids:
        link = existing.get(guest_id)
        if link:
            link.is_primary = guest_id == primary_guest_id
            continue
        reservation.guest_links.append(
            ReservationGuest(guest_id=guest_id, is_primary=guest_id == primary_guest_id)
        )

    setattr(reservation, "guest_count", len(guest_ids))


def _mark_room_as_available_if_unused(
    db: Session, room: Optional[Room], exclude_reservation_id: Optional[UUID]
) -> None:
    """Marca la habitación como disponible si no tiene otras reservas activas."""
    if not room:
        return

    query = db.query(Reservation.id).filter(
        Reservation.room_id == room.id,
        Reservation.deleted_at.is_(None),
        Reservation.status.in_(list(ACTIVE_RESERVATION_STATUSES)),
    )
    if exclude_reservation_id:
        query = query.filter(Reservation.id != exclude_reservation_id)

    if query.first() is None:
        setattr(room, "status", RoomStatus.AVAILABLE)


def _get_reservation_with_links(db: Session, reservation_id: UUID) -> Reservation:
    reservation = (
        db.query(Reservation)
        .filter(Reservation.id == reservation_id)
        .options(selectinload(Reservation.guest_links))
        .first()
    )
    reservation = validate_resource_exists(
        reservation, get_custom_message("Reservation", "not_found")
    )
    assert reservation is not None
    return reservation


@router.post(
    "",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
@handle_database_errors
def create_reservation(
    reservation: ReservationCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> ReservationResponse:
    """
    Crear una nueva reserva con huésped principal y acompañantes opcionales.
    """

    current_user_uuid = UUID(str(get_current_user_id(request)))

    guest_ids = _normalize_guests(
        db, reservation.primary_guest_id, reservation.companion_guest_ids
    )

    today = date.today()
    if reservation.check_in_date < today:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La fecha de entrada debe ser hoy o una fecha futura",
        )

    room_type = (
        db.query(RoomType).filter(RoomType.id == reservation.room_type_id).first()
    )
    room_type = validate_resource_exists(
        room_type, get_custom_message("Room", "room_type_fk")
    )
    assert room_type is not None

    max_guests = room_type.max_guests
    if len(guest_ids) > max_guests:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"La capacidad máxima del tipo de habitación es {max_guests} huéspedes",
        )

    selected_room: Optional[Room] = None
    selected_room_id: Optional[UUID] = None

    if reservation.room_id is not None:
        selected_room = db.query(Room).filter(Room.id == reservation.room_id).first()
        selected_room = validate_resource_exists(
            selected_room, get_custom_message("Room", "not_found")
        )
        assert selected_room is not None

        if selected_room.room_type_id != room_type.id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La habitación seleccionada no pertenece al tipo solicitado",
            )

        if _room_has_conflict(
            db,
            selected_room.id,
            reservation.check_in_date,
            reservation.check_out_date,
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La habitación ya tiene una reserva activa en ese rango de fechas",
            )
        selected_room_id = selected_room.id
    else:
        selected_room = _find_available_room(
            db,
            room_type.id,
            reservation.check_in_date,
            reservation.check_out_date,
        )
        if selected_room is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "No hay habitaciones disponibles para el tipo seleccionado en las fechas solicitadas",
            )
        selected_room_id = selected_room.id

    nights = (reservation.check_out_date - reservation.check_in_date).days
    if nights <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Las fechas de reserva no son válidas",
        )

    nightly_rate_source = (
        reservation.nightly_rate
        if reservation.nightly_rate is not None
        else room_type.base_rate
    )
    nightly_rate = Decimal(nightly_rate_source).quantize(
        TWO_DECIMALS, rounding=ROUND_HALF_UP
    )
    total_amount = (nightly_rate * nights).quantize(
        TWO_DECIMALS, rounding=ROUND_HALF_UP
    )

    new_reservation = Reservation(
        code=_generate_reservation_code(db),
        status=(
            ReservationStatus.CONFIRMED
            if selected_room_id is not None
            else ReservationStatus.PENDING
        ),
        primary_guest_id=reservation.primary_guest_id,
        room_type_id=room_type.id,
        room_id=selected_room_id,
        check_in_date=reservation.check_in_date,
        check_out_date=reservation.check_out_date,
        guest_count=len(guest_ids),
        nightly_rate=nightly_rate,
        total_amount=total_amount,
        channel=reservation.channel,
        notes=reservation.notes,
        created_by=current_user_uuid,
        updated_by=current_user_uuid,
    )

    _sync_guest_links(new_reservation, guest_ids, reservation.primary_guest_id)

    if selected_room is not None:
        setattr(selected_room, "updated_by", current_user_uuid)

    db.add(new_reservation)
    db.commit()

    db.refresh(
        new_reservation,
        attribute_names=[
            "guest_links",
            "room",
            "room_type",
            "payment",
        ],
    )

    return new_reservation


@router.get("", response_model=list[ReservationResponse])
@handle_database_errors
def get_reservations(
    status_filter: ReservationStatus | None = Query(
        None, description="Filtrar por estado de la reserva"
    ),
    db: Session = Depends(get_db),
):
    """
    Obtener todas las reservas del sistema, con huéspedes asociados.
    """
    query = (
        db.query(Reservation)
        .options(selectinload(Reservation.guest_links))
        .order_by(Reservation.check_in_date.desc())
    )

    if status_filter:
        query = query.filter(Reservation.status == status_filter)

    reservations = query.all()
    return reservations or []


@router.get("/{reservation_id}", response_model=ReservationResponse)
@handle_database_errors
def get_reservation(
    reservation_id: UUID,
    db: Session = Depends(get_db),
) -> ReservationResponse:
    """
    Obtener una reserva específica por su ID.
    """
    return _get_reservation_with_links(db, reservation_id)


@router.put("/{reservation_id}/cancel", status_code=status.HTTP_200_OK)
@handle_database_errors
def cancel_reservation(
    reservation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Cancelar una reserva existente y liberar la habitación si aplica.

    Devuelve un mensaje de confirmación con datos mínimos de la reserva.
    """
    current_user_uuid = UUID(str(get_current_user_id(request)))

    reservation = _get_reservation_with_links(db, reservation_id)

    if reservation.status == ReservationStatus.CANCELLED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La reserva ya está cancelada")

    setattr(reservation, "status", ReservationStatus.CANCELLED)
    setattr(reservation, "updated_by", current_user_uuid)

    reservation_room_id = reservation.room_id
    if reservation_room_id is not None:
        room = db.query(Room).filter(Room.id == reservation_room_id).first()
        if room is not None:
            _mark_room_as_available_if_unused(db, room, reservation.id)
            setattr(room, "updated_by", current_user_uuid)

    db.commit()
    db.refresh(reservation)

    return JSONResponse(
        content={
            "detail": "Reserva cancelada correctamente",
            "reservation_id": str(reservation.id),
            "reservation_code": reservation.code,
            "status": reservation.status.value,
        }
    )


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
    """
    current_user_uuid = UUID(str(get_current_user_id(request)))

    reservation = _get_reservation_with_links(db, reservation_id)

    update_data = reservation_update.model_dump(exclude_unset=True)

    new_primary_guest_id: UUID = update_data.pop(
        "primary_guest_id", reservation.primary_guest_id
    )

    if "companion_guest_ids" in update_data:
        companion_ids = update_data.pop("companion_guest_ids") or []
    else:
        companion_ids = [
            link.guest_id for link in reservation.guest_links if not link.is_primary
        ]

    companion_ids = [gid for gid in companion_ids if gid != new_primary_guest_id]

    guest_ids = _normalize_guests(db, new_primary_guest_id, companion_ids)

    room_type_id = update_data.pop("room_type_id", reservation.room_type_id)
    room_type = db.query(RoomType).filter(RoomType.id == room_type_id).first()
    room_type = validate_resource_exists(
        room_type, get_custom_message("Room", "room_type_fk")
    )
    assert room_type is not None

    max_guests = room_type.max_guests
    if len(guest_ids) > max_guests:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"La capacidad máxima del tipo de habitación es {max_guests} huéspedes",
        )

    check_in_updated = "check_in_date" in update_data
    check_out_updated = "check_out_date" in update_data
    new_check_in = update_data.pop("check_in_date", reservation.check_in_date)
    new_check_out = update_data.pop("check_out_date", reservation.check_out_date)
    if new_check_out <= new_check_in:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Las fechas de reserva no son válidas",
        )
    today = date.today()
    if check_in_updated and new_check_in < today:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La fecha de entrada debe ser hoy o una fecha futura",
        )
    if check_out_updated and new_check_out <= today:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La fecha de salida debe ser posterior a hoy",
        )

    existing_room_id = reservation.room_id
    room_field_present = "room_id" in update_data or existing_room_id is not None
    new_room_value = update_data.pop("room_id", existing_room_id)
    new_room_id = new_room_value
    new_room: Optional[Room] = None
    if new_room_id is not None:
        new_room = db.query(Room).filter(Room.id == new_room_id).first()
        new_room = validate_resource_exists(
            new_room, get_custom_message("Room", "not_found")
        )
        assert new_room is not None

        if new_room is not None and new_room.room_type_id != room_type.id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La habitación seleccionada no pertenece al tipo solicitado",
            )

        if _room_has_conflict(
            db,
            new_room.id,
            new_check_in,
            new_check_out,
            exclude_reservation_id=reservation.id,
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La habitación ya tiene una reserva activa en ese rango de fechas",
            )

    previous_room_id = existing_room_id

    if reservation_update.status is not None:
        setattr(reservation, "status", reservation_update.status)
    if "channel" in update_data:
        setattr(reservation, "channel", update_data.pop("channel"))
    if "notes" in update_data:
        setattr(reservation, "notes", update_data.pop("notes"))

    setattr(reservation, "primary_guest_id", new_primary_guest_id)
    setattr(reservation, "room_type_id", room_type.id)
    setattr(reservation, "check_in_date", new_check_in)
    setattr(reservation, "check_out_date", new_check_out)

    existing_rate = reservation.nightly_rate
    nightly_rate_value = update_data.pop("nightly_rate", existing_rate)
    nightly_rate = Decimal(nightly_rate_value).quantize(
        TWO_DECIMALS, rounding=ROUND_HALF_UP
    )
    setattr(reservation, "nightly_rate", nightly_rate)

    nights = (reservation.check_out_date - reservation.check_in_date).days
    total_amount = (nightly_rate * nights).quantize(
        TWO_DECIMALS, rounding=ROUND_HALF_UP
    )
    setattr(reservation, "total_amount", total_amount)
    setattr(reservation, "updated_by", current_user_uuid)

    _sync_guest_links(reservation, guest_ids, new_primary_guest_id)

    if room_field_present:
        setattr(reservation, "room_id", new_room_id)

    old_room: Room | None = None
    if (
        room_field_present
        and previous_room_id is not None
        and previous_room_id != new_room_id
    ):
        old_room = db.query(Room).filter(Room.id == previous_room_id).first()
        if old_room is not None:
            _mark_room_as_available_if_unused(db, old_room, reservation.id)
            setattr(old_room, "updated_by", current_user_uuid)

    final_room: Optional[Room] = new_room
    if final_room is None and reservation.room_id is not None:
        final_room = db.query(Room).filter(Room.id == reservation.room_id).first()

    if final_room is not None:
        if reservation.status == ReservationStatus.CHECKED_IN:
            room_status = RoomStatus.OCCUPIED
        else:
            room_status = RoomStatus.AVAILABLE
        setattr(final_room, "status", room_status)
        setattr(final_room, "updated_by", current_user_uuid)

    db.commit()
    db.refresh(
        reservation,
        attribute_names=[
            "guest_links",
            "room",
            "room_type",
        ],
    )
    return reservation


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_database_errors
def delete_reservation(
    reservation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Eliminar (soft-delete) una reserva del sistema.
    """
    current_user_uuid = UUID(str(get_current_user_id(request)))

    reservation = _get_reservation_with_links(db, reservation_id)

    setattr(reservation, "status", ReservationStatus.CANCELLED)
    setattr(reservation, "deleted_at", datetime.now(timezone.utc))
    setattr(reservation, "updated_by", current_user_uuid)

    reservation_room_id = reservation.room_id
    if reservation_room_id is not None:
        room = db.query(Room).filter(Room.id == reservation_room_id).first()
        if room is not None:
            _mark_room_as_available_if_unused(db, room, reservation.id)
            setattr(room, "updated_by", current_user_uuid)

    db.commit()
    return JSONResponse(content={"detail": "Reserva eliminada correctamente"})
