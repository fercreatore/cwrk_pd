#!/usr/bin/env python3
# insertar_confortable.py
# Inserta pedidos mensuales CONFORTABLE SRL — Alpargatas EVA + 710 PVC
# 7 pedidos (ABR-OCT 2026), TODO en MSGESTION01
# Velocidad real ajustada por quiebre de stock
#
# Proveedor: 236, CONFORTABLE SRL
# Mínimos: EVA = 12 pares/talle, PVC = 6 pares/talle
#
# EJECUTAR EN EL 111:
#   py -3 insertar_confortable.py --dry-run     <- solo muestra
#   py -3 insertar_confortable.py --ejecutar    <- escribe en produccion

import sys
import pyodbc
import socket
from datetime import date, datetime

# -- AUTO-DETECT SERVER vs MAC -----------------------------------------
_hostname = socket.gethostname().upper()
if _hostname in ("DELL-SVR", "DELLSVR"):
    SERVIDOR = "localhost"
    DRIVER = "ODBC Driver 17 for SQL Server"
    EXTRAS = ""
else:
    SERVIDOR = "192.168.2.111"
    DRIVER = "ODBC Driver 18 for SQL Server"
    EXTRAS = "TrustServerCertificate=yes;Encrypt=no;"

def get_conn(base):
    return (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVIDOR};"
        f"DATABASE={base};"
        f"UID=am;PWD=dl;"
        f"{EXTRAS}"
    )

# -- CONSTANTES --------------------------------------------------------
CODIGO_PEDIDO = 8
LETRA_PEDIDO = "X"
SUCURSAL_PEDIDO = 1
ORDEN_FIJA = 1  # numeric(2,0) max 99 — usar siempre 1

BASE_PEDIDO = "MSGESTION01"  # Todo va a 01, se distribuye al facturar

CABECERA_BASE = {
    "cuenta":            236,
    "denominacion":      "CONFORTABLE SRL",
    "zona":              6,
    "condicion_iva":     "I",
    "cuit":              "30700175088",
}

# -- PEDIDOS POR MES ---------------------------------------------------
# Cada tupla: (articulo, descripcion, codigo_sinonimo, cantidad, precio)
# Calculados con velocidad REAL (ajustada por quiebre), minimos EVA=12 PVC=6
PEDIDOS_MES = {
    "ABR": [  # 60p $311,177 — entrega 19/04/2026
        (63841, "ALPARGATA REFORZADA NEGRO C/ELAST S/EVA", "236495000041", 12, 5037.99),  # NEGRO EVA T41
        (304318, "710 NEGRO ALPARGATA REFORZADA SUELA PVC", "236007100042", 6, 6867.84),  # NEGRO PVC T42
        (304319, "710 NEGRO ALPARGATA REFORZADA SUELA PVC", "236007100043", 6, 5692.57),  # NEGRO PVC T43
        (110018, "ALPARGATA REFORZADA BORDO C/ELAST S/EVA", "236495003543", 12, 5037.99),  # BORDO EVA T43
        (63875, "ALPARGATA REFORZADA VERDE C/ELAST S/EVA", "236495001436", 12, 4537.25),   # VERDE EVA T36
        (63854, "ALPARGATA REFORZADA BLANCO C/ELAST S/EVA", "236495000141", 12, 5037.99),  # BLANCO EVA T41
    ],
    "MAY": [  # 96p $523,547 — entrega 19/05/2026
        (304315, "710 NEGRO ALPARGATA REFORZADA SUELA PVC", "236007100039", 6, 6867.84),   # NEGRO PVC T39
        (304320, "710 NEGRO ALPARGATA REFORZADA SUELA PVC", "236007100044", 6, 5692.57),   # NEGRO PVC T44
        (309115, "710 AZUL ALPARGATA REFORZADA SUELA PVC", "236007100238", 6, 6329.77),    # AZUL PVC T38
        (250669, "ALPARGATA REFORZADA BORDO C/ELAST S/EVA", "236495003537", 12, 4537.25),  # BORDO EVA T37
        (110740, "ALPARGATA REFORZADA BORDO C/ELAST S/EVA", "236495003540", 12, 5037.99),  # BORDO EVA T40
        (304310, "710 BORDO ALPARGATA REFORZADA SUELA PVC", "236007103042", 6, 6329.77),   # BORDO PVC T42
        (144802, "ALPARGATA REFORZADA BORDO C/ELAST S/EVA", "236495003544", 12, 5037.99),  # BORDO EVA T44
        (304323, "710 VERDE ALPARGATA REFORZADA SUELA PVC", "236007101439", 6, 6329.77),   # VERDE PVC T39
        (63881, "ALPARGATA REFORZADA VERDE C/ELAST S/EVA", "236495001442", 12, 5037.99),   # VERDE EVA T42
        (63882, "ALPARGATA REFORZADA VERDE C/ELAST S/EVA", "236495001443", 12, 5037.99),   # VERDE EVA T43
        (304327, "710 VERDE ALPARGATA REFORZADA SUELA PVC", "236007101443", 6, 6329.77),   # VERDE PVC T43
    ],
    "JUN": [  # 102p $520,213 — entrega 19/06/2026
        (63836, "ALPARGATA REFORZADA NEGRO C/ELAST S/EVA", "236495000036", 12, 4537.25),   # NEGRO EVA T36
        (63837, "ALPARGATA REFORZADA NEGRO C/ELAST S/EVA", "236495000037", 12, 4537.25),   # NEGRO EVA T37
        (348530, "710 NEGRO ALPARGATA REFORZADA SUELA PVC", "236007100037", 6, 5977.19),   # NEGRO PVC T37
        (63840, "ALPARGATA REFORZADA NEGRO C/ELAST S/EVA", "236495000040", 12, 5037.99),   # NEGRO EVA T40
        (304317, "710 NEGRO ALPARGATA REFORZADA SUELA PVC", "236007100041", 6, 6867.84),   # NEGRO PVC T41
        (63842, "ALPARGATA REFORZADA NEGRO C/ELAST S/EVA", "236495000042", 12, 5037.99),   # NEGRO EVA T42
        (63870, "ALPARGATA REFORZADA AZUL C/ELAST S/EVA", "236495000244", 12, 5037.99),    # AZUL EVA T44
        (63876, "ALPARGATA REFORZADA VERDE C/ELAST S/EVA", "236495001437", 12, 4537.25),   # VERDE EVA T37
        (304324, "710 VERDE ALPARGATA REFORZADA SUELA PVC", "236007101440", 6, 6329.77),   # VERDE PVC T40
        (63855, "ALPARGATA REFORZADA BLANCO C/ELAST S/EVA", "236495000142", 12, 5037.99),  # BLANCO EVA T42
    ],
    "JUL": [  # 42p $229,565 — entrega 19/07/2026
        (63834, "ALPARGATA REFORZADA NEGRO C/ELAST S/EVA", "236495000034", 12, 4537.25),   # NEGRO EVA T34
        (304292, "710 AZUL ALPARGATA REFORZADA SUELA PVC", "236007100240", 6, 6450.80),    # AZUL PVC T40
        (304294, "710 AZUL ALPARGATA REFORZADA SUELA PVC", "236007100242", 6, 6329.77),    # AZUL PVC T42
        (63880, "ALPARGATA REFORZADA VERDE C/ELAST S/EVA", "236495001441", 12, 5037.99),   # VERDE EVA T41
        (304326, "710 VERDE ALPARGATA REFORZADA SUELA PVC", "236007101442", 6, 6329.77),   # VERDE PVC T42
    ],
    "AGO": [  # 36p $188,080 — entrega 19/08/2026
        (304318, "710 NEGRO ALPARGATA REFORZADA SUELA PVC", "236007100042", 6, 6867.84),   # NEGRO PVC T42
        (63863, "ALPARGATA REFORZADA AZUL C/ELAST S/EVA", "236495000237", 12, 4537.25),    # AZUL EVA T37
        (304296, "710 AZUL ALPARGATA REFORZADA SUELA PVC", "236007100244", 6, 6329.77),    # AZUL PVC T44
        (63877, "ALPARGATA REFORZADA VERDE C/ELAST S/EVA", "236495001438", 12, 4537.25),   # VERDE EVA T38
    ],
    "SEP": [  # 36p $169,350 — entrega 19/09/2026
        (63838, "ALPARGATA REFORZADA NEGRO C/ELAST S/EVA", "236495000038", 12, 4537.25),   # NEGRO EVA T38
        (63865, "ALPARGATA REFORZADA AZUL C/ELAST S/EVA", "236495000239", 12, 5037.99),    # AZUL EVA T39
        (250669, "ALPARGATA REFORZADA BORDO C/ELAST S/EVA", "236495003537", 12, 4537.25),  # BORDO EVA T37
    ],
    "OCT": [  # 54p $317,262 — entrega 19/10/2026
        (304315, "710 NEGRO ALPARGATA REFORZADA SUELA PVC", "236007100039", 6, 6867.84),   # NEGRO PVC T39
        (304316, "710 NEGRO ALPARGATA REFORZADA SUELA PVC", "236007100040", 6, 6867.84),   # NEGRO PVC T40
        (110016, "ALPARGATA REFORZADA BORDO C/ELAST S/EVA", "236495003541", 12, 5037.99),  # BORDO EVA T41
        (304309, "710 BORDO ALPARGATA REFORZADA SUELA PVC", "236007103041", 6, 6329.77),   # BORDO PVC T41
        (304310, "710 BORDO ALPARGATA REFORZADA SUELA PVC", "236007103042", 6, 6329.77),   # BORDO PVC T42
        (110018, "ALPARGATA REFORZADA BORDO C/ELAST S/EVA", "236495003543", 12, 5037.99),  # BORDO EVA T43
        (309116, "710 VERDE ALPARGATA REFORZADA SUELA PVC", "236007101438", 6, 6329.77),   # VERDE PVC T38
    ],
}

FECHAS_ENTREGA = {
    "ABR": date(2026, 4, 19),
    "MAY": date(2026, 5, 19),
    "JUN": date(2026, 6, 19),
    "JUL": date(2026, 7, 19),
    "AGO": date(2026, 8, 19),
    "SEP": date(2026, 9, 19),
    "OCT": date(2026, 10, 19),
}

# -- SQL ---------------------------------------------------------------
SQL_CABECERA = """
    INSERT INTO {tabla} (
        codigo, letra, sucursal,
        numero, orden, deposito,
        cuenta, denominacion,
        fecha_comprobante, fecha_proceso,
        observaciones,
        descuento_general, monto_descuento,
        bonificacion_general, monto_bonificacion,
        financiacion_general, monto_financiacion,
        iva1, monto_iva1, iva2, monto_iva2, monto_impuesto,
        importe_neto, monto_exento,
        estado, zona, condicion_iva, numero_cuit, copias,
        cuenta_y_orden, pack, reintegro, cambio, transferencia,
        entregador, usuario, campo, sistema_cc, moneda, sector,
        forma_pago, plan_canje, tipo_vcto_pago, tipo_operacion, tipo_ajuste,
        medio_pago, cuenta_cc, concurso
    ) VALUES (
        ?, ?, ?,
        ?, ?, 0,
        ?, ?,
        ?, ?,
        ?,
        0, 0, 0, 0, 0, 0,
        21, 0, 10.5, 0, 0,
        0, 0,
        'V', ?, ?, ?, 1,
        'N', 'N', 'N', 'N', 'N',
        0, 'COWORK', 0, 2, 0, 0,
        0, 'N', 0, 0, 0,
        ' ', ?, 'N'
    )
"""

SQL_DETALLE = """
    INSERT INTO {tabla} (
        codigo, letra, sucursal,
        numero, orden, renglon,
        articulo, descripcion, codigo_sinonimo,
        cantidad, precio,
        cuenta, fecha, fecha_entrega,
        estado
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'V')
"""


def insertar_pedido(cursor, renglones, fecha_entrega, obs, label):
    """Inserta un pedido (cabecera + detalle) en MSGESTION01."""
    ahora = datetime.now()
    fecha_comprobante = date(2026, 3, 13)
    tabla_p2 = f"{BASE_PEDIDO}.dbo.pedico2"
    tabla_p1 = f"{BASE_PEDIDO}.dbo.pedico1"

    # numero = MAX+1 (numeric(8,0), sin problema)
    cursor.execute(f"SELECT ISNULL(MAX(numero),0)+1 FROM {tabla_p2} WHERE codigo = ?", CODIGO_PEDIDO)
    numero = cursor.fetchone()[0]

    # orden = 1 FIJO (numeric(2,0) max 99, MAX ya esta en 99)
    orden = ORDEN_FIJA

    cursor.execute(SQL_CABECERA.format(tabla=tabla_p2), (
        CODIGO_PEDIDO, LETRA_PEDIDO, SUCURSAL_PEDIDO,
        numero, orden,
        CABECERA_BASE["cuenta"], CABECERA_BASE["denominacion"],
        fecha_comprobante, ahora,
        obs,
        CABECERA_BASE["zona"], CABECERA_BASE["condicion_iva"], CABECERA_BASE["cuit"],
        CABECERA_BASE["cuenta"],
    ))

    for i, (art, desc, sin, qty, precio) in enumerate(renglones, 1):
        cursor.execute(SQL_DETALLE.format(tabla=tabla_p1), (
            CODIGO_PEDIDO, LETRA_PEDIDO, SUCURSAL_PEDIDO,
            numero, orden, i,
            art, desc, sin,
            qty, precio,
            CABECERA_BASE["cuenta"],
            fecha_comprobante,
            fecha_entrega,
        ))

    total_pares = sum(r[3] for r in renglones)
    total_monto = sum(r[3] * r[4] for r in renglones)
    print(f"    {label}: NP #{numero} — {len(renglones)} reng, {total_pares}p, ${total_monto:,.0f}")
    return numero


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    print(f"\n{'='*70}")
    print(f"PEDIDO CONFORTABLE SRL — ENTREGAS MENSUALES ABR-OCT 2026")
    print(f"Vel. real (quiebre), todo MSGESTION01, min EVA=12 PVC=6")
    print(f"{'='*70}")
    print(f"  Servidor:  {SERVIDOR}")
    print(f"  Base:      {BASE_PEDIDO}")
    print(f"  Orden:     {ORDEN_FIJA} (fija)")
    print(f"  Modo:      {'DRY-RUN' if dry_run else 'PRODUCCION'}")
    print(f"{'='*70}")

    gran_total = 0
    gran_monto = 0
    meses_con_pedido = []

    for mes in ["ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT"]:
        renglones = PEDIDOS_MES[mes]
        if not renglones:
            continue
        pares = sum(r[3] for r in renglones)
        monto = sum(r[3] * r[4] for r in renglones)
        gran_total += pares
        gran_monto += monto
        meses_con_pedido.append(mes)

        print(f"\n  {mes} (entrega {FECHAS_ENTREGA[mes]}): {pares}p, {len(renglones)} reng — ${monto:,.0f}")
        for art, desc, sin, qty, precio in renglones:
            print(f"    [{art:6d}] {sin} x{qty:3d} @ ${precio:,.2f}")

    print(f"\n{'='*70}")
    print(f"  TOTAL: {gran_total} pares — ${gran_monto:,.0f}")
    print(f"  Pedidos: {len(meses_con_pedido)} notas de pedido en {BASE_PEDIDO}")
    print(f"{'='*70}")

    if dry_run:
        print(f"\n[DRY RUN] Ningun dato fue escrito.")
        print(f"\n  Probando conexion a {SERVIDOR}...", end=" ")
        try:
            with pyodbc.connect(get_conn("msgestionC"), timeout=5) as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
        return

    # -- EJECUCION REAL ------------------------------------------------
    confirmacion = input(f"\nInsertar {len(meses_con_pedido)} pedidos ({gran_total} pares) en {BASE_PEDIDO}? (s/N): ").strip().lower()
    if confirmacion != "s":
        print("Cancelado.")
        sys.exit(0)

    numeros = []
    try:
        for mes in meses_con_pedido:
            renglones = PEDIDOS_MES[mes]
            fecha_ent = FECHAS_ENTREGA[mes]
            pares = sum(r[3] for r in renglones)

            obs = (f"CONFORTABLE reposicion {mes}-2026 ({pares}p). "
                   f"Vel.real quiebre. Entrega {fecha_ent}.")

            print(f"\n  {mes}:")

            with pyodbc.connect(get_conn("msgestion01"), timeout=10) as conn:
                conn.autocommit = False
                cursor = conn.cursor()
                num = insertar_pedido(cursor, renglones, fecha_ent, obs, mes)
                conn.commit()
                numeros.append((mes, num))

        print(f"\n{'='*70}")
        print(f"  {len(numeros)} PEDIDOS INSERTADOS OK en {BASE_PEDIDO}")
        print(f"{'='*70}")
        for mes, num in numeros:
            print(f"  {mes}: #{num}")

        print(f"\nVerificar:")
        for mes, num in numeros:
            print(f"  SELECT * FROM {BASE_PEDIDO}.dbo.pedico1 WHERE numero = {num} AND codigo = 8")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        print("  Rollback del ultimo pedido — los anteriores YA estan commiteados.")
        print("  Pedidos insertados antes del error:")
        for mes, num in numeros:
            print(f"    {mes}: #{num}")
        sys.exit(1)


if __name__ == "__main__":
    main()
