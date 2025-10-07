from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func, text
from app.database import Base


class Role(Base):
	__tablename__ = "roles"
	__table_args__ = {"extend_existing": True}

	id = Column(postgresql.UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
	code = Column(String, unique=True, nullable=False)
	name = Column(String, nullable=False)


class User(Base):
	__tablename__ = "users"
	__table_args__ = {"extend_existing": True}

	id = Column(postgresql.UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
	email = Column(postgresql.CITEXT, unique=True, nullable=False)
	password_hash = Column(String, nullable=False)
	full_name = Column(String, nullable=False)
	role_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
	is_active = Column(Boolean, nullable=False, server_default=text("true"))
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	created_by = Column(postgresql.UUID(as_uuid=True), nullable=True)
	updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
	updated_by = Column(postgresql.UUID(as_uuid=True), nullable=True)


# Pydantic models
class UserBase(BaseModel):
	email: EmailStr
	full_name: str
	role_id: UUID
	is_active: bool = True


class UserCreate(UserBase):
	password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
	email: Optional[EmailStr] = None
	full_name: Optional[str] = None
	role_id: Optional[UUID] = None
	is_active: Optional[bool] = None
	password: Optional[str] = Field(None, min_length=6)


class UserResponse(UserBase):
	id: UUID
	created_at: datetime
	updated_at: Optional[datetime] = None

	class Config:
		from_attributes = True


class UserLogin(BaseModel):
	email: EmailStr
	password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
	access_token: str
	token_type: str = "bearer"
