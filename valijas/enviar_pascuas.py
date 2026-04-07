#!/usr/bin/env python3
"""
Envío masivo Felices Pascuas + Outlet — Calzalindo
Template: felices_pascuas_outlet
Contactos: 30,020 (todos menos At Risk que ya recibieron otro template)

Uso:
  python3 enviar_pascuas.py --test              # Solo Fernando
  python3 enviar_pascuas.py --batch 1000        # Primeros 1000
  python3 enviar_pascuas.py --batch 1000 --dry-run  # Ver sin enviar
"""
import json, time, sys, os, glob
from datetime import datetime
import urllib.request, urllib.error, ssl

API_KEY = "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40uQLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD"
PHONE_NUMBER_ID = "1024637650727570"
TEMPLATE_NAME = "felices_pascuas_outlet"
TEMPLATE_LANG = "es_AR"
FERNANDO_PHONE = "5493462672330"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTACTS_FILE = os.path.join(BASE_DIR, "contactos_zona_outlet.json")
OPTOUT_FILE = os.path.join(BASE_DIR, "optout_list.json")

try:
    import pyodbc
    HAS_PYODBC = True
except ImportError:
    HAS_PYODBC = False

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
    # Master list
    master = os.path.join(BASE_DIR, "phones_already_sent.json")
    if os.path.exists(master):
        try:
            with open(master) as f:
                sent.update(json.load(f))
        except: pass
    # All log files
    for f in glob.glob(os.path.join(BASE_DIR, "log_pascuas_*.json")) + glob.glob(os.path.join(BASE_DIR, "log_batch*.json")):
        try:
            with open(f) as fh:
                for r in json.load(fh):
                    if r.get("status") == "sent":
                        sent.add(r.get("telefono",""))
        except: pass
    return sent

def extraer_nombre(nombre):
    if not nombre: return ""
    nombre = str(nombre).strip()
    # Formato "APELLIDO, NOMBRE SEGUNDO"
    if ',' in nombre:
        parts = nombre.split(',')
        if len(parts) >= 2:
            after = parts[1].strip()
            if after:
                return after.split()[0].title()
        # Solo apellido con coma → no usar nombre
        return ""
    # Formato "APELLIDO NOMBRE" (sin coma) — tomar el SEGUNDO word
    words = nombre.split()
    if len(words) >= 2:
        # Si todo es mayúscula, es APELLIDO NOMBRE → segundo
        # Si mixto (Arellano Sandra), también segundo
        return words[1].title()
    # Solo una palabra (solo apellido) → usar genérico
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
        with open(CONTACTS_FILE) as f:
            contacts = json.load(f)

    sent = load_sent()
    optout = load_optout()
    eligible = [c for c in contacts
                if c.get("telefono_whatsapp")
                and c["telefono_whatsapp"] not in sent
                and c["telefono_whatsapp"] not in optout]

    batch = eligible[:batch_size]
    batch_num = len(glob.glob(os.path.join(BASE_DIR, "log_pascuas_*.json"))) + 1

    print(f"""
{'='*60}
FELICES PASCUAS + OUTLET — Batch {batch_num}
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

    # Conexión SQL Server para tracking
    sql_conn = None
    if HAS_PYODBC:
        try:
            os.environ.setdefault('OPENSSL_CONF', '/tmp/openssl_legacy.cnf')
            if not os.path.exists('/tmp/openssl_legacy.cnf'):
                with open('/tmp/openssl_legacy.cnf', 'w') as f:
                    f.write('[openssl_init]\nssl_conf = ssl_sect\n[ssl_sect]\nsystem_default = system_default_sect\n[system_default_sect]\nMinProtocol = TLSv1\nCipherString = DEFAULT@SECLEVEL=0\n')
            sql_conn = pyodbc.connect(
                'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.2.112;'
                'DATABASE=clz_ventas_SQL;UID=meta106;PWD=Meta106#;TrustServerCertificate=yes', timeout=10)
            print("SQL tracking: conectado al 112")
        except Exception as e:
            print(f"SQL tracking: no disponible ({e})")
            sql_conn = None

    # Master list para actualizar en tiempo real
    master_file = os.path.join(BASE_DIR, "phones_already_sent.json")

    log = []
    enviados, errores = 0, 0
    start = time.time()

    for i, c in enumerate(batch):
        tel = c["telefono_whatsapp"]
        nombre = extraer_nombre(c.get("nombre"))
        print(f"[{i+1}/{len(batch)}] {c.get('nombre','?')[:30]} -> {tel}", end=" ")

        if dry_run:
            print("[DRY RUN]")
            continue

        ok, msg_id = enviar(tel, nombre)
        if ok:
            print(f"OK")
            log.append({"telefono": tel, "nombre": c.get("nombre"), "status": "sent", "msg_id": msg_id, "ts": datetime.now().isoformat()})
            enviados += 1
            # Tracking SQL
            if sql_conn:
                try:
                    sql_conn.cursor().execute(
                        "INSERT INTO campana_whatsapp_tracking (telefono,nombre,template_enviado,campana) VALUES (?,?,?,?)",
                        tel, c.get("nombre",""), TEMPLATE_NAME, "outlet_abril_2026")
                    sql_conn.commit()
                except: pass
            # Actualizar master list
            sent.add(tel)
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
        logfile = os.path.join(BASE_DIR, f"log_pascuas_{batch_num}.json")
        with open(logfile, "w") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        print(f"\nLog: {logfile}")
        # Actualizar master list
        try:
            with open(master_file, "w") as f:
                json.dump(sorted(sent), f)
            print(f"Master list actualizado: {len(sent)} teléfonos")
        except: pass

    if sql_conn:
        try: sql_conn.close()
        except: pass

    print(f"""
{'='*60}
RESULTADO Pascuas Batch {batch_num}:
  Enviados: {enviados} | Errores: {errores}
  Tiempo: {elapsed/60:.1f} min
  Quedan: {len(eligible) - len(batch)}
{'='*60}
""")

if __name__ == '__main__':
    main()
