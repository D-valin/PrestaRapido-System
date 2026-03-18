from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
import uuid


# ─── USUARIOS ────────────────────────────────────────────────────────────────

class UsuarioCreate(BaseModel):
    documento_identidad: str
    nombre_completo: str
    email: str
    telefono: Optional[str] = None
    password_hash: str
    estado_verificacion: Optional[str] = "pendiente"

class UsuarioUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    estado_verificacion: Optional[str] = None

class UsuarioOut(BaseModel):
    id: str
    documento_identidad: str
    nombre_completo: str
    email: str
    telefono: Optional[str]
    estado_verificacion: str
    fecha_registro: Optional[datetime]


# ─── PRESTAMOS ────────────────────────────────────────────────────────────────

class PrestamoCreate(BaseModel):
    usuario_id: str
    monto: Decimal
    tasa_interes: Decimal
    cantidad_cuotas: int
    estado: Optional[str] = "pendiente"
    fecha_desembolso: Optional[datetime] = None
    proximo_vencimiento: Optional[datetime] = None

class PrestamoUpdate(BaseModel):
    monto: Optional[Decimal] = None
    tasa_interes: Optional[Decimal] = None
    cantidad_cuotas: Optional[int] = None
    estado: Optional[str] = None
    fecha_desembolso: Optional[datetime] = None
    proximo_vencimiento: Optional[datetime] = None

class PrestamoOut(BaseModel):
    id: str
    usuario_id: str
    monto: Decimal
    tasa_interes: Decimal
    cantidad_cuotas: int
    estado: str
    fecha_desembolso: Optional[datetime]
    proximo_vencimiento: Optional[datetime]


# ─── CUOTAS ──────────────────────────────────────────────────────────────────

class CuotaCreate(BaseModel):
    prestamo_id: str
    numero_cuota: int
    monto_cuota: Decimal
    fecha_vencimiento: date
    estado_cuota: Optional[str] = "pendiente"

class CuotaUpdate(BaseModel):
    monto_cuota: Optional[Decimal] = None
    fecha_vencimiento: Optional[date] = None
    estado_cuota: Optional[str] = None

class CuotaOut(BaseModel):
    id: str
    prestamo_id: str
    numero_cuota: int
    monto_cuota: Decimal
    fecha_vencimiento: date
    estado_cuota: str


# ─── PAGOS ───────────────────────────────────────────────────────────────────

class PagoCreate(BaseModel):
    cuota_id: str
    monto_pagado: Decimal
    metodo_pago: str
    referencia_transaccion: Optional[str] = None
    fecha_pago: Optional[datetime] = None

class PagoUpdate(BaseModel):
    monto_pagado: Optional[Decimal] = None
    metodo_pago: Optional[str] = None
    referencia_transaccion: Optional[str] = None

class PagoOut(BaseModel):
    id: str
    cuota_id: str
    monto_pagado: Decimal
    metodo_pago: str
    referencia_transaccion: Optional[str]
    fecha_pago: Optional[datetime]
