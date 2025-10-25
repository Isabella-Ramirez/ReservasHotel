from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func, text

from app.database import Base


class RoomStatus(PyEnum):
    """Estados posibles de una habitación."""

    AVAILABLE = "AVAILABLE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    CLEANING = "CLEANING"
    OCCUPIED = "OCCUPIED"


class RoomType(Base):
    """
    Modelo SQLAlchemy para tipos de habitación.

    Define las características y tarifas base de cada tipo de habitación.
    """

    __tablename__ = "room_types"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    max_guests: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default=text("1"),
    )
    base_rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0.00"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(postgresql.UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(postgresql.UUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


class Room(Base):
    """
    Modelo SQLAlchemy para habitaciones.

    Representa las habitaciones físicas del hotel con su estado y tipo.
    """

    __tablename__ = "rooms"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    room_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    floor: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    room_type_id: Mapped[Optional[UUID]] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("room_types.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[RoomStatus] = mapped_column(
        Enum(RoomStatus, name="room_status", create_type=False),
        nullable=False,
        server_default=RoomStatus.AVAILABLE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


class RoomTypeBase(BaseModel):
    """Modelo base para tipos de habitación."""

    code: str
    name: str
    description: Optional[str] = None
    max_guests: int = Field(..., ge=1, description="Capacidad máxima de huéspedes")
    base_rate: float


class RoomTypeCreate(RoomTypeBase):
    """Modelo para crear un nuevo tipo de habitación."""

    pass


class RoomTypeUpdate(BaseModel):
    """Modelo para actualizar un tipo de habitación existente."""

    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    max_guests: Optional[int] = Field(None, ge=1)
    base_rate: Optional[float] = None


class RoomTypeResponse(RoomTypeBase):
    """Modelo de respuesta para tipos de habitación."""

    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoomBase(BaseModel):
    """Modelo base para habitaciones."""

    room_number: str = Field(..., description="Número de la habitación")
    floor: Optional[str] = Field(None, description="Piso de la habitación")
    room_type_id: Optional[UUID] = Field(None, description="ID del tipo de habitación")
    status: RoomStatus = Field(
        RoomStatus.AVAILABLE, description="Estado de la habitación"
    )


class RoomCreate(BaseModel):
    """Modelo para crear una nueva habitación."""

    room_number: str = Field(..., description="Número de la habitación")
    floor: Optional[str] = Field(None, description="Piso de la habitación")
    room_type_id: Optional[UUID] = Field(None, description="ID del tipo de habitación")
    status: RoomStatus = Field(
        RoomStatus.AVAILABLE, description="Estado de la habitación"
    )


class RoomUpdate(BaseModel):
    """Modelo para actualizar una habitación existente."""

    room_number: Optional[str] = None
    floor: Optional[str] = None
    room_type_id: Optional[UUID] = None
    status: Optional[RoomStatus] = None


class RoomResponse(RoomBase):
    """Modelo de respuesta para habitaciones."""

    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
