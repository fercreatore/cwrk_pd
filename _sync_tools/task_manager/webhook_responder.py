# -*- coding: utf-8 -*-
"""
Webhook Responder — Bot que responde tareas cuando alguien escribe por WhatsApp
Para el Task Manager de H4/Calzalindo

Recibe webhook de Meta (via n8n o directo) y responde con las tareas de la persona.

Uso como API standalone:
    python3 webhook_responder.py  # Levanta en :5051

Uso como modulo desde n8n:
    POST http://localhost:5051/webhook
    Body: {"from": "5493462672330", "message": "tareas"}
"""
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# Agregar path para imports
sys.path.insert(0, os.path.dirname(__file__))
from task_notifier import leer_agenda, extraer_tareas_persona, CONTACTOS
from meta_whatsapp import enviar_texto

# Mapa inverso: telefono → nombre
TEL_A_NOMBRE = {v: k for k, v in CONTACTOS.items() if v}

# Comandos que el bot entiende
COMANDOS = {
    "tareas": "Muestra tus tareas pendientes",
    "hoy": "Muestra solo las urgentes (P0)",
    "ok": "Confirma que viste el mensaje",
    "listo": "Marca que terminaste (Fernando actualiza)",
    "bloq": "Reporta que estas bloqueado",
    "ayuda": "Muestra esta lista de comandos",
}


def procesar_mensaje(telefono, mensaje):
    """Procesa un mensaje entrante y genera respuesta."""
    telefono = telefono.replace("+", "")
    nombre = TEL_A_NOMBRE.get(telefono)
    mensaje_lower = mensaje.strip().lower()

    if not nombre:
        return f"Hola! No te tengo registrado. Pedile a Fernando que te agregue al sistema."

    if mensaje_lower in ("ayuda", "help", "?", "comandos"):
        lineas = [f"Hola {nombre}! Comandos disponibles:\n"]
        for cmd, desc in COMANDOS.items():
            lineas.append(f"  *{cmd}* — {desc}")
        return "\n".join(lineas)

    if mensaje_lower in ("ok", "dale", "si", "listo", "recibido"):
        return f"Perfecto {nombre}, registrado."

    if mensaje_lower.startswith("bloq"):
        motivo = mensaje[4:].strip() or "(sin detalle)"
        # Notificar a Fernando
        enviar_texto(CONTACTOS["Fernando"],
                     f"⚠️ {nombre} reporta BLOQUEADO: {motivo}")
        return f"Listo {nombre}, le avise a Fernando que estas bloqueado."

    if mensaje_lower in ("tareas", "mis tareas", "que tengo", "pendientes", "hola"):
        contenido = leer_agenda()
        tareas = extraer_tareas_persona(contenido, nombre)

        if not tareas:
            return f"Hola {nombre}! No tenes tareas asignadas por ahora."

        pendientes = [t for t in tareas if "[x]" not in t["estado"]]
        if not pendientes:
            return f"Hola {nombre}! Todas tus tareas estan completadas. Bien ahi!"

        lineas = [f"Hola {nombre}! Tus tareas pendientes:\n"]
        for t in pendientes:
            emoji = "🔴" if t["prioridad"] == "P0" else "🟡" if t["prioridad"] == "P1" else "🟢"
            lineas.append(f"{emoji} *{t['tarea']}*")
            lineas.append(f"   Deadline: {t['deadline']}")
            lineas.append(f"   Entregar: {t['entregable']}\n")

        lineas.append("Responde *ok* cuando lo veas, *bloq* si estas trabado.")
        return "\n".join(lineas)

    if mensaje_lower in ("hoy", "urgente", "p0"):
        contenido = leer_agenda()
        tareas = extraer_tareas_persona(contenido, nombre)
        urgentes = [t for t in tareas if t["prioridad"] == "P0" and "[x]" not in t["estado"]]
        if not urgentes:
            return f"{nombre}, no tenes nada P0 urgente hoy."
        lineas = [f"🔴 URGENTE para hoy:\n"]
        for t in urgentes:
            lineas.append(f"  {t['tarea']} — {t['entregable']}")
        return "\n".join(lineas)

    # Default: mostrar tareas
    return procesar_mensaje(telefono, "tareas")


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler para recibir webhooks."""

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400, {"error": "JSON invalido"})
            return

        # Formato simplificado (desde n8n)
        telefono = data.get("from", "")
        mensaje = data.get("message", "")

        # Formato Meta webhook nativo
        if not telefono and "entry" in data:
            try:
                changes = data["entry"][0]["changes"][0]["value"]
                msg = changes["messages"][0]
                telefono = msg["from"]
                mensaje = msg.get("text", {}).get("body", "")
            except (KeyError, IndexError):
                self._respond(200, {"status": "ignored"})
                return

        if not telefono or not mensaje:
            self._respond(400, {"error": "Falta 'from' o 'message'"})
            return

        # Procesar y responder
        respuesta = procesar_mensaje(telefono, mensaje)
        resultado = enviar_texto(telefono, respuesta)

        self._respond(200, {
            "status": "ok",
            "to": telefono,
            "response": respuesta[:100] + "...",
            "meta_result": resultado
        })

    def do_GET(self):
        # Verificacion webhook Meta
        if self.path.startswith("/webhook"):
            from urllib.parse import urlparse, parse_qs
            params = parse_qs(urlparse(self.path).query)
            challenge = params.get("hub.challenge", [""])[0]
            self._respond(200, challenge, raw=True)
            return
        self._respond(200, {"status": "task_manager_bot", "commands": list(COMANDOS.keys())})

    def _respond(self, code, data, raw=False):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain" if raw else "application/json")
        self.end_headers()
        if raw:
            self.wfile.write(str(data).encode())
        else:
            self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        print(f"[BOT] {args[0]}" if args else "")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5051
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    print(f"Task Manager Bot escuchando en :{port}")
    print(f"Webhook: POST http://localhost:{port}/webhook")
    print(f"Verificacion Meta: GET http://localhost:{port}/webhook?hub.challenge=xxx")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBot detenido.")


if __name__ == "__main__":
    main()
