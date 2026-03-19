import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    return conn


def crear_tablas():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

        cur.execute("""
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
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS prestamos (
                id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                usuario_id           UUID          NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                monto                NUMERIC(14,2) NOT NULL,
                tasa_interes         NUMERIC(5,4)  NOT NULL,
                cantidad_cuotas      INTEGER       NOT NULL,
                estado               VARCHAR(20)   NOT NULL DEFAULT 'pendiente',
                fecha_desembolso     TIMESTAMPTZ,
                proximo_vencimiento  TIMESTAMPTZ
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cuotas (
                id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                prestamo_id       UUID          NOT NULL REFERENCES prestamos(id) ON DELETE CASCADE,
                numero_cuota      INTEGER       NOT NULL,
                monto_cuota       NUMERIC(14,2) NOT NULL,
                fecha_vencimiento DATE          NOT NULL,
                estado_cuota      VARCHAR(20)   NOT NULL DEFAULT 'pendiente',
                UNIQUE (prestamo_id, numero_cuota)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS pagos (
                id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                cuota_id               UUID          NOT NULL REFERENCES cuotas(id) ON DELETE CASCADE,
                monto_pagado           NUMERIC(14,2) NOT NULL,
                metodo_pago            VARCHAR(50)   NOT NULL,
                referencia_transaccion VARCHAR(100),
                fecha_pago             TIMESTAMPTZ   NOT NULL DEFAULT NOW()
            );
        """)

        # ── Migración: columnas nuevas en usuarios ──────────────────────
        cur.execute("""
            ALTER TABLE usuarios
                ADD COLUMN IF NOT EXISTS fecha_nacimiento DATE,
                ADD COLUMN IF NOT EXISTS ingreso_mensual  NUMERIC(14,2);
        """)

        conn.commit()
        print("✅ Tablas creadas y migradas correctamente.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error al crear/migrar tablas: {e}")
        raise
    finally:
        cur.close()
        conn.close()
