from typing import Optional
# -*- coding: utf-8 -*-
"""
Configuracion del Task Manager.

Equipo, tokens, conexion SQL, constantes.
"""

import os
from datetime import datetime

# ── Chatwoot ──
CHATWOOT_URL = "https://chat.calzalindo.com.ar"
CHATWOOT_TOKEN = os.environ.get("CHATWOOT_TOKEN", "zvQpseDYDoeqJpwM41GCb1LP")
CHATWOOT_ACCOUNT = 3
CHATWOOT_INBOX_ID = 9  # CALZALINDO 7436 (WhatsApp Cloud)

# ── SQL Server (produccion 111) ──
SQL_CONN_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=omicronvt;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)

# ── Equipo ──
# Formato: nombre_clave -> datos completos
# responsable_wa con formato internacional (sin +)
EQUIPO = {
    "fernando": {
        "nombre": "Fernando Calaianov",
        "wa": "+5493462672330",
        "chatwoot_id": None,
        "area": "Direccion",
        "rol": "Director / Estrategia",
        "es_admin": True,
    },
    "mati": {
        "nombre": "Mati Rodriguez",
        "wa": "+5493462508491",
        "chatwoot_id": None,
        "area": "Compras Deportes",
        "rol": "Compras Deportes / Pipeline",
        "es_admin": False,
    },
    "mariana": {
        "nombre": "Mariana",
        "wa": "+5493462317470",
        "chatwoot_id": 465,
        "area": "Admin / Compras",
        "rol": "Asistente Compras",
        "es_admin": False,
    },
    "gonzalo": {
        "nombre": "Gonzalo Bernardi",
        "wa": "+5493462317553",
        "chatwoot_id": 466,
        "area": "Deposito",
        "rol": "Asistente Deposito",
        "es_admin": False,
    },
    "gonza": {  # alias
        "nombre": "Gonzalo Bernardi",
        "wa": "+5493462317553",
        "chatwoot_id": 466,
        "area": "Deposito",
        "rol": "Asistente Deposito",
        "es_admin": False,
    },
    "emanuel": {
        "nombre": "Emanuel Cisneros",
        "wa": "+5493462317342",
        "chatwoot_id": 467,
        "area": "Operaciones",
        "rol": "Operaciones",
        "es_admin": False,
    },
    "tamara": {
        "nombre": "Tamara Calaianov",
        "wa": "+5493462677067",
        "chatwoot_id": None,
        "area": "Ventas / RRHH",
        "rol": "Ventas y RRHH",
        "es_admin": False,
    },
    "guille": {
        "nombre": "Guille Calaianov",
        "wa": "+5493462610216",
        "chatwoot_id": None,
        "area": "Infraestructura",
        "rol": "Infraestructura",
        "es_admin": False,
    },
    "lucia": {
        "nombre": "Lucia Giordano",
        "wa": "+5493462637251",
        "chatwoot_id": 468,
        "area": "Gerencia",
        "rol": "Gerencia",
        "es_admin": False,
    },
}

# Admins que pueden crear tareas (por numero WA)
ADMIN_PHONES = {"+5493462672330"}  # Fernando


def buscar_persona(texto: str) -> Optional[dict]:
    """
    Busca una persona del equipo por nombre, clave o telefono.
    Retorna el dict de la persona o None.
    """
    texto_lower = texto.strip().lower()

    # Buscar por clave directa
    if texto_lower in EQUIPO:
        return EQUIPO[texto_lower]

    # Buscar por nombre parcial
    for key, persona in EQUIPO.items():
        nombre_lower = persona["nombre"].lower()
        if texto_lower in nombre_lower or nombre_lower.startswith(texto_lower):
            return persona

    # Buscar por telefono
    for key, persona in EQUIPO.items():
        if persona["wa"] and texto in persona["wa"]:
            return persona

    return None


def buscar_persona_por_wa(telefono: str) -> Optional[dict]:
    """Busca persona por numero de WhatsApp exacto."""
    for key, persona in EQUIPO.items():
        if persona["wa"] == telefono:
            return persona
    return None


def es_admin(telefono: str) -> bool:
    """Verifica si un telefono pertenece a un admin."""
    return telefono in ADMIN_PHONES


def semana_actual() -> str:
    """Retorna la semana ISO actual en formato '2026-W14'."""
    now = datetime.now()
    return f"{now.year}-W{now.isocalendar()[1]:02d}"


# ── Rate limiting ──
DELAY_ENTRE_MENSAJES = 2  # segundos entre mensajes WA

# ── Webhook ──
WEBHOOK_SECRET = os.environ.get("TASK_WEBHOOK_SECRET", "task_mgr_2026")
