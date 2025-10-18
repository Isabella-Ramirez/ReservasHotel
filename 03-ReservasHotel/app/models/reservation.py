from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from app.database import Base
from app.models.guest import Guest
from app.models.room import Room, RoomType


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

    Representa una reserva de habitación con huésped principal, acompañantes y asignaciones.
    """

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("check_out_date > check_in_date", name="chk_res_dates"),
        {"extend_existing": True},
    )

    id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status", create_type=False),
        nullable=False,
        server_default=ReservationStatus.PENDING.value,
    )
    primary_guest_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("guests.id", ondelete="RESTRICT"),
        nullable=False,
    )
    room_type_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("room_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    room_id: Mapped[Optional[UUID]] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
    )
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    guest_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default=text("1"),
    )
    nightly_rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0.00"),
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0.00"),
    )
    channel: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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

    primary_guest: Mapped[Guest] = relationship("Guest", foreign_keys=[primary_guest_id])
    room: Mapped[Optional[Room]] = relationship("Room", foreign_keys=[room_id])
    room_type: Mapped[RoomType] = relationship("RoomType", foreign_keys=[room_type_id])
    guest_links: Mapped[list["ReservationGuest"]] = relationship(
        "ReservationGuest",
        back_populates="reservation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    payment: Mapped[Optional["Payment"]] = relationship(
        "Payment",
        back_populates="reservation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )

    @property
    def guests(self) -> list["ReservationGuest"]:
        """Expose guest links for API responses."""
        return list(self.guest_links)


class ReservationGuest(Base):
    """
    Tabla intermedia que vincula huéspedes con reservas.

    Permite marcar al huésped principal y almacenar acompañantes.
    """

    __tablename__ = "reservation_guests"
    __table_args__ = {"extend_existing": True}

    reservation_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("reservations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    guest_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("guests.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    reservation: Mapped["Reservation"] = relationship("Reservation", back_populates="guest_links")
    guest: Mapped[Guest] = relationship("Guest")


class Payment(Base):
    """
    Modelo SQLAlchemy para pagos.

    Cada reserva admite un único registro de pago.
    """

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("reservation_id", name="uq_payments_reservation"),
        {"extend_existing": True},
    )

    id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    reservation_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("reservations.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'USD'"))
    method: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", create_type=False),
        nullable=False,
        server_default=PaymentStatus.PENDING.value,
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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

    reservation: Mapped["Reservation"] = relationship("Reservation", back_populates="payment")


class ReservationGuestAssignment(BaseModel):
    """Representa un huésped asociado a una reserva."""

    guest_id: UUID
    is_primary: bool = False


class ReservationCreate(BaseModel):
    """Modelo para crear una nueva reserva."""

    primary_guest_id: UUID = Field(..., description="Huésped principal que realiza la reserva")
    companion_guest_ids: List[UUID] = Field(
        default_factory=list, description="Huéspedes adicionales asociados a la reserva"
    )
    room_type_id: UUID = Field(..., description="Tipo de habitación reservado")
    room_id: Optional[UUID] = Field(
        None, description="Habitación asignada (opcional hasta el check-in)"
    )
    check_in_date: date = Field(..., description="Fecha de entrada")
    check_out_date: date = Field(..., description="Fecha de salida")
    nightly_rate: Optional[Decimal] = Field(
        None, ge=0, description="Tarifa por noche a aplicar (opcional)"
    )
    channel: Optional[str] = Field(None, description="Canal por el que se realizó la reserva")
    notes: Optional[str] = Field(None, description="Notas adicionales de la reserva")

    @validator("check_out_date")
    def _validate_dates(cls, v, values):
        check_in = values.get("check_in_date")
        if check_in and v <= check_in:
            raise ValueError("La fecha de salida debe ser posterior a la fecha de entrada")
        return v


class ReservationUpdate(BaseModel):
    """Modelo para actualizar una reserva existente."""

    room_type_id: Optional[UUID] = None
    room_id: Optional[UUID] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    status: Optional[ReservationStatus] = None
    nightly_rate: Optional[Decimal] = Field(None, ge=0)
    channel: Optional[str] = None
    notes: Optional[str] = None
    companion_guest_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Lista completa de huéspedes adicionales a conservar en la reserva",
    )

    @validator("check_out_date")
    def _validate_update_dates(cls, v, values):
        check_in = values.get("check_in_date")
        if check_in and v and v <= check_in:
            raise ValueError("La fecha de salida debe ser posterior a la fecha de entrada")
        return v


class ReservationGuestResponse(BaseModel):
    """Respuesta para los huéspedes asociados a una reserva."""

    guest_id: UUID
    is_primary: bool

    class Config:
        from_attributes = True


class ReservationResponse(BaseModel):
    """Modelo de respuesta para reservas."""

    id: UUID
    code: str
    status: ReservationStatus
    primary_guest_id: UUID
    room_type_id: UUID
    room_id: Optional[UUID] = None
    check_in_date: date
    check_out_date: date
    guest_count: int
    nightly_rate: Decimal
    total_amount: Decimal
    channel: Optional[str] = None
    notes: Optional[str] = None
    guests: List[ReservationGuestResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
