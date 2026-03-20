#!/usr/bin/env python3
"""
Envío masivo de WhatsApp a agencias de viaje — Valijas GO
Usa la API de Meta WhatsApp Cloud directamente (WABA Chatwoot)
"""
import requests
import pandas as pd
import re
import time
import json
from datetime import datetime

# === CONFIGURACIÓN ===
API_KEY = "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40uQLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD"
PHONE_NUMBER_ID = "1046697335188691"
WABA_ID = "2155048721625121"
API_URL = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

# Template a usar
TEMPLATE_NAME = "go_valijas_agencias_2025"  # Pendiente aprobación Meta
# TEMPLATE_NAME = "promo_winback"  # Fallback ya aprobado

EXCEL_PATH = "/Users/fernandocalaianov/Desktop/cowork_pedidos/valijas/LISTA_AGENCIAS_PROSPECCION.xlsx"
LOG_PATH = "/Users/fernandocalaianov/Desktop/cowork_pedidos/valijas/log_envios_agencias.json"

# === FUNCIONES ===

def limpiar_telefono(tel_raw):
    """Convierte teléfono argentino a formato WhatsApp: 549XXXXXXXXXX"""
    if not tel_raw or str(tel_raw).strip() in ['(ver web)', '(ver Facebook)', '(ver Instagram)', 'nan']:
        return None

    tel = re.sub(r'[^\d+]', '', str(tel_raw))

    # Sacar el + inicial si existe
    tel = tel.lstrip('+')

    # Si empieza con 54 9, ya está en formato correcto
    if tel.startswith('549') and len(tel) >= 12:
        return tel

    # Si empieza con 54 sin 9, agregar 9
    if tel.startswith('54') and not tel.startswith('549'):
        tel = '549' + tel[2:]
        return tel if len(tel) >= 12 else None

    # Si empieza con 0 (código de área argentino)
    if tel.startswith('0'):
        tel = tel[1:]  # Sacar el 0
        if tel.startswith('11'):  # CABA: 011 -> 54911
            return '549' + tel
        elif tel.startswith('810'):  # 0810, no es celular
            return None
        else:
            return '549' + tel

    # Si empieza con 15 (celular sin código de área) - asumir CABA
    if tel.startswith('15') and len(tel) == 10:
        return '54911' + tel[2:]

    # Si empieza con 11 (CABA sin 0)
    if tel.startswith('11') and len(tel) == 10:
        return '549' + tel

    # Si es solo el número local (8 dígitos con código de área)
    if len(tel) >= 10 and not tel.startswith('54'):
        return '549' + tel

    return tel if len(tel) >= 12 else None


def check_template_status():
    """Verifica si el template está aprobado"""
    url = f"https://graph.facebook.com/v19.0/{WABA_ID}/message_templates"
    params = {"name": TEMPLATE_NAME, "access_token": API_KEY}
    resp = requests.get(url, params=params)
    data = resp.json()
    for t in data.get('data', []):
        if t['name'] == TEMPLATE_NAME:
            return t['status']
    return 'NOT_FOUND'


def enviar_template(telefono, nombre_agencia, template=None):
    """Envía template de WhatsApp a un número"""
    tpl = template or TEMPLATE_NAME

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Armar payload según template
    if tpl == "promo_winback":
        payload = {
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "template",
            "template": {
                "name": tpl,
                "language": {"code": "es_AR"},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": nombre_agencia}]}
                ]
            }
        }
    else:
        # go_valijas_agencias_2025
        payload = {
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "template",
            "template": {
                "name": tpl,
                "language": {"code": "es_AR"},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": nombre_agencia}]}
                ]
            }
        }

    resp = requests.post(API_URL, headers=headers, json=payload)
    return resp.json()


def cargar_agencias():
    """Lee Excel y prepara lista de agencias con teléfono válido"""
    df = pd.read_excel(EXCEL_PATH)
    agencias = []
    sin_tel = []

    for _, row in df.iterrows():
        tel = limpiar_telefono(row.get('Telefono/WhatsApp'))
        nombre = str(row.get('Nombre', '')).strip()

        if tel:
            agencias.append({
                'numero': int(row.get('#', 0)),
                'nombre': nombre,
                'ciudad': str(row.get('Ciudad', '')).strip(),
                'telefono': tel,
                'prioridad': str(row.get('Prioridad', '')).strip(),
                'tipo': str(row.get('Tipo', '')).strip()
            })
        else:
            sin_tel.append(nombre)

    return agencias, sin_tel


def enviar_campana(solo_alta=False, solo_test=False, test_numero=None):
    """Ejecuta la campaña de envío"""

    # Verificar template
    status = check_template_status()
    print(f"\n📋 Template '{TEMPLATE_NAME}': {status}")

    if status != 'APPROVED':
        print(f"⚠️  Template no aprobado ({status}). Opciones:")
        print(f"   1. Esperar aprobación de Meta")
        print(f"   2. Usar 'promo_winback' (ya aprobado)")
        usar_fallback = input("¿Usar promo_winback? (s/n): ").strip().lower()
        if usar_fallback == 's':
            tpl = "promo_winback"
        else:
            print("Abortando.")
            return
    else:
        tpl = TEMPLATE_NAME

    # Test a un número específico
    if solo_test and test_numero:
        print(f"\n🧪 TEST → {test_numero}")
        result = enviar_template(test_numero, "Fernando Test", tpl)
        print(f"   Resultado: {json.dumps(result, indent=2)}")
        return

    # Cargar agencias
    agencias, sin_tel = cargar_agencias()

    if sin_tel:
        print(f"\n⚠️  {len(sin_tel)} agencias SIN teléfono: {', '.join(sin_tel[:5])}...")

    if solo_alta:
        agencias = [a for a in agencias if a['prioridad'] == 'ALTA']

    print(f"\n📱 Enviando a {len(agencias)} agencias con template '{tpl}':")
    for a in agencias:
        print(f"   {a['numero']:2d}. {a['nombre']:30s} | {a['ciudad']:15s} | {a['telefono']} | {a['prioridad']}")

    confirmar = input(f"\n¿Confirmar envío a {len(agencias)} agencias? (s/n): ").strip().lower()
    if confirmar != 's':
        print("Cancelado.")
        return

    # Enviar
    log = []
    enviados = 0
    errores = 0

    for i, a in enumerate(agencias):
        print(f"\n[{i+1}/{len(agencias)}] {a['nombre']} → {a['telefono']}...", end=" ")

        result = enviar_template(a['telefono'], a['nombre'], tpl)

        if 'messages' in result:
            msg_id = result['messages'][0].get('id', '?')
            status = result['messages'][0].get('message_status', '?')
            print(f"✅ {status} (id: {msg_id[:20]}...)")
            enviados += 1
            log.append({**a, 'status': 'enviado', 'msg_id': msg_id, 'timestamp': datetime.now().isoformat()})
        else:
            error = result.get('error', {}).get('message', str(result))
            print(f"❌ {error[:60]}")
            errores += 1
            log.append({**a, 'status': 'error', 'error': error, 'timestamp': datetime.now().isoformat()})

        # Rate limit: esperar 3 segundos entre mensajes
        if i < len(agencias) - 1:
            time.sleep(3)

    # Guardar log
    with open(LOG_PATH, 'w') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"✅ Enviados: {enviados}")
    print(f"❌ Errores: {errores}")
    print(f"📄 Log: {LOG_PATH}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            # Test a Fernando
            enviar_campana(solo_test=True, test_numero="5493462672330")
        elif sys.argv[1] == 'alta':
            # Solo prioridad ALTA
            enviar_campana(solo_alta=True)
        elif sys.argv[1] == 'status':
            # Ver estado template
            status = check_template_status()
            print(f"Template '{TEMPLATE_NAME}': {status}")
        elif sys.argv[1] == 'todas':
            # Todas las agencias
            enviar_campana()
        else:
            print("Uso: python enviar_whatsapp_agencias.py [test|alta|status|todas]")
    else:
        print("🔧 Campaña WhatsApp — Valijas GO para Agencias")
        print("="*50)
        print("Comandos:")
        print("  python enviar_whatsapp_agencias.py test    → Envía test a Fernando")
        print("  python enviar_whatsapp_agencias.py status  → Ver estado del template")
        print("  python enviar_whatsapp_agencias.py alta    → Enviar a agencias ALTA")
        print("  python enviar_whatsapp_agencias.py todas   → Enviar a TODAS")
