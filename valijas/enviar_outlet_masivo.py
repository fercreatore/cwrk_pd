#!/usr/bin/env python3
"""
Envío masivo WhatsApp - Campaña Outlet Calzalindo Abril 2026
Usa Meta WhatsApp Cloud API via WABA Chatwoot (inbox 10, +5493462531170)

Uso:
  python3 enviar_outlet_masivo.py --test                          # Solo a Fernando
  python3 enviar_outlet_masivo.py --batch 500 --offset 0          # Primeros 500
  python3 enviar_outlet_masivo.py --batch 500 --offset 500        # Siguientes 500
  python3 enviar_outlet_masivo.py --batch 500 --offset 500 --dry-run  # Ver sin enviar
  python3 enviar_outlet_masivo.py --template outlet_calzalindo_abril  # Template familia
  python3 enviar_outlet_masivo.py --source all                    # Todos los contactos (no solo At Risk)
"""
import json, time, re, sys, os
from datetime import datetime
import urllib.request, urllib.error, ssl

# === CONFIG ===
API_KEY = "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40uQLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD"
PHONE_NUMBER_ID = "1024637650727570"
CHATWOOT_TOKEN = "zvQpseDYDoeqJpwM41GCb1LP"
CHATWOOT_URL = "https://chat.calzalindo.com.ar"
CHATWOOT_ACCOUNT = 3
CHATWOOT_INBOX = 10
FERNANDO_PHONE = "5493462672330"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AT_RISK_FILE = os.path.join(BASE_DIR, "at_risk_con_telefono.json")
ALL_CONTACTS_FILE = os.path.join(BASE_DIR, "contactos_whatsapp_calzalindo.json")
OPTOUT_FILE = os.path.join(BASE_DIR, "optout_list.json")

# Rate limiting
MSG_DELAY = 6        # segundos entre mensajes
PAUSE_EVERY_100 = 180  # 3 min cada 100 msgs
PAUSE_EVERY_500 = 600  # 10 min cada 500 msgs

def load_optout_phones():
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
    except:
        return set()

def is_optout(telefono, optout_phones):
    tel = telefono.lstrip("+").strip()
    return tel in optout_phones or (len(tel) >= 8 and tel[-8:] in optout_phones)

def load_sent_phones():
    """Carga todos los teléfonos ya enviados de logs anteriores + master list."""
    sent = set()
    master = os.path.join(BASE_DIR, "phones_already_sent.json")
    if os.path.exists(master):
        try:
            with open(master, encoding="utf-8") as f:
                sent.update(json.load(f))
        except: pass
    for f in os.listdir(BASE_DIR):
        if (f.startswith("log_batch") or f.startswith("log_pascuas")) and f.endswith(".json"):
            try:
                with open(os.path.join(BASE_DIR, f), encoding="utf-8") as fh:
                    data = json.load(fh)
                for r in data:
                    if r.get("status") == "sent":
                        sent.add(r.get("telefono", ""))
            except:
                pass
    return sent

def enviar_template(telefono, nombre, template_name, template_lang="es_AR"):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": template_lang},
            "components": [{"type": "body", "parameters": [{"type": "text", "text": nombre}]}]
        }
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Authorization', f'Bearer {API_KEY}')
    req.add_header('Content-Type', 'application/json')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    # Retry hasta 3 veces ante errores de red
    for intento in range(3):
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=30)
            result = json.loads(resp.read().decode())
            return True, result.get('messages', [{}])[0].get('id', 'ok')
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            if '429' in str(e.code) or 'rate' in body.lower():
                return False, f"RATE_LIMIT: {body}"
            return False, body
        except Exception as e:
            if intento < 2:
                time.sleep(10 * (intento + 1))  # 10s, 20s
                # Recrear request (se consume con urlopen)
                req = urllib.request.Request(url, data=data, method='POST')
                req.add_header('Authorization', f'Bearer {API_KEY}')
                req.add_header('Content-Type', 'application/json')
                continue
            return False, f"EXCEPTION: {str(e)[:200]}"

def extraer_primer_nombre(nombre):
    if not nombre:
        return ""
    nombre = str(nombre).strip()
    # Formato "APELLIDO, NOMBRE"
    if ',' in nombre:
        parts = nombre.split(',')
        if len(parts) >= 2:
            after_comma = parts[1].strip()
            if after_comma:
                words = after_comma.split()
                if words:
                    return words[0].title()
        return ""
    # Formato "APELLIDO NOMBRE" (sin coma) — segundo word es el nombre
    words = nombre.split()
    if len(words) >= 2:
        return words[1].title()
    # Solo una palabra → usar genérico
    return "🐣"

def load_contacts(source="at_risk"):
    if source == "all":
        filepath = ALL_CONTACTS_FILE
    else:
        filepath = AT_RISK_FILE
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)

def main():
    args = sys.argv[1:]

    # Parse args
    dry_run = '--dry-run' in args
    test_mode = '--test' in args
    batch_size = 500
    offset = 0
    template_name = "outlet_te_extranamos"  # Default: At Risk
    source = "at_risk"

    if '--batch' in args:
        idx = args.index('--batch')
        batch_size = int(args[idx + 1])
    if '--offset' in args:
        idx = args.index('--offset')
        offset = int(args[idx + 1])
    if '--template' in args:
        idx = args.index('--template')
        template_name = args[idx + 1]
    if '--source' in args:
        idx = args.index('--source')
        source = args[idx + 1]

    if test_mode:
        contacts = [{"telefono": FERNANDO_PHONE, "nombre": "Fernando Test", "cuenta": "TEST"}]
        offset = 0
        batch_size = 1
    else:
        contacts = load_contacts(source)

    # Filtrar ya enviados y opt-out
    sent_phones = load_sent_phones()
    optout_phones = load_optout_phones()

    # Filtrar por zona outlet (solo VT + alrededores, NO Junín)
    ZONA_OUTLET_PREFIXES = ('549346',)  # VT, Firmat, Rufino, etc.
    EXCLUIR_PREFIXES = ('549236', '54911', '549341', '549351')  # Junín, CABA, Rosario, Córdoba

    eligible = []
    for c in contacts:
        tel = c.get("telefono", c.get("telefono_whatsapp", c.get("telefono_normalizado", "")))
        if not tel:
            continue
        if tel in sent_phones:
            continue
        if is_optout(tel, optout_phones):
            continue
        # Filtro zona: solo VT y alrededores
        if not any(tel.startswith(p) for p in ZONA_OUTLET_PREFIXES):
            continue
        eligible.append(c)

    # Aplicar offset y batch
    batch = eligible[offset:offset + batch_size]

    # Detectar batch number
    batch_num = len([f for f in os.listdir(BASE_DIR) if f.startswith("log_batch") and f.endswith(".json")]) + 1

    now = datetime.now()
    hour = now.hour
    if hour < 8 or hour >= 21:
        print(f"Fuera de horario (8-21hs). Son las {now.strftime('%H:%M')}. Esperando hasta las 8:00...")
        while True:
            now = datetime.now()
            if 8 <= now.hour < 21:
                print(f"Son las {now.strftime('%H:%M')}. Arrancando envío!")
                break
            time.sleep(300)  # Check cada 5 minutos

    print(f"""
{'='*60}
CAMPANA OUTLET CALZALINDO - Batch {batch_num}
Template: {template_name}
Contactos elegibles: {len(eligible)} (de {len(contacts)} totales)
Ya enviados: {len(sent_phones)} | Opt-out: {len(optout_phones)}
Batch: {len(batch)} contactos (offset {offset})
Modo: {'DRY RUN' if dry_run else 'ENVIO REAL'}
Hora: {now.strftime('%H:%M')}
{'='*60}
""")

    if not batch:
        print("No hay contactos para enviar en este rango.")
        return

    log = []
    enviados, errores, saltados = 0, 0, 0
    start_time = time.time()

    for i, c in enumerate(batch):
        # Check horario — parar a las 21hs
        now_hour = datetime.now().hour
        if now_hour >= 21 or now_hour < 8:
            print(f"\n⏰ Son las {datetime.now().strftime('%H:%M')}. Parando hasta mañana 8:00.")
            break

        tel = c.get("telefono", c.get("telefono_whatsapp", c.get("telefono_normalizado", "")))
        nombre = c.get("nombre", "amigo/a")
        primer_nombre = extraer_primer_nombre(nombre)

        print(f"[{i+1}/{len(batch)}] {nombre} -> {tel}", end=" ")

        if dry_run:
            print("[DRY RUN]")
            log.append({"telefono": tel, "nombre": nombre, "status": "dry_run"})
            continue

        try:
            ok, msg_id = enviar_template(tel, primer_nombre, template_name)
        except Exception as e:
            ok, msg_id = False, f"EXCEPTION: {str(e)[:100]}"

        if ok:
            print(f"OK ({msg_id[:20]}...)")
            log.append({"telefono": tel, "nombre": nombre, "status": "sent", "msg_id": msg_id, "ts": datetime.now().isoformat()})
            enviados += 1
        else:
            if "RATE_LIMIT" in str(msg_id):
                print(f"RATE LIMIT - esperando 60s...")
                time.sleep(60)
                ok, msg_id = enviar_template(tel, primer_nombre, template_name)
                if ok:
                    print(f"  RETRY OK")
                    log.append({"telefono": tel, "nombre": nombre, "status": "sent", "msg_id": msg_id, "ts": datetime.now().isoformat()})
                    enviados += 1
                else:
                    print(f"  RETRY FAIL: {str(msg_id)[:60]}")
                    log.append({"telefono": tel, "nombre": nombre, "status": "error", "error": str(msg_id)[:200]})
                    errores += 1
            else:
                print(f"ERROR: {str(msg_id)[:60]}")
                log.append({"telefono": tel, "nombre": nombre, "status": "error", "error": str(msg_id)[:200]})
                errores += 1
                # Si hay muchos errores seguidos, parar
                recent_errors = sum(1 for l in log[-10:] if l.get("status") == "error")
                if recent_errors >= 5:
                    print("\n!!! 5 errores en los ultimos 10 envios. PARANDO por seguridad.")
                    break

        # Rate limiting
        if not dry_run and i < len(batch) - 1:
            time.sleep(MSG_DELAY)
            if (i + 1) % 500 == 0:
                print(f"\n--- Pausa de {PAUSE_EVERY_500//60} min (cada 500) ---")
                time.sleep(PAUSE_EVERY_500)
            elif (i + 1) % 100 == 0:
                print(f"\n--- Pausa de {PAUSE_EVERY_100//60} min (cada 100) ---")
                time.sleep(PAUSE_EVERY_100)

    elapsed = time.time() - start_time

    # Guardar log
    if not dry_run:
        log_file = os.path.join(BASE_DIR, f"log_batch{batch_num}_outlet.json")
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        print(f"\nLog guardado: {log_file}")

    print(f"""
{'='*60}
RESULTADO Batch {batch_num}:
  Enviados: {enviados}
  Errores: {errores}
  Tiempo: {elapsed/60:.1f} minutos
  Quedan: {len(eligible) - offset - len(batch)} contactos por enviar
{'='*60}
""")

if __name__ == '__main__':
    main()
