# -*- coding: utf-8 -*-
"""
Webhook handler para mensajes de Chatwoot.

Recibe eventos de Chatwoot (message_created, etc.) y los procesa
segun el tipo de mensaje detectado por el parser.
"""

import logging
from datetime import datetime

try:
    from .config import (
        CHATWOOT_INBOX_ID, es_admin, buscar_persona_por_wa, EQUIPO,
    )
    from .parser import parsear_mensaje
    from . import db
    from .scheduler import (
        notificar_tarea_creada, notificar_admin_completada,
        notificar_admin_bloqueada,
    )
    from .chatwoot_client import enviar_mensaje
except ImportError:
    from config import (
        CHATWOOT_INBOX_ID, es_admin, buscar_persona_por_wa, EQUIPO,
    )
    from parser import parsear_mensaje
    import db
    from scheduler import (
        notificar_tarea_creada, notificar_admin_completada,
        notificar_admin_bloqueada,
    )
    from chatwoot_client import enviar_mensaje

logger = logging.getLogger("task_manager.webhook")


def procesar_webhook(payload: dict, dry_run: bool = False) -> dict:
    """
    Procesa un evento webhook de Chatwoot.

    Args:
        payload: body del webhook de Chatwoot
        dry_run: si True, no envia mensajes ni modifica DB

    Returns:
        dict con resultado del procesamiento
    """
    event = payload.get("event")

    # Solo procesar mensajes nuevos entrantes
    if event != "message_created":
        return {"processed": False, "reason": f"Evento ignorado: {event}"}

    message = payload.get("content", "")
    message_type = payload.get("message_type")

    # Solo mensajes entrantes (del usuario, no nuestros)
    if message_type != "incoming":
        return {"processed": False, "reason": "No es incoming"}

    # Verificar que sea del inbox de WhatsApp
    inbox = payload.get("inbox", {})
    if inbox.get("id") != CHATWOOT_INBOX_ID:
        return {"processed": False, "reason": "No es inbox WA"}

    # Obtener datos del remitente
    sender = payload.get("sender", {})
    telefono = sender.get("phone_number", "")
    contact_id = sender.get("id")
    conversation = payload.get("conversation", {})
    conversation_id = conversation.get("id")

    if not message or not telefono:
        return {"processed": False, "reason": "Sin mensaje o telefono"}

    logger.info(f"Mensaje de {telefono}: {message[:80]}")

    # Parsear el mensaje
    parsed = parsear_mensaje(message, telefono)

    # Procesar segun tipo
    if parsed.tipo == "CREAR_TAREA":
        return _procesar_crear_tarea(parsed, telefono, contact_id,
                                     conversation_id, dry_run)
    elif parsed.tipo == "UPDATE_ESTADO":
        return _procesar_update_estado(parsed, telefono, contact_id,
                                       conversation_id, dry_run)
    elif parsed.tipo == "CONSULTA":
        return _procesar_consulta(parsed, telefono, contact_id,
                                  conversation_id, dry_run)
    else:
        return {
            "processed": False,
            "reason": "Mensaje no reconocido",
            "parsed_tipo": parsed.tipo,
            "confianza": parsed.confianza,
        }


def _procesar_crear_tarea(parsed, telefono, contact_id,
                          conversation_id, dry_run) -> dict:
    """Procesa la creacion de una tarea nueva."""
    # Solo admins pueden crear tareas
    if not es_admin(telefono):
        if not dry_run and contact_id:
            enviar_mensaje(
                contact_id,
                "Solo Fernando puede crear tareas por ahora.",
                conversation_id,
            )
        return {"processed": False, "reason": "No es admin"}

    datos = parsed.datos
    responsable = datos.get("responsable")

    if not responsable:
        if not dry_run and contact_id:
            nombre_buscado = datos.get("responsable_key", "?")
            enviar_mensaje(
                contact_id,
                f"No encontre a '{nombre_buscado}' en el equipo.",
                conversation_id,
            )
        return {"processed": False, "reason": "Responsable no encontrado"}

    if dry_run:
        logger.info(f"[DRY RUN] Crear tarea: {datos['titulo']} -> {responsable['nombre']}")
        return {
            "processed": True,
            "action": "CREAR_TAREA",
            "dry_run": True,
            "datos": {
                "titulo": datos["titulo"],
                "responsable": responsable["nombre"],
                "deadline": str(datos.get("deadline", "")),
            },
        }

    # INSERT en DB
    tarea_id = db.crear_tarea(
        titulo=datos["titulo"],
        responsable_nombre=responsable["nombre"],
        responsable_wa=responsable.get("wa"),
        responsable_chatwoot_id=responsable.get("chatwoot_id"),
        deadline=datos.get("deadline"),
        prioridad="P1",
        area=responsable.get("area"),
        canal_entrega=datos.get("canal_entrega"),
        resultado_esperado=datos.get("resultado_esperado"),
        mensaje_original=parsed.raw,
    )

    # Confirmar a Fernando
    if contact_id:
        enviar_mensaje(
            contact_id,
            f"\u2705 Tarea #{tarea_id} creada y asignada a {responsable['nombre']}.",
            conversation_id,
        )

    # Notificar al responsable
    notificar_tarea_creada(
        tarea_id=tarea_id,
        titulo=datos["titulo"],
        responsable=responsable,
        deadline=datos.get("deadline"),
        resultado_esperado=datos.get("resultado_esperado"),
        canal_entrega=datos.get("canal_entrega"),
        dry_run=False,
    )

    return {
        "processed": True,
        "action": "CREAR_TAREA",
        "tarea_id": tarea_id,
        "responsable": responsable["nombre"],
    }


def _procesar_update_estado(parsed, telefono, contact_id,
                            conversation_id, dry_run) -> dict:
    """Procesa un update de estado de una tarea."""
    # Buscar quien es el remitente
    persona = buscar_persona_por_wa(telefono)
    if not persona:
        logger.warning(f"Telefono no reconocido: {telefono}")
        return {"processed": False, "reason": "Remitente no reconocido"}

    nombre = persona["nombre"]

    # Buscar la tarea activa mas urgente de esta persona
    tarea = db.tarea_activa_de_persona(nombre)
    if not tarea:
        if not dry_run and contact_id:
            enviar_mensaje(
                contact_id,
                f"No encontre tareas activas tuyas. Si queres reportar algo, "
                f"avisale a Fernando.",
                conversation_id,
            )
        return {"processed": False, "reason": "Sin tarea activa"}

    datos = parsed.datos
    nuevo_estado = datos.get("nuevo_estado")
    notas = datos.get("notas") or datos.get("motivo")
    porcentaje = datos.get("porcentaje")

    if dry_run:
        logger.info(
            f"[DRY RUN] Update #{tarea['id']}: "
            f"{tarea['estado']} -> {nuevo_estado}"
        )
        return {
            "processed": True,
            "action": "UPDATE_ESTADO",
            "dry_run": True,
            "tarea_id": tarea["id"],
            "titulo": tarea["titulo"],
            "nuevo_estado": nuevo_estado,
        }

    # Actualizar en DB
    db.actualizar_estado(
        tarea_id=tarea["id"],
        nuevo_estado=nuevo_estado,
        notas=notas,
        porcentaje=porcentaje,
        motivo_bloqueo=datos.get("motivo") if nuevo_estado == "BLOQUEADA" else None,
        autor=nombre,
    )

    # Confirmar al remitente
    if contact_id:
        if nuevo_estado == "COMPLETA":
            enviar_mensaje(
                contact_id,
                f"\u2705 Perfecto! Tarea '{tarea['titulo']}' marcada como completada.",
                conversation_id,
            )
            # Notificar a Fernando
            notificar_admin_completada(
                tarea["id"], tarea["titulo"], nombre, dry_run=False
            )
        elif nuevo_estado == "EN_PROGRESO":
            msg = f"\U0001f44d Registrado: '{tarea['titulo']}'"
            if porcentaje:
                msg += f" al {porcentaje}%"
            enviar_mensaje(contact_id, msg, conversation_id)
        elif nuevo_estado == "BLOQUEADA":
            enviar_mensaje(
                contact_id,
                f"\U0001f6a7 Registrado: '{tarea['titulo']}' bloqueada. "
                f"Fernando va a ser notificado.",
                conversation_id,
            )
            # Notificar a Fernando
            notificar_admin_bloqueada(
                tarea["id"], tarea["titulo"], nombre,
                notas or "Sin detalle",
                dry_run=False,
            )

    return {
        "processed": True,
        "action": "UPDATE_ESTADO",
        "tarea_id": tarea["id"],
        "titulo": tarea["titulo"],
        "nuevo_estado": nuevo_estado,
    }


def _procesar_consulta(parsed, telefono, contact_id,
                       conversation_id, dry_run) -> dict:
    """Procesa una consulta de estado."""
    datos = parsed.datos
    subtipo = datos.get("subtipo", "PENDIENTES")

    if subtipo == "MIS_TAREAS":
        persona = buscar_persona_por_wa(telefono)
        if not persona:
            return {"processed": False, "reason": "Remitente no reconocido"}
        nombre = persona["nombre"]
        tareas = db.tareas_persona(nombre, solo_activas=True)
        mensaje = _formatear_lista_tareas(nombre, tareas)

    elif subtipo == "PERSONA":
        persona = datos.get("persona")
        if not persona:
            nombre_buscado = datos.get("persona_key", "?")
            mensaje = f"No encontre a '{nombre_buscado}' en el equipo."
        else:
            nombre = persona["nombre"]
            tareas = db.tareas_persona(nombre, solo_activas=True)
            mensaje = _formatear_lista_tareas(nombre, tareas)

    elif subtipo == "VENCIDAS":
        vencidas = db.tareas_vencidas()
        if not vencidas:
            mensaje = "\u2705 No hay tareas vencidas."
        else:
            lineas = [f"\u26a0\ufe0f {len(vencidas)} tareas vencidas:", ""]
            for t in vencidas:
                emoji = "\U0001f534"
                lineas.append(
                    f"{emoji} *{t['titulo']}* ({t['responsable']})\n"
                    f"   Vencio: {t['deadline']}"
                )
            mensaje = "\n".join(lineas)

    elif subtipo == "RESUMEN":
        resumen = db.resumen_semana()
        totales = resumen["totales"]
        pct = round(totales["completas"] / max(totales["total"], 1) * 100)
        lineas = [
            f"\U0001f4ca Resumen semana {resumen['semana']}",
            f"",
            f"Total: {totales['total']} tareas",
            f"Completadas: {totales['completas']} ({pct}%)",
            f"Pendientes: {totales['pendientes']}",
            f"Bloqueadas: {totales['bloqueadas']}",
        ]
        mensaje = "\n".join(lineas)

    else:  # PENDIENTES
        pendientes = db.tareas_pendientes()
        if not pendientes:
            mensaje = "\u2705 No hay tareas pendientes."
        else:
            lineas = [f"\U0001f4cb {len(pendientes)} tareas pendientes:", ""]
            por_persona = {}
            for t in pendientes:
                resp = t["responsable"]
                if resp not in por_persona:
                    por_persona[resp] = []
                por_persona[resp].append(t)

            for resp, tareas_resp in sorted(por_persona.items()):
                lineas.append(f"*{resp}*:")
                for t in tareas_resp:
                    emoji = _estado_emoji(t["estado"])
                    lineas.append(f"  {emoji} {t['titulo']} ({t['prioridad']})")
                lineas.append("")

            mensaje = "\n".join(lineas)

    if dry_run:
        logger.info(f"[DRY RUN] Consulta respuesta:\n{mensaje}")
    else:
        if contact_id:
            enviar_mensaje(contact_id, mensaje, conversation_id)

    return {
        "processed": True,
        "action": "CONSULTA",
        "subtipo": subtipo,
        "mensaje": mensaje,
    }


def _formatear_lista_tareas(nombre: str, tareas: list) -> str:
    """Formatea una lista de tareas para mostrar."""
    if not tareas:
        return f"No hay tareas activas para {nombre}."

    lineas = [f"\U0001f4cb Tareas de *{nombre}*:", ""]
    for i, t in enumerate(tareas, 1):
        emoji = _estado_emoji(t["estado"])
        deadline = t.get("deadline", "")
        if deadline:
            deadline = f" - {deadline}"
        lineas.append(f"{i}. {emoji} *{t['titulo']}* [{t['prioridad']}]{deadline}")
        if t.get("estado") == "BLOQUEADA" and t.get("motivo_bloqueo"):
            lineas.append(f"   \U0001f6a7 {t['motivo_bloqueo'][:60]}")

    return "\n".join(lineas)


def _estado_emoji(estado: str) -> str:
    return {
        "ASIGNADA": "\u23f3",
        "EN_PROGRESO": "\U0001f3c3",
        "BLOQUEADA": "\U0001f6a7",
        "COMPLETA": "\u2705",
        "CANCELADA": "\u274c",
    }.get(estado, "\u2753")
