from pathlib import Path
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.database import SessionLocal, engine
from app.models.room import RoomType, Room, RoomStatus
from app.models.guest import Guest
from app.models.rbac import Role
from app.models.user import User


def _get_alembic_config() -> Config:
    """Obtiene la configuración de Alembic desde el archivo alembic.ini del directorio raíz del proyecto."""
    project_root = Path(__file__).resolve().parents[1]
    alembic_ini = project_root / "alembic.ini"
    cfg = Config(str(alembic_ini))
    return cfg


def check_migrations_needed() -> bool:
    """Verifica si hay migraciones pendientes comparando la revisión actual con la cabecera del script."""
    try:
        cfg = _get_alembic_config()
        script = ScriptDirectory.from_config(cfg)

        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_head = context.get_current_revision()
            script_head = script.get_current_head()

            if current_head is None:
                return True

            return current_head != script_head

    except Exception:
        return True


def has_sample_data() -> bool:
    """Verifica si ya existen datos de ejemplo verificando la existencia de roles, usuarios y tipos de habitación."""
    db = SessionLocal()
    try:
        return (
            db.query(Role).count() > 0
            and db.query(User).count() > 0
            and db.query(RoomType).count() > 0
        )
    except Exception:
        return False
    finally:
        db.close()


def run_migration(target: str = "head") -> None:
    """Aplica migraciones con Alembic hasta el target indicado (por defecto 'head')."""
    cfg = _get_alembic_config()
    print(f"Aplicando migraciones hasta: {target}...")
    command.upgrade(cfg, target)
    print("Migraciones aplicadas.")


def auto_setup_database() -> None:
    """Configura automáticamente la base de datos ejecutando migraciones y seed de datos según sea necesario."""
    if check_migrations_needed():
        print("Migraciones pendientes detectadas. Ejecutando migraciones...")
        run_migration()
    else:
        print("Base de datos actualizada.")

    if not has_sample_data():
        print("No se encontraron datos de ejemplo. Ejecutando seed...")
        seed_sample_data()
    else:
        print("Datos de ejemplo ya existen.")


def rollback_migration(target: str = "-1") -> None:
    """Revierte migraciones (por defecto un paso)."""
    cfg = _get_alembic_config()
    print(f"Revirtiendo migraciones hasta: {target}...")
    command.downgrade(cfg, target)
    print("Migraciones revertidas.")


def seed_sample_data() -> None:
    """Inserta datos de ejemplo en el orden correcto: roles, users, room_types, rooms, guests."""
    db = SessionLocal()
    try:
        print("Iniciando seed de datos de ejemplo...")

        if db.query(Role).count() == 0:
            roles = [
                Role(code="ADMIN", name="Administrador"),
                Role(code="RECEPTIONIST", name="Recepcionista"),
                Role(code="GUEST", name="Huésped"),
            ]
            db.add_all(roles)
            db.flush()
            print(f"Creados {len(roles)} roles")

        if db.query(User).count() == 0:
            admin_role = db.query(Role).filter(Role.code == "ADMIN").first()
            receptionist_role = (
                db.query(Role).filter(Role.code == "RECEPTIONIST").first()
            )
            guest_role = db.query(Role).filter(Role.code == "GUEST").first()

            if not admin_role or not receptionist_role or not guest_role:
                raise ValueError(
                    "No se encontraron los roles requeridos (ADMIN, RECEPTIONIST)"
                )

            users = [
                User(
                    email="admin@hotel.com",
                    password_hash="$2b$12$KxZBbVA0IGgywO4JFWnyJu/L/uoxVLEoU82nd6BVQp0xkHcgs60RS",
                    full_name="Administrador Sistema",
                    role_id=admin_role.id,
                    is_active=True,
                ),
                User(
                    email="recepcion@hotel.com",
                    password_hash="$2b$12$7ytL0YJsVEL5WctNXxffUuGewzjZnMNXx/r3K3DSc8ycEm1bS3.Em",
                    full_name="Personal Recepción",
                    role_id=receptionist_role.id,
                    is_active=True,
                ),
                User(
                    email="anamartinez@guests.com",
                    password_hash="$2b$12$LI7/rIFV9YIZFZ7NwfBlBOslPZeH60ZPN1q4Y5r4oqqRqVr1eAmC.",
                    full_name="Ana Martínez",
                    role_id=guest_role.id,
                    is_active=True,
                )
            ]
            db.add_all(users)
            db.flush()
            print(f"Creados {len(users)} usuarios")

        if db.query(RoomType).count() == 0:
            room_types = [
                RoomType(
                    code="STD-KING",
                    name="Standard King",
                    description="Habitación estándar con cama king size",
                    max_guests=3,
                    base_rate=80.00,
                ),
                RoomType(
                    code="DLX-QUEEN",
                    name="Deluxe Queen",
                    description="Habitación deluxe con cama queen size",
                    max_guests=4,
                    base_rate=120.00,
                ),
                RoomType(
                    code="SUITE",
                    name="Suite Ejecutiva",
                    description="Suite ejecutiva con sala de estar",
                    max_guests=6,
                    base_rate=200.00,
                ),
            ]
            db.add_all(room_types)
            db.flush()
            print(f"Creados {len(room_types)} tipos de habitación")

        if db.query(Room).count() == 0:
            std_type = db.query(RoomType).filter(RoomType.code == "STD-KING").first()
            dlx_type = db.query(RoomType).filter(RoomType.code == "DLX-QUEEN").first()
            suite_type = db.query(RoomType).filter(RoomType.code == "SUITE").first()

            if not std_type or not dlx_type or not suite_type:
                raise ValueError(
                    "No se encontraron todos los tipos de habitación requeridos"
                )

            rooms = [
                Room(
                    room_number="101",
                    floor="1",
                    room_type_id=std_type.id,
                    status=RoomStatus.AVAILABLE,
                ),
                Room(
                    room_number="102",
                    floor="1",
                    room_type_id=std_type.id,
                    status=RoomStatus.AVAILABLE,
                ),
                Room(
                    room_number="103",
                    floor="1",
                    room_type_id=std_type.id,
                    status=RoomStatus.CLEANING,
                ),
                Room(
                    room_number="201",
                    floor="2",
                    room_type_id=dlx_type.id,
                    status=RoomStatus.AVAILABLE,
                ),
                Room(
                    room_number="202",
                    floor="2",
                    room_type_id=dlx_type.id,
                    status=RoomStatus.AVAILABLE,
                ),
                Room(
                    room_number="203",
                    floor="2",
                    room_type_id=dlx_type.id,
                    status=RoomStatus.OCCUPIED,
                ),
                Room(
                    room_number="301",
                    floor="3",
                    room_type_id=suite_type.id,
                    status=RoomStatus.AVAILABLE,
                ),
                Room(
                    room_number="302",
                    floor="3",
                    room_type_id=suite_type.id,
                    status=RoomStatus.OUT_OF_SERVICE,
                ),
            ]
            db.add_all(rooms)
            db.flush()
            print(f"Creadas {len(rooms)} habitaciones")

        if db.query(Guest).count() == 0:
            guests = [
                Guest(
                    first_name="Juan Carlos",
                    last_name="Pérez González",
                    email="juan.perez@example.com",
                    phone="+1-555-0101",
                    country="España",
                    city="Madrid",
                ),
                Guest(
                    first_name="María Elena",
                    last_name="García Rodríguez",
                    email="maria.garcia@example.com",
                    phone="+1-555-0102",
                    country="México",
                    city="Ciudad de México",
                ),
                Guest(
                    first_name="Ana Sofía",
                    last_name="Martínez López",
                    email="ana.martinez@example.com",
                    phone="+1-555-0103",
                    country="Colombia",
                    city="Bogotá",
                    user_id=users[2].id
                ),
                Guest(
                    first_name="Carlos Alberto",
                    last_name="Ruiz Hernández",
                    email="carlos.ruiz@example.com",
                    phone="+1-555-0104",
                    country="Argentina",
                    city="Buenos Aires",
                ),
                Guest(
                    first_name="Laura Patricia",
                    last_name="Sánchez Vargas",
                    phone="+1-555-0105",
                    country="Chile",
                    city="Santiago",
                ),
            ]
            db.add_all(guests)
            db.flush()
            print(f"Creados {len(guests)} huéspedes")

        db.commit()
        print("Seed de datos completado exitosamente")

    except Exception as e:
        db.rollback()
        print(f"Error en seed: {e}")
        raise
    finally:
        db.close()
