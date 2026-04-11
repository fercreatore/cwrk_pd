#!/usr/bin/env python3
"""Reporte diario de impacto campaña WhatsApp → ventas ERP. Envía por Telegram."""
import os, json, urllib.request, ssl
os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.cnf'
import pyodbc
from datetime import datetime

TELEGRAM_TOKEN = "7915479736:AAGNbMCyYHYXgwPT5a8y91wR5IVUbfXWK0o"
TELEGRAM_CHAT = "7610568996"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def telegram_send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        urllib.request.urlopen(req, context=ctx, timeout=10)
    except:
        pass

def main():
    with open(os.path.join(SCRIPT_DIR, 'phones_already_sent.json')) as f:
        sent = set(json.load(f))
    with open(os.path.join(SCRIPT_DIR, 'contactos_whatsapp_calzalindo.json')) as f:
        contacts = json.load(f)
    
    phone_to_mg = {}
    for c in contacts:
        tel = c.get('telefono_whatsapp', '')
        mg = c.get('nro_mg', '')
        if tel and mg:
            phone_to_mg[tel] = mg
    
    cuentas = [phone_to_mg[p] for p in sent if p in phone_to_mg]
    cuentas_str = ",".join(f"'{c}'" for c in cuentas)
    
    lines = [f"📊 <b>REPORTE CAMPAÑA WHATSAPP</b>", f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}", f"📱 Contactados: {len(cuentas)}", ""]
    
    grand_camp = 0
    grand_total = 0
    grand_cli = 0
    grand_pares = 0
    
    for base in ['msgestion03']:
        conn = pyodbc.connect(f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=192.168.2.111;DATABASE={base};UID=am;PWD=dl;TrustServerCertificate=yes;Encrypt=no', timeout=15)
        cur = conn.cursor()
        
        cur.execute(f"""
        SELECT CONVERT(DATE, v.fecha) as dia,
            COUNT(DISTINCT v.cuenta) as cli_camp,
            SUM(v.cantidad) as pares,
            SUM(v.total_item) as fact_camp
        FROM ventas1 v
        WHERE CAST(v.cuenta AS VARCHAR) IN ({cuentas_str})
        AND v.codigo NOT IN (7,36) AND v.fecha >= '2026-04-05'
        GROUP BY CONVERT(DATE, v.fecha) ORDER BY dia
        """)
        camp_data = {str(r.dia): (r.cli_camp, int(r.pares), r.fact_camp) for r in cur.fetchall()}
        
        cur.execute("""
        SELECT CONVERT(DATE, v.fecha) as dia,
            COUNT(DISTINCT v.cuenta) as cli, SUM(v.total_item) as fact
        FROM ventas1 v WHERE v.codigo NOT IN (7,36) AND v.fecha >= '2026-04-05'
        GROUP BY CONVERT(DATE, v.fecha) ORDER BY dia
        """)
        
        for r in cur.fetchall():
            dia = str(r.dia)
            cli_c, pares_c, fact_c = camp_data.get(dia, (0, 0, 0))
            pct = float(fact_c) * 100 / float(r.fact) if r.fact else 0
            lines.append(f"📅 {dia[-5:]}: {cli_c} cli ({pct:.0f}%) | {pares_c}p | ${float(fact_c)/1000:.0f}K / ${float(r.fact)/1000:.0f}K")
            grand_camp += float(fact_c)
            grand_total += float(r.fact)
            grand_cli += cli_c
            grand_pares += pares_c
        
        # Today's top buyer
        cur.execute(f"""
        SELECT TOP 3 c.denominacion, SUM(v.total_item) as t
        FROM ventas1 v JOIN clientes c ON v.cuenta=c.numero
        WHERE CAST(v.cuenta AS VARCHAR) IN ({cuentas_str})
        AND v.codigo NOT IN (7,36) AND CONVERT(DATE,v.fecha) = CONVERT(DATE,GETDATE())
        GROUP BY c.denominacion ORDER BY t DESC
        """)
        top = cur.fetchall()
        conn.close()
    
    gasto = len(sent) * 0.0618 * 1200
    roi = grand_camp / gasto if gasto else 0
    
    lines.append("")
    lines.append(f"💰 <b>TOTAL campaña: ${grand_camp/1000:.0f}K</b> ({grand_cli} cli, {grand_pares}p)")
    lines.append(f"📈 % sobre ventas totales: {grand_camp*100/grand_total:.1f}%")
    lines.append(f"💵 Gasto: ${gasto/1000:.0f}K → ROI: {roi:.0f}x")
    
    if top:
        lines.append("")
        lines.append("🏆 <b>Top hoy:</b>")
        for r in top:
            lines.append(f"  • {r.denominacion[:25]} ${float(r.t)/1000:.0f}K")
    
    msg = "\n".join(lines)
    print(msg)
    telegram_send(msg)
    print("\n✅ Enviado por Telegram")

if __name__ == "__main__":
    main()
