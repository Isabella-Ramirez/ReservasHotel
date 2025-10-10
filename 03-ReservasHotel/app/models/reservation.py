from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func, text

from app.database import Base


class ReservationStatus(PyEnum):
    """Estados posibles de una reserva."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class PaymentStatus(PyEnum):
    """Estados posibles de un pago."""

    PENDING = "PENDING"
    PAID = "PAID"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


class Reservation(Base):
    """
    Modelo SQLAlchemy para reservas.

    Representa las reservas de habitaciones con sus fechas y estado.
    """

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("check_out_date > check_in_date", name="chk_res_dates"),
        {"extend_existing": True},
    )

    id = Column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    guest_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("guests.id", ondelete="CASCADE"),
        nullable=False,
    )
    room_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(
        postgresql.ENUM(ReservationStatus, name="reservation_status", create_type=True),
        nullable=False,
        server_default=ReservationStatus.PENDING.value,
    )

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


class ReservationGuest(Base):
    """
    Modelo SQLAlchemy para la relación reserva-huésped.

    Tabla de unión entre reservas y huéspedes.
    """

    __tablename__ = "reservation_guests"
    __table_args__ = {"extend_existing": True}

    reservation_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("reservations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    guest_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("guests.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    is_primary = Column(Boolean, nullable=False, server_default=text("false"))


class ReservationRoom(Base):
    """
    Modelo SQLAlchemy para la relación reserva-habitación.

    Tabla de unión entre reservas y habitaciones con fechas específicas.
    """

    __tablename__ = "reservation_rooms"
    __table_args__ = (
        CheckConstraint("end_date > start_date", name="chk_rr_dates"),
        {"extend_existing": True},
    )

    id = Column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    reservation_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("reservations.id", ondelete="CASCADE"),
        nullable=False,
    )
    room_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
    )
    room_type_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("room_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    nightly_rate = Column(Numeric(12, 2), nullable=False, server_default=text("0.00"))
    adults = Column(SmallInteger, nullable=False, server_default=text("1"))
    children = Column(SmallInteger, nullable=False, server_default=text("0"))
    notes = Column(String, nullable=True)


class Payment(Base):
    """
    Modelo SQLAlchemy para pagos.

    Representa los pagos asociados a las reservas.
    """

    __tablename__ = "payments"
    __table_args__ = {"extend_existing": True}

    id = Column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    reservation_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("reservations.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, server_default=text("'USD'"))
    method = Column(String, nullable=False)
    status = Column(
        postgresql.ENUM(PaymentStatus, name="payment_status", create_type=True),
        nullable=False,
        server_default=PaymentStatus.PENDING.value,
    )
    paid_at = Column(DateTime(timezone=True), nullable=True)
    reference = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


class ReservationBase(BaseModel):
    """Modelo base para reservas."""

    guest_id: UUID = Field(..., description="ID del huésped")
    room_id: UUID = Field(..., description="ID de la habitación")
    check_in_date: date = Field(..., description="Fecha de entrada")
    check_out_date: date = Field(..., description="Fecha de salida")
    total_amount: float = Field(..., description="Monto total de la reserva")

    @validator("check_out_date")
    def _validate_dates(cls, v, values):
        if "check_in_date" in values and v <= values["check_in_date"]:
            raise ValueError(
                "La fecha de salida debe ser posterior a la fecha de entrada"
            )
        return v


class ReservationCreate(BaseModel):
    """Modelo para crear una nueva reserva."""

    guest_id: UUID = Field(..., description="ID del huésped")
    room_id: UUID = Field(..., description="ID de la habitación")
    check_in_date: date = Field(..., description="Fecha de entrada")
    check_out_date: date = Field(..., description="Fecha de salida")

    @validator("check_out_date")
    def _validate_dates(cls, v, values):
        if "check_in_date" in values and v <= values["check_in_date"]:
            raise ValueError(
                "La fecha de salida debe ser posterior a la fecha de entrada"
            )
        return v


class ReservationUpdate(BaseModel):
    """Modelo para actualizar una reserva existente."""

    guest_id: Optional[UUID] = None
    room_id: Optional[UUID] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    total_amount: Optional[float] = None
    status: Optional[ReservationStatus] = None


class ReservationResponse(BaseModel):
    """Modelo de respuesta para reservas."""

    id: UUID
    guest_id: UUID
    room_id: UUID
    check_in_date: date
    check_out_date: date
    total_amount: float
    status: ReservationStatus = ReservationStatus.PENDING
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
