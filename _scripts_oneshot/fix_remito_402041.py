#!/usr/bin/env python3
"""
fix_remito_402041.py  (v2 — 05-abr-2026)
==========================================
Corrige el remito testigo 402041 que quedó con datos erróneos.

SITUACION VERIFICADA (05-abr-2026):
  El remito existe en AMBAS bases (msgestion01 y msgestion03):
    compras2: sucursal=1, numero=402041, usuario=fcalaianov, dep=11, monto=79200
    compras1: renglon=1, articulo=361648 (SEATTLE T40), cantidad=1, dep=11
    movi_stock: articulo=361648, dep=11, operacion=+, cantidad=1  (en AMBAS bases)
    stock:      dep=11, articulo=361648, stock_actual=2  (en AMBAS bases — doble por bug)

  Lo correcto:
    - articulo debe ser 361645 (TEXAS T40), no 361648 (SEATTLE T40)
    - cantidad debe ser 2 (los 2 pares que llegaron)

CORRECCIONES A APLICAR (en msgestion01 Y msgestion03):
  1. compras1:   articulo 361648→361645, cantidad 1→2
  2. movi_stock: articulo 361648→361645, cantidad 1→2
  3. stock dep=11 articulo 361648: stock_actual=2 → 0  (SET directo)
  4. stock dep=11 articulo 361645: no existe → INSERT con stock_actual=2

USO:
  py -3 fix_remito_402041.py            # dry-run (default)
  py -3 fix_remito_402041.py --ejecutar # aplica cambios en produccion
"""

import sys
import pyodbc

# ── CONEXION ──────────────────────────────────────────────────────────────────
# Conecta al 111 en produccion.
import socket as _socket
_host = _socket.gethostname().upper()
if _host in ("DELL-SVR", "DELLSVR"):
    _srv = "localhost"
    _drv = "SQL Server"
else:
    _srv = "192.168.2.111"
    _drv = "ODBC Driver 17 for SQL Server"

def get_conn(base):
    return pyodbc.connect(
        f"DRIVER={{{_drv}}};SERVER={_srv};DATABASE={base};"
        "UID=am;PWD=dl;TrustServerCertificate=yes;Encrypt=no;",
        timeout=10
    )

# ── CONSTANTES ────────────────────────────────────────────────────────────────
NUMERO_REMITO  = 402041
SUCURSAL       = 1
CODIGO_REMITO  = 7
LETRA_REMITO   = "R"
DEPOSITO       = 11

ART_INCORRECTO = 361648   # SEATTLE T40  — el que quedó mal
ART_CORRECTO   = 361645   # TEXAS T40    — el correcto

CANT_ORIGINAL  = 1        # cantidad incorrecta en compras1/movi_stock
CANT_CORRECTA  = 2        # cantidad correcta (2 pares de TEXAS T40)

# Bases a corregir (el remito existe en ambas)
BASES = ["msgestion01", "msgestion03"]


# ── ESTADO ACTUAL ─────────────────────────────────────────────────────────────

def mostrar_estado(conn, base):
    cur = conn.cursor()
    print(f"\n  [{base}]")

    # compras2
    cur.execute(f"""
        SELECT sucursal, numero, orden, deposito, cuenta,
               CONVERT(varchar, fecha_comprobante, 103) as fecha, monto_general, usuario
        FROM {base}.dbo.compras2
        WHERE codigo=? AND letra=? AND sucursal=? AND numero=?
    """, CODIGO_REMITO, LETRA_REMITO, SUCURSAL, NUMERO_REMITO)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"    compras2: suc={r[0]} num={r[1]} ord={r[2]} dep={r[3]} "
                  f"cta={r[4]} fecha={r[5]} monto={r[6]:.0f} user={r[7]}")
    else:
        print(f"    compras2: NO ENCONTRADO")

    # compras1
    cur.execute(f"""
        SELECT renglon, articulo, cantidad, deposito
        FROM {base}.dbo.compras1
        WHERE codigo=? AND letra=? AND sucursal=? AND numero=?
        ORDER BY renglon
    """, CODIGO_REMITO, LETRA_REMITO, SUCURSAL, NUMERO_REMITO)
    for r in cur.fetchall():
        marca = " ← INCORRECTO" if r[1] == ART_INCORRECTO else ""
        print(f"    compras1:  ren={r[0]} art={r[1]} cant={r[2]} dep={r[3]}{marca}")

    # movi_stock
    cur.execute(f"""
        SELECT deposito, articulo, operacion, cantidad
        FROM {base}.dbo.movi_stock
        WHERE codigo_comprobante=? AND letra_comprobante=? AND numero_comprobante=?
        ORDER BY articulo
    """, CODIGO_REMITO, LETRA_REMITO, NUMERO_REMITO)
    for r in cur.fetchall():
        marca = " ← INCORRECTO" if r[1] == ART_INCORRECTO else ""
        print(f"    movi_stk:  dep={r[0]} art={r[1]} op={r[2]} cant={r[3]}{marca}")

    # stock
    cur.execute(f"""
        SELECT deposito, articulo, stock_actual
        FROM {base}.dbo.stock
        WHERE deposito=? AND articulo IN (?,?)
        ORDER BY articulo
    """, DEPOSITO, ART_INCORRECTO, ART_CORRECTO)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            label = "SEATTLE(malo)" if r[1]==ART_INCORRECTO else "TEXAS(ok)"
            print(f"    stock:     dep={r[0]} art={r[1]}({label}) actual={r[2]}")
    else:
        print(f"    stock:     SIN FILAS para arts {ART_INCORRECTO}/{ART_CORRECTO} en dep {DEPOSITO}")


# ── FIX ───────────────────────────────────────────────────────────────────────

def fix_base(base, dry_run=True):
    """Aplica el fix en una base específica."""
    print(f"\n  --- {base} ---")
    conn = get_conn(base)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. compras1: art + cantidad
        cur.execute(f"""
            UPDATE {base}.dbo.compras1
               SET articulo           = ?,
                   cantidad           = ?,
                   cantidad_entregada = ?,
                   cantidad_original  = ?,
                   unidades           = ?
             WHERE codigo   = ? AND letra    = ?
               AND sucursal = ? AND numero   = ?
               AND articulo = ?
        """, ART_CORRECTO, CANT_CORRECTA, CANT_CORRECTA,
             CANT_CORRECTA, CANT_CORRECTA,
             CODIGO_REMITO, LETRA_REMITO, SUCURSAL, NUMERO_REMITO, ART_INCORRECTO)
        n1 = cur.rowcount
        print(f"    [1] compras1 UPDATE: {n1} fila(s) — "
              f"art {ART_INCORRECTO}→{ART_CORRECTO}, cant {CANT_ORIGINAL}→{CANT_CORRECTA}")
        if n1 == 0:
            print(f"    [1] ADVERTENCIA: no se encontro renglon con art={ART_INCORRECTO} "
                  f"(ya corregido o no existe en esta base)")

        # 2. movi_stock: art + cantidad
        cur.execute(f"""
            UPDATE {base}.dbo.movi_stock
               SET articulo = ?,
                   cantidad = ?,
                   unidades = ?
             WHERE codigo_comprobante = ? AND letra_comprobante = ?
               AND numero_comprobante = ? AND articulo = ?
        """, ART_CORRECTO, CANT_CORRECTA, CANT_CORRECTA,
             CODIGO_REMITO, LETRA_REMITO, NUMERO_REMITO, ART_INCORRECTO)
        n2 = cur.rowcount
        print(f"    [2] movi_stock UPDATE: {n2} fila(s) — "
              f"art {ART_INCORRECTO}→{ART_CORRECTO}, cant {CANT_ORIGINAL}→{CANT_CORRECTA}")

        # 3. stock art incorrecto (SEATTLE) → 0
        cur.execute(f"""
            SELECT stock_actual FROM {base}.dbo.stock
            WHERE deposito=? AND articulo=? AND RTRIM(ISNULL(serie,''))=''
        """, DEPOSITO, ART_INCORRECTO)
        row = cur.fetchone()
        if row:
            print(f"    [3] stock dep={DEPOSITO} art={ART_INCORRECTO} (SEATTLE): "
                  f"{row[0]} → 0")
            cur.execute(f"""
                UPDATE {base}.dbo.stock
                   SET stock_actual = 0
                 WHERE deposito=? AND articulo=? AND RTRIM(ISNULL(serie,''))=''
            """, DEPOSITO, ART_INCORRECTO)
        else:
            print(f"    [3] stock dep={DEPOSITO} art={ART_INCORRECTO}: sin fila, OK")

        # 4. stock art correcto (TEXAS) → 2
        cur.execute(f"""
            SELECT stock_actual FROM {base}.dbo.stock
            WHERE deposito=? AND articulo=? AND RTRIM(ISNULL(serie,''))=''
        """, DEPOSITO, ART_CORRECTO)
        row = cur.fetchone()
        if row:
            print(f"    [4] stock dep={DEPOSITO} art={ART_CORRECTO} (TEXAS): "
                  f"{row[0]} → {CANT_CORRECTA} (UPDATE)")
            cur.execute(f"""
                UPDATE {base}.dbo.stock
                   SET stock_actual = ?
                 WHERE deposito=? AND articulo=? AND RTRIM(ISNULL(serie,''))=''
            """, CANT_CORRECTA, DEPOSITO, ART_CORRECTO)
        else:
            print(f"    [4] stock dep={DEPOSITO} art={ART_CORRECTO} (TEXAS): "
                  f"INSERT con stock_actual={CANT_CORRECTA}")
            cur.execute(f"""
                INSERT INTO {base}.dbo.stock (deposito, articulo, serie, stock_actual)
                VALUES (?, ?, ' ', ?)
            """, DEPOSITO, ART_CORRECTO, CANT_CORRECTA)

        if dry_run:
            conn.rollback()
            print(f"    [DRY RUN] rollback aplicado — nada escrito")
        else:
            conn.commit()
            print(f"    OK — commit confirmado")

    except Exception as e:
        conn.rollback()
        print(f"    ERROR — rollback: {e}")
        raise
    finally:
        conn.close()


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    dry_run = "--ejecutar" not in sys.argv

    print("\n" + "="*70)
    if dry_run:
        print("  DRY-RUN — mostrar cambios sin escribir nada")
        print("  Para ejecutar: py -3 fix_remito_402041.py --ejecutar")
    else:
        print("  EJECUCION REAL — se escribira en produccion (msgestion01 y msgestion03)")
    print("="*70)

    # Estado actual
    print("\n--- ESTADO ACTUAL ---")
    for base in BASES:
        try:
            conn = get_conn(base)
            mostrar_estado(conn, base)
            conn.close()
        except Exception as e:
            print(f"  ERROR leyendo {base}: {e}")

    if not dry_run:
        confirmacion = input("\n  ¿Aplicar correcciones en AMBAS bases? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("  Cancelado.")
            sys.exit(0)

    print("\n--- APLICANDO FIX ---")
    for base in BASES:
        try:
            fix_base(base, dry_run=dry_run)
        except Exception as e:
            print(f"\n  FALLO en {base}: {e}")
            print("  Abortando — revisar estado manualmente.")
            sys.exit(1)

    if not dry_run:
        print("\n--- ESTADO POST-FIX ---")
        for base in BASES:
            try:
                conn = get_conn(base)
                mostrar_estado(conn, base)
                conn.close()
            except Exception as e:
                print(f"  ERROR post-fix {base}: {e}")

    print("\nListo.")
