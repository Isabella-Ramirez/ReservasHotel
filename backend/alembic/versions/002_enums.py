"""
create hotel enums

Revision ID: 002_enums
Revises: 001_bootstrap
Create Date: 2025-09-10
"""
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_enums'
down_revision = '001_bootstrap'
branch_labels = None
depends_on = None


reservation_status = postgresql.ENUM(
    'PENDING', 'CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT', 'CANCELLED', 'NO_SHOW',
    name='reservation_status'
)

payment_status = postgresql.ENUM(
    'PENDING', 'PAID', 'REFUNDED', 'FAILED',
    name='payment_status'
)

document_type = postgresql.ENUM(
    'ID', 'PASSPORT', 'DRIVER_LICENSE', 'OTHER',
    name='document_type'
)

room_status = postgresql.ENUM(
    'AVAILABLE', 'OUT_OF_SERVICE', 'CLEANING', 'OCCUPIED',
    name='room_status'
)


def upgrade() -> None:
    bind = op.get_bind()

    # Create enums if they do not exist
    reservation_status.create(bind, checkfirst=True)
    payment_status.create(bind, checkfirst=True)
    document_type.create(bind, checkfirst=True)
    room_status.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()

    # Drop enums (will fail if still in use by columns)
    room_status.drop(bind, checkfirst=True)
    document_type.drop(bind, checkfirst=True)
    payment_status.drop(bind, checkfirst=True)
    reservation_status.drop(bind, checkfirst=True)
