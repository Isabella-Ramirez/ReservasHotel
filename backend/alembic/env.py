from logging.config import fileConfig
from typing import Any, Optional

from sqlalchemy import engine_from_config, pool, create_engine
from dotenv import load_dotenv
import os
from alembic import context

# Import SQLAlchemy metadata from the app
from app.database import Base
# Import models so tables are registered in Base.metadata
from app.models import rbac
from app.models import guest
from app.models import room
from app.models import reservation

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
# Load .env so sqlalchemy.url = env:DATABASE_URL can resolve during CLI runs
load_dotenv()

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'alembic revision --autogenerate'
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = os.getenv("DATABASE_URL")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get the database URL directly from environment variable
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Create engine configuration manually instead of using engine_from_config
    from sqlalchemy import create_engine
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
