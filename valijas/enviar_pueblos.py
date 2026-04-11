#!/usr/bin/env python3
"""
Envío a pueblos de la zona VT — outlet 9-12 abril
Contactos sin enviar previamente, filtrados por código postal.
"""
import json, time, sys, os, re
from datetime import datetime
import urllib.request, urllib.error, ssl

API_KEY = "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40uQLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD"
PHONE_NUMBER_ID = "1024637650727570"
TEMPLATE = "outlet_calzalindo_abril"
LANG = "es_AR"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONTACTS_FILE = os.path.join(SCRIPT_DIR, "contactos_pueblos_outlet.json")
MASTER_SENT = os.path.join(SCRIPT_DIR, "phones_already_sent.json")
OPTOUT = os.path.join(SCRIPT_DIR, "optout_list.json")

def extraer_primer_nombre(nombre):
    if not nombre:
        return "🐣"
    nombre = str(nombre).strip()
    if "," in nombre:
        partes = nombre.split(",", 1)
        if len(partes) > 1 and partes[1].strip():
            return partes[1].strip().split()[0].title()
    words = nombre.split()
    if len(words) >= 2:
        return words[1].title()
    if words:
        return words[0].title()
    return "🐣"

def enviar_template(telefono, nombre):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {
            "name": TEMPLATE,
            "language": {"code": LANG},
            "components": [{"type": "body", "parameters": [{"type": "text", "text": nombre}]}]
        }
    }
    data = json.dumps(payload).encode()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for intento in range(3):
        try:
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header('Authorization', f'Bearer {API_KEY}')
            req.add_header('Content-Type', 'application/json')
            resp = urllib.request.urlopen(req, context=ctx, timeout=30)
            result = json.loads(resp.read().decode())
            return True, result.get('messages', [{}])[0].get('id', 'ok')
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            return False, body
        except Exception as e:
            if intento < 2:
                time.sleep(10 * (intento + 1))
                continue
            return False, f"EXCEPTION: {str(e)[:200]}"

def load_sent():
    sent = set()
    if os.path.exists(MASTER_SENT):
        try:
            with open(MASTER_SENT, encoding='utf-8') as f:
                sent.update(json.load(f))
        except: pass
    return sent

def load_optout():
    optouts = set()
    if os.path.exists(OPTOUT):
        try:
            with open(OPTOUT, encoding='utf-8') as f:
                for d in json.load(f):
                    optouts.add(d.get('telefono', '').lstrip('+').strip())
        except: pass
    return optouts

def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    limit = 2500
    pueblo_filtro = None
    
    if '--limit' in args:
        idx = args.index('--limit')
        limit = int(args[idx + 1])
    if '--pueblo' in args:
        idx = args.index('--pueblo')
        pueblo_filtro = args[idx + 1].upper()
    
    with open(CONTACTS_FILE, encoding='utf-8') as f:
        contacts = json.load(f)
    
    sent_phones = load_sent()
    optout_phones = load_optout()
    
    eligible = []
    for c in contacts:
        tel = c.get('telefono_whatsapp', '')
        if not tel: continue
        if tel in sent_phones: continue
        if tel in optout_phones: continue
        if pueblo_filtro and c.get('pueblo', '').upper() != pueblo_filtro: continue
        eligible.append(c)
    
    now = datetime.now()
    hour = now.hour
    if hour < 8 or hour >= 21:
        print(f"Fuera de horario (8-21). Son las {now.strftime('%H:%M')}. Esperando 8:00...")
        while True:
            now = datetime.now()
            if 8 <= now.hour < 21:
                print(f"Son las {now.strftime('%H:%M')}. Arrancando!")
                break
            time.sleep(300)
    
    batch = eligible[:limit]
    
    print(f"{'='*60}")
    print(f"CAMPAÑA PUEBLOS — Outlet Calzalindo")
    print(f"Template: {TEMPLATE}")
    print(f"Eligibles: {len(eligible):,}")
    print(f"Ya enviados (master): {len(sent_phones):,}")
    print(f"Opt-out: {len(optout_phones):,}")
    print(f"Batch: {len(batch):,}")
    print(f"Modo: {'DRY RUN' if dry_run else 'ENVÍO REAL'}")
    print(f"{'='*60}\n")
    
    if dry_run:
        from collections import Counter
        c = Counter(b['pueblo'] for b in batch)
        for p, n in c.most_common():
            print(f"  {p}: {n}")
        return
    
    enviados = 0
    errores = 0
    
    for i, c in enumerate(batch):
        # Check hora
        if datetime.now().hour >= 21 or datetime.now().hour < 8:
            print(f"\n⏰ {datetime.now().strftime('%H:%M')} — Fuera de horario. Parando.")
            break
        
        tel = c['telefono_whatsapp']
        nombre = c.get('nombre', 'amigo')
        primer_nombre = extraer_primer_nombre(nombre)
        pueblo = c.get('pueblo', '?')
        
        print(f"[{i+1}/{len(batch)}] {pueblo[:10]:<10} {nombre[:25]:<25} -> {tel}", end=" ")
        
        ok, resp = enviar_template(tel, primer_nombre)
        if ok:
            print(f"OK ({resp[:25]}...)")
            enviados += 1
            sent_phones.add(tel)
            # Save master list after each
            if enviados % 10 == 0:
                with open(MASTER_SENT, 'w', encoding='utf-8') as f:
                    json.dump(sorted(sent_phones), f)
        else:
            print(f"ERROR: {resp[:80]}")
            errores += 1
        
        # Rate limit
        time.sleep(6)
        if (i + 1) % 100 == 0:
            print(f"\n--- Pausa 3 min (cada 100) ---")
            time.sleep(180)
        if (i + 1) % 500 == 0:
            print(f"\n--- Pausa 15 min (cada 500) ---")
            time.sleep(900)
    
    # Save final
    with open(MASTER_SENT, 'w', encoding='utf-8') as f:
        json.dump(sorted(sent_phones), f)
    
    print(f"\n{'='*60}")
    print(f"RESULTADO: {enviados} enviados, {errores} errores")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
