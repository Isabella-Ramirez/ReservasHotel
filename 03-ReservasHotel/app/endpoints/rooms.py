from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomCreate, RoomUpdate, RoomResponse

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(room: RoomCreate, db: Session = Depends(get_db)) -> RoomResponse:
    """
    Crear una nueva habitación en el sistema.

    Valida que el número de habitación no esté duplicado.

    Args:
        room: Datos de la habitación a crear
        db: Sesión de base de datos

    Returns:
        RoomResponse: Datos de la habitación creada

    Raises:
        HTTPException: Si el número de habitación ya existe
    """
    existing = db.query(Room).filter(Room.room_number == room.room_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="El número de habitación ya existe")

    new_room = Room(**room.dict())
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room


@router.get("/", response_model=list[RoomResponse])
def get_rooms(
    available: bool | None = Query(None, description="Filtrar por disponibilidad"),
    room_type: str | None = Query(None, description="Filtrar por tipo de habitación"),
    db: Session = Depends(get_db),
) -> list[RoomResponse]:
    """
    Obtener habitaciones con filtros opcionales.

    Permite filtrar por disponibilidad y tipo de habitación.

    Args:
        available: Filtrar por disponibilidad (True/False)
        room_type: Filtrar por tipo de habitación (búsqueda parcial)
        db: Sesión de base de datos

    Returns:
        list[RoomResponse]: Lista de habitaciones filtradas
    """
    query = db.query(Room)
    if available is not None:
        query = query.filter(Room.is_available == available)
    if room_type:
        query = query.filter(Room.room_type.ilike(f"%{room_type}%"))

    rooms = query.all()
    return [RoomResponse.model_validate(room) for room in rooms]


@router.get("/{room_id}", response_model=RoomResponse)
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
    if not room:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")
    return room


@router.put("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: UUID, room_update: RoomUpdate, db: Session = Depends(get_db)
) -> RoomResponse:
    """
    Actualizar los datos de una habitación existente.

    Args:
        room_id: ID único de la habitación
        room_update: Datos a actualizar
        db: Sesión de base de datos

    Returns:
        RoomResponse: Datos actualizados de la habitación

    Raises:
        HTTPException: Si la habitación no existe
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")

    for key, value in room_update.dict(exclude_unset=True).items():
        setattr(room, key, value)

    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: UUID, db: Session = Depends(get_db)) -> JSONResponse:
    """
    Eliminar una habitación del sistema.

    Verifica que la habitación no tenga reservas activas antes de eliminarla.

    Args:
        room_id: ID único de la habitación
        db: Sesión de base de datos

    Returns:
        JSONResponse: Confirmación de eliminación

    Raises:
        HTTPException: Si la habitación no existe o tiene reservas activas
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")

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

    db.delete(room)
    db.commit()
    return JSONResponse(content={"detail": "Habitación eliminada correctamente"})
