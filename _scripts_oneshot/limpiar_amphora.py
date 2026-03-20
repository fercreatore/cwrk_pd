#!/usr/bin/env python3
"""
limpiar_amphora.py — Borra TODO lo malo de Amphora para recargar limpio
=======================================================================
1. Borra pedidos AMPHORA/COWORK (pedico1 + pedico2)
2. Borra 10 articulos malos 361300-361309 (primer intento fallido)
3. Borra 20 articulos malos 361392-361411 (segundo intento fallido)
4. Da de baja articulo 188983 (KIRKLI viejo, barcode duplicado)

Todos con 0 ventas, 0 compras, 0 stock — verificado.

EJECUTAR EN EL 111:
  py -3 limpiar_amphora.py --dry-run
  py -3 limpiar_amphora.py --ejecutar
"""

import sys
import pyodbc
import socket

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

# Articulos a borrar (dos tandas de intentos fallidos)
ARTS_BORRAR = list(range(361300, 361310)) + list(range(361392, 361412))
# Articulo viejo a dar de baja (barcode duplicado con 361246)
ART_BAJA = 188983


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    print(f"\n{'='*60}")
    print(f"LIMPIAR AMPHORA — Borrar todo lo malo")
    print(f"{'='*60}")
    print(f"  Servidor: {SERVIDOR}")
    print(f"  Modo:     {'DRY-RUN' if dry_run else 'PRODUCCION'}")
    print(f"  Arts borrar: {len(ARTS_BORRAR)}")
    print(f"  Art baja:    {ART_BAJA}")
    print(f"{'='*60}")

    conn = pyodbc.connect(get_conn("MSGESTION01"), timeout=10)
    cursor = conn.cursor()

    # 1. Pedidos AMPHORA/COWORK
    cursor.execute("""
        SELECT numero FROM MSGESTION01.dbo.pedico2
        WHERE codigo = 8 AND denominacion = 'AMPHORA' AND usuario = 'COWORK'
    """)
    pedidos = [r[0] for r in cursor.fetchall()]
    print(f"\n  Pedidos AMPHORA/COWORK: {pedidos}")

    # 2. Verificar articulos
    safe = 0
    unsafe = 0
    for cod in ARTS_BORRAR:
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM msgestionC.dbo.ventas1 WHERE articulo = ?) as v,
                (SELECT COUNT(*) FROM msgestionC.dbo.compras1 WHERE articulo = ?) as c,
                (SELECT ISNULL(SUM(stock_actual),0) FROM msgestionC.dbo.stock WHERE articulo = ?) as s
        """, cod, cod, cod)
        r = cursor.fetchone()
        if r and (r[0] > 0 or r[1] > 0 or r[2] > 0):
            print(f"    PELIGRO [{cod}]: v={r[0]} c={r[1]} s={r[2]}")
            unsafe += 1
        else:
            safe += 1
    print(f"  Articulos: {safe} safe, {unsafe} con movimientos")

    if unsafe > 0:
        print(f"\n  HAY ARTICULOS CON MOVIMIENTOS. No se puede borrar automaticamente.")
        sys.exit(1)

    if dry_run:
        print(f"\n  [DRY RUN] No se borro nada.")
        print(f"  Para ejecutar: py -3 limpiar_amphora.py --ejecutar")
        return

    confirmacion = input(f"\n  Borrar {len(pedidos)} pedidos + {len(ARTS_BORRAR)} arts + baja {ART_BAJA}? (s/N): ").strip().lower()
    if confirmacion != "s":
        print("  Cancelado.")
        sys.exit(0)

    conn.autocommit = False

    # BORRAR PEDIDOS
    for num in pedidos:
        cursor.execute("DELETE FROM MSGESTION01.dbo.pedico1 WHERE numero = ? AND codigo = 8", num)
        d1 = cursor.rowcount
        cursor.execute("DELETE FROM MSGESTION01.dbo.pedico2 WHERE numero = ? AND codigo = 8", num)
        d2 = cursor.rowcount
        print(f"  Pedido #{num}: p1={d1} p2={d2}")

    # BORRAR ARTICULOS
    deleted = 0
    for cod in ARTS_BORRAR:
        cursor.execute("DELETE FROM msgestion01art.dbo.articulo WHERE codigo = ?", cod)
        deleted += cursor.rowcount
    print(f"  Articulos borrados: {deleted}")

    # BAJA KIRKLI VIEJO
    cursor.execute("UPDATE msgestion01art.dbo.articulo SET estado = 'B' WHERE codigo = ?", ART_BAJA)
    print(f"  Art {ART_BAJA}: estado -> B ({cursor.rowcount} row)")

    conn.commit()

    print(f"\n{'='*60}")
    print(f"  LIMPIEZA COMPLETA")
    print(f"  {len(pedidos)} pedidos borrados")
    print(f"  {deleted} articulos borrados")
    print(f"  {ART_BAJA} dado de baja")
    print(f"{'='*60}")
    print(f"\n  Ahora correr: py -3 _scripts_oneshot\\cargar_amphora_paso8.py --ejecutar")

    conn.close()


if __name__ == "__main__":
    main()
