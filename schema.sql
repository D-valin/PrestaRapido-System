-- ============================================================
--  PrestaRápido — Script de creación de base de datos
--  PostgreSQL
-- ============================================================

-- Extensión para generar UUIDs automáticamente
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ─── USUARIOS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    documento_identidad  VARCHAR(20)  NOT NULL UNIQUE,
    nombre_completo      VARCHAR(150) NOT NULL,
    email                VARCHAR(150) NOT NULL UNIQUE,
    telefono             VARCHAR(20),
    password_hash        TEXT         NOT NULL,
    estado_verificacion  VARCHAR(20)  NOT NULL DEFAULT 'pendiente',
    fecha_registro       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ─── PRESTAMOS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prestamos (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id           UUID         NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    monto                NUMERIC(14,2) NOT NULL,
    tasa_interes         NUMERIC(5,4)  NOT NULL,
    cantidad_cuotas      INTEGER       NOT NULL,
    estado               VARCHAR(20)   NOT NULL DEFAULT 'pendiente',
    fecha_desembolso     TIMESTAMPTZ,
    proximo_vencimiento  TIMESTAMPTZ
);


-- ─── CUOTAS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cuotas (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prestamo_id          UUID          NOT NULL REFERENCES prestamos(id) ON DELETE CASCADE,
    numero_cuota         INTEGER       NOT NULL,
    monto_cuota          NUMERIC(14,2) NOT NULL,
    fecha_vencimiento    DATE          NOT NULL,
    estado_cuota         VARCHAR(20)   NOT NULL DEFAULT 'pendiente',
    UNIQUE (prestamo_id, numero_cuota)
);


-- ─── PAGOS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pagos (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cuota_id               UUID          NOT NULL REFERENCES cuotas(id) ON DELETE CASCADE,
    monto_pagado           NUMERIC(14,2) NOT NULL,
    metodo_pago            VARCHAR(50)   NOT NULL,
    referencia_transaccion VARCHAR(100),
    fecha_pago             TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
