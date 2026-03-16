#!/usr/bin/env python3
# insertar_go_dance.py — Pedido GO Dance (ZOTZ #457)
# 354 pares, 6 modelos, talles 35-40, entrega 17/3/2026
# Empresa: CALZALINDO → MSGESTION01
#
# EJECUTAR DESDE MAC:
#   cd ~/Desktop/cowork_pedidos/_scripts_oneshot
#   python3 insertar_go_dance.py --dry-run
#   python3 insertar_go_dance.py --ejecutar
#
# EJECUTAR DESDE 111:
#   cd C:\cowork_pedidos\_scripts_oneshot
#   py -3 insertar_go_dance.py --dry-run
#   py -3 insertar_go_dance.py --ejecutar

import sys
import pyodbc
import socket
from datetime import date, datetime

# ── AUTO-DETECT SERVER vs MAC ────────────────────────────
_hostname = socket.gethostname().upper()
if _hostname in ("DELL-SVR", "DELLSVR"):
    SERVIDOR = "localhost"
    DRIVER = "ODBC Driver 17 for SQL Server"
    EXTRAS = ""
else:
    SERVIDOR = "192.168.2.111"
    DRIVER = "ODBC Driver 18 for SQL Server"
    EXTRAS = "TrustServerCertificate=yes;Encrypt=no;"

CONN_STR = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVIDOR};"
    f"DATABASE=msgestionC;"
    f"UID=am;PWD=dl;"
    f"{EXTRAS}"
)

# ── CONSTANTES PEDIDO ────────────────────────────────────
CODIGO_PEDIDO = 8
LETRA_PEDIDO = "X"
SUCURSAL_PEDIDO = 1
EMPRESA = "CALZALINDO"
TABLA_P2 = "MSGESTION01.dbo.pedico2"
TABLA_P1 = "MSGESTION01.dbo.pedico1"

# ── CABECERA ─────────────────────────────────────────────
cabecera = {
    "cuenta":            457,
    "denominacion":      "ZOTZ",
    "fecha_comprobante": date(2026, 3, 10),
    "fecha_entrega":     date(2026, 3, 17),
    "observaciones":     "Reposicion GO Dance otono-invierno 2026. 354 pares, 6 modelos. "
                         "Analisis ajustado por quiebre de stock (47-95% segun modelo). "
                         "501 NEGRO top seller, T38 hottest (33% share).",
    "zona":              0,
    "condicion_iva":     "I",
    "cuit":              "",
}

# ── RENGLONES (36 items) ────────────────────────────────
renglones = [
    # 360 NEGRO ZAPATO BAILE ACORD C/ TACO — 32 pares @ $30,000 (precio fabrica)
    {"articulo": 336268, "descripcion": "360 NEGRO ZAPATO BAILE ACORD C/ TACO",           "codigo_sinonimo": "457003600035", "cantidad":  2, "precio": 30000},  # T35
    {"articulo": 336269, "descripcion": "360 NEGRO ZAPATO BAILE ACORD C/ TACO",           "codigo_sinonimo": "457003600036", "cantidad":  4, "precio": 30000},  # T36
    {"articulo": 336270, "descripcion": "360 NEGRO ZAPATO BAILE ACORD C/ TACO",           "codigo_sinonimo": "457003600037", "cantidad":  8, "precio": 30000},  # T37
    {"articulo": 336271, "descripcion": "360 NEGRO ZAPATO BAILE ACORD C/ TACO",           "codigo_sinonimo": "457003600038", "cantidad":  8, "precio": 30000},  # T38
    {"articulo": 336272, "descripcion": "360 NEGRO ZAPATO BAILE ACORD C/ TACO",           "codigo_sinonimo": "457003600039", "cantidad":  6, "precio": 30000},  # T39
    {"articulo": 336273, "descripcion": "360 NEGRO ZAPATO BAILE ACORD C/ TACO",           "codigo_sinonimo": "457003600040", "cantidad":  4, "precio": 30000},  # T40

    # 501 BEIGE ZAPATO TANGO CLASICO P/ABIERTA — 46 pares @ $27,000 (precio fabrica)
    {"articulo": 332301, "descripcion": "501 BEIGE ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005011535", "cantidad":  2, "precio": 27000},  # T35
    {"articulo": 348708, "descripcion": "501 BEIGE ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005011536", "cantidad":  6, "precio": 27000},  # T36
    {"articulo": 332303, "descripcion": "501 BEIGE ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005011537", "cantidad": 12, "precio": 27000},  # T37
    {"articulo": 332304, "descripcion": "501 BEIGE ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005011538", "cantidad": 12, "precio": 27000},  # T38
    {"articulo": 332305, "descripcion": "501 BEIGE ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005011539", "cantidad":  8, "precio": 27000},  # T39
    {"articulo": 332306, "descripcion": "501 BEIGE ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005011540", "cantidad":  6, "precio": 27000},  # T40

    # 501 NEGRO ZAPATO TANGO CLASICO P/ABIERTA — 92 pares @ $27,000 (precio fabrica)
    {"articulo": 319402, "descripcion": "501 NEGRO ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005010035", "cantidad":  6, "precio": 27000},  # T35
    {"articulo": 319395, "descripcion": "501 NEGRO ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005010036", "cantidad": 12, "precio": 27000},  # T36
    {"articulo": 319396, "descripcion": "501 NEGRO ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005010037", "cantidad": 22, "precio": 27000},  # T37
    {"articulo": 319397, "descripcion": "501 NEGRO ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005010038", "cantidad": 22, "precio": 27000},  # T38
    {"articulo": 319398, "descripcion": "501 NEGRO ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005010039", "cantidad": 18, "precio": 27000},  # T39
    {"articulo": 319399, "descripcion": "501 NEGRO ZAPATO TANGO CLASICO P/ABIERTA",       "codigo_sinonimo": "457005010040", "cantidad": 12, "precio": 27000},  # T40

    # 501 NUDE ZAPATO TANGO CLASICO P/ABIERTA — 46 pares @ $24,000 (precio fabrica)
    {"articulo": 325463, "descripcion": "501 NUDE ZAPATO TANGO CLASICO P/ABIERTA",        "codigo_sinonimo": "457005012535", "cantidad":  2, "precio": 24000},  # T35
    {"articulo": 325464, "descripcion": "501 NUDE ZAPATO TANGO CLASICO P/ABIERTA",        "codigo_sinonimo": "457005012536", "cantidad":  6, "precio": 24000},  # T36
    {"articulo": 325465, "descripcion": "501 NUDE ZAPATO TANGO CLASICO P/ABIERTA",        "codigo_sinonimo": "457005012537", "cantidad": 12, "precio": 24000},  # T37
    {"articulo": 325466, "descripcion": "501 NUDE ZAPATO TANGO CLASICO P/ABIERTA",        "codigo_sinonimo": "457005012538", "cantidad": 12, "precio": 24000},  # T38
    {"articulo": 325467, "descripcion": "501 NUDE ZAPATO TANGO CLASICO P/ABIERTA",        "codigo_sinonimo": "457005012539", "cantidad":  8, "precio": 24000},  # T39
    {"articulo": 325468, "descripcion": "501 NUDE ZAPATO TANGO CLASICO P/ABIERTA",        "codigo_sinonimo": "457005012540", "cantidad":  6, "precio": 24000},  # T40

    # 502 NEGRO ZAPATO TANGO T/CRUZ P/ABIERTA — 92 pares @ $24,000 (precio fabrica)
    {"articulo": 327275, "descripcion": "502 NEGRO ZAPATO TANGO T/CRUZ P/ABIERTA",        "codigo_sinonimo": "457005020035", "cantidad":  6, "precio": 24000},  # T35
    {"articulo": 327276, "descripcion": "502 NEGRO ZAPATO TANGO T/CRUZ P/ABIERTA",        "codigo_sinonimo": "457005020036", "cantidad": 12, "precio": 24000},  # T36
    {"articulo": 327277, "descripcion": "502 NEGRO ZAPATO TANGO T/CRUZ P/ABIERTA",        "codigo_sinonimo": "457005020037", "cantidad": 22, "precio": 24000},  # T37
    {"articulo": 327278, "descripcion": "502 NEGRO ZAPATO TANGO T/CRUZ P/ABIERTA",        "codigo_sinonimo": "457005020038", "cantidad": 22, "precio": 24000},  # T38
    {"articulo": 327279, "descripcion": "502 NEGRO ZAPATO TANGO T/CRUZ P/ABIERTA",        "codigo_sinonimo": "457005020039", "cantidad": 18, "precio": 24000},  # T39
    {"articulo": 327280, "descripcion": "502 NEGRO ZAPATO TANGO T/CRUZ P/ABIERTA",        "codigo_sinonimo": "457005020040", "cantidad": 12, "precio": 24000},  # T40

    # 502/5 NEGRO ZAPATO TANGO 5.5 T/CRUZ P/ABIERTA T/CHUPETE — 46 pares @ $27,000 (precio fabrica)
    {"articulo": 353619, "descripcion": "502/5 NEGRO ZAPATO TANGO 5.5 T/CRUZ P/ABIERTA T/CHUPETE", "codigo_sinonimo": "457050250035", "cantidad":  2, "precio": 27000},  # T35
    {"articulo": 353620, "descripcion": "502/5 NEGRO ZAPATO TANGO 5.5 T/CRUZ P/ABIERTA T/CHUPETE", "codigo_sinonimo": "457050250036", "cantidad":  6, "precio": 27000},  # T36
    {"articulo": 353621, "descripcion": "502/5 NEGRO ZAPATO TANGO 5.5 T/CRUZ P/ABIERTA T/CHUPETE", "codigo_sinonimo": "457050250037", "cantidad": 12, "precio": 27000},  # T37
    {"articulo": 353622, "descripcion": "502/5 NEGRO ZAPATO TANGO 5.5 T/CRUZ P/ABIERTA T/CHUPETE", "codigo_sinonimo": "457050250038", "cantidad": 12, "precio": 27000},  # T38
    {"articulo": 353623, "descripcion": "502/5 NEGRO ZAPATO TANGO 5.5 T/CRUZ P/ABIERTA T/CHUPETE", "codigo_sinonimo": "457050250039", "cantidad":  8, "precio": 27000},  # T39
    {"articulo": 353624, "descripcion": "502/5 NEGRO ZAPATO TANGO 5.5 T/CRUZ P/ABIERTA T/CHUPETE", "codigo_sinonimo": "457050250040", "cantidad":  6, "precio": 27000},  # T40
]


# ── SQL STATEMENTS ───────────────────────────────────────

SQL_CABECERA = f"""
    INSERT INTO {TABLA_P2} (
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

SQL_DETALLE = f"""
    INSERT INTO {TABLA_P1} (
        codigo, letra, sucursal,
        numero, orden, renglon,
        articulo, descripcion, codigo_sinonimo,
        cantidad, precio,
        cuenta, fecha, fecha_entrega,
        estado
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'V')
"""


# ── MAIN ─────────────────────────────────────────────────

def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    total_pares = sum(r["cantidad"] for r in renglones)
    total_monto = sum(r["cantidad"] * r["precio"] for r in renglones)

    # Subtotales por modelo
    modelos = {}
    for r in renglones:
        modelo = r["descripcion"].split(" ZAPATO")[0]
        if modelo not in modelos:
            modelos[modelo] = {"pares": 0, "precio": r["precio"]}
        modelos[modelo]["pares"] += r["cantidad"]

    print(f"\n{'='*65}")
    print(f"PEDIDO GO DANCE (ZOTZ) — {total_pares} pares — ${total_monto:,.0f}")
    print(f"{'='*65}")
    for m, d in modelos.items():
        print(f"  {m:50s} {d['pares']:3d} pares @ ${d['precio']:>7,.0f}")
    print(f"  {'─'*60}")
    print(f"  {'TOTAL':50s} {total_pares:3d} pares = ${total_monto:>10,.0f}")
    print(f"\n  Proveedor : ZOTZ (457)")
    print(f"  Empresa   : {EMPRESA} -> {TABLA_P2.split('.')[0]}")
    print(f"  Entrega   : {cabecera['fecha_entrega']}")
    print(f"  Servidor  : {SERVIDOR} (hostname: {_hostname})")
    print(f"  Modo      : {'DRY-RUN (no escribe)' if dry_run else 'PRODUCCION'}")
    print(f"{'='*65}")

    if dry_run:
        print(f"\n[DRY RUN] Cabecera: {TABLA_P2}")
        print(f"  cuenta={cabecera['cuenta']}, denominacion={cabecera['denominacion']}")
        print(f"  fecha_comprobante={cabecera['fecha_comprobante']}")
        print(f"  fecha_entrega={cabecera['fecha_entrega']}")
        print(f"  observaciones={cabecera['observaciones'][:80]}...")
        print(f"\n[DRY RUN] Detalle: {TABLA_P1} — {len(renglones)} renglones")
        for i, r in enumerate(renglones, 1):
            print(f"  {i:>3}. [{r['articulo']}] {r['descripcion'][:50]:50s} x{r['cantidad']:>2} ${r['precio']:>7,.0f}")
        print(f"\n[DRY RUN] Ningun dato fue escrito en la base.")

        # Test conexion
        print(f"\n  Probando conexion a {SERVIDOR}...", end=" ")
        try:
            with pyodbc.connect(CONN_STR, timeout=5) as conn:
                cur = conn.cursor()
                cur.execute(f"SELECT ISNULL(MAX(numero),0)+1 FROM {TABLA_P2} WHERE codigo = {CODIGO_PEDIDO}")
                prox = cur.fetchone()[0]
                print(f"OK — proximo numero: {prox}")
        except Exception as e:
            print(f"ERROR: {e}")
        return

    # ── EJECUCION REAL ───────────────────────────────────
    confirmacion = input("\nConfirmar INSERT en produccion? (s/N): ").strip().lower()
    if confirmacion != "s":
        print("Cancelado.")
        sys.exit(0)

    ahora = datetime.now()

    try:
        with pyodbc.connect(CONN_STR, timeout=10) as conn:
            conn.autocommit = False
            cursor = conn.cursor()

            # Proximo numero y orden
            cursor.execute(f"SELECT ISNULL(MAX(numero),0)+1 FROM {TABLA_P2} WHERE codigo = ?", CODIGO_PEDIDO)
            numero = cursor.fetchone()[0]

            cursor.execute(f"SELECT ISNULL(MAX(orden),0)+1 FROM {TABLA_P2} WHERE codigo = ?", CODIGO_PEDIDO)
            orden = cursor.fetchone()[0]

            # INSERT cabecera
            cursor.execute(SQL_CABECERA, (
                CODIGO_PEDIDO, LETRA_PEDIDO, SUCURSAL_PEDIDO,
                numero, orden,
                cabecera["cuenta"], cabecera["denominacion"],
                cabecera["fecha_comprobante"], ahora,
                cabecera["observaciones"],
                cabecera["zona"], cabecera["condicion_iva"], cabecera["cuit"],
                cabecera["cuenta"],  # cuenta_cc
            ))

            # INSERT renglones
            for i, r in enumerate(renglones, 1):
                cursor.execute(SQL_DETALLE, (
                    CODIGO_PEDIDO, LETRA_PEDIDO, SUCURSAL_PEDIDO,
                    numero, orden, i,
                    r["articulo"], r["descripcion"], r.get("codigo_sinonimo", ""),
                    r["cantidad"], r["precio"],
                    cabecera["cuenta"],
                    cabecera["fecha_comprobante"],
                    cabecera["fecha_entrega"],
                ))

            conn.commit()
            print(f"\n{'='*65}")
            print(f"  PEDIDO INSERTADO OK")
            print(f"  Numero: {numero} | Orden: {orden} | Renglones: {len(renglones)}")
            print(f"  Tabla cabecera: {TABLA_P2}")
            print(f"  Tabla detalle:  {TABLA_P1}")
            print(f"{'='*65}")
            print(f"\nVerificar:")
            print(f"  SELECT * FROM {TABLA_P2} WHERE numero = {numero}")
            print(f"  SELECT * FROM {TABLA_P1} WHERE numero = {numero}")

    except Exception as e:
        print(f"\n  ERROR al insertar pedido: {e}")
        print("  Rollback ejecutado — ningun dato fue guardado.")
        sys.exit(1)


if __name__ == "__main__":
    main()
