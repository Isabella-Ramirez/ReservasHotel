from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func, text
from app.database import Base


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"extend_existing": True}

    id = Column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)


class TokenResponse(BaseModel):
    """Modelo de respuesta para tokens de autenticación."""

    access_token: str
    token_type: str = "bearer"
