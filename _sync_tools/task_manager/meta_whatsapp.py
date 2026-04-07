# -*- coding: utf-8 -*-
"""
Modulo de envio WhatsApp via Meta Cloud API
Para el Task Manager de H4/Calzalindo

Usa texto libre dentro de ventana 24hs (gratis).
Usa template utility fuera de ventana ($0.02/msg).
"""
import json
import urllib.request
import urllib.error
import ssl
import os

# Fix SSL para Mac (certifi no siempre esta configurado)
_ssl_ctx = ssl._create_unverified_context()

# Config Meta — Phone ID principal (CALZALINDO 7436)
PHONE_ID = os.environ.get("META_PHONE_ID", "1046697335188691")
META_TOKEN = os.environ.get("META_TOKEN", "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40uQLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD")
API_VERSION = "v21.0"
API_URL = f"https://graph.facebook.com/{API_VERSION}/{PHONE_ID}/messages"


def enviar_texto(telefono, mensaje):
    """
    Envia mensaje de texto libre (gratis dentro de ventana 24hs).
    telefono: con codigo pais, ej "5493462672330"
    """
    telefono = _limpiar_telefono(telefono)
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": mensaje}
    }
    return _enviar(payload)


def enviar_template(telefono, template_name, parametros=None, language="es_AR"):
    """
    Envia template (fuera de ventana 24hs, ~$0.02 USD).
    parametros: lista de strings, ej ["Fernando", "3 tareas pendientes"]
    """
    telefono = _limpiar_telefono(telefono)
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
        }
    }
    if parametros:
        payload["template"]["components"] = [{
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in parametros]
        }]
    return _enviar(payload)


def _limpiar_telefono(tel):
    """Limpia telefono: quita +, espacios, guiones."""
    tel = str(tel).strip().replace("+", "").replace(" ", "").replace("-", "")
    if not tel.startswith("54"):
        tel = "54" + tel
    return tel


def _enviar(payload):
    """POST a Meta Graph API."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {META_TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=_ssl_ctx) as resp:
            result = json.loads(resp.read().decode())
            return {"ok": True, "data": result}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return {"ok": False, "status": e.code, "error": error_body}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# === Test rapido ===
if __name__ == "__main__":
    import sys
    tel = sys.argv[1] if len(sys.argv) > 1 else "5493462672330"
    msg = sys.argv[2] if len(sys.argv) > 2 else "Test desde task_manager"
    print(f"Enviando a {tel}: {msg}")
    r = enviar_texto(tel, msg)
    print(json.dumps(r, indent=2))
