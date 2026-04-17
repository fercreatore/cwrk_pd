"""
Colector de señales de demanda desde WhatsApp/Chatwoot.

Pollea conversaciones de Chatwoot, extrae mensajes de clientes,
detecta consultas de productos y registra en demanda_db.

USO:
    python3 -m multicanal.colector_whatsapp --dias 7
    python3 -m multicanal.colector_whatsapp --dias 7 --dry-run
    python3 -m multicanal.colector_whatsapp --conversacion 12345
"""

import argparse
import json
import re
import ssl
import urllib.request
from datetime import datetime, timedelta

from multicanal.demanda_db import registrar_señal, inicializar


def _parse_fecha(val):
    """Convierte created_at de Chatwoot (epoch int o ISO string) a YYYY-MM-DD."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val).strftime('%Y-%m-%d')
    if isinstance(val, str):
        return val[:10]
    return None

# ── Chatwoot config ──
CHATWOOT_URL = "https://chat.calzalindo.com.ar"
CHATWOOT_TOKEN = "zvQpseDYDoeqJpwM41GCb1LP"
CHATWOOT_ACCOUNT = 3
INBOX_IDS = [9, 10]  # WhatsApp inboxes

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE

# ── Heurísticas de detección ──

# Palabras clave de producto
TIPOS_CALZADO = [
    'zapatilla', 'zapatillas', 'zapa', 'zapas',
    'pantufla', 'pantuflas', 'chinela', 'chinelas',
    'sandalia', 'sandalias', 'ojota', 'ojotas',
    'bota', 'botas', 'borcego', 'borcegos',
    'zapato', 'zapatos', 'mocasin', 'mocasines',
    'balerina', 'balerinas', 'guillermina',
    'deportiva', 'deportivas', 'running',
    'valija', 'valijas', 'mochila', 'mochilas',
    'cartera', 'carteras', 'bolso', 'bolsos',
]

# Marcas conocidas (para match en mensajes)
MARCAS_CONOCIDAS = [
    'topper', 'nike', 'adidas', 'reebok', 'puma', 'fila',
    'vans', 'converse', 'skechers', 'saucony', 'new balance',
    'diadora', 'atomik', 'wake', 'jaguar', 'gtn',
    'comoditas', 'savage', 'prowess', 'gaelle', 'john foos',
    'olympikus', 'rider', 'havaianas', 'ipanema',
]

# Patrones de consulta de producto
PATRONES_CONSULTA = [
    r'(?:ten[eé][si]s?|tienen|hay)\s+(.+?)[\?\.]',
    r'(?:precio|cuanto|cuánto)\s+(?:de|del|sale|está|esta)\s+(.+?)[\?\.]',
    r'(?:busco|quiero|necesito|me interesa)\s+(.+?)[\?\.\!]',
    r'(?:talle|número|numero)\s+(\d{2})',
    r'(?:en|del?)\s+(\d{2})\s*[\?\.]',
]

# Patrones de talle
PATRON_TALLE = re.compile(r'(?:talle|t(?:alle)?\.?|n[uú]mero|num\.?)\s*[:\s]?\s*(\d{2})', re.I)
PATRON_TALLE_SUELTO = re.compile(r'\b(\d{2})\b')  # fallback


def _api_get(path, params=None):
    """GET a Chatwoot API."""
    url = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT}{path}"
    if params:
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        url += f'?{query}'

    req = urllib.request.Request(url, headers={
        "api_access_token": CHATWOOT_TOKEN,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"    Error API: {e}")
        return None


def obtener_conversaciones(dias=7, page=1):
    """Obtiene conversaciones recientes de los inboxes de WhatsApp."""
    conversaciones = []
    for inbox_id in INBOX_IDS:
        result = _api_get("/conversations", {
            "inbox_id": inbox_id,
            "status": "all",
            "page": page,
        })
        if result and 'data' in result:
            data = result['data']
            payload = data.get('payload', data) if isinstance(data, dict) else data
            if isinstance(payload, list):
                conversaciones.extend(payload)
            elif isinstance(payload, dict):
                conversaciones.extend(payload.get('payload', []))
    return conversaciones


def obtener_mensajes(conversation_id, page=1):
    """Obtiene mensajes de una conversación."""
    result = _api_get(f"/conversations/{conversation_id}/messages", {"page": page})
    if result and 'payload' in result:
        return result['payload']
    return []


def es_mensaje_cliente(msg):
    """Filtra solo mensajes entrantes de clientes (no agentes)."""
    return (
        msg.get('message_type') == 0  # incoming
        and msg.get('content')
        and not msg.get('private', False)
    )


def extraer_producto_de_texto(texto):
    """
    Analiza texto de cliente y extrae señal de producto si la hay.
    Retorna dict con {producto_desc, talle, confianza} o None.
    """
    texto_lower = texto.lower().strip()

    # Detectar si es consulta de producto
    es_consulta = False
    producto_desc = None

    # 1. Buscar patrones explícitos
    for patron in PATRONES_CONSULTA:
        match = re.search(patron, texto_lower)
        if match:
            producto_desc = match.group(1).strip()
            es_consulta = True
            break

    # 2. Buscar tipos de calzado mencionados
    tipos_encontrados = [t for t in TIPOS_CALZADO if t in texto_lower]

    # 3. Buscar marcas mencionadas
    marcas_encontradas = [m for m in MARCAS_CONOCIDAS if m in texto_lower]

    # Si no hay patrón explícito pero hay tipo o marca, es señal débil
    if not es_consulta and (tipos_encontrados or marcas_encontradas):
        es_consulta = True
        partes = marcas_encontradas + tipos_encontrados
        producto_desc = ' '.join(partes)

    if not es_consulta:
        return None

    # Extraer talle
    talle = None
    talle_match = PATRON_TALLE.search(texto)
    if talle_match:
        talle = talle_match.group(1)
    elif tipos_encontrados or marcas_encontradas:
        # Buscar número suelto que podría ser talle (35-46)
        for m in PATRON_TALLE_SUELTO.finditer(texto):
            num = int(m.group(1))
            if 20 <= num <= 46:
                talle = str(num)
                break

    # Limpiar producto_desc
    if producto_desc:
        producto_desc = re.sub(r'\s+', ' ', producto_desc).strip()
        # Limitar largo
        if len(producto_desc) > 100:
            producto_desc = producto_desc[:100]

    return {
        'producto_desc': producto_desc or ' '.join(tipos_encontrados + marcas_encontradas),
        'talle': talle,
        'tipos': tipos_encontrados,
        'marcas': marcas_encontradas,
    }


def procesar_conversacion(conversation_id, dry_run=True):
    """Procesa una conversación y extrae señales de demanda."""
    señales = []
    mensajes = obtener_mensajes(conversation_id)

    for msg in mensajes:
        if not es_mensaje_cliente(msg):
            continue

        texto = msg.get('content', '')
        resultado = extraer_producto_de_texto(texto)

        if resultado:
            señal = {
                'fuente': 'whatsapp',
                'tipo': 'consulta_producto',
                'producto_desc': resultado['producto_desc'],
                'talle': resultado.get('talle'),
                'raw_text': texto[:500],
                'conversation_id': str(conversation_id),
                'fecha': _parse_fecha(msg.get('created_at')),
            }
            señales.append(señal)

            if not dry_run:
                registrar_señal(**señal)

    return señales


def colectar(dias=7, dry_run=True, max_conversaciones=100):
    """Colecta señales de demanda de las últimas conversaciones."""
    print(f"\n{'='*60}")
    print(f"  COLECTOR WHATSAPP {'[DRY RUN]' if dry_run else '[REAL]'}")
    print(f"  Últimos {dias} días")
    print(f"{'='*60}\n")

    if not dry_run:
        inicializar()

    print("Obteniendo conversaciones...")
    todas_conversaciones = []
    for page in range(1, 10):
        convs = obtener_conversaciones(dias=dias, page=page)
        if not convs:
            break
        todas_conversaciones.extend(convs)
        if len(todas_conversaciones) >= max_conversaciones:
            break

    print(f"  {len(todas_conversaciones)} conversaciones encontradas\n")

    total_señales = 0
    total_conversaciones_con_señal = 0

    for conv in todas_conversaciones[:max_conversaciones]:
        conv_id = conv.get('id')
        if not conv_id:
            continue

        señales = procesar_conversacion(conv_id, dry_run=dry_run)
        if señales:
            total_conversaciones_con_señal += 1
            total_señales += len(señales)

            contacto = conv.get('meta', {}).get('sender', {}).get('name', '?')
            print(f"  Conv #{conv_id} ({contacto}): {len(señales)} señales")
            for s in señales[:3]:
                talle_str = f" T:{s['talle']}" if s.get('talle') else ""
                print(f"    → {s['producto_desc'][:50]}{talle_str}")
                if len(s.get('raw_text', '')) > 0:
                    print(f"      \"{s['raw_text'][:60]}...\"")

    print(f"\n{'='*60}")
    print(f"  RESUMEN")
    print(f"  Conversaciones procesadas: {min(len(todas_conversaciones), max_conversaciones)}")
    print(f"  Con señales de producto: {total_conversaciones_con_señal}")
    print(f"  Total señales extraídas: {total_señales}")
    print(f"{'='*60}")

    return {'total_señales': total_señales, 'conversaciones': total_conversaciones_con_señal}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Colector de señales WhatsApp/Chatwoot')
    parser.add_argument('--dias', type=int, default=7, help='Días hacia atrás')
    parser.add_argument('--dry-run', action='store_true', help='Preview sin registrar')
    parser.add_argument('--conversacion', type=int, help='Procesar una conversación específica')
    args = parser.parse_args()

    if args.conversacion:
        señales = procesar_conversacion(args.conversacion, dry_run=args.dry_run)
        for s in señales:
            print(f"  {s['producto_desc']} | T:{s.get('talle', '?')} | {s['raw_text'][:60]}")
    else:
        colectar(dias=args.dias, dry_run=args.dry_run)
