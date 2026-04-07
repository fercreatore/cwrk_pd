#!/usr/bin/env python3
"""
eliminar_remito_amphora.py — Elimina el remito Amphora cargado sin mercaderia
=============================================================================
Remito: codigo=7, letra='R', sucursal=1, numero=99855223
Base: MSGESTION03
Cuenta: 44 (AMPHORA)
Fecha: 17/03/2026
Detalle: 9 renglones, 14 unidades (JULIA, ANGELA, CHARLOTE, JENIFER, KIRKLI)

El pedido #1134073 NO se toca — queda vigente para cuando llegue.

EJECUTAR EN EL 111:
  py -3 eliminar_remito_amphora.py --dry-run     <- muestra que va a borrar
  py -3 eliminar_remito_amphora.py --ejecutar    <- borra en produccion
"""

import sys
import pyodbc
import socket

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

# -- DATOS DEL REMITO --------------------------------------------------
BASE = "MSGESTION03"
CODIGO = 7
LETRA = "R"
SUCURSAL = 1
NUMERO = 99855223


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    print(f"\n{'='*60}")
    print(f"ELIMINAR REMITO AMPHORA")
    print(f"{'='*60}")
    print(f"  Remito:   {CODIGO}-{LETRA}-{SUCURSAL}-{NUMERO}")
    print(f"  Base:     {BASE}")
    print(f"  Servidor: {SERVIDOR}")
    print(f"  Modo:     {'DRY-RUN' if dry_run else 'PRODUCCION'}")
    print(f"{'='*60}")

    with pyodbc.connect(get_conn(BASE), timeout=10) as conn:
        cursor = conn.cursor()

        # 1. Mostrar cabecera
        print(f"\n  CABECERA (compras2):")
        cursor.execute(
            f"SELECT cuenta, denominacion, fecha_comprobante, estado "
            f"FROM {BASE}.dbo.compras2 "
            f"WHERE codigo = ? AND letra = ? AND sucursal = ? AND numero = ?",
            CODIGO, LETRA, SUCURSAL, NUMERO
        )
        row = cursor.fetchone()
        if not row:
            print(f"    NO ENCONTRADO — ya fue eliminado o no existe")
            return
        print(f"    Cuenta: {row[0]}, Denom: {row[1]}, Fecha: {row[2]}, Estado: {row[3]}")

        # 2. Mostrar detalle
        print(f"\n  DETALLE (compras1):")
        cursor.execute(
            f"SELECT c1.renglon, c1.articulo, a.descripcion_1, c1.cantidad, c1.precio "
            f"FROM {BASE}.dbo.compras1 c1 "
            f"JOIN msgestion01art.dbo.articulo a ON a.codigo = c1.articulo "
            f"WHERE c1.codigo = ? AND c1.letra = ? AND c1.sucursal = ? AND c1.numero = ? "
            f"ORDER BY c1.renglon",
            CODIGO, LETRA, SUCURSAL, NUMERO
        )
        renglones = cursor.fetchall()
        total_uds = 0
        for r in renglones:
            desc = (r[2] or '')[:45]
            print(f"    [{r[0]:2d}] Art {r[1]}: {desc:45s} x{r[3]} @ ${r[4]:,.0f}")
            total_uds += r[3]
        print(f"    --- {len(renglones)} renglones, {total_uds} unidades")

        # 3. Verificar comprasr
        cursor.execute(
            f"SELECT COUNT(*) FROM {BASE}.dbo.comprasr "
            f"WHERE codigo = ? AND letra = ? AND sucursal = ? AND numero = ?",
            CODIGO, LETRA, SUCURSAL, NUMERO
        )
        comprasr_count = cursor.fetchone()[0]
        print(f"\n  VINCULACION (comprasr): {comprasr_count} registros")

        if dry_run:
            print(f"\n  [DRY RUN] No se borro nada.")
            print(f"  Para ejecutar: py -3 eliminar_remito_amphora.py --ejecutar")
            return

        # 4. EJECUTAR BORRADO
        confirmacion = input(f"\n  Borrar remito {NUMERO} ({total_uds} uds) de {BASE}? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("  Cancelado.")
            sys.exit(0)

        conn.autocommit = False

        # Borrar comprasr si existe
        if comprasr_count > 0:
            cursor.execute(
                f"DELETE FROM {BASE}.dbo.comprasr "
                f"WHERE codigo = ? AND letra = ? AND sucursal = ? AND numero = ?",
                CODIGO, LETRA, SUCURSAL, NUMERO
            )
            print(f"    comprasr: {cursor.rowcount} registros eliminados")

        # Borrar detalle
        cursor.execute(
            f"DELETE FROM {BASE}.dbo.compras1 "
            f"WHERE codigo = ? AND letra = ? AND sucursal = ? AND numero = ?",
            CODIGO, LETRA, SUCURSAL, NUMERO
        )
        print(f"    compras1: {cursor.rowcount} renglones eliminados")

        # Borrar cabecera
        cursor.execute(
            f"DELETE FROM {BASE}.dbo.compras2 "
            f"WHERE codigo = ? AND letra = ? AND sucursal = ? AND numero = ?",
            CODIGO, LETRA, SUCURSAL, NUMERO
        )
        print(f"    compras2: {cursor.rowcount} cabecera eliminada")

        conn.commit()

        print(f"\n{'='*60}")
        print(f"  REMITO ELIMINADO OK")
        print(f"  Pedido #1134073 sigue vigente (no se toco)")
        print(f"{'='*60}")

        # Verificar
        cursor.execute(
            f"SELECT COUNT(*) FROM {BASE}.dbo.compras2 "
            f"WHERE codigo = ? AND letra = ? AND sucursal = ? AND numero = ?",
            CODIGO, LETRA, SUCURSAL, NUMERO
        )
        check = cursor.fetchone()[0]
        print(f"\n  Verificacion: compras2 count = {check} (debe ser 0)")


if __name__ == "__main__":
    main()
