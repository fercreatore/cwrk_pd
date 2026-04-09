#!/usr/bin/env python3
"""
responder_agencias.py - Auto-responder Chatwoot para consultas de valijas GO
Monitorea inbox WhatsApp y responde automaticamente a consultas de agencias.

Uso:
    python3 responder_agencias.py           # Polling continuo cada 30s
    python3 responder_agencias.py --once    # Una sola ejecucion y sale
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
CHATWOOT_URL = "https://chat.calzalindo.com.ar"
API_TOKEN = "zvQpseDYDoeqJpwM41GCb1LP"
ACCOUNT_ID = 3
INBOX_ID = 10  # Calzalindo 1170 (campaña valijas)
POLL_INTERVAL = 30  # segundos

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESPONDED_FILE = os.path.join(SCRIPT_DIR, "responded_conversations.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "log_responder.json")
OPTOUT_FILE = os.path.join(SCRIPT_DIR, "optout_list.json")

# SSL context sin verificacion (Mac + certs internos)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# Respuestas
# ---------------------------------------------------------------------------
RESPUESTA_INTERES_INICIAL = (
    "Genial! Te cuento las dos opciones que tenemos para agencias:\n\n"
    "*OPCION A - COMISION POR VENTA*\n"
    "Tus pasajeros compran en calzalindo.com.ar con un codigo de descuento "
    "exclusivo para tu agencia. Por cada set vendido te transferimos $20.000 "
    "de comision. Nosotros nos encargamos del envio gratis a todo el pais. "
    "Vos solo recomendas y cobras.\n\n"
    "*OPCION B - PRECIO MAYORISTA*\n"
    "Compras los sets a $100.000 c/u y los revendes al precio que quieras "
    "(sugerido $162.499). Te queda un margen de $62.499 por set. Minimo 5 "
    "sets. Envio incluido a tu deposito.\n\n"
    "Los sets son 3 valijas rigidas marca GO (18\"+19\"+21\"), ABS, 8 ruedas "
    "360 grados. 4 colores: Negro, Rojo, Rosa y Rosa Gold.\n"
    "Precio publico: $162.499 o $129.999 con transferencia.\n"
    "Envio gratis a todo el pais.\n\n"
    "Cual te interesa mas? Te puedo mandar fotos del producto."
)

RESPUESTA_FOTOS = (
    "Te mando las fotos por aca! Tenemos 4 colores:\n\n"
    "Negro: https://calzalindo.com.ar/productos/set-de-valijas-rigidas-x3-go-negro/\n"
    "Rojo: https://calzalindo.com.ar/productos/set-de-valijas-rigidas-x3-go-rojo/\n"
    "Rosa: https://calzalindo.com.ar/productos/set-de-valijas-rigidas-x3-go-rosa-rtfv3/\n"
    "Rosa Gold: https://calzalindo.com.ar/productos/set-de-valijas-rigidas-x3-go-rosa-gold/\n\n"
    "Cual color te interesa?"
)

RESPUESTA_COLORES = (
    "Tenemos 4 colores: Negro, Rojo, Rosa y Rosa Gold. Todos disponibles. "
    "Cual te gusta mas?"
)

RESPUESTA_MEDIDAS = (
    "Cada set incluye 3 valijas: 18 pulgadas (carry on), 19 pulgadas "
    "(cabina) y 21 pulgadas (mediana). Todas rigidas ABS con 8 ruedas "
    "360 grados."
)

RESPUESTA_COMISION = (
    "Perfecto! Con la Opcion A, por cada set que tus pasajeros compren "
    "con tu codigo de descuento, te transferimos $20.000. Sin limite. "
    "Nosotros nos encargamos del envio y la atencion. Vos solo recomendas. "
    "Para activar tu codigo, hablemos con Fernando: wa.me/5493462672330"
)

RESPUESTA_MAYORISTA = (
    "Genial! Con la Opcion B compras los sets a $100.000 c/u (minimo 5 "
    "sets) y los revendes al precio que quieras. Te queda un margen de "
    "hasta $62.499 por set. Envio incluido a tu deposito. Para coordinar, "
    "hablemos con Fernando: wa.me/5493462672330"
)

RESPUESTA_GARANTIA = (
    "Todos nuestros sets tienen 6 meses de garantia. Si hay algun defecto "
    "de fabrica, lo reemplazamos sin costo."
)

RESPUESTA_NO_GRACIAS = (
    "Entendido! Si en algun momento te interesa, escribinos. Gracias por "
    "tu tiempo!"
)

RESPUESTA_OPTOUT = (
    "Mil disculpas por la molestia! 🙏 Ya te dimos de baja, "
    "no vas a recibir mas mensajes nuestros. "
    "Perdon por la incomodidad y gracias por tu paciencia."
)

KEYWORDS_OPTOUT = [
    "no me manden mas", "no me manden más",
    "dame de baja", "darme de baja", "darse de baja",
    "no quiero recibir", "dejen de mandar",
    "no molestar", "no me escriban mas",
    "sacar de la lista", "desuscribir",
    "quitadme", "quitame de la lista", "quitar de la lista",
    "sacame de la lista", "borrame de la lista",
    "no me envien", "no me manden",
    "esto es spam", "los voy a bloquear", "los voy a denunciar",
    "dejen de mandarme",
]
# NOTA: NO usar palabras cortas como "baja" (matchea "trabajando"),
# "no gracias" (matchea "bueno gracias"), "stop", "borrar", "eliminar"
# Solo frases completas e inequívocas de baja.

# Respuesta para número equivocado (más empática que opt-out genérico)
# RRHH — Maite
MAITE_PHONE = "5493462371166"

# TELEGRAM — Notificaciones internas (gratis, sin límite)
TELEGRAM_BOT_TOKEN = "8650255274:AAHqQ6pacJ8yjvLXYUht2d7Ot181w3_HISo"
TELEGRAM_CHAT_ID = "5624243292"  # Chat Fernando — alertas generales

# TELEGRAM RRHH — Bot separado para CVs (@Rrhhclz_bot)
TELEGRAM_RRHH_TOKEN = "8328528721:AAGnNd-w-wKUq8FfbZM7vM9tzQndU_zGhpY"
TELEGRAM_RRHH_CHAT_ID = ""  # TODO: obtener cuando Maite le mande msg al bot

def telegram_rrhh(text):
    """Envía CV/consulta laboral al bot RRHH de Telegram."""
    if not TELEGRAM_RRHH_CHAT_ID:
        # Fallback: mandar por el bot general
        telegram_notify(text)
        return
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_RRHH_TOKEN}/sendMessage'
        data = json.dumps({'chat_id': TELEGRAM_RRHH_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        ctx = ssl.create_default_context()
        urllib.request.urlopen(req, context=ctx, timeout=10)
    except:
        telegram_notify(text)  # fallback

def telegram_notify(text):
    """Envía notificación al equipo por Telegram (gratis)."""
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        data = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        ctx = ssl.create_default_context()
        urllib.request.urlopen(req, context=ctx, timeout=10)
    except:
        pass  # No fallar si Telegram no responde
RESPUESTA_CV = (
    "Gracias por tu interes en Calzalindo! 🙌 "
    "Le pasamos tu mensaje a nuestra area de RRHH. "
    "Te van a contactar si hay una busqueda que encaje. Exitos! 💪"
)

RESPUESTA_NUMERO_EQUIVOCADO = (
    "Mil disculpas! 🙏 Nos equivocamos de contacto. "
    "Ya te sacamos de la lista, no vas a recibir mas mensajes. "
    "Perdon por la molestia!"
)

# Respuesta para preguntas de cambios/devoluciones
RESPUESTA_CAMBIOS = (
    "Si! Tenes 30 dias para cambiar por otro talle o modelo "
    "presentando el ticket de compra. Si compraste por la web, "
    "el cambio es sin costo. Cualquier duda escribinos! 😊"
)

# Respuesta para ventas por mayor
RESPUESTA_MAYORISTA_OUTLET = (
    "Si! Tenemos precios especiales por mayor. "
    "Escribile directo a Fernando al +5493462672330 "
    "y te arma una propuesta. 🤝"
)

# --- OUTLET MUNICIPAL ATR ---
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

OUTLET_FLYER_PATH = "/Users/fernandocalaianov/Desktop/cowork_pedidos/valijas/imagenes/flyer_outlet_abril.jpg"

RESPUESTA_OUTLET_PASCUAS = (
    "Felices Pascuas para vos y toda tu familia! 🐣🙏\n"
    "Que pasen un hermoso dia juntos.\n\n"
    "Y acordate: la semana que viene arranca el OUTLET! "
    "Del 9 al 12 de abril, precios desde $4.999 + Sector Pague Lo Que Quiera.\n"
    "Comparti el flyer con tu familia asi vienen todos! 🔥"
)

RESPUESTA_OUTLET_LOCALES = (
    "Estamos en Venado Tuerto:\n"
    "📍 Central: Brown 1080\n"
    "📍 Norte: Castelli 401\n"
    "📍 Eva Peron: Eva Peron 1150\n"
    "El outlet es en TODOS los locales, del 9 al 12 de abril!\n"
    "Horario: Lun a Vie 8:30-12:30 y 16:00-20:30, Sab 8:30-13:00 y 16:30-20:30"
)

RESPUESTA_OUTLET_HORARIO = (
    "El outlet arranca el miercoles 9 de abril.\n"
    "Horario: Lunes a Viernes 8:30-12:30 y 16:00-20:30\n"
    "Sabados 8:30-13:00 y 16:30-20:30\n"
    "Te esperamos! 🔥"
)

RESPUESTA_OUTLET_JUNIN = (
    "Hola! En Junin no tenemos outlet presencial, pero esta semana "
    "liquidamos TODO en calzalindo.com.ar con ENVIO GRATIS a todo el pais! 📦\n"
    "Zapatillas, botas, camperas desde $4.999.\n"
    "👉 calzalindo.com.ar"
)

RESPUESTA_OUTLET_POSITIVA = (
    "Que bueno! 😊 Te esperamos del 9 al 12 de abril.\n"
    "📍 Av. Santa Fe 1246, Venado Tuerto\n"
    "🕐 10:00 a 21:00 hs\n"
    "Hay Sector Pague Lo Que Quiera + ventas por mayor.\n\n"
    "Te pido un favor? 🙏 Compartí el flyer en tu estado de WhatsApp "
    "asi se enteran tus contactos. Cuantos mas vengan, mejor para todos! 🔥"
)

RESPUESTA_OUTLET_GRACIAS = (
    "De nada! 😊 Te dejo el flyer por si lo queres poner en tu estado "
    "de WhatsApp y que se enteren tus amigos/familia.\n"
    "📅 Del 9 al 12 de abril\n"
    "📍 Av. Santa Fe 1246, Venado Tuerto\n"
    "🕐 10:00 a 21:00 hs\n"
    "Te esperamos! 🔥"
)

RESPUESTA_OUTLET_SALUDO = (
    "Hola! 😊 Que bueno saber de vos! Te esperamos en nuestro outlet.\n"
    "Liquidamos todo desde $4.999!\n"
    "📅 Del 9 al 12 de abril\n"
    "📍 Av. Santa Fe 1246, Venado Tuerto\n"
    "🕐 10:00 a 21:00 hs\n"
    "Sector Pague Lo Que Quiera!"
)

RESPUESTA_OUTLET_HORARIO = (
    "El outlet arranca el miercoles 9 de abril! 📅\n"
    "Del 9 al 12, de 10:00 a 21:00 hs.\n"
    "📍 Av. Santa Fe 1246, Venado Tuerto\n\n"
    "Faltan pocos dias, guarda plata! 😉"
)

UNMATCHED_LOG = os.path.join(SCRIPT_DIR, "log_unmatched_messages.json")

def _log_unmatched(text):
    """Guarda mensajes que no matchearon para revisar y mejorar keywords."""
    entries = []
    if os.path.exists(UNMATCHED_LOG):
        try:
            with open(UNMATCHED_LOG, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except:
            entries = []
    entries.append({"timestamp": ts(), "message": text[:300]})
    if len(entries) > 2000:
        entries = entries[-2000:]
    with open(UNMATCHED_LOG, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

# Palabras clave de interes inicial (orden importa: mas especificas primero)
KEYWORDS_INTERES = [
    "info valijas go", "si contame", "si, contame",
    r"s[ií] contame", r"s[ií],? contame",
    "valijas", "valija", "set de viaje", "equipaje",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ts():
    """Timestamp legible."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_action(action: str, conversation_id=None, detail: str = ""):
    """Append una entrada al log JSON."""
    entry = {
        "timestamp": ts(),
        "action": action,
        "conversation_id": conversation_id,
        "detail": detail,
    }
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except (json.JSONDecodeError, IOError):
            logs = []
    logs.append(entry)
    # Mantener ultimas 5000 entradas
    if len(logs) > 5000:
        logs = logs[-5000:]
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def load_responded() -> dict:
    """Carga el dict de conversaciones respondidas.
    Formato: {conv_id_str: {"last_message_id": int, "responded_at": str, "initial_sent": bool}}
    """
    if os.path.exists(RESPONDED_FILE):
        try:
            with open(RESPONDED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_responded(data: dict):
    with open(RESPONDED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_optouts() -> list:
    """Carga la lista de opt-outs desde JSON."""
    if os.path.exists(OPTOUT_FILE):
        try:
            with open(OPTOUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_optout(telefono: str, nombre: str = "", motivo: str = ""):
    """Agrega un telefono a la lista de opt-out."""
    tel_norm = telefono.lstrip("+").strip()
    optouts = load_optouts()
    # Verificar si ya existe
    for entry in optouts:
        if entry.get("telefono", "").lstrip("+").strip() == tel_norm:
            return  # Ya existe
    optouts.append({
        "telefono": tel_norm,
        "nombre": nombre,
        "motivo": motivo,
        "origen": "keyword",
        "fecha_baja": ts(),
    })
    with open(OPTOUT_FILE, "w", encoding="utf-8") as f:
        json.dump(optouts, f, ensure_ascii=False, indent=2)


def is_optout(telefono: str) -> bool:
    """Verifica si un telefono esta en la lista de opt-out."""
    tel_norm = telefono.lstrip("+").strip()
    for entry in load_optouts():
        entry_tel = entry.get("telefono", "").lstrip("+").strip()
        if entry_tel == tel_norm or tel_norm[-8:] == entry_tel[-8:]:
            return True
    return False


def api_get(endpoint: str):
    """GET a la API de Chatwoot."""
    url = f"{CHATWOOT_URL}{endpoint}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("api_access_token", API_TOKEN)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_post(endpoint: str, body: dict):
    """POST a la API de Chatwoot."""
    url = f"{CHATWOOT_URL}{endpoint}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("api_access_token", API_TOKEN)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_message(conversation_id: int, content: str):
    """Envia un mensaje outgoing a una conversacion."""
    endpoint = f"/api/v1/accounts/{ACCOUNT_ID}/conversations/{conversation_id}/messages"
    body = {
        "content": content,
        "message_type": "outgoing",
        "private": False,
    }
    return api_post(endpoint, body)


def get_conversations(page: int = 1) -> list:
    """Lista conversaciones abiertas del inbox WhatsApp."""
    endpoint = (
        f"/api/v1/accounts/{ACCOUNT_ID}/conversations"
        f"?inbox_id={INBOX_ID}&status=open&page={page}"
    )
    data = api_get(endpoint)
    # La API devuelve {"data": {"meta": {...}, "payload": [...]}}
    if isinstance(data, dict):
        payload = data.get("data", data)
        if isinstance(payload, dict):
            return payload.get("payload", [])
        return payload if isinstance(payload, list) else []
    return data if isinstance(data, list) else []


def get_messages(conversation_id: int) -> list:
    """Obtiene mensajes de una conversacion."""
    endpoint = (
        f"/api/v1/accounts/{ACCOUNT_ID}/conversations/{conversation_id}/messages"
    )
    data = api_get(endpoint)
    # La API devuelve {"payload": [...]}
    if isinstance(data, dict):
        return data.get("payload", [])
    return data if isinstance(data, list) else []


# ---------------------------------------------------------------------------
# Clasificacion de mensajes
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Normaliza texto para matching: minusculas, sin acentos comunes."""
    t = text.lower().strip()
    # Reemplazos basicos de acentos
    for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
                 ("ü", "u"), ("ñ", "n")]:
        t = t.replace(a, b)
    return t


def classify_message(text, initial_already_sent):
    """Devuelve la respuesta apropiada o None si no debe responder.

    Args:
        text: Texto del mensaje del cliente.
        initial_already_sent: Si ya le mandamos la respuesta inicial a esta conv.

    Returns:
        String con la respuesta o None.
    """
    t = normalize(text)

    # Auto-responders de empresas/personas → SKIP (no responder, no loguear)
    autoresponder_patterns = [
        "en este momento no te puedo responder",
        "en este momento no puedo responder",
        "no puedo atenderte ahora",
        "te respondo en un rato",
        "como podemos ayudarte",  # bots de empresas
        "gracias por comunicarte con",  # bots de empresas
        "mensaje automatico",
        "fuera de horario",
        "respuesta automatica",
        "en breve te respondo",  # auto-reply personal
        "en breve conte",  # "en breve contestamos"
        "en la brevedad",  # "a la brevedad te respondo"
        "deja tu nombre",  # "dejá tu nombre y te respondo"
        "deja tu mensaje",
        "estoy fuera de mi trabajo",  # fuera de oficina
        "este es un mensaje automatico",
        "hace tu pedido",  # bots de delivery
        "comunicate al",  # redireccionadores
        "podes dejar tu",  # "podes dejar tu mensaje"
        "nuestro horario",  # respuestas de horario comercial
    ]
    if any(kw in t for kw in autoresponder_patterns):
        return None  # skip silencioso, no loguear como unmatched

    # Número equivocado (prioridad máxima — dar de baja con disculpa)
    if any(kw in t for kw in ["se equivocaron", "equivocaron de numero", "numero equivocado",
                                "no soy", "no me llamo", "ese no soy yo", "no es mi nombre",
                                "no es para mi", "este no es el telefono", "quien te dio mi numero",
                                "quien sos", "no es mi nombre", "no es para mi ese mensaje"]):
        return "NUMERO_EQUIVOCADO"

    # Opt-out detection (prioridad maxima absoluta)
    if any(kw in t for kw in KEYWORDS_OPTOUT):
        return "OPTOUT"

    # CV / curriculum — responder amigable y derivar a RRHH
    if any(kw in t for kw in ["curriculum", "cv", "busco trabajo", "busco empleo",
                                "trabajo", "puesto", "vacante", "empleo"]):
        return "CV_RRHH"

    # Cambios / devoluciones / talles
    if any(kw in t for kw in ["cambio", "cambiar", "devolucion", "devolver", "talle",
                                "no me anda", "me queda grande", "me queda chico"]):
        return "CAMBIOS"

    # Medios de pago
    if any(kw in t for kw in ["como pago", "medios de pago", "formas de pago", "cuotas",
                                "tarjeta", "transferencia", "efectivo", "debito", "credito",
                                "pago", "los pagos"]):
        return "MEDIOS_PAGO"

    # Consulta de producto / stock / talle
    if any(kw in t for kw in ["tienen", "tenes", "hay en", "modelo", "consulta",
                                "quisiera saber", "quiero saber", "talle 3", "talle 4",
                                "nro 3", "nro 4", "numero 3", "numero 4",
                                "rojo", "azul", "negro", "blanco", "rosa",
                                "river", "boca", "conjunto"]):
        return "CONSULTA_PRODUCTO"

    # Ventas por mayor
    if any(kw in t for kw in ["por mayor", "mayorista", "mayoreo", "cantidad", "lote"]):
        return "MAYORISTA_OUTLET"

    # LOCALES / DIRECCIÓN
    if any(kw in t for kw in ["donde quedan", "donde queda", "direccion", "ubicacion",
                                "locales", "domicilio", "como llego", "donde es", "donde estan"]):
        return "OUTLET_LOCALES"

    # HORARIO
    if any(kw in t for kw in ["horario", "hora", "abierto", "abren", "a que hora",
                                "que hora", "cuando abren", "hoy abren", "hoy esta abierto",
                                "abren manana", "abren el sabado", "abren el domingo"]):
        return "OUTLET_HORARIO"

    # JUNÍN — detectar si preguntan por Junín
    if any(kw in t for kw in ["junin", "envio", "envian", "mandan", "comprar online",
                                "comprar por la web", "web", "pagina"]):
        return "OUTLET_JUNIN"

    # Botones OUTLET (prioridad maxima)
    if "avisame cuando arranque" in t or "avisame" in t:
        return "OUTLET_AVISAME"
    if any(kw in t for kw in ["que va a haber", "que hay", "que van a tener",
                                "q va a haber", "q hay", "que habra", "que tienen",
                                "hay algo", "tienen algo"]):
        return "OUTLET_QUE_HAY"

    # Botones valijas interactive message
    if "comision $20k/set" in t or "comision 20k" in t or "btn_comision" in t:
        return RESPUESTA_COMISION
    if "mayorista $100k/set" in t or "mayorista 100k" in t or "btn_mayorista" in t:
        return RESPUESTA_MAYORISTA
    if "ver mas fotos" in t or "ver fotos" in t or "btn_fotos" in t:
        return RESPUESTA_FOTOS

    # PASCUAS — responder con cariño + flyer
    pascuas_kw = ["felices pascuas", "feliz pascua", "pascuas", "pascua",
                  "felices fiestas", "cristo", "resurreccion", "huevo de pascua"]
    if any(kw in t for kw in pascuas_kw):
        return "OUTLET_PASCUAS"

    # Respuesta POSITIVA → con flyer (prioridad alta)
    positivas = [
        "voy", "vamos", "ahi estare", "ahi voy", "nos vemos", "los voy a",
        "voy a ir", "voy a estar", "voy a pasar", "paso seguro", "cuenten conmigo",
        "visitando", "visitar", "ya voy", "ahi andare", "ahi ando",
        "genial", "buenisimo", "excelente", "dale", "joya", "barbaro",
        "invitando", "le aviso", "le digo", "les cuento",
        "si si", "sisi", "claro que si", "obvio", "por supuesto",
        "me encanta", "que bueno", "espectacular", "hermoso",
        "ok", "okey", "okk", "listo", "perfecto", "bien ahi", "de una",
        "ta bien", "todo bien", "esta bien",
    ]
    if any(kw in t for kw in positivas):
        return "OUTLET_POSITIVA"

    # Agradecimiento corto → con flyer
    # Detectar variantes con letras repetidas: graciiias, graciasss, etc.
    if (any(kw in t for kw in ["gracias", "gracia", "bendicion", "buen dia", "buenas"])
        or re.search(r"g+r+a+c+i+a+s+", t)) and len(t) < 60:
        return "OUTLET_GRACIAS"

    # Saludo simple → con flyer
    # Detectar variantes con letras repetidas: hooolaa, holaaaa, etc.
    if (any(kw in t for kw in ["hola", "buenas tardes", "buenos dias", "buenas noches", "buen dia"])
        or re.search(r"h+o+l+a+", t)) and len(t) < 30:
        return "OUTLET_SALUDO"

    # Emoji positivo solo → con flyer
    emojis_positivos = set("👍🙌❤️💖😊😄🔥✅👏💪🎉😍🥰😘👋")
    if len(t) <= 10 and all(c in emojis_positivos or not c.isalpha() for c in text.strip()):
        return "OUTLET_POSITIVA"

    # Negativo explícito
    if any(kw in t for kw in ["no gracias", "no, gracias", "no me interesa", "no puedo", "no tengo plata"]):
        return RESPUESTA_NO_GRACIAS

    # Ubicación
    if any(kw in t for kw in ["donde queda", "direccion", "ubicacion", "como llego", "donde es", "donde estan"]):
        return "OUTLET_QUE_HAY"

    # Horario / abierto / cuando
    if any(kw in t for kw in ["horario", "a que hora", "cuando abre", "cuando es", "que dia",
                                "hoy esta abierto", "esta abierto", "estan abiertos", "abren hoy",
                                "hoy abren", "a que hora abren", "hasta que hora",
                                "abierto hoy", "hoy abris", "abren manana", "manana abren",
                                "abren el sabado", "abren el domingo", "dias abierto"]):
        return "OUTLET_HORARIO"

    # Pago / precio
    if any(kw in t for kw in ["tarjeta", "cuotas", "efectivo", "debito", "credito"]):
        return "OUTLET_QUE_HAY"

    # Preguntan qué hay / fotos de productos / categorías
    if any(kw in t for kw in ["zapatillas", "zapatilla", "botas", "bota", "zapato", "zapatos",
                                "campera", "camperas", "ropa", "cartera", "mochila",
                                "que van a tener", "que productos", "lo que va a haber",
                                "foto", "fotos", "imagen", "mostrame", "cuanto", "precio"]):
        return RESPUESTA_FOTOS

    if any(kw in t for kw in ["comision", "opcion a"]):
        return RESPUESTA_COMISION

    if any(kw in t for kw in ["mayorista", "opcion b", "comprar"]):
        return RESPUESTA_MAYORISTA

    if any(kw in t for kw in ["garantia"]):
        return RESPUESTA_GARANTIA

    # Keywords de interes — SIEMPRE responder
    for kw in KEYWORDS_INTERES:
        if kw in t:
            return RESPUESTA_INTERES_INICIAL

    # No matchea → loguear para aprendizaje y dejar para humano
    _log_unmatched(text)
    return None


# ---------------------------------------------------------------------------
# Logica principal
# ---------------------------------------------------------------------------

def process_conversations():
    """Procesa todas las conversaciones abiertas del inbox."""
    responded = load_responded()
    changed = False

    try:
        conversations = get_conversations()
    except Exception as e:
        print(f"[{ts()}] ERROR listando conversaciones: {e}")
        log_action("error_list_conversations", detail=str(e))
        return

    print(f"[{ts()}] Encontradas {len(conversations)} conversaciones abiertas")

    for conv in conversations:
        conv_id = conv.get("id")
        if not conv_id:
            continue

        conv_key = str(conv_id)

        # Skip contactos que pidieron opt-out
        sender = conv.get("meta", {}).get("sender", {})
        sender_phone = str(sender.get("phone_number", ""))
        if sender_phone and is_optout(sender_phone):
            continue

        try:
            messages = get_messages(conv_id)
        except Exception as e:
            print(f"[{ts()}]   Conv {conv_id}: ERROR obteniendo mensajes: {e}")
            log_action("error_get_messages", conv_id, str(e))
            continue

        if not messages:
            continue

        # Ordenar por created_at (mas reciente ultimo)
        messages.sort(key=lambda m: m.get("created_at", 0))

        last_msg = messages[-1]
        last_msg_id = last_msg.get("id", 0)
        msg_type = last_msg.get("message_type")  # 0=incoming, 1=outgoing, 2=activity

        # Si el ultimo mensaje es outgoing (1) -> ya respondimos, skip
        if msg_type == 1:
            continue

        # Si no es incoming (0), skip (activity, etc)
        if msg_type != 0:
            continue

        # Verificar si ya procesamos este mensaje
        prev = responded.get(conv_key, {})
        if prev.get("last_message_id") == last_msg_id:
            continue

        content = last_msg.get("content", "")
        if not content:
            continue

        initial_already_sent = prev.get("initial_sent", False)
        response = classify_message(content, initial_already_sent)

        if response is None:
            print(f"[{ts()}]   Conv {conv_id}: mensaje no matchea, dejando para humano")
            log_action("skip_no_match", conv_id, content[:100])
            # Registrar que vimos este mensaje para no re-procesarlo
            responded[conv_key] = {
                "last_message_id": last_msg_id,
                "responded_at": prev.get("responded_at", ""),
                "initial_sent": initial_already_sent,
                "skipped_at": ts(),
            }
            changed = True
            continue

        # Enviar respuesta
        try:
            if response == "OPTOUT":
                # Extraer telefono del contacto
                sender = conv.get("meta", {}).get("sender", {})
                phone = str(sender.get("phone_number", ""))
                sender_name = str(sender.get("name", ""))
                save_optout(phone, sender_name, f"keyword: {content[:100]}")
                send_message(conv_id, RESPUESTA_OPTOUT)
                log_action("optout_registered", conv_id, f"phone={phone} name={sender_name}")
                print(f"[{ts()}]   Conv {conv_id}: OPT-OUT registrado -> {phone}")
                responded[conv_key] = {
                    "last_message_id": last_msg_id,
                    "responded_at": ts(),
                    "initial_sent": True,
                    "optout": True,
                }
                changed = True
                continue

            # CV / RRHH — responder amigable + reenviar a Maite
            if response == "CV_RRHH":
                send_message(conv_id, RESPUESTA_CV)
                # Reenviar a Maite por TELEGRAM RRHH (gratis)
                sender_name = c.get('meta',{}).get('sender',{}).get('name','Alguien')
                sender_phone = c.get('meta',{}).get('sender',{}).get('phone_number','')
                telegram_rrhh(
                    f"📋 <b>CV/Consulta laboral</b>\n"
                    f"De: {sender_name} ({sender_phone})\n"
                    f"Mensaje: {content[:300]}\n\n"
                    f"👉 Maite: respondele a {sender_phone}"
                )
                log_action("cv_forwarded_telegram", conv_id, f"from={sender_name}")
                changed = True
                continue

            # Número equivocado — dar de baja con disculpa especial
            if response == "NUMERO_EQUIVOCADO":
                send_message(conv_id, RESPUESTA_NUMERO_EQUIVOCADO)
                phone = c.get('meta',{}).get('sender',{}).get('phone_number','').lstrip('+')
                sender_name = c.get('meta',{}).get('sender',{}).get('name','')
                if phone:
                    save_optout(phone, sender_name, f"numero equivocado: {content[:60]}")
                changed = True
                continue

            # Cambios / devoluciones
            if response == "CAMBIOS":
                send_message(conv_id, RESPUESTA_CAMBIOS)
                changed = True
                continue

            # Ventas por mayor → notificar a Fernando por Telegram
            if response == "MAYORISTA_OUTLET":
                send_message(conv_id, RESPUESTA_MAYORISTA_OUTLET)
                sender_name = c.get('meta',{}).get('sender',{}).get('name','?')
                sender_phone = c.get('meta',{}).get('sender',{}).get('phone_number','')
                telegram_notify(
                    f"🤝 <b>Consulta MAYORISTA</b>\n"
                    f"De: {sender_name} ({sender_phone})\n"
                    f"Mensaje: {content[:200]}\n"
                    f"👉 Fernando: contactalo"
                )
                changed = True
                continue

            # Medios de pago
            if response == "MEDIOS_PAGO":
                send_message(conv_id, "Aceptamos efectivo, debito, credito hasta 6 cuotas sin interes, y transferencia bancaria (con descuento extra). En el outlet que arranca mañana hay precios especiales! Te esperamos.")
                changed = True
                continue

            # Consulta de producto
            if response == "CONSULTA_PRODUCTO":
                send_message(conv_id, "Hola! Para consultas de stock y talles te recomendamos pasar por el local o escribirnos a +5493462672330. Mañana arranca el outlet con descuentos increibles en todas las marcas!")
                changed = True
                continue

            if response in ("OUTLET_AVISAME", "OUTLET_QUE_HAY", "OUTLET_POSITIVA", "OUTLET_GRACIAS", "OUTLET_SALUDO", "OUTLET_PASCUAS", "OUTLET_LOCALES", "OUTLET_HORARIO", "OUTLET_JUNIN"):
                text_map = {
                    "OUTLET_AVISAME": RESPUESTA_OUTLET_AVISAME,
                    "OUTLET_QUE_HAY": RESPUESTA_OUTLET_QUE_HAY,
                    "OUTLET_POSITIVA": RESPUESTA_OUTLET_POSITIVA,
                    "OUTLET_GRACIAS": RESPUESTA_OUTLET_GRACIAS,
                    "OUTLET_SALUDO": RESPUESTA_OUTLET_SALUDO,
                    "OUTLET_PASCUAS": RESPUESTA_OUTLET_PASCUAS,
                    "OUTLET_LOCALES": RESPUESTA_OUTLET_LOCALES,
                    "OUTLET_HORARIO": RESPUESTA_OUTLET_HORARIO,
                    "OUTLET_JUNIN": RESPUESTA_OUTLET_JUNIN,
                }
                actual_text = text_map.get(response, RESPUESTA_OUTLET_QUE_HAY)
                # Mandar flyer + texto via curl multipart
                import subprocess
                flyer = OUTLET_FLYER_PATH
                if os.path.exists(flyer):
                    cmd = ['curl', '-sk', '-X', 'POST',
                           '-H', f'api_access_token: {API_TOKEN}',
                           '-F', f'content={actual_text}',
                           '-F', 'message_type=outgoing',
                           '-F', 'private=false',
                           '-F', f'attachments[]=@{flyer};type=image/jpeg',
                           f'{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{conv_id}/messages']
                    subprocess.run(cmd, capture_output=True, timeout=30)
                else:
                    send_message(conv_id, actual_text)
                response = actual_text
            else:
                send_message(conv_id, response)
            is_initial = (response == RESPUESTA_INTERES_INICIAL)
            responded[conv_key] = {
                "last_message_id": last_msg_id,
                "responded_at": ts(),
                "initial_sent": initial_already_sent or is_initial,
            }
            changed = True

            response_preview = response[:80].replace("\n", " ")
            print(f"[{ts()}]   Conv {conv_id}: RESPONDIDO -> {response_preview}...")
            log_action("responded", conv_id, f"msg_id={last_msg_id} | {response_preview}")

        except Exception as e:
            print(f"[{ts()}]   Conv {conv_id}: ERROR enviando respuesta: {e}")
            log_action("error_send", conv_id, str(e))

    if changed:
        save_responded(responded)


def main():
    once = "--once" in sys.argv

    print(f"[{ts()}] Responder Agencias Valijas GO iniciado")
    print(f"[{ts()}] Modo: {'una ejecucion' if once else f'polling cada {POLL_INTERVAL}s'}")
    print(f"[{ts()}] Chatwoot: {CHATWOOT_URL} | Account: {ACCOUNT_ID} | Inbox: {INBOX_ID}")
    log_action("start", detail=f"mode={'once' if once else 'continuous'}")

    if once:
        process_conversations()
        print(f"[{ts()}] Ejecucion completada")
        log_action("stop", detail="once")
        return

    try:
        while True:
            process_conversations()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Detenido por el usuario")
        log_action("stop", detail="keyboard_interrupt")


if __name__ == "__main__":
    main()
