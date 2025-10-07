import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None or DATABASE_URL == "":
    raise ValueError("DATABASE_URL environment variable is not set")

connect_args = {"sslmode": "require", "prepare_threshold": 0}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=15,
    max_overflow=5,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Obtener una sesión de base de datos.

    Yields:
        Session: Sesión de SQLAlchemy para operaciones de base de datos
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> bool:
    """
    Probar la conexión a la base de datos.

    Returns:
        bool: True si la conexión es exitosa, False en caso contrario
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Conexión a la base de datos exitosa.")
        return True
    except Exception as e:
        print(f"Error de conexión a la base de datos: {e}")
        return False
