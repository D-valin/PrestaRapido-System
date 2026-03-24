from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from db import get_connection, crear_tablas
from auth import router as auth_router, get_usuario_actual, hashear_password
from evaluacion import evaluar_solicitud, generar_cuotas
from models import (
    UsuarioCreate, UsuarioUpdate, UsuarioOut,
    PrestamoCreate, PrestamoUpdate, PrestamoOut,
    CuotaCreate, CuotaUpdate, CuotaOut,
    PagoCreate, PagoUpdate, PagoOut,
    EvaluacionOut,
)

app = FastAPI(
    title="PrestaRápido API",
    description="CRUD del Mínimo Producto Viable — Sistema de solicitud y evaluación de créditos",
    version="1.0.0",
)

@app.on_event("startup")
def startup():
    crear_tablas()

# Servir archivos estáticos (frontend)
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/static/login.html")

app.include_router(auth_router)


# ═══════════════════════════════════════════════════════════════════════════════
#  USUARIOS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/usuarios/", tags=["Usuarios"], summary="Crear un usuario")
def crear_usuario(usuario: UsuarioCreate):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO usuarios (
                documento_identidad, nombre_completo, email,
                telefono, password_hash, estado_verificacion,
                fecha_nacimiento, ingreso_mensual
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            usuario.documento_identidad, usuario.nombre_completo, usuario.email,
            usuario.telefono, hashear_password(usuario.password_hash), usuario.estado_verificacion,
            usuario.fecha_nacimiento, usuario.ingreso_mensual,
        ))
        nuevo_id = cur.fetchone()[0]
        conn.commit()
        return {"mensaje": "Usuario creado exitosamente", "id": str(nuevo_id)}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.get("/usuarios/", tags=["Usuarios"], summary="Obtener todos los usuarios")
def obtener_usuarios():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, documento_identidad, nombre_completo, email,
               telefono, estado_verificacion, fecha_registro,
               fecha_nacimiento, ingreso_mensual
        FROM usuarios
        ORDER BY fecha_registro DESC;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        UsuarioOut(
            id=str(r[0]), documento_identidad=r[1], nombre_completo=r[2],
            email=r[3], telefono=r[4], estado_verificacion=r[5], fecha_registro=r[6],
            fecha_nacimiento=r[7], ingreso_mensual=r[8],
        ) for r in rows
    ]


@app.get("/usuarios/{usuario_id}", tags=["Usuarios"], summary="Obtener un usuario por ID")
def obtener_usuario(usuario_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, documento_identidad, nombre_completo, email,
               telefono, estado_verificacion, fecha_registro,
               fecha_nacimiento, ingreso_mensual
        FROM usuarios WHERE id = %s;
    """, (usuario_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UsuarioOut(
        id=str(row[0]), documento_identidad=row[1], nombre_completo=row[2],
        email=row[3], telefono=row[4], estado_verificacion=row[5], fecha_registro=row[6],
        fecha_nacimiento=row[7], ingreso_mensual=row[8],
    )


@app.put("/usuarios/{usuario_id}", tags=["Usuarios"], summary="Actualizar un usuario")
def actualizar_usuario(usuario_id: str, datos: UsuarioUpdate, _=Depends(get_usuario_actual)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        campos = {k: v for k, v in datos.model_dump().items() if v is not None}
        if not campos:
            raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")
        set_clause = ", ".join(f"{k} = %s" for k in campos)
        valores = list(campos.values()) + [usuario_id]
        cur.execute(f"UPDATE usuarios SET {set_clause} WHERE id = %s", valores)
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return {"mensaje": "Usuario actualizado correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.delete("/usuarios/{usuario_id}", tags=["Usuarios"], summary="Eliminar un usuario")
def eliminar_usuario(usuario_id: str, _=Depends(get_usuario_actual)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return {"mensaje": "Usuario eliminado correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  PRESTAMOS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/prestamos/evaluar", tags=["Préstamos"], summary="Evaluar elegibilidad sin crear préstamo")
def evaluar_prestamo(prestamo: PrestamoCreate):
    """Corre todas las reglas de negocio RNF-01..08 y devuelve el resultado sin persistir nada."""
    resultado = evaluar_solicitud(
        usuario_id=prestamo.usuario_id,
        monto=prestamo.monto,
        cantidad_cuotas=prestamo.cantidad_cuotas,
    )
    return resultado


@app.post("/prestamos/", tags=["Préstamos"], summary="Crear un préstamo (con evaluación automática)")
def crear_prestamo(prestamo: PrestamoCreate):
    """
    Evalúa la solicitud con las reglas RNF-01..08.
    - Si es 'rechazado': devuelve 422 con el motivo.
    - Si es 'aprobado' o 'en_revision': crea el préstamo y genera las cuotas automáticamente.
    La tasa de interés es asignada por el sistema según el nivel de riesgo, ignorando
    cualquier valor enviado por el cliente.
    """
    # ── Evaluación ──────────────────────────────────────────────────────────
    resultado = evaluar_solicitud(
        usuario_id=prestamo.usuario_id,
        monto=prestamo.monto,
        cantidad_cuotas=prestamo.cantidad_cuotas,
    )

    if resultado["estado_final"] == "rechazado":
        raise HTTPException(
            status_code=422,
            detail={
                "estado": "rechazado",
                "motivo": resultado["motivo_rechazo"],
                "evaluacion": resultado,
            }
        )

    # La tasa la asigna el backend, no el cliente
    tasa_asignada = resultado["tasa_interes"]
    estado_prestamo = resultado["estado_final"]  # 'aprobado' o 'en_revision'

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO prestamos (
                usuario_id, monto, tasa_interes, cantidad_cuotas,
                estado, fecha_desembolso, proximo_vencimiento
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            prestamo.usuario_id, prestamo.monto, tasa_asignada,
            prestamo.cantidad_cuotas, estado_prestamo,
            prestamo.fecha_desembolso, prestamo.proximo_vencimiento,
        ))
        nuevo_id = str(cur.fetchone()[0])
        conn.commit()

        # ── Generar cuotas automáticamente si está aprobado ──────────────────
        if estado_prestamo == "aprobado":
            generar_cuotas(
                prestamo_id=nuevo_id,
                monto=prestamo.monto,
                tasa_interes=tasa_asignada,
                cantidad_cuotas=prestamo.cantidad_cuotas,
            )

        return {
            "mensaje": f"Solicitud {estado_prestamo} correctamente",
            "id": nuevo_id,
            "estado": estado_prestamo,
            "tasa_asignada": float(tasa_asignada),
            "nivel_riesgo": resultado["nivel_riesgo"],
            "score_plataforma": resultado["score_plataforma"],
            "cuotas_generadas": prestamo.cantidad_cuotas if estado_prestamo == "aprobado" else 0,
            "evaluacion": resultado,
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.get("/prestamos/", tags=["Préstamos"], summary="Obtener todos los préstamos")
def obtener_prestamos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, usuario_id, monto, tasa_interes, cantidad_cuotas,
               estado, fecha_desembolso, proximo_vencimiento
        FROM prestamos
        ORDER BY fecha_desembolso DESC NULLS LAST;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        PrestamoOut(
            id=str(r[0]), usuario_id=str(r[1]), monto=r[2], tasa_interes=r[3],
            cantidad_cuotas=r[4], estado=r[5], fecha_desembolso=r[6], proximo_vencimiento=r[7],
        ) for r in rows
    ]


@app.get("/prestamos/{prestamo_id}", tags=["Préstamos"], summary="Obtener un préstamo por ID")
def obtener_prestamo(prestamo_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, usuario_id, monto, tasa_interes, cantidad_cuotas,
               estado, fecha_desembolso, proximo_vencimiento
        FROM prestamos WHERE id = %s;
    """, (prestamo_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    return PrestamoOut(
        id=str(row[0]), usuario_id=str(row[1]), monto=row[2], tasa_interes=row[3],
        cantidad_cuotas=row[4], estado=row[5], fecha_desembolso=row[6], proximo_vencimiento=row[7],
    )


@app.get("/usuarios/{usuario_id}/prestamos", tags=["Préstamos"], summary="Préstamos de un usuario")
def obtener_prestamos_usuario(usuario_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, usuario_id, monto, tasa_interes, cantidad_cuotas,
               estado, fecha_desembolso, proximo_vencimiento
        FROM prestamos WHERE usuario_id = %s
        ORDER BY fecha_desembolso DESC NULLS LAST;
    """, (usuario_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        PrestamoOut(
            id=str(r[0]), usuario_id=str(r[1]), monto=r[2], tasa_interes=r[3],
            cantidad_cuotas=r[4], estado=r[5], fecha_desembolso=r[6], proximo_vencimiento=r[7],
        ) for r in rows
    ]


@app.put("/prestamos/{prestamo_id}", tags=["Préstamos"], summary="Actualizar un préstamo")
def actualizar_prestamo(prestamo_id: str, datos: PrestamoUpdate):
    conn = get_connection()
    cur = conn.cursor()
    try:
        campos = {k: v for k, v in datos.model_dump().items() if v is not None}
        if not campos:
            raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")
        set_clause = ", ".join(f"{k} = %s" for k in campos)
        valores = list(campos.values()) + [prestamo_id]
        cur.execute(f"UPDATE prestamos SET {set_clause} WHERE id = %s", valores)
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")
        return {"mensaje": "Préstamo actualizado correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.delete("/prestamos/{prestamo_id}", tags=["Préstamos"], summary="Eliminar un préstamo")
def eliminar_prestamo(prestamo_id: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM prestamos WHERE id = %s", (prestamo_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")
        return {"mensaje": "Préstamo eliminado correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  CUOTAS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/cuotas/", tags=["Cuotas"], summary="Crear una cuota")
def crear_cuota(cuota: CuotaCreate):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO cuotas (
                prestamo_id, numero_cuota, monto_cuota,
                fecha_vencimiento, estado_cuota
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            cuota.prestamo_id, cuota.numero_cuota, cuota.monto_cuota,
            cuota.fecha_vencimiento, cuota.estado_cuota,
        ))
        nuevo_id = cur.fetchone()[0]
        conn.commit()
        return {"mensaje": "Cuota creada exitosamente", "id": str(nuevo_id)}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.get("/cuotas/", tags=["Cuotas"], summary="Obtener todas las cuotas")
def obtener_cuotas():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, prestamo_id, numero_cuota, monto_cuota,
               fecha_vencimiento, estado_cuota
        FROM cuotas
        ORDER BY prestamo_id, numero_cuota;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        CuotaOut(
            id=str(r[0]), prestamo_id=str(r[1]), numero_cuota=r[2],
            monto_cuota=r[3], fecha_vencimiento=r[4], estado_cuota=r[5],
        ) for r in rows
    ]


@app.get("/cuotas/{cuota_id}", tags=["Cuotas"], summary="Obtener una cuota por ID")
def obtener_cuota(cuota_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, prestamo_id, numero_cuota, monto_cuota,
               fecha_vencimiento, estado_cuota
        FROM cuotas WHERE id = %s;
    """, (cuota_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")
    return CuotaOut(
        id=str(row[0]), prestamo_id=str(row[1]), numero_cuota=row[2],
        monto_cuota=row[3], fecha_vencimiento=row[4], estado_cuota=row[5],
    )


@app.get("/prestamos/{prestamo_id}/cuotas", tags=["Cuotas"], summary="Cuotas de un préstamo")
def obtener_cuotas_prestamo(prestamo_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, prestamo_id, numero_cuota, monto_cuota,
               fecha_vencimiento, estado_cuota
        FROM cuotas WHERE prestamo_id = %s
        ORDER BY numero_cuota;
    """, (prestamo_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        CuotaOut(
            id=str(r[0]), prestamo_id=str(r[1]), numero_cuota=r[2],
            monto_cuota=r[3], fecha_vencimiento=r[4], estado_cuota=r[5],
        ) for r in rows
    ]


@app.put("/cuotas/{cuota_id}", tags=["Cuotas"], summary="Actualizar una cuota")
def actualizar_cuota(cuota_id: str, datos: CuotaUpdate):
    conn = get_connection()
    cur = conn.cursor()
    try:
        campos = {k: v for k, v in datos.model_dump().items() if v is not None}
        if not campos:
            raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")
        set_clause = ", ".join(f"{k} = %s" for k in campos)
        valores = list(campos.values()) + [cuota_id]
        cur.execute(f"UPDATE cuotas SET {set_clause} WHERE id = %s", valores)
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Cuota no encontrada")
        return {"mensaje": "Cuota actualizada correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.delete("/cuotas/{cuota_id}", tags=["Cuotas"], summary="Eliminar una cuota")
def eliminar_cuota(cuota_id: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM cuotas WHERE id = %s", (cuota_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Cuota no encontrada")
        return {"mensaje": "Cuota eliminada correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGOS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/pagos/", tags=["Pagos"], summary="Registrar un pago")
def crear_pago(pago: PagoCreate):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO pagos (
                cuota_id, monto_pagado, metodo_pago,
                referencia_transaccion, fecha_pago
            )
            VALUES (%s, %s, %s, %s, COALESCE(%s, NOW()))
            RETURNING id;
        """, (
            pago.cuota_id, pago.monto_pagado, pago.metodo_pago,
            pago.referencia_transaccion, pago.fecha_pago,
        ))
        nuevo_id = cur.fetchone()[0]
        # Marcar la cuota como pagada automáticamente
        cur.execute(
            "UPDATE cuotas SET estado_cuota = 'pagada' WHERE id = %s",
            (pago.cuota_id,)
        )
        conn.commit()
        return {"mensaje": "Pago registrado exitosamente", "id": str(nuevo_id)}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.get("/pagos/", tags=["Pagos"], summary="Obtener todos los pagos")
def obtener_pagos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, cuota_id, monto_pagado, metodo_pago,
               referencia_transaccion, fecha_pago
        FROM pagos
        ORDER BY fecha_pago DESC;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        PagoOut(
            id=str(r[0]), cuota_id=str(r[1]), monto_pagado=r[2],
            metodo_pago=r[3], referencia_transaccion=r[4], fecha_pago=r[5],
        ) for r in rows
    ]


@app.get("/pagos/{pago_id}", tags=["Pagos"], summary="Obtener un pago por ID")
def obtener_pago(pago_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, cuota_id, monto_pagado, metodo_pago,
               referencia_transaccion, fecha_pago
        FROM pagos WHERE id = %s;
    """, (pago_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return PagoOut(
        id=str(row[0]), cuota_id=str(row[1]), monto_pagado=row[2],
        metodo_pago=row[3], referencia_transaccion=row[4], fecha_pago=row[5],
    )


@app.get("/cuotas/{cuota_id}/pagos", tags=["Pagos"], summary="Pagos de una cuota")
def obtener_pagos_cuota(cuota_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, cuota_id, monto_pagado, metodo_pago,
               referencia_transaccion, fecha_pago
        FROM pagos WHERE cuota_id = %s
        ORDER BY fecha_pago DESC;
    """, (cuota_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        PagoOut(
            id=str(r[0]), cuota_id=str(r[1]), monto_pagado=r[2],
            metodo_pago=r[3], referencia_transaccion=r[4], fecha_pago=r[5],
        ) for r in rows
    ]


@app.put("/pagos/{pago_id}", tags=["Pagos"], summary="Actualizar un pago")
def actualizar_pago(pago_id: str, datos: PagoUpdate):
    conn = get_connection()
    cur = conn.cursor()
    try:
        campos = {k: v for k, v in datos.model_dump().items() if v is not None}
        if not campos:
            raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")
        set_clause = ", ".join(f"{k} = %s" for k in campos)
        valores = list(campos.values()) + [pago_id]
        cur.execute(f"UPDATE pagos SET {set_clause} WHERE id = %s", valores)
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pago no encontrado")
        return {"mensaje": "Pago actualizado correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.delete("/pagos/{pago_id}", tags=["Pagos"], summary="Eliminar un pago")
def eliminar_pago(pago_id: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM pagos WHERE id = %s", (pago_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pago no encontrado")
        return {"mensaje": "Pago eliminado correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()
import os
import uvicorn
