# -*- coding: utf-8 -*-
"""
Cliente Chatwoot para enviar mensajes WhatsApp.

Usa la API de Chatwoot (chat.calzalindo.com.ar) para enviar mensajes
a contactos del equipo via WhatsApp Cloud API (inbox 9).
"""

import json
import logging
import ssl
import urllib.request
import urllib.error
from typing import Optional

try:
    from .config import (
        CHATWOOT_URL, CHATWOOT_TOKEN, CHATWOOT_ACCOUNT, CHATWOOT_INBOX_ID,
    )
except ImportError:
    from config import (
        CHATWOOT_URL, CHATWOOT_TOKEN, CHATWOOT_ACCOUNT, CHATWOOT_INBOX_ID,
    )

logger = logging.getLogger("task_manager.chatwoot")

# SSL para macOS
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE


def _api_request(method: str, path: str, data: dict = None) -> dict:
    """Hace un request a la API de Chatwoot."""
    url = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT}{path}"

    body = None
    if data:
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "api_access_token": CHATWOOT_TOKEN,
            "Content-Type": "application/json",
        },
        method=method,
    )

    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        logger.error(f"Chatwoot API error {e.code}: {error_body[:300]}")
        raise
    except Exception as e:
        logger.error(f"Chatwoot API error: {e}")
        raise


def buscar_contacto(telefono: str) -> Optional[dict]:
    """
    Busca un contacto en Chatwoot por telefono.

    Args:
        telefono: formato +5493462XXXXXX

    Returns:
        dict con datos del contacto o None
    """
    try:
        result = _api_request("GET", f"/contacts/search?q={telefono}&page=1")
        payload = result.get("payload", [])
        if payload:
            return payload[0]
        return None
    except Exception:
        logger.exception(f"Error buscando contacto {telefono}")
        return None


def crear_contacto(nombre: str, telefono: str) -> Optional[dict]:
    """
    Crea un contacto en Chatwoot.

    Args:
        nombre: nombre del contacto
        telefono: formato +5493462XXXXXX

    Returns:
        dict del contacto creado
    """
    try:
        data = {
            "name": nombre,
            "phone_number": telefono,
            "inbox_id": CHATWOOT_INBOX_ID,
        }
        result = _api_request("POST", "/contacts", data)
        return result.get("payload", {}).get("contact", result)
    except Exception:
        logger.exception(f"Error creando contacto {nombre}")
        return None


def obtener_o_crear_contacto(nombre: str, telefono: str) -> Optional[dict]:
    """Busca un contacto o lo crea si no existe."""
    contacto = buscar_contacto(telefono)
    if contacto:
        return contacto
    return crear_contacto(nombre, telefono)


def buscar_conversacion_abierta(contact_id: int) -> Optional[dict]:
    """
    Busca una conversacion abierta con un contacto en el inbox de WA.

    Returns:
        dict de la conversacion o None
    """
    try:
        result = _api_request(
            "GET",
            f"/contacts/{contact_id}/conversations"
        )
        payload = result.get("payload", [])
        for conv in payload:
            if (conv.get("inbox_id") == CHATWOOT_INBOX_ID
                    and conv.get("status") == "open"):
                return conv
        # Si no hay abierta, usar la mas reciente del inbox correcto
        for conv in payload:
            if conv.get("inbox_id") == CHATWOOT_INBOX_ID:
                return conv
        return None
    except Exception:
        logger.exception(f"Error buscando conversacion para contact {contact_id}")
        return None


def crear_conversacion(contact_id: int) -> Optional[dict]:
    """Crea una conversacion nueva con un contacto."""
    try:
        data = {
            "contact_id": contact_id,
            "inbox_id": CHATWOOT_INBOX_ID,
            "status": "open",
        }
        return _api_request("POST", "/conversations", data)
    except Exception:
        logger.exception(f"Error creando conversacion para contact {contact_id}")
        return None


def enviar_mensaje(contact_id: int, texto: str,
                   conversation_id: int = None) -> dict:
    """
    Envia un mensaje a un contacto via Chatwoot.

    Si no se provee conversation_id, busca una conversacion abierta
    o crea una nueva.

    Args:
        contact_id: ID del contacto en Chatwoot
        texto: mensaje a enviar
        conversation_id: ID de conversacion (opcional)

    Returns:
        dict con resultado del envio
    """
    # Obtener o crear conversacion
    if not conversation_id:
        conv = buscar_conversacion_abierta(contact_id)
        if not conv:
            conv = crear_conversacion(contact_id)
        if conv:
            conversation_id = conv.get("id")
        else:
            return {"ok": False, "error": "No se pudo crear conversacion"}

    # Enviar mensaje
    try:
        data = {
            "content": texto,
            "message_type": "outgoing",
            "private": False,
        }
        result = _api_request(
            "POST",
            f"/conversations/{conversation_id}/messages",
            data
        )
        return {"ok": True, "message_id": result.get("id"), "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def enviar_mensaje_a_telefono(nombre: str, telefono: str, texto: str) -> dict:
    """
    Envia un mensaje a un numero de telefono.

    Busca o crea el contacto, busca o crea la conversacion,
    y envia el mensaje.

    Args:
        nombre: nombre del contacto
        telefono: formato +5493462XXXXXX
        texto: mensaje a enviar

    Returns:
        dict con resultado
    """
    contacto = obtener_o_crear_contacto(nombre, telefono)
    if not contacto:
        return {"ok": False, "error": f"No se pudo encontrar/crear contacto {telefono}"}

    contact_id = contacto.get("id")
    return enviar_mensaje(contact_id, texto)
