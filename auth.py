import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from db import get_connection

# ── Configuración ─────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "1gjh4f3gh24vhn2n4m5bm6h54jh64hjg4jgf")
ALGORITHM = "HS256"
EXPIRE_MINUTOS = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Utilidades de contraseña ───────────────────────────────────
def verificar_password(password_plano: str, password_hash: str) -> bool:
    return pwd_context.verify(password_plano, password_hash)

def hashear_password(password: str) -> str:
    password = str(password).strip()[:72]
    return pwd_context.hash(password)


# ── Generar token JWT ──────────────────────────────────────────
def crear_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=EXPIRE_MINUTOS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ── Verificar token y obtener usuario actual ───────────────────
def get_usuario_actual(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, nombre_completo FROM usuarios WHERE email = %s",
        (email,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        raise credentials_exception

    return {"id": str(row[0]), "email": row[1], "nombre_completo": row[2]}


# ── Endpoint de login ──────────────────────────────────────────
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Autenticación"])

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    usuario: dict

class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str

class RecuperarPasswordRequest(BaseModel):
    email: str
    documento_identidad: str
    password_nueva: str


@router.post("/cambiar-password", summary="Cambiar contraseña (autenticado)")
def cambiar_password(datos: CambiarPasswordRequest, usuario_actual=Depends(get_usuario_actual)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM usuarios WHERE id = %s", (usuario_actual["id"],))
    row = cur.fetchone()
    if not row or not verificar_password(datos.password_actual, row[0]):
        cur.close(); conn.close()
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
    nuevo_hash = hashear_password(datos.password_nueva)
    cur.execute("UPDATE usuarios SET password_hash = %s WHERE id = %s", (nuevo_hash, usuario_actual["id"]))
    conn.commit()
    cur.close(); conn.close()
    return {"mensaje": "Contraseña actualizada correctamente"}


@router.post("/recuperar-password", summary="Recuperar contraseña (sin sesión)")
def recuperar_password(datos: RecuperarPasswordRequest):
    """Verifica identidad por correo + documento y permite cambiar la contraseña."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM usuarios WHERE email = %s AND documento_identidad = %s",
        (datos.email, datos.documento_identidad)
    )
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="No se encontró una cuenta con ese correo y documento")
    nuevo_hash = hashear_password(datos.password_nueva)
    cur.execute("UPDATE usuarios SET password_hash = %s WHERE id = %s", (nuevo_hash, str(row[0])))
    conn.commit()
    cur.close(); conn.close()
    return {"mensaje": "Contraseña recuperada correctamente. Ya puedes iniciar sesión."}


@router.post("/login", response_model=LoginResponse, summary="Iniciar sesión y obtener token JWT")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, nombre_completo, password_hash FROM usuarios WHERE email = %s",
        (form_data.username,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row or not verificar_password(form_data.password, row[3]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = crear_token(data={"sub": row[1]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": str(row[0]),
            "email": row[1],
            "nombre_completo": row[2],
        }
    }
