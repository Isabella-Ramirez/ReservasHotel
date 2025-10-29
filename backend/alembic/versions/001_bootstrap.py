"""
bootstrap extensions

Revision ID: 001_bootstrap
Revises:
Create Date: 2025-09-10
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '001_bootstrap'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    # Normalmente no se dropean extensiones en downgrade
    pass
