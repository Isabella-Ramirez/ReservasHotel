from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomCreate, RoomUpdate, RoomResponse
from app.tools.auth import get_current_user_id
from app.tools.error_handlers import (
    handle_database_errors,
    validate_resource_exists,
    validate_unique_field,
    validate_resource_not_deleted,
    get_custom_message,
)

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
@handle_database_errors
def create_room(
    room: RoomCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> RoomResponse:
    """
    Crear una nueva habitación en el sistema.

    Valida que el número de habitación no esté duplicado.

    Args:
        room: Datos de la habitación a crear
        request: Request object para obtener usuario del middleware
        db: Sesión de base de datos

    Returns:
        RoomResponse: Datos de la habitación creada

    Raises:
        HTTPException: Si el número de habitación ya existe
    """
    current_user_id = get_current_user_id(request)

    validate_unique_field(
        db=db,
        model_class=Room,
        field_name="room_number",
        field_value=room.room_number,
        error_message=get_custom_message("Room", "room_number_unique"),
    )

    new_room = Room(
        **room.model_dump(),
        created_by=current_user_id,
        updated_by=current_user_id,
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room


@router.get("", response_model=list[RoomResponse])
@handle_database_errors
def get_rooms(
    status: str | None = Query(
        None, description="Filtrar por estado (AVAILABLE, OCCUPIED, etc.)"
    ),
    room_type_id: str | None = Query(
        None, description="Filtrar por ID del tipo de habitación"
    ),
    db: Session = Depends(get_db),
):
    """
    Obtener habitaciones con filtros opcionales.

    Permite filtrar por estado y tipo de habitación.

    Args:
        status: Filtrar por estado de la habitación
        room_type_id: Filtrar por ID del tipo de habitación
        db: Sesión de base de datos

    Returns:
        list[RoomResponse]: Lista de habitaciones filtradas
    """
    query = db.query(Room)
    if status is not None:
        query = query.filter(Room.status == status)
    if room_type_id:
        query = query.filter(Room.room_type_id == room_type_id)

    rooms = query.all()
    return rooms


@router.get("/{room_id}", response_model=RoomResponse)
@handle_database_errors
def get_room(room_id: UUID, db: Session = Depends(get_db)) -> RoomResponse:
    """
    Obtener una habitación específica por su ID.

    Args:
        room_id: ID único de la habitación
        db: Sesión de base de datos

    Returns:
        RoomResponse: Datos de la habitación

    Raises:
        HTTPException: Si la habitación no existe
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    return validate_resource_exists(room, get_custom_message("Room", "not_found"))


@router.put("/{room_id}", response_model=RoomResponse)
@handle_database_errors
def update_room(
    room_id: UUID,
    room_update: RoomUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> RoomResponse:
    """
    Actualizar los datos de una habitación existente.

    Args:
        room_id: ID único de la habitación
        request: Request object para obtener usuario del middleware
        room_update: Datos a actualizar
        db: Sesión de base de datos

    Returns:
        RoomResponse: Datos actualizados de la habitación

    Raises:
        HTTPException: Si la habitación no existe
    """
    current_user_id = get_current_user_id(request)

    room = db.query(Room).filter(Room.id == room_id).first()
    room = validate_resource_exists(room, get_custom_message("Room", "not_found"))
    validate_resource_not_deleted(room, "habitación")

    if room_update.room_number and room_update.room_number != room.room_number:
        validate_unique_field(
            db=db,
            model_class=Room,
            field_name="room_number",
            field_value=room_update.room_number,
            exclude_id=room_id,
            error_message=get_custom_message("Room", "room_number_unique"),
        )

    update_data = room_update.model_dump(exclude_unset=True)
    update_data["updated_by"] = current_user_id

    for key, value in update_data.items():
        setattr(room, key, value)

    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_database_errors
def delete_room(
    room_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Eliminar una habitación del sistema.

    Verifica que la habitación no tenga reservas activas antes de eliminarla.

    Args:
        room_id: ID único de la habitación
        request: Request object para obtener usuario del middleware
        db: Sesión de base de datos

    Returns:
        JSONResponse: Confirmación de eliminación

    Raises:
        HTTPException: Si la habitación no existe o tiene reservas activas
    """
    current_user_id = get_current_user_id(request)

    room = db.query(Room).filter(Room.id == room_id).first()
    room = validate_resource_exists(room, get_custom_message("Room", "not_found"))
    validate_resource_not_deleted(room, "habitación")

    reservation = (
        db.query(Reservation)
        .filter(
            Reservation.room_id == room_id,
            Reservation.status != ReservationStatus.CANCELLED,
            Reservation.status != ReservationStatus.CHECKED_OUT,
        )
        .first()
    )

    if reservation:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar la habitación con reservas activas",
        )

    current_time = datetime.now(timezone.utc)
    setattr(room, "deleted_at", current_time)
    setattr(room, "updated_by", current_user_id)

    db.commit()
    return JSONResponse(content={"detail": "Habitación eliminada correctamente"})
