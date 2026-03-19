from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import date, datetime
from decimal import Decimal


# ─── TIPOS COMUNES ───────────────────────────────────────────────────────────

NivelRiesgo    = Literal["bajo", "medio", "alto"]
EstadoFinal    = Literal["aprobado", "en_revision", "rechazado"]
EstadoPrestamo = Literal["pendiente", "aprobado", "activo", "rechazado", "pagado"]
EstadoCuota    = Literal["pendiente", "pagada", "vencida"]
EstadoVerif    = Literal["pendiente", "verificado", "rechazado"]


# ─── USUARIOS ────────────────────────────────────────────────────────────────

class UsuarioCreate(BaseModel):
    documento_identidad: str
    nombre_completo: str
    email: EmailStr
    telefono: Optional[str] = None
    password_hash: str
    estado_verificacion: Optional[EstadoVerif] = "pendiente"
    fecha_nacimiento: Optional[date] = None
    ingreso_mensual: Optional[Decimal] = None

class UsuarioUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    estado_verificacion: Optional[EstadoVerif] = None
    fecha_nacimiento: Optional[date] = None
    ingreso_mensual: Optional[Decimal] = None

class UsuarioOut(BaseModel):
    id: str
    documento_identidad: str
    nombre_completo: str
    email: str
    telefono: Optional[str]
    estado_verificacion: str
    fecha_registro: Optional[datetime]
    fecha_nacimiento: Optional[date]
    ingreso_mensual: Optional[Decimal]


# ─── PRESTAMOS ───────────────────────────────────────────────────────────────

class PrestamoCreate(BaseModel):
    usuario_id: str
    monto: Decimal
    cantidad_cuotas: int
    # tasa_interes ya NO la elige el usuario; la asigna el backend según riesgo
    tasa_interes: Optional[Decimal] = None
    estado: Optional[EstadoPrestamo] = "pendiente"
    fecha_desembolso: Optional[datetime] = None
    proximo_vencimiento: Optional[datetime] = None

class PrestamoUpdate(BaseModel):
    monto: Optional[Decimal] = None
    tasa_interes: Optional[Decimal] = None
    cantidad_cuotas: Optional[int] = None
    estado: Optional[EstadoPrestamo] = None
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
    estado_cuota: Optional[EstadoCuota] = "pendiente"

class CuotaUpdate(BaseModel):
    monto_cuota: Optional[Decimal] = None
    fecha_vencimiento: Optional[date] = None
    estado_cuota: Optional[EstadoCuota] = None

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


# ─── EVALUACIÓN ──────────────────────────────────────────────────────────────

class EvaluacionOut(BaseModel):
    estado_final: EstadoFinal
    nivel_riesgo: Optional[NivelRiesgo]
    tasa_interes: Optional[Decimal]
    monto_maximo: Optional[Decimal]
    cuotas_maximas: int
    score_plataforma: int
    ratio_endeudamiento: Optional[Decimal]
    motivo_rechazo: Optional[str]
    detalles: dict
