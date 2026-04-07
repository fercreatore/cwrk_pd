#!/usr/bin/env python3
"""
Cruce diario: Ventas ERP vs Campaña WhatsApp
Corre automático cada día a las 21:00 durante el outlet
Genera reporte y lo manda por Telegram
"""
import os, json, sys, requests
from datetime import datetime, timedelta

os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.cnf'
if not os.path.exists('/tmp/openssl_legacy.cnf'):
    with open('/tmp/openssl_legacy.cnf', 'w') as f:
        f.write("[openssl_init]\nssl_conf = ssl_sect\n[ssl_sect]\nsystem_default = system_default_sect\n[system_default_sect]\nMinProtocol = TLSv1\nCipherString = DEFAULT@SECLEVEL=0\n")

import pyodbc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHONES_FILE = os.path.join(BASE_DIR, 'phones_already_sent.json')
REPORTES_DIR = os.path.join(BASE_DIR, 'reportes_cruce')
TELEGRAM_TOKEN = "7775397058:AAFoJ3HJl4A-Gxl3hVrcFnCXcDMUVXjWsqg"
TELEGRAM_CHAT_ID = "-4733498509"

DEP_NAMES = {0:'Central VT',1:'Deposito',2:'Norte',4:'Cuore/Chovet',5:'Eva Peron',
             6:'Junin',7:'Firmat',8:'Rufino',9:'San Jorge',11:'Online'}

def normalize_phone(p):
    if not p: return set()
    r = set()
    p = p.replace(' ','').replace('-','').replace('(','').replace(')','').replace('+','')
    if p.startswith('0'): p = p[1:]
    r.add(p)
    if p.startswith('3462') and len(p) >= 10: r.add('549' + p)
    if p.startswith('15') and len(p) == 8: r.add('5493462' + p[2:])
    if p.startswith('346215'): r.add('549' + p[:4] + p[6:])
    if p.startswith('236') and len(p) >= 10: r.add('549' + p)
    if p.startswith('549'): r.add(p)
    return r

def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print(f"Error Telegram: {e}")

def run_cruce(fecha=None):
    """Corre el cruce para una fecha específica o hoy"""
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=192.168.2.111;DATABASE=msgestionC;"
        "UID=am;PWD=dl;TrustServerCertificate=yes;Encrypt=no"
    )
    cursor = conn.cursor()

    if fecha:
        fecha_sql = fecha
    else:
        fecha_sql = datetime.now().strftime('%Y-%m-%d')

    # Ventas del día
    cursor.execute("""
        SELECT CAST(v.cuenta AS VARCHAR(20)) as cuenta, v.deposito,
               SUM(v.precio * v.cantidad) as total_venta,
               SUM(v.cantidad) as cant_pares,
               COUNT(DISTINCT v.numero) as cant_tickets
        FROM ventas1 v
        WHERE CONVERT(date, v.fecha) = ?
          AND v.codigo NOT IN (7, 36)
          AND v.cuenta > 0
        GROUP BY CAST(v.cuenta AS VARCHAR(20)), v.deposito
        ORDER BY total_venta DESC
    """, fecha_sql)

    ventas = []
    for r in cursor.fetchall():
        ventas.append({
            'cuenta': str(r[0]).strip(),
            'dep': int(r[1]),
            'total': float(r[2] or 0),
            'pares': int(r[3] or 0),
            'tix': r[4]
        })

    if not ventas:
        print(f"Sin ventas para {fecha_sql}")
        send_telegram(f"📊 <b>Cruce {fecha_sql}</b>\nSin ventas registradas hoy.")
        conn.close()
        return

    # Info clientes
    cuentas = list(set(int(v['cuenta']) for v in ventas if v['cuenta'].isdigit()))
    cli = {}
    for i in range(0, len(cuentas), 500):
        b = cuentas[i:i+500]
        ph = ','.join([str(c) for c in b])
        cursor.execute(f"""
            SELECT CAST(numero AS VARCHAR(20)), denominacion, telefonos,
                   area_cel1, cel1, area_cel2, cel2
            FROM clientes WHERE numero IN ({ph})
        """)
        for r in cursor.fetchall():
            n = str(r[0]).strip()
            cli[n] = {
                'nombre': str(r[1] or '').strip(),
                'tel': str(r[2] or '').strip(),
                'acel1': str(r[3] or '').strip(), 'cel1': str(r[4] or '').strip(),
                'acel2': str(r[5] or '').strip(), 'cel2': str(r[6] or '').strip()
            }
    conn.close()

    # Cargar phones campaña
    with open(PHONES_FILE) as f:
        sent = set(json.load(f))

    # Cruzar
    matches, nomatches = [], []
    for v in ventas:
        c = cli.get(v['cuenta'], {})
        v['nombre'] = c.get('nombre', '?')
        v['dn'] = DEP_NAMES.get(v['dep'], f"Dep {v['dep']}")
        phones = set()
        for p in [c.get('tel',''), c.get('cel1',''), c.get('cel2','')]:
            phones |= normalize_phone(p)
        if c.get('acel1') and c.get('cel1'):
            phones |= normalize_phone(c['acel1'] + c['cel1'])
        if c.get('acel2') and c.get('cel2'):
            phones |= normalize_phone(c['acel2'] + c['cel2'])
        v['wh'] = bool(phones & sent)
        (matches if v['wh'] else nomatches).append(v)

    # Totales
    total_all = sum(v['total'] for v in ventas)
    total_wh = sum(m['total'] for m in matches)
    total_sin = sum(m['total'] for m in nomatches)
    uniq_all = len(set(v['cuenta'] for v in ventas))
    uniq_wh = len(set(m['cuenta'] for m in matches))

    # Reporte texto
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  CRUCE VENTAS vs CAMPAÑA WH — {fecha_sql}")
    lines.append(f"{'='*60}")
    lines.append(f"  Total clientes:    {uniq_all}")
    lines.append(f"  Facturación:       ${total_all:,.0f}")
    lines.append(f"")
    lines.append(f"  CON WhatsApp:      {uniq_wh} clientes ({uniq_wh*100/max(uniq_all,1):.1f}%)")
    lines.append(f"  Facturaron:        ${total_wh:,.0f} ({total_wh*100/max(total_all,1):.1f}%)")
    lines.append(f"")
    lines.append(f"  SIN WhatsApp:      {uniq_all - uniq_wh} clientes")
    lines.append(f"  Facturaron:        ${total_sin:,.0f}")
    lines.append(f"")

    if matches:
        lines.append(f"  DETALLE — Recibieron WH y compraron:")
        for m in sorted(matches, key=lambda x: -x['total']):
            lines.append(f"   ✅ {m['nombre'][:32]:32s} ${m['total']:>11,.0f}  {m['pares']:>3}p  {m['dn']}")

    # Por local
    lines.append(f"\n  POR LOCAL:")
    deps_all = {}
    deps_wh = {}
    for v in ventas:
        deps_all[v['dn']] = deps_all.get(v['dn'], 0) + v['total']
    for m in matches:
        deps_wh[m['dn']] = deps_wh.get(m['dn'], 0) + m['total']
    for d in sorted(deps_all, key=lambda x: -deps_all[x]):
        wh_val = deps_wh.get(d, 0)
        pct = wh_val * 100 / max(deps_all[d], 1)
        lines.append(f"   {d:20s} Total: ${deps_all[d]:>11,.0f}  WH: ${wh_val:>11,.0f} ({pct:.0f}%)")

    reporte = '\n'.join(lines)
    print(reporte)

    # Guardar reporte
    os.makedirs(REPORTES_DIR, exist_ok=True)
    with open(os.path.join(REPORTES_DIR, f'cruce_{fecha_sql}.txt'), 'w') as f:
        f.write(reporte)

    # Guardar JSON para dashboards
    data = {
        'fecha': fecha_sql,
        'total_clientes': uniq_all,
        'total_facturacion': total_all,
        'wh_clientes': uniq_wh,
        'wh_facturacion': total_wh,
        'pct_clientes': round(uniq_wh * 100 / max(uniq_all, 1), 1),
        'pct_facturacion': round(total_wh * 100 / max(total_all, 1), 1),
        'detalle_wh': [{'nombre': m['nombre'], 'total': m['total'], 'pares': m['pares'], 'local': m['dn']} for m in sorted(matches, key=lambda x: -x['total'])],
        'por_local': {d: {'total': deps_all[d], 'wh': deps_wh.get(d, 0)} for d in deps_all}
    }
    with open(os.path.join(REPORTES_DIR, f'cruce_{fecha_sql}.json'), 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Mandar por Telegram
    tg = f"📊 <b>CRUCE VENTAS vs CAMPAÑA WH</b>\n"
    tg += f"📅 {fecha_sql}\n\n"
    tg += f"👥 Clientes: {uniq_all}\n"
    tg += f"💰 Facturación: ${total_all:,.0f}\n\n"
    tg += f"📱 <b>Con WhatsApp: {uniq_wh} ({uniq_wh*100/max(uniq_all,1):.0f}%)</b>\n"
    tg += f"💵 Facturaron: ${total_wh:,.0f} ({total_wh*100/max(total_all,1):.0f}%)\n\n"

    if matches:
        tg += "✅ <b>Detalle:</b>\n"
        for m in sorted(matches, key=lambda x: -x['total'])[:15]:
            tg += f"  {m['nombre'][:25]} — ${m['total']:,.0f} ({m['pares']}p) {m['dn']}\n"
        if len(matches) > 15:
            tg += f"  ... y {len(matches)-15} más\n"

    if total_wh > 181000:
        roi = total_wh / 181000
        tg += f"\n🚀 ROI acumulado: {roi:.1f}x"

    send_telegram(tg)
    return data

def run_acumulado(desde='2026-04-05'):
    """Corre cruce acumulado desde el inicio de la campaña"""
    fecha_inicio = datetime.strptime(desde, '%Y-%m-%d')
    hoy = datetime.now()

    total_wh = 0
    total_all = 0
    total_cli_wh = 0
    total_cli = 0
    dias_data = []

    for i in range((hoy - fecha_inicio).days + 1):
        fecha = (fecha_inicio + timedelta(days=i)).strftime('%Y-%m-%d')
        reporte_json = os.path.join(REPORTES_DIR, f'cruce_{fecha}.json')

        if os.path.exists(reporte_json):
            with open(reporte_json) as f:
                d = json.load(f)
        else:
            d = run_cruce(fecha)
            if not d:
                continue

        dias_data.append(d)
        total_wh += d.get('wh_facturacion', 0)
        total_all += d.get('total_facturacion', 0)
        total_cli_wh += d.get('wh_clientes', 0)
        total_cli += d.get('total_clientes', 0)

    print(f"\n{'='*60}")
    print(f"  ACUMULADO CAMPAÑA — {desde} a {hoy.strftime('%Y-%m-%d')}")
    print(f"{'='*60}")
    print(f"  Días con ventas:      {len(dias_data)}")
    print(f"  Facturación total:    ${total_all:,.0f}")
    print(f"  Con WhatsApp:         ${total_wh:,.0f} ({total_wh*100/max(total_all,1):.1f}%)")
    print(f"  Clientes WH:         {total_cli_wh} de {total_cli}")
    print(f"  Inversión:            $181,000")
    if total_wh > 0:
        print(f"  ROI:                  {total_wh/181000:.1f}x")

    # Telegram acumulado
    tg = f"📈 <b>ACUMULADO CAMPAÑA WH</b>\n"
    tg += f"📅 {desde} → {hoy.strftime('%Y-%m-%d')}\n\n"
    tg += f"💰 Total: ${total_all:,.0f}\n"
    tg += f"📱 Con WH: ${total_wh:,.0f} ({total_wh*100/max(total_all,1):.0f}%)\n"
    tg += f"👥 {total_cli_wh} de {total_cli} clientes\n"
    tg += f"💵 Inversión: $181,000\n"
    if total_wh > 0:
        tg += f"🚀 <b>ROI: {total_wh/181000:.1f}x</b>"
    send_telegram(tg)

if __name__ == '__main__':
    if '--acumulado' in sys.argv:
        run_acumulado()
    elif '--fecha' in sys.argv:
        idx = sys.argv.index('--fecha')
        run_cruce(sys.argv[idx+1])
    else:
        # Default: cruce de hoy + acumulado
        run_cruce()
        run_acumulado()
