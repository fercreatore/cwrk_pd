#!/usr/bin/env python3
"""
Envio masivo Pascuas Junin — Envio Gratis — Calzalindo
Template: pascuas_junin_envio_gratis
Contactos: 7,439 de Junin (549236*) + At Risk de Junin

Uso:
  python3 enviar_pascuas_junin.py --test              # Solo Fernando
  python3 enviar_pascuas_junin.py --batch 1000        # Primeros 1000
  python3 enviar_pascuas_junin.py --batch 1000 --dry-run  # Ver sin enviar
"""
import json, time, sys, os, glob
from datetime import datetime
import urllib.request, urllib.error, ssl

API_KEY = "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40uQLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD"
PHONE_NUMBER_ID = "1024637650727570"
TEMPLATE_NAME = "pascuas_junin_envio_gratis"
TEMPLATE_LANG = "es_AR"
FERNANDO_PHONE = "5493462672330"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTACTS_FILE = os.path.join(BASE_DIR, "contactos_pascuas_junin.json")
AT_RISK_FILE = os.path.join(BASE_DIR, "at_risk_con_telefono.json")
OPTOUT_FILE = os.path.join(BASE_DIR, "optout_list.json")

MSG_DELAY = 6
PAUSE_EVERY_100 = 180
PAUSE_EVERY_500 = 600

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
    sent = set()
    for f in glob.glob(os.path.join(BASE_DIR, "log_pascuas_junin_*.json")):
        try:
            with open(f) as fh:
                for r in json.load(fh):
                    if r.get("status") == "sent":
                        sent.add(r["telefono"])
        except: pass
    return sent

def load_contacts():
    """Carga contactos de Junin + At Risk de Junin (deduplicados por telefono)."""
    # 1) Contactos principales de Junin
    with open(CONTACTS_FILE) as f:
        contacts = json.load(f)

    phones_seen = set(c["telefono_whatsapp"] for c in contacts if c.get("telefono_whatsapp"))

    # 2) At Risk de Junin (telefono empieza con 549236)
    at_risk_added = 0
    if os.path.exists(AT_RISK_FILE):
        with open(AT_RISK_FILE) as f:
            at_risk = json.load(f)
        for ar in at_risk:
            tel = ar.get("telefono", "")
            if tel.startswith("549236") and tel not in phones_seen:
                contacts.append({
                    "telefono_whatsapp": tel,
                    "nombre": ar.get("nombre", ""),
                    "fuente": "at_risk"
                })
                phones_seen.add(tel)
                at_risk_added += 1

    print(f"Contactos Junin: {len(contacts) - at_risk_added} base + {at_risk_added} at_risk = {len(contacts)} total")
    return contacts

def extraer_nombre(nombre):
    if not nombre: return ""
    nombre = str(nombre).strip()
    if ',' in nombre:
        parts = nombre.split(',')
        if len(parts) >= 2:
            after = parts[1].strip()
            if after:
                return after.split()[0].title()
        return "🐣"
    words = nombre.split()
    if len(words) >= 2:
        return words[1].title()
    return "🐣"

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
        body = e.read().decode()[:300]
        return False, body
    except Exception as e:
        return False, f"EXCEPTION: {str(e)[:100]}"

def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    test_mode = '--test' in args
    batch_size = 1000

    if '--batch' in args:
        idx = args.index('--batch')
        batch_size = int(args[idx + 1])

    if test_mode:
        contacts = [{"telefono_whatsapp": FERNANDO_PHONE, "nombre": "Fernando Test"}]
    else:
        contacts = load_contacts()

    sent = load_sent()
    optout = load_optout()
    eligible = [c for c in contacts
                if c.get("telefono_whatsapp")
                and c["telefono_whatsapp"] not in sent
                and c["telefono_whatsapp"] not in optout]

    batch = eligible[:batch_size]
    batch_num = len(glob.glob(os.path.join(BASE_DIR, "log_pascuas_junin_*.json"))) + 1

    print(f"""
{'='*60}
PASCUAS JUNIN ENVIO GRATIS — Batch {batch_num}
Template: {TEMPLATE_NAME}
Elegibles: {len(eligible)} | Ya enviados: {len(sent)} | Opt-out: {len(optout)}
Este batch: {len(batch)} contactos
Modo: {'DRY RUN' if dry_run else 'ENVIO REAL'}
Hora: {datetime.now().strftime('%H:%M')}
{'='*60}
""")

    if not batch:
        print("No hay contactos para enviar.")
        return

    log = []
    enviados, errores = 0, 0
    start = time.time()

    for i, c in enumerate(batch):
        tel = c["telefono_whatsapp"]
        nombre = extraer_nombre(c.get("nombre"))
        fuente = f" [at_risk]" if c.get("fuente") == "at_risk" else ""
        print(f"[{i+1}/{len(batch)}] {c.get('nombre','?')[:30]}{fuente} -> {tel}", end=" ")

        if dry_run:
            print("[DRY RUN]")
            continue

        ok, msg_id = enviar(tel, nombre)
        if ok:
            print(f"OK")
            log.append({"telefono": tel, "nombre": c.get("nombre"), "status": "sent", "msg_id": msg_id, "ts": datetime.now().isoformat()})
            enviados += 1
        else:
            if "rate" in str(msg_id).lower() or "429" in str(msg_id):
                print("RATE LIMIT — pausa 60s")
                time.sleep(60)
                ok, msg_id = enviar(tel, nombre)
                if ok:
                    print(f"  RETRY OK")
                    log.append({"telefono": tel, "nombre": c.get("nombre"), "status": "sent", "msg_id": msg_id, "ts": datetime.now().isoformat()})
                    enviados += 1
                else:
                    print(f"  RETRY FAIL")
                    log.append({"telefono": tel, "nombre": c.get("nombre"), "status": "error", "error": str(msg_id)[:200]})
                    errores += 1
            else:
                print(f"ERROR: {str(msg_id)[:60]}")
                log.append({"telefono": tel, "nombre": c.get("nombre"), "status": "error", "error": str(msg_id)[:200]})
                errores += 1
                if sum(1 for l in log[-10:] if l.get("status")=="error") >= 5:
                    print("\n!!! 5 errores en 10 — PARANDO")
                    break

        if not dry_run and i < len(batch)-1:
            time.sleep(MSG_DELAY)
            if (i+1) % 500 == 0:
                print(f"\n--- Pausa 10 min (cada 500) ---")
                time.sleep(PAUSE_EVERY_500)
            elif (i+1) % 100 == 0:
                print(f"\n--- Pausa 3 min (cada 100) ---")
                time.sleep(PAUSE_EVERY_100)

    elapsed = time.time() - start
    if not dry_run and log:
        logfile = os.path.join(BASE_DIR, f"log_pascuas_junin_{batch_num}.json")
        with open(logfile, "w") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        print(f"\nLog: {logfile}")

    print(f"""
{'='*60}
RESULTADO Pascuas Junin Batch {batch_num}:
  Enviados: {enviados} | Errores: {errores}
  Tiempo: {elapsed/60:.1f} min
  Quedan: {len(eligible) - len(batch)}
{'='*60}
""")

if __name__ == '__main__':
    main()
