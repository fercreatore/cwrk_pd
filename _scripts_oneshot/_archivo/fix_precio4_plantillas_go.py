#!/usr/bin/env python3
"""
fix_precio4_plantillas_go.py
Actualiza precio_4 (mayorista) de plantillas Go by CLZ al 100% sobre costo.
Antes: utilidad_4 = 45% → precio_4 = costo * 1.45
Ahora: utilidad_4 = 100% → precio_4 = costo * 2

27 artículos, marca 17, subrubro 27.

EJECUTAR EN 111:
    py -3 fix_precio4_plantillas_go.py --dry-run
    py -3 fix_precio4_plantillas_go.py --ejecutar
"""
import sys
import pyodbc

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
)

NUEVA_UTILIDAD_4 = 100  # 100% sobre costo


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('--dry-run', '--ejecutar'):
        print("Uso: py -3 fix_precio4_plantillas_go.py --dry-run|--ejecutar")
        sys.exit(1)

    dry_run = sys.argv[1] == '--dry-run'
    modo = "DRY-RUN" if dry_run else "EJECUTAR"
    print(f"\n{'='*65}")
    print(f"  PLANTILLAS GO BY CLZ: P4 al {NUEVA_UTILIDAD_4}% — {modo}")
    print(f"{'='*65}\n")

    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    # Mostrar antes
    cursor.execute("""
        SELECT codigo, descripcion_1, precio_costo, precio_4, utilidad_4
        FROM msgestion01art.dbo.articulo
        WHERE marca = 17 AND subrubro = 27 AND estado = 'V'
        ORDER BY descripcion_1, codigo
    """)
    rows = cursor.fetchall()
    print(f"  {len(rows)} artículos encontrados\n")
    print(f"  {'Modelo':<45s} {'Costo':>10s} {'P4 actual':>10s} {'P4 nuevo':>10s}")
    print(f"  {'-'*45} {'-'*10} {'-'*10} {'-'*10}")
    for r in rows:
        costo = float(r.precio_costo) if r.precio_costo else 0
        p4_act = float(r.precio_4) if r.precio_4 else 0
        nuevo_p4 = round(costo * (1 + NUEVA_UTILIDAD_4 / 100), 2)
        print(f"  {r.descripcion_1[:45]:<45s} ${costo:>8,.0f} ${p4_act:>8,.0f} ${nuevo_p4:>8,.0f}")

    if dry_run:
        print(f"\n  DRY-RUN — no se modificó nada.")
    else:
        cursor.execute("""
            UPDATE msgestion01art.dbo.articulo
            SET utilidad_4 = ?,
                precio_4 = ROUND(precio_costo * (1 + ? / 100.0), 2)
            WHERE marca = 17 AND subrubro = 27 AND estado = 'V'
        """, NUEVA_UTILIDAD_4, NUEVA_UTILIDAD_4)
        afectados = cursor.rowcount
        conn.commit()
        print(f"\n  ✓ {afectados} artículos actualizados: utilidad_4={NUEVA_UTILIDAD_4}%, precio_4=costo×2")

    conn.close()
    print(f"\n{'='*65}\n")


if __name__ == '__main__':
    main()
