# -*- coding: utf-8 -*-
"""
Autenticación centralizada contra MySQL clz_ventas_mysql en 192.168.2.109.
Misma DB que usa web2py (calzalindo_informes).
Compatible con el hash PBKDF2 de web2py.

Endpoints:
  POST /api/v1/auth/login          → Login con email + password
  GET  /api/v1/auth/me             → Info del usuario logueado
  POST /api/v1/auth/logout         → Cerrar sesión
  GET  /api/v1/auth/check_token    → Validar token vigente
"""
import hashlib
import hmac
import secrets
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel
import pymysql
from config import settings

router = APIRouter()

# ── Sesiones en memoria (simple, sin Redis) ──────────────
# {token: {user_id, email, nombre, roles, sucursal, codigo_vendedor, ts}}
SESSIONS: dict = {}
SESSION_TTL = 86400 * 7  # 7 días

# ── MySQL auth connection (misma que web2py) ─────────────
MYSQL_AUTH = {
    "host": "192.168.2.109",
    "user": "root",
    "password": "cagr$2011",
    "database": "clz_ventas_mysql",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


def query_auth(sql: str) -> list:
    """Ejecuta query contra MySQL auth y retorna lista de dicts."""
    conn = pymysql.connect(**MYSQL_AUTH)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


# ── Modelos ───────────────────────────────────────────────
class LoginIn(BaseModel):
    email: str
    password: str


class LoginOut(BaseModel):
    ok: bool
    token: Optional[str] = None
    usuario: Optional[dict] = None
    mensaje: str = ""


# ── PBKDF2 compatible con web2py ──────────────────────────
def verify_web2py_password(plain: str, stored: str) -> bool:
    """
    Valida password contra hash web2py formato:
    pbkdf2(1000,20,sha512)$salt_hex$hash_hex
    """
    try:
        # Parsear: "pbkdf2(1000,20,sha512)$salt$hash"
        parts = stored.split("$")
        if len(parts) != 3:
            return False

        algo_part = parts[0]   # pbkdf2(1000,20,sha512)
        salt_hex = parts[1]
        hash_hex = parts[2]

        # Extraer parámetros: iterations, key_length, digest
        inner = algo_part.split("(")[1].rstrip(")")
        params = inner.split(",")
        iterations = int(params[0])
        key_length = int(params[1])
        digest = params[2]

        # web2py usa el salt como STRING utf-8, no como bytes decodificados
        salt = salt_hex.encode("utf-8")

        # Derivar con PBKDF2
        dk = hashlib.pbkdf2_hmac(
            digest,
            plain.encode("utf-8"),
            salt,
            iterations,
            dklen=key_length,
        )

        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# ── Helpers ───────────────────────────────────────────────
def get_user_roles(user_id: int) -> list:
    """Obtiene los roles del usuario desde auth_membership + auth_group."""
    sql = """
        SELECT g.role
        FROM auth_membership m
        JOIN auth_group g ON g.id = m.group_id
        WHERE m.user_id = %d
    """ % user_id
    rows = query_auth(sql)
    return [r["role"] for r in rows]


def get_codigo_vendedor(user_id: int, email: str) -> Optional[str]:
    """
    Busca si el usuario tiene vendedor_freelance asociado.
    Intenta por viajante_cod extraído del email (vendedor{N}@...)
    """
    from db import query
    viajante_cod = None
    if email and email.startswith("vendedor"):
        try:
            num_str = email.split("@")[0].replace("vendedor", "")
            viajante_cod = int(num_str)
        except (ValueError, IndexError):
            pass

    if viajante_cod:
        rows = query(
            "SELECT codigo_atrib FROM vendedor_freelance WHERE viajante_cod = %d AND activo = 1"
            % viajante_cod,
            settings.DB_ANALITICA,
        )
        if rows:
            return rows[0]["codigo_atrib"]

    return None


def generate_token() -> str:
    return secrets.token_hex(32)


def cleanup_sessions():
    """Limpia sesiones expiradas."""
    now = time.time()
    expired = [k for k, v in SESSIONS.items() if now - v["ts"] > SESSION_TTL]
    for k in expired:
        del SESSIONS[k]


# ── Dependencia: obtener usuario actual ──────────────────
async def get_current_user(request: Request) -> Optional[dict]:
    """Extrae usuario de cookie o header Authorization."""
    token = request.cookies.get("h4_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if token and token in SESSIONS:
        session = SESSIONS[token]
        if time.time() - session["ts"] < SESSION_TTL:
            return session
    return None


async def require_user(request: Request) -> dict:
    """Como get_current_user pero lanza 401 si no hay sesión."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Sesión no válida. Inicia sesión.")
    return user


async def require_admin(request: Request) -> dict:
    """Requiere que el usuario sea admin o gerencial."""
    user = await require_user(request)
    if "admins" not in user.get("roles", []) and "ges_admin" not in user.get("roles", []):
        raise HTTPException(403, "Acceso denegado. Se requiere rol de administrador.")
    return user


# ── Endpoints ─────────────────────────────────────────────
@router.post("/login", response_model=LoginOut)
async def login(data: LoginIn, response: Response):
    """Autenticar contra MySQL clz_ventas_mysql en .109."""
    cleanup_sessions()

    email = data.email.strip().lower()
    password = data.password

    # Buscar usuario en MySQL
    sql = """
        SELECT id, email, password, first_name, last_name,
               sucursal, habilitado
        FROM auth_user
        WHERE LOWER(email) = '%s'
    """ % email.replace("'", "\\'")

    try:
        rows = query_auth(sql)
    except Exception as e:
        raise HTTPException(500, "Error de conexión a base de autenticación: %s" % str(e))

    if not rows:
        raise HTTPException(401, "Usuario o contraseña incorrectos")

    user = rows[0]

    # Verificar habilitado
    if user.get("habilitado") != "T":
        raise HTTPException(403, "Usuario deshabilitado. Contactar al administrador.")

    # Verificar password
    stored_hash = user.get("password", "")
    if not verify_web2py_password(password, stored_hash):
        raise HTTPException(401, "Usuario o contraseña incorrectos")

    # Obtener roles y código vendedor
    user_id = user["id"]
    roles = get_user_roles(user_id)
    codigo_vendedor = get_codigo_vendedor(user_id, email)

    # Determinar tipo de acceso
    es_admin = "admins" in roles or "ges_admin" in roles
    es_vendedor = codigo_vendedor is not None

    # Crear sesión
    token = generate_token()
    session_data = {
        "user_id": user_id,
        "email": email,
        "nombre": ("%s %s" % (user.get("first_name", ""), user.get("last_name", ""))).strip(),
        "sucursal": user.get("sucursal"),
        "roles": roles,
        "es_admin": es_admin,
        "es_vendedor": es_vendedor,
        "codigo_vendedor": codigo_vendedor,
        "ts": time.time(),
    }
    SESSIONS[token] = session_data

    # Cookie httponly
    response.set_cookie(
        key="h4_token",
        value=token,
        httponly=True,
        max_age=SESSION_TTL,
        samesite="lax",
    )

    return LoginOut(
        ok=True,
        token=token,
        usuario={
            "id": user_id,
            "nombre": session_data["nombre"],
            "email": email,
            "sucursal": user.get("sucursal"),
            "es_admin": es_admin,
            "es_vendedor": es_vendedor,
            "codigo_vendedor": codigo_vendedor,
            "roles": roles,
        },
        mensaje="Bienvenido, %s" % session_data["nombre"],
    )


@router.get("/me")
async def me(user: dict = Depends(require_user)):
    """Info del usuario logueado."""
    return {
        "user_id": user["user_id"],
        "nombre": user["nombre"],
        "email": user["email"],
        "sucursal": user["sucursal"],
        "es_admin": user["es_admin"],
        "es_vendedor": user["es_vendedor"],
        "codigo_vendedor": user["codigo_vendedor"],
        "roles": user["roles"],
    }


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Cerrar sesión."""
    token = request.cookies.get("h4_token")
    if token and token in SESSIONS:
        del SESSIONS[token]
    response.delete_cookie("h4_token")
    return {"ok": True, "mensaje": "Sesión cerrada"}


@router.get("/check_token")
async def check_token(request: Request):
    """Verificar si el token actual es válido."""
    user = await get_current_user(request)
    if user:
        return {"valid": True, "user_id": user["user_id"], "nombre": user["nombre"]}
    return {"valid": False}
