# -*- coding: utf-8 -*-
"""
Parser de mensajes WhatsApp para el Task Manager.

Interpreta mensajes entrantes y los clasifica en:
  - CREAR_TAREA: Fernando asigna una tarea
  - UPDATE_ESTADO: Responsable reporta avance/completado/bloqueado
  - CONSULTA: Alguien pide estado de tareas
  - DESCONOCIDO: No se pudo interpretar

Robusto con variantes de espanol argentino.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

try:
    from .config import buscar_persona
except ImportError:
    from config import buscar_persona


# ── Tipos de mensaje ──

@dataclass
class MensajeParsed:
    tipo: str  # CREAR_TAREA, UPDATE_ESTADO, CONSULTA, DESCONOCIDO
    datos: dict = field(default_factory=dict)
    confianza: float = 0.0  # 0.0 a 1.0
    raw: str = ""


# ── Patrones para UPDATE_ESTADO ──

# Completado
_PAT_COMPLETA = re.compile(
    r'^\s*(?:'
    r'listo|hecho|terminado|terminada|ya est[aá]|completado|completada|'
    r'done|ready|ok\s*$|entregado|entregada|finalizado|finalizada|'
    r'ya lo hice|ya la hice|ya mand[eé]|ya envi[eé]|ya lo envi[eé]|'
    r'100\s*%'
    r')\s*[.!]?\s*$',
    re.IGNORECASE
)

# Avance parcial: "avance 70%", "voy por el 50%", "estoy en 80%", "70%"
_PAT_AVANCE = re.compile(
    r'(?:'
    r'(?:avance|voy\s+(?:por|en)|estoy\s+(?:por|en)|progreso|llevo)\s*'
    r'(?:(?:el|un|al)?\s*)?'
    r'(\d{1,3})\s*%'
    r'|'
    r'^(\d{1,3})\s*%\s*$'  # solo "70%"
    r')',
    re.IGNORECASE
)

# Avance sin porcentaje: "avanzando", "estoy en eso", "voy bien"
_PAT_AVANCE_GENERICO = re.compile(
    r'^\s*(?:'
    r'avanzando|estoy en eso|voy bien|en eso estoy|'
    r'la estoy haciendo|estoy con eso|en progreso|'
    r'arrancando|empec[eé]|ya arranqu[eé]|'
    r'mañana lo termino|ma[nñ]ana termino|'
    r'lo tengo casi|casi listo|casi terminado'
    r')\s*[.!]?\s*$',
    re.IGNORECASE
)

# Bloqueado: "bloqueado", "no puedo", "falta X"
_PAT_BLOQUEADO = re.compile(
    r'^\s*(?:'
    r'bloqueado|bloqueada|trabado|trabada|no puedo|'
    r'no\s+(?:puedo|pude|logro)|falta\s+.+|'
    r'necesito\s+.+|dependo\s+de\s+.+|'
    r'esperando\s+.+|no\s+tengo\s+.+'
    r')',
    re.IGNORECASE
)

# ── Patrones para CONSULTA ──

# "estado mati", "como va mati", "que tiene mati"
_PAT_CONSULTA_PERSONA = re.compile(
    r'^\s*(?:'
    r'(?:estado|status|c[oó]mo\s+va|qu[eé]\s+tiene|tareas\s+(?:de|para))\s+'
    r'(\w+)'
    r')\s*[?]?\s*$',
    re.IGNORECASE
)

# "pendientes", "vencidas", "todas las tareas", "resumen"
_PAT_CONSULTA_GENERAL = re.compile(
    r'^\s*(?:'
    r'pendientes|vencidas|atrasadas|todas(?:\s+las\s+tareas)?|'
    r'resumen|dashboard|tablero|kanban|'
    r'esta\s+semana|semana\s+actual|'
    r'qu[eé]\s+falta|qu[eé]\s+queda'
    r')\s*[?]?\s*$',
    re.IGNORECASE
)

# "mis tareas", "que tengo", "lo mio"
_PAT_MIS_TAREAS = re.compile(
    r'^\s*(?:'
    r'mis\s+tareas|qu[eé]\s+tengo|lo\s+m[ií]o|'
    r'qu[eé]\s+me\s+falta|mis\s+pendientes'
    r')\s*[?]?\s*$',
    re.IGNORECASE
)

# ── Patron para CREAR_TAREA ──

# Formato: "Mati: [TAREA] X [PARA] Y [QUE] Z [ENTREGAR] W"
# O mas flexible: "Mati: Stock Reebok para mie 2-abr, planilla talles, por WA"
_PAT_TAREA_FORMAL = re.compile(
    r'^\s*(\w+)\s*:\s*'                          # nombre:
    r'(?:\[TAREA\]\s*)?(.+?)'                     # titulo
    r'\s*\[PARA\]\s*(.+?)'                        # deadline
    r'\s*\[QUE\]\s*(.+?)'                         # resultado
    r'(?:\s*\[ENTREGAR\]\s*(.+?))?'               # canal (opcional)
    r'\s*$',
    re.IGNORECASE | re.DOTALL
)

# Formato flexible: "Mati: hacer X para mie"
_PAT_TAREA_FLEX = re.compile(
    r'^\s*(\w+)\s*:\s*'                           # nombre:
    r'(.+?)'                                       # titulo/descripcion
    r'(?:\s+para\s+(.+?))?'                        # deadline (opcional)
    r'\s*$',
    re.IGNORECASE | re.DOTALL
)


# ── Parsing de fechas coloquiales ──

_DIAS_SEMANA = {
    'lun': 0, 'lunes': 0,
    'mar': 1, 'martes': 1,
    'mie': 2, 'miercoles': 2, 'mi\u00e9rcoles': 2,
    'jue': 3, 'jueves': 3,
    'vie': 4, 'viernes': 4,
    'sab': 5, 's\u00e1bado': 5, 'sabado': 5,
    'dom': 6, 'domingo': 6,
}

_MESES = {
    'ene': 1, 'enero': 1,
    'feb': 2, 'febrero': 2,
    'mar': 3, 'marzo': 3,
    'abr': 4, 'abril': 4,
    'may': 5, 'mayo': 5,
    'jun': 6, 'junio': 6,
    'jul': 7, 'julio': 7,
    'ago': 8, 'agosto': 8,
    'sep': 9, 'septiembre': 9,
    'oct': 10, 'octubre': 10,
    'nov': 11, 'noviembre': 11,
    'dic': 12, 'diciembre': 12,
}


def parsear_fecha(texto: str) -> Optional[datetime]:
    """
    Parsea fechas coloquiales argentinas.

    Ejemplos validos:
      "mie 2-abr", "miercoles 2 de abril", "vie", "viernes",
      "manana", "hoy", "2/4", "2-abr", "abril"
    """
    texto = texto.strip().lower()

    # Hoy / manana
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if texto in ('hoy',):
        return hoy
    if texto in ('ma\u00f1ana', 'manana', 'mañana'):
        return hoy + timedelta(days=1)

    # "mie 2-abr" o "miercoles 2 de abril"
    m = re.match(
        r'(?:\w+\s+)?(\d{1,2})\s*[-/de\s]+\s*(\w+)',
        texto
    )
    if m:
        dia = int(m.group(1))
        mes_texto = m.group(2).strip().rstrip('.')
        mes = _MESES.get(mes_texto)
        if mes:
            anio = hoy.year
            try:
                fecha = datetime(anio, mes, dia)
                if fecha < hoy:
                    fecha = datetime(anio + 1, mes, dia)
                return fecha
            except ValueError:
                pass

    # Solo dia de la semana: "vie", "miercoles"
    for dia_key, dia_num in _DIAS_SEMANA.items():
        if texto.startswith(dia_key):
            dias_adelante = (dia_num - hoy.weekday()) % 7
            if dias_adelante == 0:
                dias_adelante = 7  # proximo, no hoy
            return hoy + timedelta(days=dias_adelante)

    # "2/4" o "02/04"
    m = re.match(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', texto)
    if m:
        dia = int(m.group(1))
        mes = int(m.group(2))
        anio = int(m.group(3)) if m.group(3) else hoy.year
        if anio < 100:
            anio += 2000
        try:
            fecha = datetime(anio, mes, dia)
            if fecha < hoy and not m.group(3):
                fecha = datetime(anio + 1, mes, dia)
            return fecha
        except ValueError:
            pass

    # Solo mes: "abril" -> fin de mes
    for mes_key, mes_num in _MESES.items():
        if texto.strip() == mes_key:
            anio = hoy.year
            # Ultimo dia del mes
            if mes_num == 12:
                ultimo = datetime(anio + 1, 1, 1) - timedelta(days=1)
            else:
                ultimo = datetime(anio, mes_num + 1, 1) - timedelta(days=1)
            if ultimo < hoy:
                if mes_num == 12:
                    ultimo = datetime(anio + 2, 1, 1) - timedelta(days=1)
                else:
                    ultimo = datetime(anio + 1, mes_num + 1, 1) - timedelta(days=1)
            return ultimo

    return None


# ── Funcion principal ──

def parsear_mensaje(texto: str, telefono_remitente: str = "") -> MensajeParsed:
    """
    Parsea un mensaje de WhatsApp y determina la intencion.

    Args:
        texto: contenido del mensaje
        telefono_remitente: numero WA del remitente (para contexto)

    Returns:
        MensajeParsed con tipo, datos y confianza
    """
    texto = texto.strip()
    if not texto:
        return MensajeParsed(tipo="DESCONOCIDO", raw=texto)

    # 1. Intentar CREAR_TAREA (formato formal con tags)
    m = _PAT_TAREA_FORMAL.match(texto)
    if m:
        nombre_resp = m.group(1).strip()
        persona = buscar_persona(nombre_resp)
        deadline_texto = m.group(3).strip()
        deadline = parsear_fecha(deadline_texto)

        return MensajeParsed(
            tipo="CREAR_TAREA",
            datos={
                "responsable_key": nombre_resp.lower(),
                "responsable": persona,
                "titulo": m.group(2).strip(),
                "deadline": deadline,
                "deadline_texto": deadline_texto,
                "resultado_esperado": m.group(4).strip(),
                "canal_entrega": (m.group(5) or "").strip() or None,
            },
            confianza=0.95,
            raw=texto,
        )

    # 2. Intentar CREAR_TAREA (formato flexible "Nombre: tarea para dia")
    m = _PAT_TAREA_FLEX.match(texto)
    if m:
        nombre_resp = m.group(1).strip()
        persona = buscar_persona(nombre_resp)
        if persona:
            deadline = None
            deadline_texto = ""
            if m.group(3):
                deadline_texto = m.group(3).strip()
                deadline = parsear_fecha(deadline_texto)

            return MensajeParsed(
                tipo="CREAR_TAREA",
                datos={
                    "responsable_key": nombre_resp.lower(),
                    "responsable": persona,
                    "titulo": m.group(2).strip(),
                    "deadline": deadline,
                    "deadline_texto": deadline_texto,
                    "resultado_esperado": None,
                    "canal_entrega": None,
                },
                confianza=0.70,
                raw=texto,
            )

    # 3. UPDATE_ESTADO: completado
    if _PAT_COMPLETA.match(texto):
        return MensajeParsed(
            tipo="UPDATE_ESTADO",
            datos={
                "nuevo_estado": "COMPLETA",
                "porcentaje": 100,
            },
            confianza=0.90,
            raw=texto,
        )

    # 4. UPDATE_ESTADO: avance con porcentaje
    m = _PAT_AVANCE.search(texto)
    if m:
        pct = int(m.group(1) or m.group(2))
        pct = min(pct, 100)
        estado = "COMPLETA" if pct >= 100 else "EN_PROGRESO"
        return MensajeParsed(
            tipo="UPDATE_ESTADO",
            datos={
                "nuevo_estado": estado,
                "porcentaje": pct,
                "notas": texto,
            },
            confianza=0.85,
            raw=texto,
        )

    # 5. UPDATE_ESTADO: avance generico
    if _PAT_AVANCE_GENERICO.match(texto):
        return MensajeParsed(
            tipo="UPDATE_ESTADO",
            datos={
                "nuevo_estado": "EN_PROGRESO",
                "porcentaje": None,
                "notas": texto,
            },
            confianza=0.75,
            raw=texto,
        )

    # 6. UPDATE_ESTADO: bloqueado
    m = _PAT_BLOQUEADO.match(texto)
    if m:
        return MensajeParsed(
            tipo="UPDATE_ESTADO",
            datos={
                "nuevo_estado": "BLOQUEADA",
                "motivo": texto,
            },
            confianza=0.80,
            raw=texto,
        )

    # 7. CONSULTA: mis tareas
    if _PAT_MIS_TAREAS.match(texto):
        return MensajeParsed(
            tipo="CONSULTA",
            datos={
                "subtipo": "MIS_TAREAS",
            },
            confianza=0.90,
            raw=texto,
        )

    # 8. CONSULTA: persona especifica
    m = _PAT_CONSULTA_PERSONA.match(texto)
    if m:
        nombre = m.group(1).strip()
        persona = buscar_persona(nombre)
        return MensajeParsed(
            tipo="CONSULTA",
            datos={
                "subtipo": "PERSONA",
                "persona_key": nombre.lower(),
                "persona": persona,
            },
            confianza=0.85,
            raw=texto,
        )

    # 9. CONSULTA: general
    if _PAT_CONSULTA_GENERAL.match(texto):
        subtipo = "PENDIENTES"
        if re.search(r'vencid|atrasad', texto, re.IGNORECASE):
            subtipo = "VENCIDAS"
        elif re.search(r'resumen|dashboard|tablero', texto, re.IGNORECASE):
            subtipo = "RESUMEN"
        return MensajeParsed(
            tipo="CONSULTA",
            datos={"subtipo": subtipo},
            confianza=0.85,
            raw=texto,
        )

    # 10. No se pudo clasificar
    return MensajeParsed(
        tipo="DESCONOCIDO",
        datos={"texto": texto},
        confianza=0.0,
        raw=texto,
    )
