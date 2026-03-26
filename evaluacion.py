"""
evaluacion.py — Motor de evaluación de solicitudes de crédito
Implementa las reglas de negocio RNF-01 al RNF-08 del SRS de PrestaRápido.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from db import get_connection


# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTES DE NEGOCIO
# ═══════════════════════════════════════════════════════════════════════════════

EDAD_MINIMA = 21
EDAD_MAXIMA = 65
CUOTAS_MAXIMAS_DEFAULT = 3

# Tasas de interés mensual por nivel de riesgo (RNF-07)
TASAS = {
    "bajo":  Decimal("1.5"),
    "medio": Decimal("2.8"),
    "alto":  Decimal("4.2"),
}

# Montos máximos por nivel de riesgo (RNF-05)
MONTOS_MAXIMOS = {
    "bajo":  Decimal("10000000"),   # 10M COP
    "medio": Decimal("5000000"),    # 5M COP
    "alto":  Decimal("2000000"),    # 2M COP
}

# Umbrales de score de la plataforma (RNF-03)
# Score: puntos acumulados por historial de pagos en la plataforma
SCORE_RIESGO_BAJO   = 80   # >= 80 puntos → riesgo bajo
SCORE_RIESGO_MEDIO  = 40   # 40-79 puntos → riesgo medio
                            # < 40 puntos  → riesgo alto

# Ratio de endeudamiento máximo permitido (RNF-04)
# Si deuda_actual / ingreso_mensual >= este umbral → en_revision (zona gris)
RATIO_ZONA_GRIS_MIN = Decimal("0.40")   # >= 40% → zona gris (en_revision)
RATIO_RECHAZO       = Decimal("0.70")   # >= 70% → rechazo automático


# ═══════════════════════════════════════════════════════════════════════════════
#  FUNCIONES DE CÁLCULO
# ═══════════════════════════════════════════════════════════════════════════════

def calcular_edad(fecha_nacimiento: date) -> int:
    """Calcula la edad en años completos a partir de la fecha de nacimiento."""
    hoy = date.today()
    return hoy.year - fecha_nacimiento.year - (
        (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )


def calcular_score_plataforma(usuario_id: str, conn=None) -> int:
    """
    RNF-02 — Historial de la plataforma.
    Calcula el score basado en el historial de pagos del usuario:
      +10 puntos por cada cuota pagada a tiempo (antes del vencimiento)
      -20 puntos por cada cuota vencida sin pagar
      -5  puntos por cada cuota pagada tarde
    El score parte de 50 (usuarios nuevos sin historial).
    """
    cerrar = False
    if conn is None:
        conn = get_connection()
        cerrar = True

    cur = conn.cursor()
    try:
        # Obtener todas las cuotas de préstamos del usuario
        cur.execute("""
            SELECT c.estado_cuota,
                   c.fecha_vencimiento,
                   MAX(p.fecha_pago) AS fecha_ultimo_pago
            FROM cuotas c
            JOIN prestamos pr ON pr.id = c.prestamo_id
            LEFT JOIN pagos p ON p.cuota_id = c.id
            WHERE pr.usuario_id = %s
            GROUP BY c.id, c.estado_cuota, c.fecha_vencimiento
        """, (usuario_id,))
        cuotas = cur.fetchall()
    finally:
        cur.close()
        if cerrar:
            conn.close()

    if not cuotas:
        return 50  # Nuevo cliente sin historial → score neutro

    score = 50
    for estado, vencimiento, fecha_pago in cuotas:
        if estado == "pagada" and fecha_pago is not None:
            # Convertir a date para comparar
            if hasattr(fecha_pago, 'date'):
                fecha_pago_d = fecha_pago.date()
            else:
                fecha_pago_d = fecha_pago
            if fecha_pago_d <= vencimiento:
                score += 10   # Pago a tiempo
            else:
                score -= 5    # Pago tardío
        elif estado == "vencida":
            score -= 20       # Vencida sin pagar

    return max(0, min(100, score))  # Clamped entre 0 y 100


def calcular_ratio_endeudamiento(usuario_id: str, monto_nuevo: Decimal,
                                  ingreso_mensual: Decimal, conn=None) -> Decimal:
    """
    RNF-04 — Ratio de endeudamiento.
    Ratio = (deuda_mensual_activa + cuota_nueva) / ingreso_mensual
    Donde deuda_mensual_activa = suma de cuotas pendientes vigentes del usuario.
    """
    cerrar = False
    if conn is None:
        conn = get_connection()
        cerrar = True

    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COALESCE(SUM(c.monto_cuota), 0)
            FROM cuotas c
            JOIN prestamos pr ON pr.id = c.prestamo_id
            WHERE pr.usuario_id = %s
              AND c.estado_cuota = 'pendiente'
              AND pr.estado IN ('activo', 'aprobado')
        """, (usuario_id,))
        deuda_actual = Decimal(str(cur.fetchone()[0]))
    finally:
        cur.close()
        if cerrar:
            conn.close()

    # Cuota estimada del nuevo préstamo (promedio simple, sin interés aquí)
    cuota_estimada = monto_nuevo / 3  # Asumimos 3 cuotas para ser conservador
    ratio = (deuda_actual + cuota_estimada) / ingreso_mensual
    return ratio.quantize(Decimal("0.0001"))


def determinar_nivel_riesgo(score: int) -> str:
    """RNF-03 — Clasificación por score crediticio."""
    if score >= SCORE_RIESGO_BAJO:
        return "bajo"
    elif score >= SCORE_RIESGO_MEDIO:
        return "medio"
    else:
        return "alto"


# ═══════════════════════════════════════════════════════════════════════════════
#  MOTOR DE EVALUACIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def evaluar_solicitud(
    usuario_id: str,
    monto: Decimal,
    cantidad_cuotas: int,
) -> dict:
    """
    Evalúa una solicitud de crédito aplicando todas las reglas de negocio
    RNF-01 a RNF-08. Devuelve un diccionario con el resultado completo.

    Retorna:
      estado_final:       'aprobado' | 'en_revision' | 'rechazado'
      nivel_riesgo:       'bajo' | 'medio' | 'alto' | None
      tasa_interes:       Decimal (% mensual) | None
      monto_maximo:       Decimal | None
      cuotas_maximas:     int
      score_plataforma:   int
      ratio_endeudamiento: Decimal | None
      motivo_rechazo:     str | None
      detalles:           dict con cada verificación
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        # ── Obtener datos del usuario ─────────────────────────────────────────
        cur.execute("""
            SELECT fecha_nacimiento, ingreso_mensual
            FROM usuarios
            WHERE id = %s
        """, (usuario_id,))
        row = cur.fetchone()

        if not row:
            return _rechazo("Usuario no encontrado en el sistema", {})

        fecha_nacimiento, ingreso_mensual = row
        ingreso_mensual = Decimal(str(ingreso_mensual)) if ingreso_mensual else None

        detalles = {}

        # ── RNF-01: Elegibilidad básica ───────────────────────────────────────
        if fecha_nacimiento is None:
            return _rechazo("Fecha de nacimiento no registrada. Por favor actualiza tu perfil.", detalles)

        edad = calcular_edad(fecha_nacimiento)
        detalles["edad"] = edad
        detalles["rnf01_edad_ok"] = EDAD_MINIMA <= edad <= EDAD_MAXIMA

        if edad < EDAD_MINIMA:
            return _rechazo(f"Edad insuficiente: {edad} años. Mínimo requerido: {EDAD_MINIMA} años.", detalles)
        if edad > EDAD_MAXIMA:
            return _rechazo(f"Edad fuera del rango permitido: {edad} años. Máximo: {EDAD_MAXIMA} años.", detalles)

        if ingreso_mensual is None or ingreso_mensual <= 0:
            return _rechazo("Ingreso mensual no registrado o igual a $0. Por favor actualiza tu perfil.", detalles)
        detalles["ingreso_mensual"] = float(ingreso_mensual)
        detalles["rnf01_ingreso_ok"] = True

        # ── RNF-02 / RNF-03: Score y nivel de riesgo ─────────────────────────
        score = calcular_score_plataforma(usuario_id, conn)
        nivel_riesgo = determinar_nivel_riesgo(score)
        detalles["score_plataforma"] = score
        detalles["nivel_riesgo"] = nivel_riesgo

        if score < SCORE_RIESGO_MEDIO:
            return _rechazo(
                f"Score crediticio muy bajo ({score}/100). El umbral mínimo es {SCORE_RIESGO_MEDIO} puntos.",
                detalles,
                nivel_riesgo=nivel_riesgo,
                score=score
            )

        # ── RNF-05: Límite de monto ───────────────────────────────────────────
        monto_maximo = MONTOS_MAXIMOS[nivel_riesgo]
        detalles["monto_solicitado"] = float(monto)
        detalles["monto_maximo_permitido"] = float(monto_maximo)
        detalles["rnf05_monto_ok"] = monto <= monto_maximo

        if monto > monto_maximo:
            return _rechazo(
                f"Monto solicitado (${monto:,.0f}) supera el límite permitido para tu nivel de riesgo '{nivel_riesgo}' (${monto_maximo:,.0f}).",
                detalles,
                nivel_riesgo=nivel_riesgo,
                score=score,
                monto_maximo=monto_maximo
            )

        # ── RNF-06: Plazo permitido ───────────────────────────────────────────
        detalles["cuotas_solicitadas"] = cantidad_cuotas
        detalles["cuotas_maximas"] = CUOTAS_MAXIMAS_DEFAULT
        detalles["rnf06_plazo_ok"] = cantidad_cuotas <= CUOTAS_MAXIMAS_DEFAULT

        if cantidad_cuotas > CUOTAS_MAXIMAS_DEFAULT:
            return _rechazo(
                f"El plazo solicitado ({cantidad_cuotas} meses) supera el máximo permitido ({CUOTAS_MAXIMAS_DEFAULT} meses).",
                detalles,
                nivel_riesgo=nivel_riesgo,
                score=score,
                monto_maximo=monto_maximo
            )

        # ── RNF-04: Ratio de endeudamiento ────────────────────────────────────
        ratio = calcular_ratio_endeudamiento(usuario_id, monto, ingreso_mensual, conn)
        detalles["ratio_endeudamiento"] = float(ratio)
        detalles["rnf04_ratio_ok"] = ratio < RATIO_ZONA_GRIS_MIN

        if ratio >= RATIO_RECHAZO:
            return _rechazo(
                f"Ratio de endeudamiento muy alto ({ratio:.1%}). El límite máximo es {RATIO_RECHAZO:.0%} del ingreso mensual.",
                detalles,
                nivel_riesgo=nivel_riesgo,
                score=score,
                monto_maximo=monto_maximo,
                ratio=ratio
            )

        # ── RNF-07: Tasa de interés ───────────────────────────────────────────
        tasa = TASAS[nivel_riesgo]
        detalles["tasa_interes_mensual"] = float(tasa)

        # ── RNF-08: Estado final ──────────────────────────────────────────────
        # Si el ratio está en zona gris (40%-70%) → en_revision
        if ratio >= RATIO_ZONA_GRIS_MIN:
            estado_final = "en_revision"
            detalles["motivo_revision"] = f"Ratio de endeudamiento en zona gris: {ratio:.1%} (umbral de revisión: {RATIO_ZONA_GRIS_MIN:.0%})"
        else:
            estado_final = "aprobado"

        return {
            "estado_final": estado_final,
            "nivel_riesgo": nivel_riesgo,
            "tasa_interes": tasa,
            "monto_maximo": monto_maximo,
            "cuotas_maximas": CUOTAS_MAXIMAS_DEFAULT,
            "score_plataforma": score,
            "ratio_endeudamiento": ratio,
            "motivo_rechazo": None,
            "detalles": detalles,
        }

    finally:
        cur.close()
        conn.close()


def _rechazo(motivo: str, detalles: dict, **kwargs) -> dict:
    """Helper que construye un resultado de rechazo."""
    return {
        "estado_final": "rechazado",
        "nivel_riesgo": kwargs.get("nivel_riesgo"),
        "tasa_interes": None,
        "monto_maximo": kwargs.get("monto_maximo"),
        "cuotas_maximas": CUOTAS_MAXIMAS_DEFAULT,
        "score_plataforma": kwargs.get("score", 0),
        "ratio_endeudamiento": kwargs.get("ratio"),
        "motivo_rechazo": motivo,
        "detalles": detalles,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  GENERACIÓN AUTOMÁTICA DE CUOTAS
# ═══════════════════════════════════════════════════════════════════════════════

def generar_cuotas(prestamo_id: str, monto: Decimal, tasa_interes: Decimal,
                   cantidad_cuotas: int, conn=None):
    """
    Genera automáticamente las cuotas de un préstamo aprobado.
    Fórmula: cuota_mensual = (monto * tasa/100 * n + monto) / n
    Las fechas de vencimiento se calculan a partir de hoy + 1 semana por cuota.
    """
    cerrar = False
    if conn is None:
        conn = get_connection()
        cerrar = True

    cur = conn.cursor()
    try:
        interes_total = monto * (tasa_interes / 100) * cantidad_cuotas
        total = monto + interes_total
        monto_cuota = (total / cantidad_cuotas).quantize(Decimal("0.01"))

        hoy = date.today()
        for i in range(1, cantidad_cuotas + 1):
            # Vencimiento: 1 semana por cuota
            vencimiento = hoy + timedelta(days=7 * i)

            cur.execute("""
                INSERT INTO cuotas (prestamo_id, numero_cuota, monto_cuota,
                                    fecha_vencimiento, estado_cuota)
                VALUES (%s, %s, %s, %s, 'pendiente')
            """, (prestamo_id, i, monto_cuota, vencimiento))

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        if cerrar:
            conn.close()
