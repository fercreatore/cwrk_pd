#!/usr/bin/env python3
# modificar_carmel_134069.py
# Elimina el pedido #134069 (CARMEL CANELA original, 30 pares)
# y lo reemplaza con lo que realmente van a entregar (12 pares):
#   AZUL/COGNAC CARMEL 03: T41=1, T43=3
#   CANELA CARMEL 03:      T41=1, T42=4, T43=3
#
# Empresa: H4 → MSGESTION03
# Proveedor: 561 Souter S.A. (RINGO/CARMEL)
#
# EJECUTAR DESDE MAC:
#   cd ~/Desktop/cowork_pedidos/_scripts_oneshot
#   python3 modificar_carmel_134069.py --dry-run
#   python3 modificar_carmel_134069.py --ejecutar

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

# ── CONSTANTES ───────────────────────────────────────────
CODIGO_PEDIDO = 8
LETRA_PEDIDO = "X"
SUCURSAL_PEDIDO = 1
NUMERO_VIEJO = 134069  # pedido a eliminar
TABLA_P2 = "MSGESTION03.dbo.pedico2"
TABLA_P1 = "MSGESTION03.dbo.pedico1"

# ── CABECERA NUEVA ───────────────────────────────────────
cabecera = {
    "cuenta":            561,
    "denominacion":      "Souter S.A.",
    "fecha_comprobante": date(2026, 3, 10),
    "fecha_entrega":     date(2026, 3, 17),
    "observaciones":     "CARMEL RINGO reposicion inv 2026 (reemplazo de NP 134069). "
                         "Solo entregan 12 pares: AZUL/COGNAC 03 (4p) + CANELA 03 (8p).",
    "zona":              5,
    "condicion_iva":     "I",
    "cuit":              "30707508597",
}

# ── RENGLONES NUEVOS (12 pares) ──────────────────────────
# Precios = $34,700 (precio de compra CARMEL 03, mismo que pedido original)
renglones = [
    # AZUL/COGNAC CARMEL 03 — 4 pares
    {"articulo": 260999, "descripcion": "CARMEL 03 AZUL/COGNAC NAUTICO 2 ELAST DET TALON", "codigo_sinonimo": "561CAR035141", "cantidad": 1, "precio": 34700},  # T41
    {"articulo": 261001, "descripcion": "CARMEL 03 AZUL/COGNAC NAUTICO 2 ELAST DET TALON", "codigo_sinonimo": "561CAR035143", "cantidad": 3, "precio": 34700},  # T43

    # CANELA CARMEL 03 — 8 pares
    {"articulo": 249885, "descripcion": "CARMEL 03 CANELA NAUTICO 2 ELAST DET TALON",      "codigo_sinonimo": "561CAR032241", "cantidad": 1, "precio": 34700},  # T41
    {"articulo": 249886, "descripcion": "CARMEL 03 CANELA NAUTICO 2 ELAST DET TALON",      "codigo_sinonimo": "561CAR032242", "cantidad": 4, "precio": 34700},  # T42
    {"articulo": 249887, "descripcion": "CARMEL 03 CANELA NAUTICO 2 ELAST DET TALON",      "codigo_sinonimo": "561CAR032243", "cantidad": 3, "precio": 34700},  # T43
]

# ── SQL ──────────────────────────────────────────────────
SQL_DELETE_P1 = f"DELETE FROM {TABLA_P1} WHERE numero = ? AND codigo = ?"
SQL_DELETE_P2 = f"DELETE FROM {TABLA_P2} WHERE numero = ? AND codigo = ?"

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


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    total_pares = sum(r["cantidad"] for r in renglones)
    total_monto = sum(r["cantidad"] * r["precio"] for r in renglones)

    print(f"\n{'='*65}")
    print(f"MODIFICACION PEDIDO CARMEL (reemplaza NP #{NUMERO_VIEJO})")
    print(f"{'='*65}")
    print(f"  ANTES: 30 pares (CANELA 03 + CANELA 04, 8 renglones)")
    print(f"  AHORA: {total_pares} pares (AZUL/COGNAC 03 + CANELA 03, {len(renglones)} renglones)")
    print()
    for i, r in enumerate(renglones, 1):
        talle = r["codigo_sinonimo"][-2:]
        color = "AZUL/COGNAC" if "AZUL" in r["descripcion"] else "CANELA"
        print(f"    {i}. [{r['articulo']}] {color} T{talle} x{r['cantidad']} @ ${r['precio']:,.0f}")
    print(f"\n  Total: {total_pares} pares — ${total_monto:,.0f}")
    print(f"  Proveedor : Souter S.A. (561)")
    print(f"  Empresa   : H4 -> MSGESTION03")
    print(f"  Servidor  : {SERVIDOR}")
    print(f"  Modo      : {'DRY-RUN' if dry_run else 'PRODUCCION'}")
    print(f"{'='*65}")

    if dry_run:
        print(f"\n[DRY RUN] Paso 1: DELETE pedico1 WHERE numero={NUMERO_VIEJO}")
        print(f"[DRY RUN] Paso 2: DELETE pedico2 WHERE numero={NUMERO_VIEJO}")
        print(f"[DRY RUN] Paso 3: INSERT nuevo pedico2 (numero nuevo via MAX+1)")
        print(f"[DRY RUN] Paso 4: INSERT {len(renglones)} renglones en pedico1")
        print(f"\n[DRY RUN] Ningun dato fue escrito.")

        # Test conexion
        print(f"\n  Probando conexion a {SERVIDOR}...", end=" ")
        try:
            with pyodbc.connect(CONN_STR, timeout=5) as conn:
                cur = conn.cursor()
                # Verificar que el pedido viejo existe
                cur.execute(f"SELECT COUNT(*) FROM {TABLA_P1} WHERE numero = ? AND codigo = ?",
                           NUMERO_VIEJO, CODIGO_PEDIDO)
                cnt = cur.fetchone()[0]
                print(f"OK — pedido #{NUMERO_VIEJO} tiene {cnt} renglones en {TABLA_P1}")
        except Exception as e:
            print(f"ERROR: {e}")
        return

    # ── EJECUCION REAL ───────────────────────────────────
    confirmacion = input(f"\nVa a ELIMINAR NP #{NUMERO_VIEJO} y crear uno nuevo con {total_pares} pares. Confirmar? (s/N): ").strip().lower()
    if confirmacion != "s":
        print("Cancelado.")
        sys.exit(0)

    ahora = datetime.now()

    try:
        with pyodbc.connect(CONN_STR, timeout=10) as conn:
            conn.autocommit = False
            cursor = conn.cursor()

            # Paso 1: DELETE detalle viejo
            cursor.execute(SQL_DELETE_P1, (NUMERO_VIEJO, CODIGO_PEDIDO))
            deleted_p1 = cursor.rowcount
            print(f"  Paso 1: DELETE pedico1 #{NUMERO_VIEJO} — {deleted_p1} renglones eliminados")

            # Paso 2: DELETE cabecera vieja
            cursor.execute(SQL_DELETE_P2, (NUMERO_VIEJO, CODIGO_PEDIDO))
            deleted_p2 = cursor.rowcount
            print(f"  Paso 2: DELETE pedico2 #{NUMERO_VIEJO} — {deleted_p2} cabecera(s) eliminada(s)")

            # Paso 3: Nuevo numero
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
                cabecera["cuenta"],
            ))
            print(f"  Paso 3: INSERT pedico2 — nuevo numero: {numero}")

            # Paso 4: INSERT renglones
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
            print(f"  Paso 4: INSERT pedico1 — {len(renglones)} renglones")
            print(f"\n{'='*65}")
            print(f"  PEDIDO REEMPLAZADO OK")
            print(f"  Viejo: #{NUMERO_VIEJO} (eliminado)")
            print(f"  Nuevo: #{numero} | {total_pares} pares | ${total_monto:,.0f}")
            print(f"{'='*65}")
            print(f"\nVerificar:")
            print(f"  SELECT * FROM {TABLA_P2} WHERE numero = {numero}")
            print(f"  SELECT * FROM {TABLA_P1} WHERE numero = {numero}")
            print(f"  -- Confirmar que el viejo no existe:")
            print(f"  SELECT * FROM {TABLA_P2} WHERE numero = {NUMERO_VIEJO}")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        print("  Rollback ejecutado — nada fue modificado.")
        sys.exit(1)


if __name__ == "__main__":
    main()
