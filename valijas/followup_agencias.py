#!/usr/bin/env python3
"""
Follow-up automático para campaña Valijas GO - Agencias de viaje.

Secuencia:
  Día 0: Template inicial (valijas_go_agencias) — ya enviado por enviar_whatsapp_agencias.py
  Día 2: Si no respondió → valijas_go_followup_dia2
  Día 7: Si no respondió → valijas_go_followup_dia7

Uso:
  python3 followup_agencias.py --dryrun    # Mostrar qué se enviaría
  python3 followup_agencias.py --send      # Enviar follow-ups realmente
"""
import json, os, sys, time, re
import urllib.request, urllib.error, ssl
from datetime import datetime, timezone

# ── Configuración ────────────────────────────────────────────────────────────

META_API_URL = "https://graph.facebook.com/v19.0/1024637650727570/messages"  # Calzalindo 1170
META_ACCESS_TOKEN = (
    "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40u"
    "QLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2"
    "TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD"
)

CHATWOOT_URL = "https://chat.calzalindo.com.ar"
CHATWOOT_TOKEN = "zvQpseDYDoeqJpwM41GCb1LP"
CHATWOOT_ACCOUNT = 3

TEMPLATE_LANG = "es_AR"

FOLLOWUP_SEQUENCE = [
    {"day": 2, "template": "valijas_go_followup_dia2"},
    {"day": 7, "template": "valijas_go_followup_dia7"},
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "log_envios_agencias.json")
FOLLOWUP_LOG_PATH = os.path.join(BASE_DIR, "log_followup_agencias.json")
EXCEL_PATH = os.path.join(BASE_DIR, "LISTA_AGENCIAS_PROSPECCION.xlsx")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


# ── Utilidades ───────────────────────────────────────────────────────────────

def normalizar_telefono(raw):
    """Normaliza teléfono argentino a formato 549XXXXXXXXXX."""
    if not raw or str(raw).strip() in ('(ver web)', '(ver Facebook)', '(ver Instagram)', 'nan'):
        return None
    tel = re.sub(r'[^\d+]', '', str(raw)).lstrip('+')
    if tel.startswith('549') and len(tel) >= 12:
        return tel
    if tel.startswith('54') and not tel.startswith('549'):
        return '549' + tel[2:]
    if tel.startswith('0'):
        tel = tel[1:]
        if tel.startswith('15'):
            return '54911' + tel[2:]
        return '549' + tel
    if tel.startswith('15'):
        return '54911' + tel[2:]
    if tel.startswith('11'):
        return '549' + tel
    if len(tel) >= 10:
        return '549' + tel
    return None


def extraer_primer_nombre(nombre):
    nombre = nombre.strip().strip('"').strip("'")
    if ' - ' in nombre:
        nombre = nombre.split(' - ')[0]
    return nombre


def api_request(url, data=None, headers=None, method=None):
    """HTTP request con SSL verification deshabilitada."""
    if data and isinstance(data, dict):
        data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=data, method=method or ('POST' if data else 'GET'))
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=30)
    return json.loads(resp.read().decode('utf-8'))


# ── Cargar datos ─────────────────────────────────────────────────────────────

def cargar_log_envios():
    """Lee log_envios_agencias.json. Retorna lista de envíos."""
    if not os.path.exists(LOG_PATH):
        print(f"WARN: No existe {LOG_PATH}")
        return []
    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if not content:
            return []
        return json.loads(content)


def cargar_log_followup():
    """Lee log de follow-ups ya enviados."""
    if not os.path.exists(FOLLOWUP_LOG_PATH):
        return []
    with open(FOLLOWUP_LOG_PATH, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if not content:
            return []
        return json.loads(content)


def guardar_log_followup(log):
    with open(FOLLOWUP_LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def cargar_agencias_excel():
    """Lee Excel y retorna dict telefono_normalizado → datos."""
    try:
        import pandas as pd
    except ImportError:
        import openpyxl
        wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        headers = [str(h) for h in rows[0]]
        agencias = {}
        for row in rows[1:]:
            d = dict(zip(headers, row))
            tel = normalizar_telefono(d.get('Telefono/WhatsApp'))
            if tel:
                agencias[tel] = {
                    'nombre': str(d.get('Nombre', '')),
                    'ciudad': str(d.get('Ciudad', '')),
                    'prioridad': str(d.get('Prioridad', '')),
                    'primer_nombre': extraer_primer_nombre(str(d.get('Nombre', ''))),
                }
        return agencias

    df = pd.read_excel(EXCEL_PATH)
    agencias = {}
    for _, row in df.iterrows():
        tel = normalizar_telefono(row.get('Telefono/WhatsApp'))
        if not tel:
            continue
        agencias[tel] = {
            'nombre': str(row.get('Nombre', '')),
            'ciudad': str(row.get('Ciudad', '')),
            'prioridad': str(row.get('Prioridad', '')),
            'primer_nombre': extraer_primer_nombre(str(row.get('Nombre', ''))),
        }
    return agencias


# ── Chatwoot: chequear si el contacto respondió ─────────────────────────────

def buscar_contacto_chatwoot(telefono):
    """Busca contacto en Chatwoot por teléfono. Retorna contact_id o None."""
    search_phone = f"+{telefono}"
    url = (
        f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT}/contacts/search"
        f"?q={urllib.parse.quote(search_phone)}&include_contacts=true"
    )
    try:
        import urllib.parse
        result = api_request(url, headers={'api_access_token': CHATWOOT_TOKEN})
        payload = result.get('payload', [])
        for contact in payload:
            c_phone = (contact.get('phone_number') or '').lstrip('+')
            if c_phone == telefono:
                return contact.get('id')
        return None
    except Exception as e:
        print(f"    WARN Chatwoot search: {str(e)[:100]}")
        return None


def contacto_respondio(contact_id):
    """
    Verifica si un contacto respondió revisando sus conversaciones.
    Retorna True si hay al menos un mensaje incoming del contacto.
    """
    url = (
        f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT}"
        f"/contacts/{contact_id}/conversations"
    )
    try:
        result = api_request(url, headers={'api_access_token': CHATWOOT_TOKEN})
        conversations = result.get('payload', [])
        for conv in conversations:
            # Método 1: customer_last_seen_at > 0 indica actividad
            customer_last_seen = conv.get('customer_last_seen_at', 0)
            if customer_last_seen and customer_last_seen > 0:
                return True

            # Método 2: buscar mensajes incoming en la conversación
            conv_id = conv.get('id')
            if conv_id:
                msgs_url = (
                    f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT}"
                    f"/conversations/{conv_id}/messages"
                )
                try:
                    msgs_result = api_request(
                        msgs_url, headers={'api_access_token': CHATWOOT_TOKEN}
                    )
                    messages = msgs_result.get('payload', [])
                    for msg in messages:
                        if msg.get('message_type') == 0:  # 0 = incoming
                            return True
                except Exception:
                    pass
        return False
    except Exception as e:
        print(f"    WARN Chatwoot conversations: {str(e)[:100]}")
        return False


# ── Enviar template via Meta Graph API ───────────────────────────────────────

def enviar_template(telefono, nombre, template_name):
    """Envía template de WhatsApp. Retorna (ok, message_id_o_error)."""
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": TEMPLATE_LANG},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": nombre}],
                }
            ],
        },
    }
    try:
        result = api_request(
            META_API_URL,
            data=payload,
            headers={
                'Authorization': f'Bearer {META_ACCESS_TOKEN}',
                'Content-Type': 'application/json',
            },
        )
        msg_id = result.get('messages', [{}])[0].get('id', 'ok')
        return True, msg_id
    except urllib.error.HTTPError as e:
        return False, e.read().decode()[:200]
    except Exception as e:
        return False, str(e)[:200]


# ── Lógica principal ─────────────────────────────────────────────────────────

import urllib.parse  # noqa: E402 (needed for Chatwoot search)


def determinar_followup(telefono, envio_ts, followups_previos):
    """
    Dado un teléfono y su timestamp de envío inicial, determina qué
    follow-up corresponde enviar (si alguno).
    Retorna dict del paso de la secuencia, o None.
    """
    ahora = datetime.now(timezone.utc)
    enviado_dt = datetime.fromisoformat(envio_ts.replace('Z', '+00:00'))
    dias_transcurridos = (ahora - enviado_dt).total_seconds() / 86400

    # Qué templates ya se enviaron a este teléfono
    templates_enviados = {
        fp['template'] for fp in followups_previos if fp.get('telefono') == telefono
    }

    # Recorrer secuencia de mayor a menor día para enviar el más reciente aplicable
    for step in reversed(FOLLOWUP_SEQUENCE):
        if dias_transcurridos >= step['day'] and step['template'] not in templates_enviados:
            return step

    return None


def main():
    args = sys.argv[1:]

    if '--send' in args:
        dry_run = False
    elif '--dryrun' in args:
        dry_run = True
    else:
        print(__doc__)
        return

    print(f"\n{'=' * 65}")
    print(f"FOLLOW-UP VALIJAS GO — Agencias de viaje")
    print(f"Modo: {'DRY RUN (no envía nada)' if dry_run else 'ENVIO REAL'}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 65}\n")

    # 1. Cargar datos
    envios = cargar_log_envios()
    if not envios:
        print("No hay envíos registrados en log_envios_agencias.json. Nada que hacer.")
        return

    agencias = cargar_agencias_excel()
    followup_log = cargar_log_followup()

    print(f"Envíos iniciales en log: {len(envios)}")
    print(f"Agencias en Excel: {len(agencias)}")
    print(f"Follow-ups previos en log: {len(followup_log)}")
    print()

    # 2. Procesar cada envío
    pendientes = []

    for envio in envios:
        telefono = envio.get('telefono')
        timestamp = envio.get('timestamp') or envio.get('fecha')
        nombre = envio.get('nombre', '')
        ok = envio.get('ok', envio.get('status') == 'ok')

        if not telefono or not timestamp or not ok:
            continue

        # Enriquecer con datos del Excel si disponible
        datos_excel = agencias.get(telefono, {})
        primer_nombre = datos_excel.get('primer_nombre') or extraer_primer_nombre(nombre)
        ciudad = datos_excel.get('ciudad', '')

        # Determinar qué follow-up toca
        step = determinar_followup(telefono, timestamp, followup_log)
        if not step:
            continue

        pendientes.append({
            'telefono': telefono,
            'nombre': nombre,
            'primer_nombre': primer_nombre,
            'ciudad': ciudad,
            'timestamp_inicial': timestamp,
            'step': step,
        })

    if not pendientes:
        print("No hay follow-ups pendientes. Todas las agencias ya fueron contactadas o respondieron.")
        return

    print(f"Candidatos a follow-up: {len(pendientes)}")
    print(f"\nVerificando respuestas en Chatwoot...\n")

    # 3. Filtrar los que NO respondieron (via Chatwoot)
    a_enviar = []
    for item in pendientes:
        tel = item['telefono']
        nombre_display = f"{item['nombre']} ({item['ciudad']})" if item['ciudad'] else item['nombre']
        template = item['step']['template']
        dia = item['step']['day']

        print(f"  [{tel}] {nombre_display} — día {dia} ({template})", end="")

        contact_id = buscar_contacto_chatwoot(tel)
        if contact_id:
            respondio = contacto_respondio(contact_id)
            if respondio:
                print(" → RESPONDIO, skip")
                continue
            else:
                print(" → sin respuesta")
        else:
            print(" → no encontrado en Chatwoot (sin respuesta)")

        a_enviar.append(item)

    print(f"\n{'─' * 65}")
    print(f"Total a enviar: {len(a_enviar)}")
    print(f"{'─' * 65}\n")

    if not a_enviar:
        print("Todos respondieron o no hay follow-ups pendientes.")
        return

    # 4. Enviar (o simular)
    enviados = 0
    errores = 0

    for i, item in enumerate(a_enviar):
        tel = item['telefono']
        template = item['step']['template']
        dia = item['step']['day']
        primer_nombre = item['primer_nombre']
        nombre_display = f"{item['nombre']} ({item['ciudad']})" if item['ciudad'] else item['nombre']

        print(f"[{i + 1}/{len(a_enviar)}] {nombre_display} → {tel}")
        print(f"         Template: {template} (día {dia})")

        if dry_run:
            print(f"         → [DRY RUN] no se envía\n")
            continue

        ok, msg = enviar_template(tel, primer_nombre, template)
        if ok:
            print(f"         → OK (msg_id: {msg})\n")
            enviados += 1
            followup_log.append({
                'telefono': tel,
                'nombre': item['nombre'],
                'template': template,
                'dia': dia,
                'message_id': msg,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })
        else:
            print(f"         → ERROR: {msg}\n")
            errores += 1

        # Rate limit: 3 segundos entre mensajes
        if i < len(a_enviar) - 1:
            time.sleep(3)

    # 5. Guardar log de follow-ups
    if not dry_run and enviados > 0:
        guardar_log_followup(followup_log)
        print(f"Log guardado en {FOLLOWUP_LOG_PATH}")

    # Resumen
    print(f"\n{'=' * 65}")
    if dry_run:
        print(f"RESUMEN DRY RUN: {len(a_enviar)} follow-ups pendientes de enviar")
    else:
        print(f"RESULTADO: {enviados} enviados, {errores} errores")
    print(f"{'=' * 65}\n")


if __name__ == '__main__':
    main()
