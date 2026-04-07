#!/usr/bin/env python3
"""
Recordatorio DÍA D — Miércoles 9 de abril
Envía template outlet_hoy_arranca a los 68 que pidieron recordatorio.

Uso:
  python3 enviar_recordatorio_dia_d.py --dry-run    # Ver sin enviar
  python3 enviar_recordatorio_dia_d.py               # Enviar
  python3 enviar_recordatorio_dia_d.py --test         # Solo a Fernando
"""
import json, time, sys, os, re
from datetime import datetime
import urllib.request, urllib.error, ssl

API_KEY = "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40uQLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD"
PHONE_NUMBER_ID = "1024637650727570"
TEMPLATE_NAME = "outlet_hoy_arranca"
TEMPLATE_LANG = "es_AR"
FERNANDO_PHONE = "5493462672330"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LISTA_FILE = os.path.join(BASE_DIR, "lista_recordatorio_dia_d.json")
OPTOUT_FILE = os.path.join(BASE_DIR, "optout_list.json")
MASTER_SENT = os.path.join(BASE_DIR, "phones_sent_dia_d.json")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

def load_optout():
    if not os.path.exists(OPTOUT_FILE): return set()
    try:
        with open(OPTOUT_FILE) as f:
            return set(e.get("telefono","").lstrip("+") for e in json.load(f))
    except: return set()

def load_sent():
    if not os.path.exists(MASTER_SENT): return set()
    try:
        with open(MASTER_SENT) as f:
            return set(json.load(f))
    except: return set()

def extraer_nombre(nombre):
    if not nombre: return "🔥"
    nombre = str(nombre).strip()
    # Emojis y caracteres especiales al inicio → limpiar
    nombre = re.sub(r'^[^a-zA-ZáéíóúÁÉÍÓÚñÑ]+', '', nombre).strip()
    if not nombre: return "🔥"
    return nombre.split()[0].title()

def enviar(telefono, nombre):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    payload = {"messaging_product":"whatsapp","to":telefono,"type":"template",
        "template":{"name":TEMPLATE_NAME,"language":{"code":TEMPLATE_LANG},
            "components":[{"type":"body","parameters":[{"type":"text","text":nombre}]}]}}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Authorization', f'Bearer {API_KEY}')
    req.add_header('Content-Type', 'application/json')
    try:
        resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=30)
        result = json.loads(resp.read().decode())
        return True, result.get('messages',[{}])[0].get('id','ok')
    except urllib.error.HTTPError as e:
        return False, e.read().decode()[:200]
    except Exception as e:
        return False, str(e)[:100]

def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    test = '--test' in args

    if test:
        contacts = [{"phone": f"+{FERNANDO_PHONE}", "name": "Fernando Test", "conv_id": 0}]
    else:
        with open(LISTA_FILE) as f:
            contacts = json.load(f)

    sent = load_sent()
    optout = load_optout()

    eligible = []
    for c in contacts:
        phone = c.get('phone','').lstrip('+')
        if not phone: continue
        if phone in sent: continue
        if phone in optout: continue
        eligible.append(c)

    print(f"""
{'='*60}
DÍA D — HOY ARRANCA EL OUTLET
Template: {TEMPLATE_NAME}
Contactos que pidieron recordatorio: {len(eligible)}
Ya enviados: {len(sent)} | Opt-out: {len(optout)}
Modo: {'DRY RUN' if dry_run else 'ENVIO REAL'}
{'='*60}
""")

    enviados = 0
    for i, c in enumerate(eligible):
        phone = c.get('phone','').lstrip('+')
        name = extraer_nombre(c.get('name',''))
        print(f"[{i+1}/{len(eligible)}] {c.get('name','?')[:25]} -> {phone}", end=" ")

        if dry_run:
            print(f"[DRY RUN] nombre={name}")
            continue

        ok, msg = enviar(phone, name)
        if ok:
            print(f"OK ({name})")
            enviados += 1
            sent.add(phone)
        else:
            print(f"ERROR: {msg[:50]}")

        time.sleep(3)

    if not dry_run:
        with open(MASTER_SENT, 'w') as f:
            json.dump(sorted(sent), f)

    print(f"\nEnviados: {enviados}/{len(eligible)}")

if __name__ == '__main__':
    main()
