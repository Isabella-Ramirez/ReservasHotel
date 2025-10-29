-- Habilitar extensiones
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

-- =========================
-- Enums
-- =========================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reservation_status') THEN
    CREATE TYPE reservation_status AS ENUM ('PENDING','CONFIRMED','CHECKED_IN','CHECKED_OUT','CANCELLED','NO_SHOW');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status') THEN
    CREATE TYPE payment_status AS ENUM ('PENDING','AUTHORIZED','PAID','REFUNDED','FAILED','PARTIAL');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_type') THEN
    CREATE TYPE document_type AS ENUM ('ID','PASSPORT','DRIVER_LICENSE','OTHER');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'room_status') THEN
    CREATE TYPE room_status AS ENUM ('AVAILABLE','OUT_OF_SERVICE','CLEANING','OCCUPIED');
  END IF;
END$$;

-- =========================
-- Utilidades / auditoría
-- =========================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := NOW();
  RETURN NEW;
END$$;

-- =========================
-- Seguridad / cuentas
-- =========================
CREATE TABLE IF NOT EXISTS roles (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code         TEXT UNIQUE NOT NULL,      -- e.g. 'ADMIN','RECEPTION','GUEST'
  name         TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by   UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_by   UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  deleted_at   TIMESTAMPTZ NULL DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_roles_deleted_at ON roles (deleted_at);
CREATE TRIGGER trg_roles_updated_at
BEFORE UPDATE ON roles
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS users (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email        CITEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,            -- almacenar hash
  full_name    TEXT NOT NULL,
  role_id      UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by   UUID NULL,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_by   UUID NULL,
  deleted_at   TIMESTAMPTZ NULL DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON users (deleted_at);
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================
-- Huéspedes
-- =========================
CREATE TABLE IF NOT EXISTS guests (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  first_name    TEXT NOT NULL,
  last_name     TEXT NOT NULL,
  email         CITEXT UNIQUE NOT NULL,
  phone         TEXT NULL,
  birth_date    DATE NULL,
  document_kind document_type NOT NULL,
  document_no   TEXT UNIQUE NOT NULL,
  user_id       UUID NULL UNIQUE,  -- un huésped puede tener a lo sumo un usuario
  -- Dirección básica opcional
  country       TEXT NULL,
  city          TEXT NULL,
  address_line  TEXT NULL,

  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by    UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_by    UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  deleted_at    TIMESTAMPTZ NULL DEFAULT NULL,

  CONSTRAINT fk_guest_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_guests_name ON guests (last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_guests_email ON guests (email);
CREATE INDEX IF NOT EXISTS idx_guests_deleted_at ON guests (deleted_at);
CREATE TRIGGER trg_guests_updated_at
BEFORE UPDATE ON guests
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================
-- Habitaciones y tipos
-- =========================
CREATE TABLE IF NOT EXISTS room_types (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code               TEXT UNIQUE NOT NULL,     -- e.g., STD-KING, DLX-QUEEN
  name               TEXT NOT NULL,
  description        TEXT,
  max_guests         SMALLINT NOT NULL CHECK (max_guests > 0),
  base_rate          NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by         UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_by         UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  deleted_at         TIMESTAMPTZ NULL DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_room_types_deleted_at ON room_types (deleted_at);
CREATE TRIGGER trg_room_types_updated_at
BEFORE UPDATE ON room_types
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS rooms (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  room_number   TEXT UNIQUE NOT NULL,
  floor         TEXT NULL,
  room_type_id  UUID NOT NULL REFERENCES room_types(id) ON DELETE RESTRICT,
  status        room_status NOT NULL DEFAULT 'AVAILABLE',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by    UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_by    UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  deleted_at    TIMESTAMPTZ NULL DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_rooms_type ON rooms(room_type_id);
CREATE INDEX IF NOT EXISTS idx_rooms_deleted_at ON rooms (deleted_at);
CREATE TRIGGER trg_rooms_updated_at
BEFORE UPDATE ON rooms
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================
-- Reservas
-- =========================
CREATE TABLE IF NOT EXISTS reservations (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code              TEXT UNIQUE NOT NULL,              -- localizador/PNR
  status            reservation_status NOT NULL DEFAULT 'PENDING',
  primary_guest_id  UUID NOT NULL REFERENCES guests(id) ON DELETE RESTRICT,
  room_type_id      UUID NOT NULL REFERENCES room_types(id) ON DELETE RESTRICT,
  room_id           UUID NULL REFERENCES rooms(id) ON DELETE SET NULL,
  check_in_date     DATE NOT NULL,
  check_out_date    DATE NOT NULL,
  guest_count       SMALLINT NOT NULL CHECK (guest_count > 0),
  nightly_rate      NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  total_amount      NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  channel           TEXT NULL,                         -- web, phone, OTA, etc.
  notes             TEXT NULL,

  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by        UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_by        UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  deleted_at        TIMESTAMPTZ NULL DEFAULT NULL,

  CONSTRAINT chk_res_dates CHECK (check_out_date > check_in_date)
);
CREATE INDEX IF NOT EXISTS idx_reservations_dates ON reservations(check_in_date, check_out_date);
CREATE INDEX IF NOT EXISTS idx_reservations_deleted_at ON reservations (deleted_at);
CREATE TRIGGER trg_reservations_updated_at
BEFORE UPDATE ON reservations
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Huéspedes por reserva (N a N) + rol del huésped en la reserva
CREATE TABLE IF NOT EXISTS reservation_guests (
  reservation_id  UUID NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
  guest_id        UUID NOT NULL REFERENCES guests(id) ON DELETE RESTRICT,
  is_primary      BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (reservation_id, guest_id)
);
CREATE INDEX IF NOT EXISTS idx_res_guest_guest ON reservation_guests(guest_id);

-- Habitaciones asignadas a una reserva (soporta multi-habitación)
-- Pagos
CREATE TABLE IF NOT EXISTS payments (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reservation_id  UUID NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
  amount          NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
  currency        CHAR(3) NOT NULL DEFAULT 'USD',
  method          TEXT NOT NULL,                -- tarjeta, efectivo, transferencia, etc.
  status          payment_status NOT NULL DEFAULT 'PENDING',
  paid_at         TIMESTAMPTZ NULL,
  notes           TEXT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by      UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_by      UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  deleted_at      TIMESTAMPTZ NULL DEFAULT NULL,
  CONSTRAINT uq_payments_reservation UNIQUE (reservation_id)
);
CREATE INDEX IF NOT EXISTS idx_payments_res ON payments(reservation_id);
CREATE INDEX IF NOT EXISTS idx_payments_deleted_at ON payments (deleted_at);
CREATE TRIGGER trg_payments_updated_at
BEFORE UPDATE ON payments
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
