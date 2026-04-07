#!/usr/bin/env python3
"""
Webhook Responder — Auto-respuestas WhatsApp Outlet Calzalindo
Escucha webhooks de Chatwoot y responde automáticamente.

Corre como servicio en Linux (systemd) o Windows (nssm).
Puerto: 5055

Uso:
  python3 webhook_responder.py                # Producción
  python3 webhook_responder.py --test         # Test mode (no envía, solo logea)
  python3 webhook_responder.py --port 8080    # Puerto custom

Systemd:
  [Unit]
  Description=Calzalindo WhatsApp Webhook Responder
  After=network.target
  [Service]
  ExecStart=/usr/bin/python3 /opt/calzalindo/valijas/webhook_responder.py
  Restart=always
  RestartSec=5
  [Install]
  WantedBy=multi-user.target
"""
import json
import os
import sys
import ssl
import re
import urllib.request
import urllib.error
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# =============================================================================
# CONFIG
# =============================================================================
PORT = 5055
CHATWOOT_URL = "https://chat.calzalindo.com.ar"
CHATWOOT_TOKEN = "zvQpseDYDoeqJpwM41GCb1LP"
ACCOUNT_ID = 3
INBOX_ID = 10  # Calzalindo 1170 (campañas)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPTOUT_FILE = os.path.join(SCRIPT_DIR, "optout_list.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "log_webhook_responder.json")
FLYER_PATH = os.path.join(SCRIPT_DIR, "imagenes", "flyer_outlet_abril.jpg")

TEST_MODE = False

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# =============================================================================
# RESPUESTAS
# =============================================================================
RESPUESTA_OUTLET_AVISAME = (
    "Listo! Te aviso el 9 de abril que arranca. "
    "Guarda plata porque va a haber precios increibles 🔥\n\n"
    "📍 Av. Santa Fe 1246, Venado Tuerto\n"
    "🕐 10:00 a 21:00 hs\n"
    "📅 Del 9 al 12 de abril (solo 4 dias!)\n"
    "Sector Pague Lo Que Quiera + Ventas por mayor"
)

RESPUESTA_OUTLET_QUE_HAY = (
    "LIQUIDAMOS TODO! 🔥\n\n"
    "Hombre - Mujer - Niños\n"
    "Desde $4.999\n"
    "Sector Pague Lo Que Quiera!\n"
    "Ventas por mayor tambien.\n\n"
    "📅 Solo 4 dias: del 9 al 12 de abril\n"
    "📍 Av. Santa Fe 1246, Venado Tuerto\n"
    "🕐 De 10:00 a 21:00 hs\n\n"
    "No te lo pierdas!"
)

RESPUESTA_OPTOUT = (
    "Listo! Te dimos de baja de nuestros mensajes. No vas a recibir mas "
    "comunicaciones. Si cambias de idea, escribinos cuando quieras. "
    "Gracias y disculpa las molestias!"
)

RESPUESTA_UBICACION = (
    "📍 Estamos en Av. Santa Fe 1246, Venado Tuerto, Santa Fe.\n"
    "De 10:00 a 21:00 hs del 9 al 12 de abril.\n"
    "Te esperamos!"
)

RESPUESTA_HORARIO = (
    "🕐 Del 9 al 12 de abril, de 10:00 a 21:00 hs.\n"
    "📍 Av. Santa Fe 1246, Venado Tuerto.\n"
    "4 dias nada mas!"
)

RESPUESTA_PAGO = (
    "Aceptamos efectivo, debito y credito.\n"
    "Hay un sector de Pague Lo Que Quiera!\n"
    "Y tambien ventas por mayor."
)

RESPUESTA_GRACIAS = (
    "De nada! 😊 Te esperamos del 9 al 12 de abril.\n"
    "📍 Av. Santa Fe 1246, Venado Tuerto\n"
    "🕐 10:00 a 21:00 hs"
)

RESPUESTA_SALUDO = (
    "Hola! 😊 Que bueno saber de vos! Te esperamos en nuestro outlet "
    "del 9 al 12 de abril. Liquidamos todo desde $4.999!\n\n"
    "📍 Av. Santa Fe 1246, Venado Tuerto\n"
    "🕐 10:00 a 21:00 hs\n"
    "Sector Pague Lo Que Quiera!"
)

RESPUESTA_POSITIVA = (
    "Que bueno! Te esperamos del 9 al 12 de abril.\n"
    "📍 Av. Santa Fe 1246, Venado Tuerto\n"
    "🕐 10:00 a 21:00 hs\n"
    "Veni tranquilo/a que hay de todo!"
)

KEYWORDS_OPTOUT = [
    "no me manden mas", "no me manden más", "baja", "stop",
    "no quiero", "dejen de mandar", "no molestar", "no me escriban",
    "sacar de la lista", "desuscribir",
]

# =============================================================================
# HELPERS
# =============================================================================
def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_action(action, conv_id=None, detail=""):
    entry = {"timestamp": ts(), "action": action, "conv_id": conv_id, "detail": detail[:200]}
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except:
            logs = []
    logs.append(entry)
    if len(logs) > 10000:
        logs = logs[-10000:]
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def normalize(text):
    t = text.lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ü","u"),("ñ","n")]:
        t = t.replace(a, b)
    return t

def load_optouts():
    if os.path.exists(OPTOUT_FILE):
        try:
            with open(OPTOUT_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []

def save_optout(telefono, nombre="", motivo=""):
    tel = telefono.lstrip("+").strip()
    optouts = load_optouts()
    for e in optouts:
        if e.get("telefono","").lstrip("+").strip() == tel:
            return
    optouts.append({"telefono": tel, "nombre": nombre, "motivo": motivo, "origen": "webhook", "fecha_baja": ts()})
    with open(OPTOUT_FILE, "w") as f:
        json.dump(optouts, f, ensure_ascii=False, indent=2)

def is_optout(telefono):
    tel = telefono.lstrip("+").strip()
    for e in load_optouts():
        et = e.get("telefono","").lstrip("+").strip()
        if et == tel or (len(tel) >= 8 and len(et) >= 8 and tel[-8:] == et[-8:]):
            return True
    return False

def send_message(conv_id, content):
    url = f"{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{conv_id}/messages"
    data = json.dumps({"content": content, "message_type": "outgoing", "private": False}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("api_access_token", CHATWOOT_TOKEN)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
        return json.loads(resp.read().decode())

def send_message_with_flyer(conv_id, content):
    if not os.path.exists(FLYER_PATH):
        return send_message(conv_id, content)
    cmd = ['curl', '-sk', '-X', 'POST',
           '-H', f'api_access_token: {CHATWOOT_TOKEN}',
           '-F', f'content={content}',
           '-F', 'message_type=outgoing',
           '-F', 'private=false',
           '-F', f'attachments[]=@{FLYER_PATH};type=image/jpeg',
           f'{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{conv_id}/messages']
    subprocess.run(cmd, capture_output=True, timeout=30)

# =============================================================================
# CLASSIFY MESSAGE
# =============================================================================
def classify(text):
    t = normalize(text)

    # Opt-out (prioridad absoluta)
    if any(kw in t for kw in KEYWORDS_OPTOUT):
        return "OPTOUT"

    # Botones del template
    if "avisame cuando arranque" in t or ("avisame" in t and len(t) < 30):
        return "OUTLET_AVISAME"
    if "que va a haber" in t or "que hay" in t or "que van a tener" in t:
        return "OUTLET_QUE_HAY"

    # Ubicación
    if any(kw in t for kw in ["donde queda", "direccion", "ubicacion", "como llego", "donde es", "donde estan"]):
        return "UBICACION"

    # Horario
    if any(kw in t for kw in ["horario", "hora", "a que hora", "cuando abre", "cuando es"]):
        return "HORARIO"

    # Pago
    if any(kw in t for kw in ["tarjeta", "cuotas", "pago", "efectivo", "debito", "credito", "transferencia"]):
        return "PAGO"

    # Positivo (viene, va a ir, genial, etc)
    if any(kw in t for kw in ["voy", "vamos", "ahi estare", "ahi voy", "nos vemos", "genial", "buenisimo", "excelente", "dale"]):
        return "POSITIVA"

    # Agradecimiento
    if any(kw in t for kw in ["gracias", "gracia", "bendicion"]) and len(t) < 50:
        return "GRACIAS"

    # Saludo simple
    if any(kw in t for kw in ["hola", "buen dia", "buenas", "buenos dias"]) and len(t) < 30:
        return "SALUDO"

    # Emoji positivo solo
    if all(c in "👍🙌❤️💖😊😄🔥✅👏💪🎉" or not c.isalpha() for c in text) and len(text.strip()) <= 10:
        return "POSITIVA"

    # No matchea → dejar para humano
    return None

# =============================================================================
# WEBHOOK HANDLER
# =============================================================================
class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')

        try:
            data = json.loads(body.decode('utf-8'))
            self.process_webhook(data)
        except Exception as e:
            print(f"[{ts()}] ERROR procesando webhook: {e}")
            log_action("error", detail=str(e))

    def process_webhook(self, data):
        event = data.get("event")
        if event != "message_created":
            return

        message = data.get("content", "") or ""
        msg_type = data.get("message_type")
        inbox = data.get("inbox", {})
        inbox_id = inbox.get("id")
        conv = data.get("conversation", {})
        conv_id = conv.get("id") if isinstance(conv, dict) else None
        sender = data.get("sender", {})
        sender_type = sender.get("type", "")
        sender_name = sender.get("name", "")
        sender_phone = data.get("conversation", {}).get("contact", {}).get("phone_number", "") if isinstance(data.get("conversation"), dict) else ""

        # Solo inbox 10 (campañas)
        if inbox_id != INBOX_ID:
            return

        # Solo mensajes incoming (del cliente)
        if msg_type != "incoming":
            return

        # Skip si es opt-out
        if sender_phone and is_optout(sender_phone):
            return

        if not message or not conv_id:
            return

        print(f"[{ts()}] Conv {conv_id}: {sender_name} -> [{message[:80]}]")

        classification = classify(message)

        if classification is None:
            print(f"[{ts()}]   -> No matchea, dejando para humano")
            log_action("skip", conv_id, f"{sender_name}: {message[:100]}")
            return

        if TEST_MODE:
            print(f"[{ts()}]   -> TEST MODE: clasificado como {classification}")
            return

        try:
            if classification == "OPTOUT":
                save_optout(sender_phone, sender_name, f"keyword: {message[:100]}")
                send_message(conv_id, RESPUESTA_OPTOUT)
                print(f"[{ts()}]   -> OPT-OUT registrado: {sender_phone}")
                log_action("optout", conv_id, sender_phone)

            elif classification == "OUTLET_AVISAME":
                send_message_with_flyer(conv_id, RESPUESTA_OUTLET_AVISAME)
                print(f"[{ts()}]   -> AVISAME + flyer")
                log_action("responded_avisame", conv_id)

            elif classification == "OUTLET_QUE_HAY":
                send_message_with_flyer(conv_id, RESPUESTA_OUTLET_QUE_HAY)
                print(f"[{ts()}]   -> QUE HAY + flyer")
                log_action("responded_que_hay", conv_id)

            elif classification == "UBICACION":
                send_message(conv_id, RESPUESTA_UBICACION)
                print(f"[{ts()}]   -> UBICACION")
                log_action("responded_ubicacion", conv_id)

            elif classification == "HORARIO":
                send_message(conv_id, RESPUESTA_HORARIO)
                print(f"[{ts()}]   -> HORARIO")
                log_action("responded_horario", conv_id)

            elif classification == "PAGO":
                send_message(conv_id, RESPUESTA_PAGO)
                print(f"[{ts()}]   -> PAGO")
                log_action("responded_pago", conv_id)

            elif classification == "GRACIAS":
                send_message(conv_id, RESPUESTA_GRACIAS)
                print(f"[{ts()}]   -> GRACIAS")
                log_action("responded_gracias", conv_id)

            elif classification == "SALUDO":
                send_message(conv_id, RESPUESTA_SALUDO)
                print(f"[{ts()}]   -> SALUDO")
                log_action("responded_saludo", conv_id)

            elif classification == "POSITIVA":
                send_message(conv_id, RESPUESTA_POSITIVA)
                print(f"[{ts()}]   -> POSITIVA")
                log_action("responded_positiva", conv_id)

        except Exception as e:
            print(f"[{ts()}]   -> ERROR respondiendo: {e}")
            log_action("error_respond", conv_id, str(e))

    def log_message(self, format, *args):
        pass  # Silenciar logs HTTP estándar

# =============================================================================
# MAIN
# =============================================================================
def main():
    global TEST_MODE, PORT

    if "--test" in sys.argv:
        TEST_MODE = True
        print(f"[{ts()}] MODO TEST activado")

    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        PORT = int(sys.argv[idx + 1])

    print(f"[{ts()}] Webhook Responder Calzalindo")
    print(f"[{ts()}] Puerto: {PORT}")
    print(f"[{ts()}] Inbox: {INBOX_ID} (Calzalindo 1170)")
    print(f"[{ts()}] Flyer: {'OK' if os.path.exists(FLYER_PATH) else 'NO ENCONTRADO'}")
    print(f"[{ts()}] Opt-outs: {len(load_optouts())}")
    print(f"[{ts()}] Esperando webhooks...")

    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Apagando...")
        server.shutdown()

if __name__ == "__main__":
    main()
