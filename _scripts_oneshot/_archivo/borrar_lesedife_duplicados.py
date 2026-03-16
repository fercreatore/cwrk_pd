#!/usr/bin/env python3
"""
borrar_lesedife_duplicados.py
Elimina pedidos duplicados #1134068 y #1134069 de Lesedife.
El script se ejecutó 2 veces y generó duplicados.

Pedidos a MANTENER: 1134065, 1134066, 1134067
Pedidos a BORRAR:   1134068, 1134069

Ejecutar en 111: py -3 borrar_lesedife_duplicados.py
"""
import sys
import pyodbc

CONN_STR = "DRIVER={SQL Server};SERVER=192.168.2.111;UID=am;PWD=dl"
DUPLICADOS = [1134068, 1134069]
CODIGO = 8
LETRA = 'X'
SUCURSAL = 1

# Ambas bases comparten pedico1/pedico2, pero hay registros en las dos
BASES = ["MSGESTION03", "MSGESTION01"]

def main():
    dry_run = "--ejecutar" not in sys.argv

    if dry_run:
        print("=" * 60)
        print("  MODO DRY-RUN — No se borra nada")
        print("  Agregar --ejecutar para borrar de verdad")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  ⚠️  MODO EJECUCIÓN — SE VAN A BORRAR REGISTROS")
        print("=" * 60)

    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    for base in BASES:
        print(f"\n--- {base} ---")
        for num in DUPLICADOS:
            # Verificar qué hay
            cursor.execute(
                f"SELECT COUNT(*) FROM {base}.dbo.pedico1 "
                f"WHERE codigo=? AND letra=? AND sucursal=? AND numero=?",
                CODIGO, LETRA, SUCURSAL, num
            )
            renglones = cursor.fetchone()[0]

            cursor.execute(
                f"SELECT COUNT(*) FROM {base}.dbo.pedico2 "
                f"WHERE codigo=? AND letra=? AND sucursal=? AND numero=?",
                CODIGO, LETRA, SUCURSAL, num
            )
            cabecera = cursor.fetchone()[0]

            print(f"  Pedido #{num}: {cabecera} cabecera(s), {renglones} renglón(es)")

            if dry_run:
                print(f"    → [DRY-RUN] Se borrarían {renglones} renglones + {cabecera} cabecera")
            else:
                if renglones > 0:
                    cursor.execute(
                        f"DELETE FROM {base}.dbo.pedico1 "
                        f"WHERE codigo=? AND letra=? AND sucursal=? AND numero=?",
                        CODIGO, LETRA, SUCURSAL, num
                    )
                    print(f"    → Borrados {cursor.rowcount} renglones de pedico1")

                if cabecera > 0:
                    cursor.execute(
                        f"DELETE FROM {base}.dbo.pedico2 "
                        f"WHERE codigo=? AND letra=? AND sucursal=? AND numero=?",
                        CODIGO, LETRA, SUCURSAL, num
                    )
                    print(f"    → Borrada {cursor.rowcount} cabecera de pedico2")

    if not dry_run:
        conn.commit()
        print("\n✅ COMMIT OK — Duplicados eliminados")
        print("\nVerificación — pedidos Lesedife restantes:")
        for base in BASES:
            cursor.execute(
                f"SELECT numero, "
                f"  (SELECT COUNT(*) FROM {base}.dbo.pedico1 d "
                f"   WHERE d.numero=c.numero AND d.codigo=c.codigo "
                f"   AND d.letra=c.letra AND d.sucursal=c.sucursal) as renglones, "
                f"  (SELECT SUM(cantidad) FROM {base}.dbo.pedico1 d "
                f"   WHERE d.numero=c.numero AND d.codigo=c.codigo "
                f"   AND d.letra=c.letra AND d.sucursal=c.sucursal) as pares "
                f"FROM {base}.dbo.pedico2 c "
                f"WHERE codigo=? AND cuenta=42 ORDER BY numero",
                CODIGO
            )
            rows = cursor.fetchall()
            print(f"\n  {base}:")
            for r in rows:
                print(f"    #{r.numero}: {r.renglones} renglones, {r.pares} pares")
    else:
        print("\n→ Ejecutar con --ejecutar para borrar los duplicados")

    conn.close()

if __name__ == "__main__":
    main()
