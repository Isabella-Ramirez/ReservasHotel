"""
init core tables for hotel management system

Revision ID: 003_tables
Revises: 002_enums
Create Date: 2025-09-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_tables'
down_revision = '002_enums'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # roles
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
        sa.UniqueConstraint('code', name=op.f('uq_roles_code'))
    )
    op.create_index('idx_roles_deleted_at', 'roles', ['deleted_at'], unique=False)

    # users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', postgresql.CITEXT(), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('full_name', sa.Text(), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email')),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='RESTRICT', name=op.f('fk_users_role_id_roles'))
    )
    op.create_index('idx_users_deleted_at', 'users', ['deleted_at'], unique=False)

    # guests
    op.create_table(
        'guests',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('first_name', sa.Text(), nullable=False),
        sa.Column('last_name', sa.Text(), nullable=False),
        sa.Column('email', postgresql.CITEXT(), nullable=True),
        sa.Column('phone', sa.Text(), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('document_kind', postgresql.ENUM('ID','PASSPORT','DRIVER_LICENSE','OTHER', name='document_type', create_type=False), nullable=True),
        sa.Column('document_no', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('country', sa.Text(), nullable=True),
        sa.Column('city', sa.Text(), nullable=True),
        sa.Column('address_line', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL', name=op.f('fk_guests_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_guests'))
    )
    op.create_index('idx_guests_name', 'guests', ['last_name', 'first_name'], unique=False)
    op.create_index('idx_guests_email', 'guests', ['email'], unique=False)
    op.create_index('idx_guests_deleted_at', 'guests', ['deleted_at'], unique=False)

    # room_types
    op.create_table(
        'room_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('capacity_adults', sa.SmallInteger(), nullable=False),
        sa.Column('capacity_children', sa.SmallInteger(), nullable=False),
        sa.Column('base_rate', sa.Numeric(12,2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_room_types')),
        sa.UniqueConstraint('code', name=op.f('uq_room_types_code'))
    )
    op.create_index('idx_room_types_deleted_at', 'room_types', ['deleted_at'], unique=False)

    # rooms
    op.create_table(
        'rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('room_number', sa.Text(), nullable=False),
        sa.Column('floor', sa.Text(), nullable=True),
        sa.Column('room_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('AVAILABLE','OUT_OF_SERVICE','CLEANING','OCCUPIED', name='room_status', create_type=False), nullable=False, server_default=sa.text("'AVAILABLE'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_rooms')),
        sa.UniqueConstraint('room_number', name=op.f('uq_rooms_room_number')),
        sa.ForeignKeyConstraint(['room_type_id'], ['room_types.id'], ondelete='RESTRICT', name=op.f('fk_rooms_room_type_id_room_types'))
    )
    op.create_index('idx_rooms_type', 'rooms', ['room_type_id'], unique=False)
    op.create_index('idx_rooms_deleted_at', 'rooms', ['deleted_at'], unique=False)

    # reservations
    op.create_table(
        'reservations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING','CONFIRMED','CHECKED_IN','CHECKED_OUT','CANCELLED','NO_SHOW', name='reservation_status', create_type=False), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column('checkin_date', sa.Date(), nullable=False),
        sa.Column('checkout_date', sa.Date(), nullable=False),
        sa.Column('channel', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_reservations')),
        sa.UniqueConstraint('code', name=op.f('uq_reservations_code'))
    )
    op.create_check_constraint('chk_res_dates', 'reservations', 'checkout_date > checkin_date')
    op.create_index('idx_reservations_dates', 'reservations', ['checkin_date', 'checkout_date'], unique=False)
    op.create_index('idx_reservations_deleted_at', 'reservations', ['deleted_at'], unique=False)

    # reservation_guests
    op.create_table(
        'reservation_guests',
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('guest_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_primary', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.PrimaryKeyConstraint('reservation_id', 'guest_id', name=op.f('pk_reservation_guests')),
        sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id'], ondelete='CASCADE', name=op.f('fk_reservation_guests_reservation_id_reservations')),
        sa.ForeignKeyConstraint(['guest_id'], ['guests.id'], ondelete='RESTRICT', name=op.f('fk_reservation_guests_guest_id_guests'))
    )
    op.create_index('idx_res_guest_guest', 'reservation_guests', ['guest_id'], unique=False)

    # reservation_rooms
    op.create_table(
        'reservation_rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('room_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('nightly_rate', sa.Numeric(12,2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('adults', sa.SmallInteger(), server_default=sa.text('1'), nullable=False),
        sa.Column('children', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_reservation_rooms')),
        sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id'], ondelete='CASCADE', name=op.f('fk_reservation_rooms_reservation_id_reservations')),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='SET NULL', name=op.f('fk_reservation_rooms_room_id_rooms')),
        sa.ForeignKeyConstraint(['room_type_id'], ['room_types.id'], ondelete='RESTRICT', name=op.f('fk_reservation_rooms_room_type_id_room_types'))
    )
    op.create_index('idx_rr_res', 'reservation_rooms', ['reservation_id'], unique=False)
    op.create_index('idx_rr_room', 'reservation_rooms', ['room_id'], unique=False)
    op.create_index('idx_rr_dates', 'reservation_rooms', ['start_date', 'end_date'], unique=False)

    # payments (simplified statuses)
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(12,2), nullable=False),
        sa.Column('currency', sa.String(3), server_default=sa.text("'USD'"), nullable=False),
        sa.Column('method', sa.Text(), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING','PAID','REFUNDED','FAILED', name='payment_status', create_type=False), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reference', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_payments')),
        sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id'], ondelete='CASCADE', name=op.f('fk_payments_reservation_id_reservations'))
    )
    op.create_index('idx_payments_res', 'payments', ['reservation_id'], unique=False)
    op.create_index('idx_payments_deleted_at', 'payments', ['deleted_at'], unique=False)

    # Add foreign keys for audit fields in roles table (after users table is created)
    op.create_foreign_key('fk_roles_created_by_users', 'roles', 'users', ['created_by'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_roles_updated_by_users', 'roles', 'users', ['updated_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_index('idx_payments_deleted_at', table_name='payments')
    op.drop_index('idx_payments_res', table_name='payments')
    op.drop_table('payments')

    op.drop_index('idx_rr_dates', table_name='reservation_rooms')
    op.drop_index('idx_rr_room', table_name='reservation_rooms')
    op.drop_index('idx_rr_res', table_name='reservation_rooms')
    op.drop_table('reservation_rooms')

    op.drop_index('idx_res_guest_guest', table_name='reservation_guests')
    op.drop_table('reservation_guests')

    op.drop_index('idx_reservations_deleted_at', table_name='reservations')
    op.drop_index('idx_reservations_dates', table_name='reservations')
    op.drop_constraint('chk_res_dates', 'reservations', type_='check')
    op.drop_table('reservations')

    op.drop_index('idx_rooms_deleted_at', table_name='rooms')
    op.drop_index('idx_rooms_type', table_name='rooms')
    op.drop_table('rooms')

    op.drop_index('idx_room_types_deleted_at', table_name='room_types')
    op.drop_table('room_types')

    op.drop_index('idx_guests_deleted_at', table_name='guests')
    op.drop_index('idx_guests_email', table_name='guests')
    op.drop_index('idx_guests_name', table_name='guests')
    op.drop_table('guests')

    op.drop_index('idx_users_deleted_at', table_name='users')
    op.drop_table('users')
    op.drop_constraint('fk_roles_updated_by_users', 'roles', type_='foreignkey')
    op.drop_constraint('fk_roles_created_by_users', 'roles', type_='foreignkey')
    op.drop_index('idx_roles_deleted_at', table_name='roles')
    op.drop_table('roles')
