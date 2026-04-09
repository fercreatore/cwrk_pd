#!/usr/bin/env python3
"""
Envío personalizado WhatsApp — Campaña Inteligente Junín
Envía mensajes personalizados por marca a clientes que compraron esa marca.

Template Meta: novedades_marca_junin (2 params: {{1}}=nombre, {{2}}=marca)
  "Hola {{1}}! Llegaron novedades de {{2}} a Calzalindo Junín.
   Sabemos que te gusta esa marca. Pasá a verlas o escribinos para fotos."
  Botones: "Mandame fotos" / "Qué más llegó?"

Uso:
  python3 enviar_junin_personalizado.py --test                    # Solo a Fernando
  python3 enviar_junin_personalizado.py --marca TOPPER --batch 100  # 100 clientes de TOPPER
  python3 enviar_junin_personalizado.py --top 5 --batch 200       # Top 5 marcas, 200 c/u
  python3 enviar_junin_personalizado.py --top 5 --batch 200 --dry-run
  python3 enviar_junin_personalizado.py --stats                   # Solo mostrar estadísticas
"""
import json, time, sys, os, glob
from datetime import datetime
import urllib.request, urllib.error, ssl

# === CONFIG ===
API_KEY = "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40uQLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD"
PHONE_NUMBER_ID = "1024637650727570"
TEMPLATE_NAME = "novedades_marca_junin"
TEMPLATE_LANG = "es_AR"
FERNANDO_PHONE = "5493462672330"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEGMENTOS_FILE = os.path.join(BASE_DIR, "segmentos_junin.json")
OPTOUT_FILE = os.path.join(BASE_DIR, "optout_list.json")

# Rate limiting
MSG_DELAY = 6           # 6s entre mensajes
PAUSE_EVERY_100 = 180   # 3 min cada 100
PAUSE_EVERY_500 = 600   # 10 min cada 500
WEEKLY_LIMIT = 2427     # Presupuesto semanal

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def load_optout():
    if not os.path.exists(OPTOUT_FILE):
        return set()
    try:
        with open(OPTOUT_FILE) as f:
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


def load_sent():
    """Carga todos los teléfonos ya enviados (todas las campañas)."""
    sent = set()
    master = os.path.join(BASE_DIR, "phones_already_sent.json")
    if os.path.exists(master):
        try:
            with open(master) as f:
                sent.update(json.load(f))
        except:
            pass
    for f in os.listdir(BASE_DIR):
        if f.startswith("log_") and f.endswith(".json"):
            try:
                with open(os.path.join(BASE_DIR, f)) as fh:
                    data = json.load(fh)
                for r in data:
                    if r.get("status") == "sent":
                        sent.add(r.get("telefono", ""))
            except:
                pass
    return sent


def load_sent_this_campaign():
    """Carga teléfonos ya enviados en ESTA campaña (junin_personalizado)."""
    sent = {}  # telefono -> {marca, ts}
    for f in sorted(os.listdir(BASE_DIR)):
        if f.startswith("log_junin_") and f.endswith(".json"):
            try:
                with open(os.path.join(BASE_DIR, f)) as fh:
                    data = json.load(fh)
                for r in data:
                    if r.get("status") == "sent":
                        sent[r["telefono"]] = {"marca": r.get("marca", ""), "ts": r.get("ts", "")}
            except:
                pass
    return sent


def count_sent_this_week():
    """Cuenta mensajes enviados esta semana (lun-dom) en todas las campañas."""
    from datetime import timedelta
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    count = 0
    for f in os.listdir(BASE_DIR):
        if f.startswith("log_") and f.endswith(".json"):
            try:
                with open(os.path.join(BASE_DIR, f)) as fh:
                    data = json.load(fh)
                for r in data:
                    if r.get("status") == "sent" and r.get("ts"):
                        ts_date = datetime.fromisoformat(r["ts"]).date()
                        if ts_date >= monday:
                            count += 1
            except:
                pass
    return count


def enviar_template(telefono, nombre, marca):
    """Envía template con 2 parámetros: nombre y marca."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANG},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": nombre},
                    {"type": "text", "text": marca}
                ]
            }]
        }
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Authorization', f'Bearer {API_KEY}')
    req.add_header('Content-Type', 'application/json')
    try:
        resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=30)
        result = json.loads(resp.read().decode())
        return True, result.get('messages', [{}])[0].get('id', 'ok')
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        if '429' in str(e.code) or 'rate' in body.lower():
            return False, f"RATE_LIMIT: {body}"
        return False, body
    except Exception as e:
        return False, f"EXCEPTION: {str(e)[:200]}"


def load_segmentos():
    with open(SEGMENTOS_FILE) as f:
        return json.load(f)


def show_stats(segmentos_data):
    """Muestra estadísticas de los segmentos."""
    sent_campaign = load_sent_this_campaign()
    sent_all = load_sent()
    optout = load_optout()
    week_count = count_sent_this_week()

    print(f"\n{'='*70}")
    print(f"ESTADÍSTICAS CAMPAÑA INTELIGENTE JUNÍN")
    print(f"Generado: {segmentos_data['generado']}")
    print(f"{'='*70}")
    print(f"\nMensajes esta semana: {week_count}/{WEEKLY_LIMIT}")
    print(f"Quedan esta semana: {WEEKLY_LIMIT - week_count}")
    print(f"Teléfonos ya campaneados (todas): {len(sent_all)}")
    print(f"Enviados en esta campaña: {len(sent_campaign)}")
    print(f"Opt-outs: {len(optout)}")

    print(f"\n{'Marca':<25} {'Total':>6} {'C/Tel':>6} {'Eleg':>6} {'Enviados':>9} {'Stock':>7}")
    print("-" * 65)

    total_elegibles = 0
    for seg in segmentos_data["segmentos"]:
        marca = seg["marca"]
        total = seg["stats"]["total_clientes"]
        con_tel = seg["stats"]["con_telefono"]

        # Recalcular elegibles excluyendo enviados de esta campaña y opt-outs
        elegibles = 0
        for c in seg["clientes"]:
            tel = c["telefono"]
            if tel not in sent_campaign and tel not in sent_all and not is_optout(tel, optout):
                elegibles += 1

        enviados_marca = sum(1 for t, d in sent_campaign.items() if d.get("marca") == marca)
        stock = seg.get("stock_actual", {}).get("total", 0)

        print(f"{marca:<25} {total:>6} {con_tel:>6} {elegibles:>6} {enviados_marca:>9} {stock:>7}")
        total_elegibles += elegibles

    print(f"\n  TOTAL ELEGIBLES: {total_elegibles}")
    print(f"  PRESUPUESTO SEMANAL RESTANTE: {WEEKLY_LIMIT - week_count}")


def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    test_mode = '--test' in args
    stats_mode = '--stats' in args

    segmentos_data = load_segmentos()

    if stats_mode:
        show_stats(segmentos_data)
        return

    # Parse args
    batch_size = 100
    target_marcas = []
    top_n = None

    if '--batch' in args:
        idx = args.index('--batch')
        batch_size = int(args[idx + 1])
    if '--marca' in args:
        idx = args.index('--marca')
        target_marcas = [args[idx + 1].upper()]
    if '--top' in args:
        idx = args.index('--top')
        top_n = int(args[idx + 1])

    if test_mode:
        # Enviar a Fernando con marca de prueba
        print("MODO TEST: enviando a Fernando")
        ok, msg = enviar_template(FERNANDO_PHONE, "Fernando", "TOPPER")
        print(f"  Resultado: {'OK' if ok else 'ERROR'} — {msg}")
        return

    # Cargar filtros
    sent_all = load_sent()
    sent_campaign = load_sent_this_campaign()
    optout = load_optout()
    week_count = count_sent_this_week()
    remaining_week = WEEKLY_LIMIT - week_count

    if remaining_week <= 0:
        print(f"PRESUPUESTO SEMANAL AGOTADO ({week_count}/{WEEKLY_LIMIT}). Esperar al lunes.")
        return

    # Seleccionar marcas
    segmentos = segmentos_data["segmentos"]
    if target_marcas:
        segmentos = [s for s in segmentos if s["marca"].upper() in target_marcas]
    elif top_n:
        # Solo marcas con stock
        segmentos = [s for s in segmentos if s.get("stock_actual", {}).get("total", 0) > 0][:top_n]

    if not segmentos:
        print("No hay segmentos que matcheen los filtros.")
        return

    # Preparar cola de envío: priorizar por total_gastado DESC (mejores clientes primero)
    cola = []
    for seg in segmentos:
        marca = seg["marca"]
        stock = seg.get("stock_actual", {}).get("total", 0)
        if stock == 0:
            print(f"  {marca}: sin stock, saltando")
            continue

        for c in seg["clientes"]:
            tel = c["telefono"]
            if tel in sent_all or tel in sent_campaign:
                continue
            if is_optout(tel, optout):
                continue
            cola.append({
                "telefono": tel,
                "nombre": c["primer_nombre"],
                "nombre_completo": c["nombre"],
                "marca": marca,
                "total_gastado": c["total_gastado"],
                "ultima_compra": c["ultima_compra"],
                "cuenta": c["cuenta"]
            })

    # Ordenar: mayor gasto primero (mejores clientes = más probable que compren)
    cola.sort(key=lambda x: x["total_gastado"], reverse=True)

    # Limitar al batch y presupuesto semanal
    cola = cola[:min(batch_size, remaining_week)]

    # Detectar batch number
    batch_num = len([f for f in os.listdir(BASE_DIR) if f.startswith("log_junin_") and f.endswith(".json")]) + 1

    now = datetime.now()
    if now.hour < 8 or now.hour >= 21:
        print(f"ATENCION: Son las {now.strftime('%H:%M')}. Fuera de horario (8-21).")
        time.sleep(5)

    # Resumen por marca
    marcas_en_cola = {}
    for c in cola:
        marcas_en_cola[c["marca"]] = marcas_en_cola.get(c["marca"], 0) + 1

    print(f"""
{'='*60}
CAMPAÑA INTELIGENTE JUNÍN — Batch {batch_num}
Template: {TEMPLATE_NAME}
Cola: {len(cola)} mensajes | Presupuesto semana: {remaining_week}
Marcas: {', '.join(f'{m}({n})' for m, n in marcas_en_cola.items())}
Modo: {'DRY RUN' if dry_run else 'ENVÍO REAL'}
Hora: {now.strftime('%H:%M')}
{'='*60}
""")

    if not cola:
        print("No hay contactos elegibles para enviar.")
        return

    log = []
    enviados, errores = 0, 0
    start = time.time()

    for i, c in enumerate(cola):
        nombre_display = c["nombre_completo"][:30] if c["nombre_completo"] else c["nombre"]
        print(f"[{i+1}/{len(cola)}] {nombre_display} | {c['marca']} | ${c['total_gastado']:,.0f} -> {c['telefono']}", end=" ")

        if dry_run:
            print("[DRY RUN]")
            log.append({"telefono": c["telefono"], "nombre": c["nombre_completo"],
                        "marca": c["marca"], "status": "dry_run"})
            continue

        ok, msg_id = enviar_template(c["telefono"], c["nombre"], c["marca"])
        if ok:
            print("OK")
            log.append({
                "telefono": c["telefono"], "nombre": c["nombre_completo"],
                "marca": c["marca"], "cuenta": c["cuenta"],
                "total_gastado": c["total_gastado"],
                "status": "sent", "msg_id": msg_id,
                "ts": datetime.now().isoformat()
            })
            enviados += 1
        else:
            if "RATE_LIMIT" in str(msg_id):
                print("RATE LIMIT — pausa 60s")
                time.sleep(60)
                ok, msg_id = enviar_template(c["telefono"], c["nombre"], c["marca"])
                if ok:
                    print("  RETRY OK")
                    log.append({
                        "telefono": c["telefono"], "nombre": c["nombre_completo"],
                        "marca": c["marca"], "cuenta": c["cuenta"],
                        "total_gastado": c["total_gastado"],
                        "status": "sent", "msg_id": msg_id,
                        "ts": datetime.now().isoformat()
                    })
                    enviados += 1
                else:
                    print(f"  RETRY FAIL: {str(msg_id)[:60]}")
                    log.append({"telefono": c["telefono"], "nombre": c["nombre_completo"],
                                "marca": c["marca"], "status": "error", "error": str(msg_id)[:200]})
                    errores += 1
            else:
                print(f"ERROR: {str(msg_id)[:60]}")
                log.append({"telefono": c["telefono"], "nombre": c["nombre_completo"],
                            "marca": c["marca"], "status": "error", "error": str(msg_id)[:200]})
                errores += 1
                if sum(1 for l in log[-10:] if l.get("status") == "error") >= 5:
                    print("\n!!! 5 errores en últimos 10 — PARANDO")
                    break

        if not dry_run and i < len(cola) - 1:
            time.sleep(MSG_DELAY)
            if (i + 1) % 500 == 0:
                print(f"\n--- Pausa {PAUSE_EVERY_500//60} min (cada 500) ---")
                time.sleep(PAUSE_EVERY_500)
            elif (i + 1) % 100 == 0:
                print(f"\n--- Pausa {PAUSE_EVERY_100//60} min (cada 100) ---")
                time.sleep(PAUSE_EVERY_100)

    elapsed = time.time() - start

    if not dry_run and log:
        logfile = os.path.join(BASE_DIR, f"log_junin_{batch_num}.json")
        with open(logfile, "w") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        print(f"\nLog: {logfile}")

    # Resumen por marca
    marcas_env = {}
    for l in log:
        if l.get("status") == "sent":
            m = l.get("marca", "?")
            marcas_env[m] = marcas_env.get(m, 0) + 1

    print(f"""
{'='*60}
RESULTADO Batch {batch_num}:
  Enviados: {enviados} | Errores: {errores}
  Por marca: {', '.join(f'{m}({n})' for m, n in marcas_env.items())}
  Tiempo: {elapsed/60:.1f} min
  Presupuesto semana restante: {remaining_week - enviados}
{'='*60}
""")


if __name__ == '__main__':
    main()
