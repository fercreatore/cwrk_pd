# -*- coding: utf-8 -*-
"""
GENERADOR DE ORDENES DE AUDITORIA DE STOCK
===========================================
Genera ordenes de auditoria priorizadas para stock muerto (>5 uds, 0 ventas 12m).
Cruza con t_articulos_last_audit para priorizar articulos NUNCA auditados o
auditados hace mucho tiempo.

Prioridades:
  P1 URGENTE: valor_stock > $300K + nunca auditado
  P2 ALTA:    valor_stock > $100K + nunca auditado, O auditado hace > 180 dias
  P3 MEDIA:   valor_stock > $50K  + auditado hace > 90 dias
  P4 BAJA:    resto

Uso:
    python3 generar_ordenes_auditoria.py          # Genera CSV + resumen
    python3 generar_ordenes_auditoria.py --csv     # (default, siempre genera CSV)

Ejecutar en Mac o en 111.
"""
import sys
import os
import csv
import datetime

# ─── OPENSSL LEGACY FIX (SQL Server 2012 TLS 1.0) ──────────────────
_openssl_conf = '/tmp/openssl_legacy.cnf'
if not os.path.exists(_openssl_conf):
    with open(_openssl_conf, 'w') as f:
        f.write(
            "openssl_conf = openssl_init\n"
            "[openssl_init]\n"
            "ssl_conf = ssl_sect\n"
            "[ssl_sect]\n"
            "system_default = system_default_sect\n"
            "[system_default_sect]\n"
            "CipherString = DEFAULT:@SECLEVEL=0\n"
        )
os.environ['OPENSSL_CONF'] = _openssl_conf

import pyodbc  # noqa: E402

# ─── CONFIGURACION ──────────────────────────────────────────────────
SERVER = '192.168.2.111,1433'
UID = 'am'
PWD = 'dl'
CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={SERVER};"
    f"UID={UID};PWD={PWD};"
    "TrustServerCertificate=yes;"
)

DEPOSITOS = '0,1,2,3,4,5,6,7,8,9,11,12,14,15,198'
MARCAS_EXCLUIR = '1316,1317,1158,436'

DEPO_NOMBRES = {
    0: 'CENTRAL',
    1: 'ML',
    2: 'NORTE',
    4: 'CLAUDIA',
    6: 'CUORE',
    7: 'EVA PERON',
    8: 'JUNIN',
    9: 'TOKIO',
    11: 'ALT CENTRAL',
    15: 'JUNIN GO',
    198: 'DEPOSITO 198',
    3: 'DEPOSITO 3',
    5: 'DEPOSITO 5',
    12: 'DEPOSITO 12',
    14: 'DEPOSITO 14',
}

# Umbrales de prioridad (en pesos)
UMBRAL_P1 = 300_000
UMBRAL_P2 = 100_000
UMBRAL_P3 = 50_000
DIAS_P2 = 180
DIAS_P3 = 90


def get_connection():
    return pyodbc.connect(CONN_STR)


def query_db(conn, sql):
    cursor = conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    cursor.execute(sql)
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ─── QUERIES ─────────────────────────────────────────────────────────

SQL_STOCK_MUERTO = """
SELECT
  sm.articulo,
  a.codigo_sinonimo AS csr,
  a.descripcion_1 AS descripcion,
  a.marca,
  a.subrubro,
  a.precio_costo,
  sm.stock_total,
  sm.stock_total * ISNULL(a.precio_costo, 0) AS valor_stock,
  la.fecha AS ultima_auditoria,
  la.depo_macro,
  DATEDIFF(DAY, la.fecha, GETDATE()) AS dias_sin_auditar
FROM (
  SELECT s.articulo, SUM(s.stock_actual) AS stock_total
  FROM msgestionC.dbo.stock s WITH (NOLOCK)
  WHERE s.deposito IN (%(depos)s)
  GROUP BY s.articulo
  HAVING SUM(s.stock_actual) > 5
) sm
JOIN msgestion01art.dbo.articulo a WITH (NOLOCK) ON a.codigo = sm.articulo
LEFT JOIN omicronvt.dbo.t_articulos_last_audit la
  ON la.codigo = sm.articulo AND la.depo_macro = 0
LEFT JOIN (
  SELECT v.articulo
  FROM msgestionC.dbo.ventas1 v WITH (NOLOCK)
  WHERE v.codigo NOT IN (7,36) AND v.cantidad > 0
    AND v.fecha >= DATEADD(MONTH, -12, GETDATE())
  GROUP BY v.articulo
) vtas ON vtas.articulo = sm.articulo
WHERE vtas.articulo IS NULL
  AND a.marca NOT IN (%(marcas_excl)s)
ORDER BY sm.stock_total * ISNULL(a.precio_costo, 0) DESC
""" % {'depos': DEPOSITOS, 'marcas_excl': MARCAS_EXCLUIR}

SQL_MARCAS = """
SELECT codigo AS numero, descripcion AS denominacion
FROM msgestion01art.dbo.marcas
WHERE codigo IN (
  SELECT DISTINCT a.marca
  FROM msgestion01art.dbo.articulo a WITH (NOLOCK)
  JOIN msgestionC.dbo.stock s WITH (NOLOCK) ON s.articulo = a.codigo
  WHERE s.deposito IN (%s) AND s.stock_actual > 0
)
""" % DEPOSITOS

SQL_STOCK_POR_DEPO = """
SELECT s.deposito, s.articulo, s.stock_actual
FROM msgestionC.dbo.stock s WITH (NOLOCK)
WHERE s.deposito IN (%(depos)s) AND s.stock_actual > 0
  AND s.articulo IN (
    SELECT sm2.articulo
    FROM (
      SELECT s2.articulo, SUM(s2.stock_actual) AS st
      FROM msgestionC.dbo.stock s2 WITH (NOLOCK)
      WHERE s2.deposito IN (%(depos)s)
      GROUP BY s2.articulo
      HAVING SUM(s2.stock_actual) > 5
    ) sm2
    LEFT JOIN (
      SELECT DISTINCT v.articulo
      FROM msgestionC.dbo.ventas1 v WITH (NOLOCK)
      WHERE v.codigo NOT IN (7,36) AND v.cantidad > 0
        AND v.fecha >= DATEADD(MONTH, -12, GETDATE())
    ) vt ON vt.articulo = sm2.articulo
    WHERE vt.articulo IS NULL
  )
""" % {'depos': DEPOSITOS}


def clasificar_prioridad(valor_stock, ultima_auditoria, dias_sin_auditar):
    """
    Clasifica la prioridad de auditoria.
    P1 URGENTE: valor > $300K + nunca auditado
    P2 ALTA:    valor > $100K + nunca auditado, O auditado hace > 180 dias
    P3 MEDIA:   valor > $50K  + auditado hace > 90 dias
    P4 BAJA:    resto
    """
    nunca_auditado = ultima_auditoria is None
    dias = dias_sin_auditar or 9999 if not nunca_auditado else 9999

    if valor_stock > UMBRAL_P1 and nunca_auditado:
        return 'P1 URGENTE'
    if valor_stock > UMBRAL_P2 and (nunca_auditado or dias > DIAS_P2):
        return 'P2 ALTA'
    if valor_stock > UMBRAL_P3 and (nunca_auditado or dias > DIAS_P3):
        return 'P3 MEDIA'
    return 'P4 BAJA'


def main():
    hoy = datetime.date.today()
    fecha_str = hoy.strftime('%Y%m%d')

    print("=" * 70)
    print("GENERADOR DE ORDENES DE AUDITORIA DE STOCK")
    print("Fecha: %s" % hoy.strftime('%d/%m/%Y'))
    print("=" * 70)
    print()

    # ─── Conectar ────────────────────────────────────────────────────
    print("[1/4] Conectando a SQL Server 111...")
    conn = get_connection()
    print("  OK")

    # ─── Q1: Stock muerto con datos de articulo y ultima auditoria ───
    print("[2/4] Obteniendo stock muerto con datos de auditoria...")
    rows = query_db(conn, SQL_STOCK_MUERTO)
    print("  %d articulos con stock muerto (>5 uds, 0 ventas 12m)" % len(rows))

    # ─── Q2: Nombres de marca ────────────────────────────────────────
    print("[3/4] Obteniendo nombres de marca...")
    try:
        marca_rows = query_db(conn, SQL_MARCAS)
        marca_map = {
            r['numero']: str(r['denominacion'] or '').strip()
            for r in marca_rows
        }
        print("  %d marcas cargadas" % len(marca_map))
    except Exception as e:
        print("  WARN: No se pudo leer tabla marcas (%s), usando fallback" % e)
        marca_map = {}
    # Fallback hardcoded para marcas conocidas
    MARCAS_CONOCIDAS = {
        3: 'DELI', 17: 'GO by CZL', 42: 'LESEDIFE', 57: 'CAVATINI', 75: 'CROCS',
        87: 'VANS', 99: 'LADY STORK', 104: 'GTN', 139: 'HUSH PUPPIES', 162: 'SKECHERS',
        196: 'RIDER', 264: 'GRIMOLDI', 294: 'CARMEL', 311: 'ROFREVE', 314: 'TOPPER',
        328: 'SOFI MARTIRE', 515: 'ELEMENTO', 513: 'REEBOK', 561: 'RINGO', 594: 'ATOMIK',
        599: 'NEW BALANCE', 608: 'BALL ONE', 614: 'DIADORA', 639: 'SAUCONY',
        653: 'FILA', 656: 'DISTRINANDO DEP', 657: 'ADIDAS', 664: 'PUMA', 669: 'LANACUER',
        675: 'DIADORA', 679: 'KAPPA', 684: 'ASICS', 705: 'MERRELL', 713: 'DISTRINANDO MODA',
        722: 'GLOBAL BRANDS', 724: 'DEMOCRATA', 744: 'HAVAIANAS', 746: 'PICCADILLY',
        759: 'CATERPILLAR', 765: 'HUSH PUPPIES', 770: 'PRIMER ROUND', 773: 'JAGUAR',
        775: 'UNDER ARMOUR', 794: 'SAVAGE', 817: 'KALIF', 822: 'CLZ TEXTIL', 860: 'PRUNE',
        873: 'LA MARTINA', 883: 'SAUCONY', 891: 'PARUOLO', 946: 'SOFI', 950: 'TIVORY',
        990: 'CLZ BEAUTY', 1260: 'SHOEHOLIC',
    }
    for cod, nombre in MARCAS_CONOCIDAS.items():
        if cod not in marca_map:
            marca_map[cod] = nombre

    # ─── Q3: Stock por deposito ──────────────────────────────────────
    print("[4/4] Obteniendo distribucion de stock por deposito...")
    depo_rows = query_db(conn, SQL_STOCK_POR_DEPO)
    # Construir dict: articulo -> {depo: stock}
    stock_por_depo = {}
    for r in depo_rows:
        art = r['articulo']
        dep = r['deposito']
        stk = float(r['stock_actual'] or 0)
        if art not in stock_por_depo:
            stock_por_depo[art] = {}
        stock_por_depo[art][dep] = stock_por_depo[art].get(dep, 0) + stk
    print("  %d registros de stock por deposito" % len(depo_rows))

    conn.close()

    # ─── Clasificar por prioridad ────────────────────────────────────
    print("\nClasificando por prioridad...")

    ordenes = []
    for r in rows:
        articulo = r['articulo']
        valor_stock = float(r['valor_stock'] or 0)
        ultima_aud = r['ultima_auditoria']
        dias = r['dias_sin_auditar']

        prioridad = clasificar_prioridad(valor_stock, ultima_aud, dias)

        marca_cod = r['marca']
        marca_nombre = marca_map.get(marca_cod, 'MARCA %s' % marca_cod)

        # Formatear ultima auditoria
        if ultima_aud:
            if hasattr(ultima_aud, 'strftime'):
                ult_aud_str = ultima_aud.strftime('%d/%m/%Y')
            else:
                ult_aud_str = str(ultima_aud)[:10]
            dias_str = str(dias) if dias is not None else '?'
        else:
            ult_aud_str = 'NUNCA'
            dias_str = '-'

        # Depositos donde esta este articulo
        depos = stock_por_depo.get(articulo, {})
        depos_txt = ', '.join(
            '%s(%d)' % (DEPO_NOMBRES.get(d, 'DEP%d' % d), int(s))
            for d, s in sorted(depos.items(), key=lambda x: -x[1])
            if s > 0
        )

        ordenes.append({
            'prioridad': prioridad,
            'prioridad_num': int(prioridad[1]),  # 1,2,3,4
            'articulo': articulo,
            'sinonimo': str(r['csr'] or '').strip(),
            'descripcion': str(r['descripcion'] or '').strip(),
            'marca': marca_nombre,
            'stock_total': int(r['stock_total'] or 0),
            'valor_stock': valor_stock,
            'ultima_auditoria': ult_aud_str,
            'dias_sin_auditar': dias_str,
            'depositos': depos_txt,
        })

    # Ordenar: P1 primero, dentro de cada prioridad por valor descendente
    ordenes.sort(key=lambda x: (x['prioridad_num'], -x['valor_stock']))

    # ─── Resumen ─────────────────────────────────────────────────────
    conteo = {'P1 URGENTE': 0, 'P2 ALTA': 0, 'P3 MEDIA': 0, 'P4 BAJA': 0}
    valor_por_prio = {'P1 URGENTE': 0, 'P2 ALTA': 0, 'P3 MEDIA': 0, 'P4 BAJA': 0}
    nunca_auditados = sum(1 for o in ordenes if o['ultima_auditoria'] == 'NUNCA')

    for o in ordenes:
        p = o['prioridad']
        conteo[p] += 1
        valor_por_prio[p] += o['valor_stock']

    total_valor = sum(o['valor_stock'] for o in ordenes)
    valor_riesgo = valor_por_prio['P1 URGENTE'] + valor_por_prio['P2 ALTA']

    print()
    print("=" * 70)
    print("RESUMEN ORDENES DE AUDITORIA")
    print("=" * 70)
    print()
    print("  Total articulos stock muerto: %d" % len(ordenes))
    print("  Nunca auditados:              %d (%.0f%%)" % (
        nunca_auditados, nunca_auditados / len(ordenes) * 100 if ordenes else 0))
    print()
    print("  %-12s  %6s  %15s" % ('Prioridad', 'Items', 'Valor Stock'))
    print("  " + "-" * 38)
    for p in ['P1 URGENTE', 'P2 ALTA', 'P3 MEDIA', 'P4 BAJA']:
        print("  %-12s  %6d  $%14s" % (p, conteo[p], format(int(valor_por_prio[p]), ',')))
    print("  " + "-" * 38)
    print("  %-12s  %6d  $%14s" % ('TOTAL', len(ordenes), format(int(total_valor), ',')))
    print()
    print("  VALOR EN RIESGO (P1+P2): $%s" % format(int(valor_riesgo), ','))
    print()

    # ─── Top 15 P1+P2 ────────────────────────────────────────────────
    top = [o for o in ordenes if o['prioridad_num'] <= 2][:15]
    if top:
        print("TOP ARTICULOS URGENTES (P1+P2)")
        print("-" * 100)
        print("%-11s %-8s %-30s %-14s %6s %13s %-10s" % (
            'Prioridad', 'Cod', 'Descripcion', 'Marca', 'Stock', 'Valor', 'Ult.Audit'))
        print("-" * 100)
        for o in top:
            print("%-11s %-8s %-30s %-14s %6d $%12s %-10s" % (
                o['prioridad'],
                o['articulo'],
                o['descripcion'][:30],
                o['marca'][:14],
                o['stock_total'],
                format(int(o['valor_stock']), ','),
                o['ultima_auditoria'],
            ))
        print()

    # ─── Generar CSV ─────────────────────────────────────────────────
    informes_dir = os.path.join(os.path.dirname(__file__), '..', '_informes')
    os.makedirs(informes_dir, exist_ok=True)

    csv_path = os.path.join(informes_dir, 'orden_auditoria_%s.csv' % fecha_str)

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow([
            'Prioridad', 'Articulo', 'Sinonimo', 'Descripcion', 'Marca',
            'Stock Sistema', 'Ultima Auditoria', 'Dias Sin Auditar',
            'Valor Estimado', 'Depositos'
        ])
        for o in ordenes:
            w.writerow([
                o['prioridad'],
                o['articulo'],
                o['sinonimo'],
                o['descripcion'],
                o['marca'],
                o['stock_total'],
                o['ultima_auditoria'],
                o['dias_sin_auditar'],
                int(o['valor_stock']),
                o['depositos'],
            ])

    print("CSV generado: %s" % os.path.abspath(csv_path))
    print("  %d filas escritas" % len(ordenes))

    # ─── Resumen para Gonzalo/Emanuel ────────────────────────────────
    print()
    print("=" * 70)
    print("INSTRUCCIONES PARA GONZALO / EMANUEL")
    print("=" * 70)
    print()
    print("1. Empezar por P1 URGENTE (%d articulos, $%s en riesgo)" % (
        conteo['P1 URGENTE'], format(int(valor_por_prio['P1 URGENTE']), ',')))
    print("2. Seguir con P2 ALTA (%d articulos)" % conteo['P2 ALTA'])
    print("3. Verificar fisicamente que el stock del sistema coincida")
    print("4. Si el articulo NO EXISTE fisicamente -> marcar para dar de BAJA")
    print("5. Si el stock no coincide -> anotar cantidad real")
    print()
    print("Listo.")


if __name__ == '__main__':
    main()
