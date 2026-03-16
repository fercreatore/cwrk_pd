#!/usr/bin/env python3
"""
aplicar_transferencias_piccadilly.py — Hacer efectivas las transferencias dep 11→0
===================================================================================
Las transferencias están registradas en movistoc1/movistoc2 pero el stock no se
movió correctamente por el problema de series.

Después de correr fix_series_stock.py (que consolidó todo a serie=' '),
este script aplica los movimientos de stock pendientes.

LÓGICA:
- Lee las transferencias de movistoc1/2 en ambas bases (msg01 y msg03)
- Calcula cuánto DEBERÍA haber en dep 0 por artículo (total transferido)
- Compara con el stock ACTUAL en dep 0 (vista combinada msgestionC)
- Aplica la diferencia en msgestion03 (donde está el stock real positivo en dep 11)
- Para artículos con stock en dep 0 parcial de msg01, solo ajusta lo faltante en msg03

EJECUTAR EN EL 111:
  py -3 aplicar_transferencias_piccadilly.py                ← dry-run
  py -3 aplicar_transferencias_piccadilly.py --ejecutar     ← escribe en producción
"""

import sys
import pyodbc

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
    "Trusted_Connection=no;"
)

DRY_RUN = "--ejecutar" not in sys.argv
SERIE = " "  # serie blanca (ya consolidada por fix_series)


def main():
    if DRY_RUN:
        print("=" * 60)
        print("  MODO DRY-RUN — No se escribe nada en la BD")
        print("  Agregar --ejecutar para escribir de verdad")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  ⚠️  MODO EJECUCIÓN — SE VA A ESCRIBIR EN LA BD")
        print("=" * 60)
        resp = input("  Continuar? (si/no): ")
        if resp.lower() not in ("si", "sí", "s", "yes", "y"):
            print("  Cancelado.")
            return

    conn = pyodbc.connect(CONN_STR, timeout=30)
    cursor = conn.cursor()

    # =========================================================================
    # 1. Leer transferencias de msgestion01 (transfers #25475-25490)
    # =========================================================================
    print("\n--- Leyendo transferencias msgestion01 ---")
    cursor.execute("""
        SELECT m1.articulo, SUM(m1.cantidad) as total
        FROM msgestion01.dbo.movistoc2 m2
        JOIN msgestion01.dbo.movistoc1 m1
          ON m1.numero = m2.numero
         AND m1.codigo = m2.codigo
         AND m1.letra = m2.letra
         AND m1.sucursal = m2.sucursal
        WHERE m2.numero BETWEEN 25475 AND 25490
          AND m1.deposito_emisor = 11
          AND m1.deposito_receptor = 0
          AND m1.articulo >= 360000
        GROUP BY m1.articulo
    """)
    transf_msg01 = {row[0]: row[1] for row in cursor.fetchall()}
    print(f"  Artículos en transferencias msg01: {len(transf_msg01)}")
    print(f"  Total pares msg01: {sum(transf_msg01.values())}")

    # =========================================================================
    # 2. Leer transferencia de msgestion03 (#377)
    # =========================================================================
    print("\n--- Leyendo transferencia msgestion03 #377 ---")
    cursor.execute("""
        SELECT m1.articulo, SUM(m1.cantidad) as total
        FROM msgestion03.dbo.movistoc2 m2
        JOIN msgestion03.dbo.movistoc1 m1
          ON m1.numero = m2.numero
         AND m1.codigo = m2.codigo
         AND m1.letra = m2.letra
         AND m1.sucursal = m2.sucursal
        WHERE m2.numero = 377
          AND m1.deposito_emisor = 11
          AND m1.deposito_receptor = 0
          AND m1.articulo >= 360000
        GROUP BY m1.articulo
    """)
    transf_msg03 = {row[0]: row[1] for row in cursor.fetchall()}
    print(f"  Artículos en transferencia msg03: {len(transf_msg03)}")
    print(f"  Total pares msg03: {sum(transf_msg03.values())}")

    # =========================================================================
    # 3. Leer stock actual COMBINADO (msgestionC) para estos artículos
    # =========================================================================
    all_arts = sorted(set(list(transf_msg01.keys()) + list(transf_msg03.keys())))
    print(f"\n--- Total artículos únicos en transferencias: {len(all_arts)} ---")

    # Stock combinado por (articulo, deposito)
    placeholders = ",".join(["?"] * len(all_arts))
    cursor.execute(f"""
        SELECT articulo, deposito, stock_actual
        FROM msgestionC.dbo.stock
        WHERE articulo IN ({placeholders})
          AND serie = ' '
          AND deposito IN (0, 11)
    """, all_arts)

    stock_combinado = {}  # (art, dep) -> stock
    for art, dep, stk in cursor.fetchall():
        stock_combinado[(art, dep)] = stk

    # =========================================================================
    # 4. Leer stock msgestion03 dep 11 (donde vamos a aplicar ajustes)
    # =========================================================================
    cursor.execute(f"""
        SELECT articulo, stock_actual
        FROM msgestion03.dbo.stock
        WHERE articulo IN ({placeholders})
          AND serie = ' '
          AND deposito = 11
    """, all_arts)

    stock_msg03_dep11 = {row[0]: row[1] for row in cursor.fetchall()}

    # Stock msgestion03 dep 0
    cursor.execute(f"""
        SELECT articulo, stock_actual
        FROM msgestion03.dbo.stock
        WHERE articulo IN ({placeholders})
          AND serie = ' '
          AND deposito = 0
    """, all_arts)

    stock_msg03_dep0 = {row[0]: row[1] for row in cursor.fetchall()}

    # =========================================================================
    # 5. Calcular ajustes necesarios
    # =========================================================================
    print("\n--- Calculando ajustes ---")
    print("{:>8} {:>8} {:>8} {:>8} {:>8} {:>8}  {}".format(
        "ART", "DEP11_C", "DEP0_C", "TRANSF", "M03_D11", "MOVER", "ACCION"))
    print("-" * 75)

    ajustes = []  # (articulo, cantidad_a_mover)
    total_mover = 0
    ya_ok = 0

    for art in all_arts:
        dep11_comb = stock_combinado.get((art, 11), 0)
        dep0_comb = stock_combinado.get((art, 0), 0)

        # Total que debería estar en dep 0 según transferencias
        transf_total = transf_msg01.get(art, 0) + transf_msg03.get(art, 0)

        # Cuánto falta en dep 0
        falta = transf_total - dep0_comb

        # Stock disponible en msg03 dep 11 para mover
        msg03_d11 = stock_msg03_dep11.get(art, 0)

        if falta <= 0:
            ya_ok += 1
            continue

        # Solo mover lo que hay disponible en msg03 dep 11
        mover = min(falta, msg03_d11)

        if mover <= 0:
            print("{:>8} {:>8} {:>8} {:>8} {:>8} {:>8}  {}".format(
                art, dep11_comb, dep0_comb, transf_total, msg03_d11, 0,
                "SIN STOCK EN MSG03"))
            continue

        accion = "INSERT dep0" if art not in stock_msg03_dep0 else "UPDATE dep0"
        print("{:>8} {:>8} {:>8} {:>8} {:>8} {:>8}  {}".format(
            art, dep11_comb, dep0_comb, transf_total, msg03_d11, mover, accion))

        ajustes.append((art, mover, art in stock_msg03_dep0))
        total_mover += mover

    print(f"\n  Artículos ya OK (dep 0 correcto): {ya_ok}")
    print(f"  Artículos a ajustar: {len(ajustes)}")
    print(f"  Total pares a mover dep 11→0 en msg03: {total_mover}")

    if not ajustes:
        print("\n  ✅ Nada que ajustar, todo OK.")
        conn.close()
        return

    # =========================================================================
    # 6. Aplicar ajustes en msgestion03
    # =========================================================================
    if not DRY_RUN:
        print("\n--- Aplicando ajustes en msgestion03 ---")

        for art, cantidad, dep0_existe in ajustes:
            # Restar de dep 11
            cursor.execute("""
                UPDATE msgestion03.dbo.stock
                SET stock_actual = stock_actual - ?
                WHERE articulo = ? AND deposito = 11 AND serie = ' '
            """, [cantidad, art])

            if dep0_existe:
                # Sumar a dep 0 existente
                cursor.execute("""
                    UPDATE msgestion03.dbo.stock
                    SET stock_actual = stock_actual + ?
                    WHERE articulo = ? AND deposito = 0 AND serie = ' '
                """, [cantidad, art])
            else:
                # Crear fila dep 0 copiando estructura de dep 11
                cursor.execute("""
                    INSERT INTO msgestion03.dbo.stock
                        (deposito, articulo, serie, stock_actual, stock_unidades)
                    SELECT 0, articulo, serie, ?, stock_unidades
                    FROM msgestion03.dbo.stock
                    WHERE articulo = ? AND deposito = 11 AND serie = ' '
                """, [cantidad, art])

        conn.commit()
        print(f"  ✅ COMMIT realizado — {len(ajustes)} artículos ajustados, {total_mover} pares movidos")
    else:
        print(f"\n  DRY-RUN: Se moverían {total_mover} pares en {len(ajustes)} artículos")

    # =========================================================================
    # 7. Verificación post-ajuste
    # =========================================================================
    if not DRY_RUN:
        print("\n--- Verificación post-ajuste ---")
        cursor.execute(f"""
            SELECT deposito, COUNT(*) as arts, SUM(stock_actual) as total_stock
            FROM msgestionC.dbo.stock
            WHERE articulo IN ({placeholders})
              AND serie = ' '
              AND deposito IN (0, 11)
            GROUP BY deposito
            ORDER BY deposito
        """, all_arts)

        for dep, arts, total in cursor.fetchall():
            print(f"  Dep {dep}: {arts} artículos, stock total = {total}")

    conn.close()

    print(f"\n{'='*60}")
    print(f"  {'DRY-RUN completado' if DRY_RUN else 'EJECUCIÓN completada'}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
