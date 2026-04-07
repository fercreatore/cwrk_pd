# -*- coding: utf-8 -*-
"""
Scheduler para checkpoints automaticos.

- Checkpoint miercoles: pide update a cada persona con tareas activas
- Cierre viernes: resumen semanal a Fernando
"""

import logging
from datetime import datetime

try:
    from . import db
    from .config import EQUIPO, buscar_persona, semana_actual
    from .chatwoot_client import enviar_mensaje_a_telefono
except ImportError:
    import db
    from config import EQUIPO, buscar_persona, semana_actual
    from chatwoot_client import enviar_mensaje_a_telefono

logger = logging.getLogger("task_manager.scheduler")


# ── Emojis de estado ──

_EMOJI_ESTADO = {
    "ASIGNADA": "\u23f3",      # hourglass
    "EN_PROGRESO": "\U0001f3c3",  # runner
    "BLOQUEADA": "\U0001f6a7",    # construction
    "COMPLETA": "\u2705",         # check
    "CANCELADA": "\u274c",        # x
}


def _formato_deadline(deadline) -> str:
    """Formatea un deadline para mostrar en mensaje."""
    if not deadline:
        return "sin fecha"
    if isinstance(deadline, datetime):
        return deadline.strftime("%a %d/%m")
    return str(deadline)


def _formato_tarea_linea(tarea: dict, numerada: bool = True, num: int = 1) -> str:
    """Formatea una tarea como linea de texto."""
    emoji = _EMOJI_ESTADO.get(tarea.get("estado", ""), "\u2753")
    titulo = tarea.get("titulo", "?")
    deadline = _formato_deadline(tarea.get("deadline"))
    pct = tarea.get("porcentaje", 0) or 0

    linea = f"{emoji} {titulo} ({deadline})"

    if tarea.get("estado") == "EN_PROGRESO" and pct > 0:
        linea += f" [{pct}%]"
    if tarea.get("estado") == "BLOQUEADA" and tarea.get("motivo_bloqueo"):
        linea += f" - {tarea['motivo_bloqueo'][:50]}"

    if numerada:
        return f"{num}. {linea}"
    return linea


# ── Checkpoint miercoles ──

def generar_checkpoint_miercoles(dry_run: bool = True) -> list:
    """
    Genera y envia (o muestra) mensajes de checkpoint del miercoles.

    Para cada persona con tareas activas, envia un resumen
    pidiendo update.

    Returns:
        lista de dicts con {nombre, telefono, mensaje, enviado}
    """
    personas = db.personas_con_tareas_activas()
    resultados = []

    for p in personas:
        nombre = p["nombre"]
        telefono = p["wa"]

        tareas = db.tareas_persona(nombre, solo_activas=True)
        if not tareas:
            continue

        # Armar mensaje
        lineas = [
            f"\U0001f514 Checkpoint mitad de semana",
            f"",
            f"Hola {nombre.split()[0]}, tus tareas esta semana:",
            "",
        ]

        for i, t in enumerate(tareas, 1):
            lineas.append(_formato_tarea_linea(t, numerada=True, num=i))

        lineas.extend([
            "",
            "Contesta con:",
            "\u2022 *listo* = terminada",
            "\u2022 *70%* = avance parcial",
            "\u2022 *bloqueado: [motivo]* = trabada",
        ])

        mensaje = "\n".join(lineas)

        resultado = {
            "nombre": nombre,
            "telefono": telefono,
            "mensaje": mensaje,
            "enviado": False,
        }

        if dry_run:
            logger.info(f"[DRY RUN] Checkpoint para {nombre}:\n{mensaje}")
        else:
            if telefono:
                res = enviar_mensaje_a_telefono(nombre, telefono, mensaje)
                resultado["enviado"] = res.get("ok", False)
                if not res.get("ok"):
                    resultado["error"] = res.get("error")
                    logger.error(f"Error enviando checkpoint a {nombre}: {res}")
            else:
                resultado["error"] = "Sin telefono"
                logger.warning(f"No hay telefono para {nombre}")

        resultados.append(resultado)

    return resultados


# ── Cierre viernes ──

def generar_cierre_viernes(dry_run: bool = True) -> dict:
    """
    Genera y envia resumen semanal a Fernando.

    Returns:
        dict con resumen y estado de envio
    """
    semana = semana_actual()
    resumen = db.resumen_semana(semana)
    totales = resumen["totales"]

    # Calcular porcentaje
    if totales["total"] > 0:
        pct_completo = round(totales["completas"] / totales["total"] * 100)
    else:
        pct_completo = 0

    # Armar mensaje
    lineas = [
        f"\U0001f4ca Cierre semana {semana}",
        "",
        f"Completadas: {totales['completas']}/{totales['total']} ({pct_completo}%)",
        f"Bloqueadas: {totales['bloqueadas']}",
        f"Pendientes: {totales['pendientes']}",
        "",
        "Detalle por persona:",
    ]

    for nombre, datos in sorted(resumen["por_persona"].items()):
        emoji = "\u2705" if datos["pendientes"] == 0 else "\U0001f4cb"
        lineas.append(
            f"{emoji} *{nombre}*: "
            f"{datos['completas']}/{datos['total']} completadas"
        )
        if datos["bloqueadas"] > 0:
            lineas.append(f"   \u26a0\ufe0f {datos['bloqueadas']} bloqueadas")

    # Agregar tareas vencidas
    vencidas = db.tareas_vencidas()
    if vencidas:
        lineas.extend([
            "",
            f"\u26a0\ufe0f *{len(vencidas)} tareas vencidas:*",
        ])
        for t in vencidas[:5]:  # max 5
            lineas.append(
                f"\u2022 {t['titulo']} ({t['responsable']}, "
                f"vencio {_formato_deadline(t['deadline'])})"
            )
        if len(vencidas) > 5:
            lineas.append(f"   ... y {len(vencidas) - 5} mas")

    mensaje = "\n".join(lineas)

    resultado = {
        "semana": semana,
        "resumen": resumen,
        "mensaje": mensaje,
        "enviado": False,
    }

    fernando = EQUIPO.get("fernando", {})

    if dry_run:
        logger.info(f"[DRY RUN] Cierre semanal:\n{mensaje}")
    else:
        telefono = fernando.get("wa")
        if telefono:
            res = enviar_mensaje_a_telefono(
                fernando["nombre"], telefono, mensaje
            )
            resultado["enviado"] = res.get("ok", False)
            if not res.get("ok"):
                resultado["error"] = res.get("error")
        else:
            resultado["error"] = "Sin telefono de Fernando"

    return resultado


# ── Notificaciones puntuales ──

def notificar_tarea_creada(tarea_id: int, titulo: str,
                           responsable: dict, deadline=None,
                           resultado_esperado: str = None,
                           canal_entrega: str = None,
                           dry_run: bool = True) -> dict:
    """
    Notifica al responsable que se le asigno una tarea.
    """
    nombre = responsable.get("nombre", "?")
    telefono = responsable.get("wa")

    lineas = [
        f"\U0001f4cb Nueva tarea asignada",
        f"",
        f"*{titulo}*",
    ]

    if deadline:
        lineas.append(f"\u23f0 Para: {_formato_deadline(deadline)}")
    if resultado_esperado:
        lineas.append(f"\U0001f4dd Que: {resultado_esperado}")
    if canal_entrega:
        lineas.append(f"\u2705 Entregar: {canal_entrega}")

    lineas.extend([
        "",
        "Contesta:",
        "\u2022 *listo* cuando termines",
        "\u2022 *avance X%* para reportar progreso",
        "\u2022 *bloqueado: motivo* si te trabas",
    ])

    mensaje = "\n".join(lineas)

    resultado = {"nombre": nombre, "mensaje": mensaje, "enviado": False}

    if dry_run:
        logger.info(f"[DRY RUN] Notificacion a {nombre}:\n{mensaje}")
    else:
        if telefono:
            res = enviar_mensaje_a_telefono(nombre, telefono, mensaje)
            resultado["enviado"] = res.get("ok", False)
            if not res.get("ok"):
                resultado["error"] = res.get("error")
        else:
            resultado["error"] = "Sin telefono"

    return resultado


def notificar_admin_completada(tarea_id: int, titulo: str,
                               responsable_nombre: str,
                               dry_run: bool = True) -> dict:
    """Notifica a Fernando que una tarea se completo."""
    fernando = EQUIPO.get("fernando", {})
    mensaje = (
        f"\u2705 Tarea completada\n\n"
        f"*{titulo}*\n"
        f"Completada por: {responsable_nombre}"
    )

    resultado = {"mensaje": mensaje, "enviado": False}

    if dry_run:
        logger.info(f"[DRY RUN] Admin notificacion:\n{mensaje}")
    else:
        telefono = fernando.get("wa")
        if telefono:
            res = enviar_mensaje_a_telefono(
                fernando["nombre"], telefono, mensaje
            )
            resultado["enviado"] = res.get("ok", False)

    return resultado


def notificar_admin_bloqueada(tarea_id: int, titulo: str,
                              responsable_nombre: str, motivo: str,
                              dry_run: bool = True) -> dict:
    """Notifica a Fernando que una tarea esta bloqueada."""
    fernando = EQUIPO.get("fernando", {})
    mensaje = (
        f"\U0001f6a7 Tarea bloqueada\n\n"
        f"*{titulo}*\n"
        f"Responsable: {responsable_nombre}\n"
        f"Motivo: {motivo}"
    )

    resultado = {"mensaje": mensaje, "enviado": False}

    if dry_run:
        logger.info(f"[DRY RUN] Admin bloqueada:\n{mensaje}")
    else:
        telefono = fernando.get("wa")
        if telefono:
            res = enviar_mensaje_a_telefono(
                fernando["nombre"], telefono, mensaje
            )
            resultado["enviado"] = res.get("ok", False)

    return resultado
