#!/usr/bin/env python3
"""
fix_cavatini_damas_xl_20260403.py
==================================
Fixes dos problemas en artículos DAMAS XL Cavatini OI26:

PROBLEMA 1 — Sinónimos duplicados (solo SEATTLE / NASHVILLE / BOSTON)
  Estado actual verificado en BD (04-abr-2026):
    TEXAS    (361645-361647): sinónimos 96052846XXXX → YA CORRECTOS, NO TOCAR.
    SEATTLE  (361648-361651): sinónimos 960000000XXX → COLISIÓN con NASHVILLE y BOSTON
    NASHVILLE(361652-361654): sinónimos 960000000XXX → COLISIÓN
    BOSTON   (361655-361657): sinónimos 960000000XXX → COLISIÓN

  Raíz: MODELO_COD_OBJ en insertar_cavatini_oi26.py no tenía SEATTLE/NASHVILLE/BOSTON
  → cod_obj = "000000" → los 5 dígitos del modelo son siempre "00000" → colisión.

  Solución: asignar MMMMM único por modelo usando siglas:
    - SEATTLE   → modelo_id = "SE000"  → 960SE000CC TT
    - NASHVILLE → modelo_id = "NA000"  → 960NA000CC TT
    - BOSTON    → modelo_id = "BO000"  → 960BO000CC TT

  NOTA: codigo_sinonimo es VARCHAR(40) → acepta letras. No tocamos codigo_barra
  (es NUMERIC y ya tiene valor válido).

PROBLEMA 2 — descripcion_1 genérica en los 10 artículos SEATTLE/NASHVILLE/BOSTON
  Muestra "SEATTLE SEATTLE NEGRO BOTA" en vez del formato estándar con código.
  Como no tenemos el código real del catálogo Cavatini, mantenemos el formato
  actual (es menor, no afecta funcionamiento).

PROBLEMA 2 — Stock negativo en dep 11 para artículo 361645
  Un comprobante 87-X suc9 num55 ord58 (usuario=RE, TRANI?) movió:
    dep11 artículo 361645 operacion='-' cantidad=1
    dep0  artículo 361645 operacion='+' cantidad=1
  Resultado: dep11 stock_actual=-1, dep0 stock_actual=+1.

  El artículo tiene 1 par en dep0 (incorrecto, transferido desde dep11) y
  -1 en dep11 (donde debería estar). La corrección lógica: revertir el efecto
  del movimiento erróneo en la tabla stock (no en movi_stock, que es historial).
    - dep11: -1 → 0  (no tenía stock antes del movimiento erróneo)
    - dep0:  +1 → 0  (no debería tener stock)

EJECUTAR:
  py -3 fix_cavatini_damas_xl_20260403.py             -- dry-run (default)
  py -3 fix_cavatini_damas_xl_20260403.py --ejecutar  -- escribe en produccion
"""

import sys
import socket
import pyodbc

# ──────────────────────────────────────────────────────────────────────────────
# CONEXION
# ──────────────────────────────────────────────────────────────────────────────

_hostname = socket.gethostname().upper()
if _hostname in ("DELL-SVR", "DELLSVR"):
    _SERVER = "localhost"
    _DRIVER = "SQL Server"
else:
    _SERVER = "192.168.2.111"
    _DRIVER = "SQL Server"

def get_conn(base):
    return (
        f"DRIVER={{{_DRIVER}}};"
        f"SERVER={_SERVER};"
        f"DATABASE={base};"
        f"UID=am;PWD=dl;"
    )

CONN_ART     = get_conn("msgestion01art")
CONN_PEDIDOS = get_conn("msgestion01")

# ──────────────────────────────────────────────────────────────────────────────
# SINÓNIMOS CORRECTOS PARA DAMAS XL
# ──────────────────────────────────────────────────────────────────────────────
# Estado verificado en BD el 04-abr-2026:
#
#  codigo | desc1                          | talle | sinonimo ACTUAL       | accion
#  361645 | TEXAS TEXAS NEGRO BOTA         | 40    | 960528460040          | OK — no tocar
#  361646 | TEXAS TEXAS NEGRO BOTA         | 41    | 960528460041          | OK — no tocar
#  361647 | TEXAS TEXAS NEGRO BOTA         | 42    | 960528460042          | OK — no tocar
#  361648 | SEATTLE SEATTLE NEGRO BOTA     | 40    | 960000000040  COLISION | → 960SE0000040
#  361649 | SEATTLE SEATTLE NEGRO BOTA     | 41    | 960000000041  COLISION | → 960SE0000041
#  361650 | SEATTLE SEATTLE NEGRO BOTA     | 42    | 960000000042  COLISION | → 960SE0000042
#  361651 | SEATTLE SEATTLE NEGRO BOTA     | 43    | 960000000043  COLISION | → 960SE0000043
#  361652 | NASHVILLE NASHVILLE NEGRO BOTA | 40    | 960000000040  COLISION | → 960NA0000040
#  361653 | NASHVILLE NASHVILLE NEGRO BOTA | 41    | 960000000041  COLISION | → 960NA0000041
#  361654 | NASHVILLE NASHVILLE NEGRO BOTA | 42    | 960000000042  COLISION | → 960NA0000042
#  361655 | BOSTON BOSTON NEGRO CASUAL     | 40    | 960000000040  COLISION | → 960BO0000040
#  361656 | BOSTON BOSTON NEGRO CASUAL     | 41    | 960000000041  COLISION | → 960BO0000041
#  361657 | BOSTON BOSTON NEGRO CASUAL     | 42    | 960000000042  COLISION | → 960BO0000042

SINONIMOS_NUEVOS = [
    # (codigo_articulo, sinonimo_nuevo)
    # TEXAS (361645-361647): YA TIENEN SINONIMOS CORRECTOS (96052846XXXX) → NO INCLUIDOS
    #
    # SEATTLE → SE000 (CC=00 NEGRO, TT=talle)
    (361648, "960SE0000040"),
    (361649, "960SE0000041"),
    (361650, "960SE0000042"),
    (361651, "960SE0000043"),
    # NASHVILLE → NA000
    (361652, "960NA0000040"),
    (361653, "960NA0000041"),
    (361654, "960NA0000042"),
    # BOSTON → BO000
    (361655, "960BO0000040"),
    (361656, "960BO0000041"),
    (361657, "960BO0000042"),
]

# ──────────────────────────────────────────────────────────────────────────────
# FIX 1: ACTUALIZAR SINÓNIMOS
# ──────────────────────────────────────────────────────────────────────────────

def fix_sinonimos(dry_run=True):
    print("\n" + "="*60)
    print("  FIX 1: ACTUALIZAR SINONIMOS SEATTLE/NASHVILLE/BOSTON")
    print("  (TEXAS ya tiene sinonimos correctos 96052846XXXX, no se toca)")
    print("="*60)

    conn = pyodbc.connect(CONN_ART, timeout=15)
    cur = conn.cursor()

    # Verificar estado actual
    codigos = [r[0] for r in SINONIMOS_NUEVOS]
    placeholders = ",".join("?" * len(codigos))
    cur.execute(
        f"SELECT codigo, RTRIM(codigo_sinonimo), RTRIM(descripcion_1), RTRIM(descripcion_5) "
        f"FROM articulo WHERE codigo IN ({placeholders}) ORDER BY codigo",
        codigos
    )
    rows = cur.fetchall()
    print("\n  Estado ACTUAL en BD:")
    print(f"  {'codigo':>7}  {'sinonimo_actual':>15}  {'desc1':<35}  talle")
    print(f"  {'-'*7}  {'-'*15}  {'-'*35}  -----")
    for r in rows:
        print(f"  {r[0]:>7}  {str(r[1]):>15}  {str(r[2]):<35}  {r[3]}")

    print(f"\n  Cambios a aplicar:")
    for codigo, sin_nuevo in SINONIMOS_NUEVOS:
        # Buscar el actual para mostrar
        actual = next((str(r[1]) for r in rows if r[0] == codigo), "???")
        print(f"  art {codigo:>6}: {actual:>15}  →  {sin_nuevo}")

    if dry_run:
        print("\n  [DRY RUN] No se escribio nada.")
        conn.close()
        return

    print("\n  Ejecutando UPDATEs...")
    conn.autocommit = False
    try:
        for codigo, sin_nuevo in SINONIMOS_NUEVOS:
            cur.execute(
                "UPDATE msgestion01art.dbo.articulo "
                "SET codigo_sinonimo = ? "
                "WHERE codigo = ?",
                sin_nuevo, codigo
            )
            if cur.rowcount != 1:
                raise RuntimeError(f"UPDATE afecto {cur.rowcount} filas para codigo={codigo}")
            print(f"    OK  art {codigo} → sinonimo='{sin_nuevo}'")
        conn.commit()
        print(f"\n  OK: {len(SINONIMOS_NUEVOS)} sinonimos actualizados.")
    except Exception as e:
        conn.rollback()
        print(f"\n  ERROR: {e}")
        raise
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# FIX 2: CORREGIR STOCK ARTÍCULO 361645
# ──────────────────────────────────────────────────────────────────────────────
# Estado actual (verificado):
#   dep 0,  serie='': stock_actual =  1  (stock fantasma creado por TRANI)
#   dep 11, serie='': stock_actual = -1  (creado por TRANI erróneo)
#
# El comprobante 87-X suc9 num55 ord58 (usuario=RE) transfirió 1 par de dep11
# a dep0. Esto es un error: el artículo llegó vía remito en dep11 (correcto),
# y el TRANI lo movió incorrectamente a dep0.
#
# Corrección en tabla stock (el historial movi_stock queda intacto):
#   dep 0:  stock_actual = 0  (eliminar stock fantasma)
#   dep 11: stock_actual = 0  (el par fue vendido/transferido, no hay stock real)
#
# IMPORTANTE: NO intentamos "devolver" el par a dep11 porque el comprobante de
# transferencia ya existe en el sistema. La corrección lleva ambos a 0 para
# reflejar que el artículo efectivamente no está disponible.
# Si el par fisico existe en dep11, el usuario debe hacer un ajuste de stock
# manualmente en el ERP (ajuste de inventario).

ARTICULO_AFECTADO = 361645
BASE_STOCK = "MSGESTION01"  # msgestion01 (CLZ tiene los movimientos)

def fix_stock(dry_run=True):
    print("\n" + "="*60)
    print("  FIX 2: CORREGIR STOCK ARTÍCULO 361645 (TEXAS T40)")
    print("="*60)

    conn = pyodbc.connect(CONN_PEDIDOS, timeout=15)
    cur = conn.cursor()

    # Mostrar estado actual
    cur.execute(
        f"SELECT deposito, RTRIM(ISNULL(serie,'')) as serie, stock_actual "
        f"FROM {BASE_STOCK}.dbo.stock "
        f"WHERE articulo = ? ORDER BY deposito",
        ARTICULO_AFECTADO
    )
    rows = cur.fetchall()
    print(f"\n  Stock actual de articulo {ARTICULO_AFECTADO}:")
    for r in rows:
        print(f"    dep={r[0]}  serie='{r[1]}'  stock_actual={r[2]}")

    print(f"\n  Cambios a aplicar:")
    print(f"    dep 0,  serie='' : stock_actual = 0  (quitar stock fantasma)")
    print(f"    dep 11, serie='' : stock_actual = 0  (corregir negativo)")

    if dry_run:
        print("\n  [DRY RUN] No se escribio nada.")
        conn.close()
        return

    conn.autocommit = False
    try:
        # Corregir dep 0
        cur.execute(
            f"UPDATE {BASE_STOCK}.dbo.stock "
            f"SET stock_actual = 0 "
            f"WHERE articulo = ? AND deposito = 0 AND RTRIM(ISNULL(serie,'')) = ''",
            ARTICULO_AFECTADO
        )
        filas_dep0 = cur.rowcount
        print(f"    dep 0:  {filas_dep0} fila(s) actualizada(s) → stock_actual=0")

        # Corregir dep 11
        cur.execute(
            f"UPDATE {BASE_STOCK}.dbo.stock "
            f"SET stock_actual = 0 "
            f"WHERE articulo = ? AND deposito = 11 AND RTRIM(ISNULL(serie,'')) = ''",
            ARTICULO_AFECTADO
        )
        filas_dep11 = cur.rowcount
        print(f"    dep 11: {filas_dep11} fila(s) actualizada(s) → stock_actual=0")

        conn.commit()
        print(f"\n  OK: stock de articulo {ARTICULO_AFECTADO} corregido.")
        print(f"  AVISO: si el par fisico existe en dep11, hacer ajuste de inventario en ERP.")
    except Exception as e:
        conn.rollback()
        print(f"\n  ERROR: {e}")
        raise
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# VERIFICACION FINAL
# ──────────────────────────────────────────────────────────────────────────────

def verificar():
    print("\n" + "="*60)
    print("  VERIFICACION FINAL")
    print("="*60)

    # Sinónimos
    conn_art = pyodbc.connect(CONN_ART, timeout=15)
    cur_art = conn_art.cursor()
    codigos = [r[0] for r in SINONIMOS_NUEVOS]
    placeholders = ",".join("?" * len(codigos))
    cur_art.execute(
        f"SELECT codigo, RTRIM(codigo_sinonimo), RTRIM(descripcion_1), RTRIM(descripcion_5) "
        f"FROM articulo WHERE codigo IN ({placeholders}) ORDER BY codigo",
        codigos
    )
    rows = cur_art.fetchall()
    conn_art.close()

    print("\n  Sinonimos actuales para Damas XL:")
    print(f"  {'codigo':>7}  {'sinonimo':>15}  {'desc1':<35}  talle")
    for r in rows:
        print(f"  {r[0]:>7}  {str(r[1]):>15}  {str(r[2]):<35}  {r[3]}")

    # Unicidad
    sinon_list = [str(r[1]) for r in rows]
    duplicados = [s for s in set(sinon_list) if sinon_list.count(s) > 1]
    if duplicados:
        print(f"\n  ALERTA: Siguen habiendo sinonimos duplicados: {duplicados}")
    else:
        print(f"\n  OK: Todos los sinonimos son unicos ({len(sinon_list)} articulos).")

    # Stock
    conn_ped = pyodbc.connect(CONN_PEDIDOS, timeout=15)
    cur_ped = conn_ped.cursor()
    cur_ped.execute(
        f"SELECT deposito, RTRIM(ISNULL(serie,'')) as serie, stock_actual "
        f"FROM {BASE_STOCK}.dbo.stock "
        f"WHERE articulo = ? ORDER BY deposito",
        ARTICULO_AFECTADO
    )
    stock_rows = cur_ped.fetchall()
    conn_ped.close()

    print(f"\n  Stock de articulo {ARTICULO_AFECTADO} post-fix:")
    for r in stock_rows:
        estado = "OK" if r[2] >= 0 else "ALERTA NEGATIVO"
        print(f"    dep={r[0]}  serie='{r[1]}'  stock_actual={r[2]}  [{estado}]")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    dry_run = "--ejecutar" not in sys.argv

    if dry_run:
        print("\n" + "!"*60)
        print("  MODO DRY RUN — no se escribe nada en la base")
        print("!"*60)
    else:
        print("\n" + "!"*60)
        print("  MODO EJECUCION REAL — se escribira en produccion")
        print("!"*60)
        confirmacion = input("  Confirmar? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("  Cancelado.")
            sys.exit(0)

    fix_sinonimos(dry_run=dry_run)
    fix_stock(dry_run=dry_run)

    if not dry_run:
        verificar()

    print("\nListo.")
