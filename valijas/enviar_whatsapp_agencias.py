#!/usr/bin/env python3
"""
Envio masivo WhatsApp a agencias de viaje - Valijas GO
Usa Meta WhatsApp Cloud API via credenciales Chatwoot WABA

Uso:
  python3 enviar_whatsapp_agencias.py --test           # Solo a Fernando
  python3 enviar_whatsapp_agencias.py --prioridad ALTA  # Solo ALTA
  python3 enviar_whatsapp_agencias.py --todas            # Todas con telefono
  python3 enviar_whatsapp_agencias.py --dry-run --todas  # Ver sin enviar
"""
import json, time, re, sys, os
from datetime import datetime
import pandas as pd
import urllib.request, urllib.error, ssl

API_KEY = "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40uQLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD"
PHONE_NUMBER_ID = "1024637650727570"  # Calzalindo 1170
TEMPLATE_NAME = "valijas_go_propuesta_v2"
TEMPLATE_LANG = "es_AR"
CHATWOOT_TOKEN = "zvQpseDYDoeqJpwM41GCb1LP"
CHATWOOT_URL = "https://chat.calzalindo.com.ar"
CHATWOOT_ACCOUNT = 3
CHATWOOT_INBOX = 10  # Calzalindo 1170
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "LISTA_AGENCIAS_PROSPECCION.xlsx")
OPTOUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "optout_list.json")
FERNANDO_PHONE = "5493462672330"


def load_optout_phones() -> set:
    """Carga telefonos opt-out como set de ultimos 8 digitos para matching flexible."""
    if not os.path.exists(OPTOUT_FILE):
        return set()
    try:
        with open(OPTOUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        phones = set()
        for entry in data:
            tel = entry.get("telefono", "").lstrip("+").strip()
            if tel:
                phones.add(tel)
                if len(tel) >= 8:
                    phones.add(tel[-8:])
        return phones
    except (json.JSONDecodeError, IOError):
        return set()


def is_optout(telefono: str, optout_phones: set) -> bool:
    """Verifica si un telefono esta en la lista de opt-out."""
    tel = telefono.lstrip("+").strip()
    if tel in optout_phones:
        return True
    if len(tel) >= 8 and tel[-8:] in optout_phones:
        return True
    return False

def normalizar_telefono(raw):
    if not raw or str(raw).strip() in ['(ver web)','(ver Facebook)','(ver Instagram)','nan']:
        return None
    tel = re.sub(r'[^\d+]', '', str(raw)).lstrip('+')
    if tel.startswith('549') and len(tel) >= 12: return tel
    if tel.startswith('54') and not tel.startswith('549'): return '549' + tel[2:]
    if tel.startswith('0'):
        tel = tel[1:]
        if tel.startswith('15'): return '54911' + tel[2:]
        return '549' + tel
    if tel.startswith('15'): return '54911' + tel[2:]
    if tel.startswith('11'): return '549' + tel
    if len(tel) >= 10: return '549' + tel
    return None

def extraer_primer_nombre(nombre):
    nombre = nombre.strip().strip('"').strip("'")
    if ' - ' in nombre: nombre = nombre.split(' - ')[0]
    return nombre

def enviar_template(telefono, nombre):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    payload = {"messaging_product":"whatsapp","to":telefono,"type":"template",
        "template":{"name":TEMPLATE_NAME,"language":{"code":TEMPLATE_LANG},
            "components":[{"type":"body","parameters":[{"type":"text","text":nombre}]}]}}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Authorization', f'Bearer {API_KEY}')
    req.add_header('Content-Type', 'application/json')
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        result = json.loads(resp.read().decode())
        return True, result.get('messages',[{}])[0].get('id','ok')
    except urllib.error.HTTPError as e:
        return False, e.read().decode()[:200]

def crear_contacto_chatwoot(nombre, telefono):
    url = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT}/contacts"
    payload = {"inbox_id":CHATWOOT_INBOX,"name":nombre,"phone_number":f"+{telefono}"}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('api_access_token', CHATWOOT_TOKEN)
    req.add_header('Content-Type', 'application/json')
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        return True
    except: return False

def buscar_conversacion_chatwoot(telefono):
    """Busca conversación abierta en inbox 10 para este teléfono."""
    url = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT}/conversations?inbox_id={CHATWOOT_INBOX}&status=open&page=1"
    req = urllib.request.Request(url)
    req.add_header('api_access_token', CHATWOOT_TOKEN)
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        data = json.loads(resp.read().decode())
        payload = data.get('data',{}).get('payload',[]) if isinstance(data.get('data'),dict) else []
        for c in payload:
            sender = c.get('meta',{}).get('sender',{})
            phone = str(sender.get('phone_number',''))
            if telefono[-8:] in phone:
                return c['id']
    except: pass
    return None

def enviar_msg_chatwoot(conv_id, content):
    """Envía mensaje de texto por Chatwoot."""
    url = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT}/conversations/{conv_id}/messages"
    payload = {"content":content,"message_type":"outgoing","private":False}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('api_access_token', CHATWOOT_TOKEN)
    req.add_header('Content-Type', 'application/json')
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        return True
    except: return False

def enviar_msg_chatwoot_con_fotos(conv_id, content, fotos):
    """Envía mensaje con attachments por Chatwoot usando multipart."""
    import subprocess
    cmd = ['curl', '-sk', '-X', 'POST',
           '-H', f'api_access_token: {CHATWOOT_TOKEN}',
           '-F', f'content={content}',
           '-F', 'message_type=outgoing',
           '-F', 'private=false']
    for foto in fotos:
        cmd.extend(['-F', f'attachments[]=@{foto};type=image/jpeg'])
    cmd.append(f'{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT}/conversations/{conv_id}/messages')
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0

def enviar_botones_interactivos(telefono):
    """Envía mensaje interactivo con 3 botones via Meta API."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product":"whatsapp","to":telefono,"type":"interactive",
        "interactive":{
            "type":"button",
            "header":{"type":"text","text":"Opciones para agencias"},
            "body":{"text":"Tenemos dos modelos de negocio. Elegí el que más te sirva y te explico en detalle:"},
            "footer":{"text":"Calzalindo - 35 años en el negocio"},
            "action":{"buttons":[
                {"type":"reply","reply":{"id":"btn_comision","title":"Comisión $20K/set"}},
                {"type":"reply","reply":{"id":"btn_mayorista","title":"Mayorista $100K/set"}},
                {"type":"reply","reply":{"id":"btn_fotos","title":"Ver más fotos"}}
            ]}
        }
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Authorization', f'Bearer {API_KEY}')
    req.add_header('Content-Type', 'application/json')
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        return True
    except: return False

MSG2_CONTENT = """📦 *SET DE 3 VALIJAS RIGIDAS GO*

✅ 3 tamaños: 18" (carry on) + 19" (cabina) + 21" (mediana)
✅ Material ABS ultra resistente
✅ 8 ruedas 360° (giran para todos lados)
✅ Cierre de seguridad TSA
✅ 4 colores: Negro, Rojo, Rosa Gold, Rosa
✅ Envío gratis a todo el país

💰 *Precio público:* $162.499 (o $129.999 transferencia)
💰 *6 cuotas sin interés:* $27.083/mes

Ideal para tus pasajeros: livianas, resistentes y con diseño premium."""

FOTOS = [
    "/tmp/valijas_imgs/set_negro.jpg",
    "/tmp/valijas_imgs/set_rosagold.jpg",
    "/tmp/valijas_imgs/interior_ruedas.jpeg"
]

def cargar_agencias(prioridad=None):
    df = pd.read_excel(EXCEL_PATH)
    agencias = []
    for _, row in df.iterrows():
        tel = normalizar_telefono(row.get('Telefono/WhatsApp'))
        if not tel: continue
        if prioridad and str(row.get('Prioridad','')).upper() != prioridad.upper(): continue
        agencias.append({'nombre':row['Nombre'],'ciudad':row.get('Ciudad',''),
            'telefono':tel,'prioridad':row.get('Prioridad',''),
            'primer_nombre':extraer_primer_nombre(str(row['Nombre']))})
    return agencias

def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    test_mode = '--test' in args
    if test_mode:
        agencias = [{'nombre':'Fernando Test','ciudad':'VT','telefono':FERNANDO_PHONE,
                      'prioridad':'TEST','primer_nombre':'Fernando'}]
    elif '--prioridad' in args:
        idx = args.index('--prioridad')
        prio = args[idx+1] if idx+1 < len(args) else 'ALTA'
        agencias = cargar_agencias(prioridad=prio)
    elif '--todas' in args:
        agencias = cargar_agencias()
    else:
        print("Uso:\n  --test\n  --prioridad ALTA\n  --todas\n  --dry-run --todas")
        return

    optout_phones = load_optout_phones()
    print(f"\n{'='*60}\nCAMPANA VALIJAS GO - WhatsApp Agencias\nTemplate: {TEMPLATE_NAME}\nAgencias: {len(agencias)} | Opt-outs cargados: {len(optout_phones)}\nModo: {'DRY RUN' if dry_run else 'ENVIO REAL'}\n{'='*60}\n")
    enviados, errores, saltados = 0, 0, 0
    for i, ag in enumerate(agencias):
        print(f"\n[{i+1}/{len(agencias)}] {ag['nombre']} ({ag['ciudad']}) -> {ag['telefono']}")

        # Verificar opt-out
        if is_optout(ag['telefono'], optout_phones):
            print(f"  -> SALTADO (opt-out registrado)")
            saltados += 1
            continue

        if dry_run:
            print("  -> [DRY RUN] MSG1 template + MSG2 info+fotos + MSG3 botones"); continue

        # MSG1: Template
        crear_contacto_chatwoot(ag['nombre'], ag['telefono'])
        ok, msg = enviar_template(ag['telefono'], ag['primer_nombre'])
        if not ok:
            print(f"  -> ERROR MSG1: {msg[:80]}"); errores += 1; continue
        print(f"  -> MSG1 OK (template)")
        enviados += 1
        time.sleep(4)

        # MSG2: Info + fotos via Chatwoot
        conv_id = buscar_conversacion_chatwoot(ag['telefono'])
        if conv_id:
            enviar_msg_chatwoot_con_fotos(conv_id, MSG2_CONTENT, FOTOS)
            print(f"  -> MSG2 OK (info+fotos)")
        else:
            print(f"  -> MSG2 SKIP (sin conversacion en Chatwoot)")
        time.sleep(4)

        # MSG3: Botones interactivos
        if enviar_botones_interactivos(ag['telefono']):
            print(f"  -> MSG3 OK (botones)")
        else:
            print(f"  -> MSG3 SKIP (botones interactivos)")

        if i < len(agencias)-1: time.sleep(5)
    print(f"\n{'='*60}\nRESULTADO: {enviados} enviados, {errores} errores, {saltados} saltados (opt-out)\n{'='*60}")

if __name__ == '__main__':
    main()
