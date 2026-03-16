#!/usr/bin/env python3
"""
fix_stock_serie_cleanup.py — Limpieza de datos creados por remito WB 1926645
y valijas con stock_unidades roto.

CONTEXTO:
- Remito 1926645 (5/mar/2026) fue creado por nuestro codigo web (WB) en msg03.
  Usó serie='2603' pero msg03 usa serie=' '. Además actualizó stock en AMBAS
  series, duplicando las cantidades.
- Remito 35309 (3/mar/2026, PIRA ejecutable) está BIEN, NO se toca.
- Valijas tuvieron un remito web que se eliminó, pero quedaron filas residuales.

ACCIONES:
1. msg03 stock: restar cantidades duplicadas de serie ' ' y eliminar filas '2603'
2. msg03 compras1/movi_stock del remito 1926645: cambiar serie de '2603' a ' '
3. msg03 movi_stock remito 1926645: fix unidades (de 1 a cantidad real)
4. Valijas msg03: eliminar filas serie '2603' huérfanas, fix stock_unidades
5. msg01 stock serie '2603': fix stock_unidades = stock_actual

Ejecutar en 111 con: py -3 fix_stock_serie_cleanup.py
"""
import pyodbc

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=localhost;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes;"
)

# Remito WB en msg03 — el UNICO que hay que limpiar
REMITO_WB = 1926645

# Artículos del remito WB 1926645 con sus cantidades
# (verificado contra compras1)
ITEMS_REMITO_WB = [
    (196897, 1),   # CAMILA NEGRO
    (205975, 2),   # CAMILA GRIS
    (207777, 1),   # CAMILA NEGRO
    (207784, 2),   # CAMILA AZUL
    (226835, 1),   # PUNTOS NEGRO
    (226836, 2),   # PUNTOS NEGRO
    (248387, 1),   # CAMILA NEGRO/NEGRO
    (248388, 2),   # CAMILA NEGRO/NEGRO
]

# Valijas con filas residuales
VALIJAS = [359226, 359228, 359230]


def run():
    conn = pyodbc.connect(CONN_STR, autocommit=False)
    cur = conn.cursor()

    print("=" * 60)
    print("FIX STOCK SERIE — LIMPIEZA REMITO WB 1926645 + VALIJAS")
    print("=" * 60)

    # ============================================================
    # PARTE 1: msg03 stock — deshacer doble conteo del remito WB
    # ============================================================
    print("\n--- PARTE 1: msgestion03.stock — deshacer doble conteo ---")
    print(f"  Remito WB: {REMITO_WB}")

    for art, cant in ITEMS_REMITO_WB:
        # Verificar estado actual de serie '2603'
        cur.execute("""
            SELECT stock_actual, stock_unidades
            FROM msgestion03.dbo.stock
            WHERE deposito = 11 AND articulo = ? AND serie = '2603'
        """, art)
        row = cur.fetchone()

        if row:
            stk_2603, stku_2603 = row
            print(f"\n  Art {art}: serie '2603' stock={stk_2603}, unidades={stku_2603}")

            # Verificar serie ' '
            cur.execute("""
                SELECT stock_actual, stock_unidades
                FROM msgestion03.dbo.stock
                WHERE deposito = 11 AND articulo = ? AND serie = ' '
            """, art)
            row_sp = cur.fetchone()
            if row_sp:
                stk_sp, stku_sp = row_sp
                print(f"         serie ' '  stock={stk_sp}, unidades={stku_sp}")

                # Restar lo que WB sumó de más en serie ' '
                # WB sumó 'cant' en serie ' ' (además de en '2603')
                new_stk = stk_sp - cant
                new_stku = stku_sp - cant
                print(f"    -> Restando {cant} de serie ' ': {stk_sp}->{new_stk}, {stku_sp}->{new_stku}")
                cur.execute("""
                    UPDATE msgestion03.dbo.stock
                    SET stock_actual = stock_actual - ?,
                        stock_unidades = stock_unidades - ?
                    WHERE deposito = 11 AND articulo = ? AND serie = ' '
                """, cant, cant, art)

            # Eliminar fila serie '2603'
            print(f"    -> Eliminando fila serie '2603'")
            cur.execute("""
                DELETE FROM msgestion03.dbo.stock
                WHERE deposito = 11 AND articulo = ? AND serie = '2603'
            """, art)
            print(f"    -> Deleted: {cur.rowcount}")
        else:
            print(f"\n  Art {art}: NO tiene serie '2603' en dep 11 (ya limpio)")

    # ============================================================
    # PARTE 2: msg03 compras1 — cambiar serie de '2603' a ' '
    # ============================================================
    print("\n--- PARTE 2: msgestion03.compras1 — fix serie remito WB ---")
    cur.execute("""
        SELECT articulo, serie, cantidad, unidades
        FROM msgestion03.dbo.compras1
        WHERE codigo = 7 AND numero = ?
        ORDER BY renglon
    """, REMITO_WB)
    rows = cur.fetchall()
    print(f"  Renglones del remito {REMITO_WB}: {len(rows)}")
    for art, serie, cant, unid in rows:
        print(f"    Art {art}: serie='{serie.strip() or '(espacio)'}' cant={cant} unid={unid}")

    cur.execute("""
        UPDATE msgestion03.dbo.compras1
        SET serie = ' '
        WHERE codigo = 7 AND numero = ? AND serie <> ' '
    """, REMITO_WB)
    print(f"  -> Serie actualizada a ' ' en {cur.rowcount} renglones")

    # ============================================================
    # PARTE 3: msg03 movi_stock — fix serie y unidades del remito WB
    # ============================================================
    print("\n--- PARTE 3: msgestion03.movi_stock — fix serie + unidades ---")
    cur.execute("""
        SELECT articulo, serie, cantidad, unidades
        FROM msgestion03.dbo.movi_stock
        WHERE codigo_comprobante = 7 AND numero_comprobante = ? AND usuario = 'WB'
        ORDER BY articulo
    """, REMITO_WB)
    rows = cur.fetchall()
    print(f"  Registros movi_stock WB del remito: {len(rows)}")
    for art, serie, cant, unid in rows:
        print(f"    Art {art}: serie='{serie.strip() or '(espacio)'}' cant={cant} unid={unid}")

    # Fix serie a ' '
    cur.execute("""
        UPDATE msgestion03.dbo.movi_stock
        SET serie = ' '
        WHERE codigo_comprobante = 7 AND numero_comprobante = ?
          AND usuario = 'WB' AND RTRIM(serie) <> ''
    """, REMITO_WB)
    print(f"  -> Serie actualizada a ' ' en {cur.rowcount} registros")

    # Fix unidades = cantidad (el original tenia unidades=1)
    cur.execute("""
        UPDATE msgestion03.dbo.movi_stock
        SET unidades = cantidad
        WHERE codigo_comprobante = 7 AND numero_comprobante = ?
          AND usuario = 'WB' AND unidades <> cantidad
    """, REMITO_WB)
    print(f"  -> Unidades = cantidad en {cur.rowcount} registros")

    # ============================================================
    # PARTE 4: Valijas msg03 — limpiar filas huérfanas
    # ============================================================
    print("\n--- PARTE 4: Valijas msgestion03 — limpiar residuos ---")

    for art in VALIJAS:
        # Eliminar filas serie '2603' (huérfanas, stock=0)
        cur.execute("""
            SELECT deposito, stock_actual, stock_unidades
            FROM msgestion03.dbo.stock
            WHERE articulo = ? AND serie = '2603'
        """, art)
        rows = cur.fetchall()
        for dep, stk, stku in rows:
            print(f"  Art {art} dep={dep}: serie '2603' stock={stk} -> DELETE")
            cur.execute("""
                DELETE FROM msgestion03.dbo.stock
                WHERE deposito = ? AND articulo = ? AND serie = '2603'
            """, dep, art)

        # Fix stock_unidades en serie ' '
        cur.execute("""
            SELECT deposito, stock_actual, stock_unidades
            FROM msgestion03.dbo.stock
            WHERE articulo = ? AND serie = ' ' AND stock_unidades <> stock_actual
        """, art)
        rows = cur.fetchall()
        for dep, stk, stku in rows:
            print(f"  Art {art} dep={dep}: serie ' ' stock_unidades {stku} -> {stk}")
            cur.execute("""
                UPDATE msgestion03.dbo.stock
                SET stock_unidades = stock_actual
                WHERE deposito = ? AND articulo = ? AND serie = ' '
            """, dep, art)

    # ============================================================
    # PARTE 5: msg01 stock — fix stock_unidades en serie '2603' de WB
    # ============================================================
    print("\n--- PARTE 5: msgestion01.stock — fix stock_unidades serie '2603' WB ---")

    # Solo filas donde stock_unidades != stock_actual (señal de que WB las creó mal)
    cur.execute("""
        SELECT s.deposito, s.articulo, s.stock_actual, s.stock_unidades
        FROM msgestion01.dbo.stock s
        WHERE s.serie = '2603'
          AND s.stock_unidades <> s.stock_actual
        ORDER BY s.articulo, s.deposito
    """)
    rows_msg01 = cur.fetchall()
    print(f"  Filas '2603' con stock_unidades != stock_actual: {len(rows_msg01)}")

    for dep, art, stk, stku in rows_msg01:
        print(f"  Art {art} dep={dep}: stock_unidades {stku} -> {stk}")
        cur.execute("""
            UPDATE msgestion01.dbo.stock
            SET stock_unidades = stock_actual
            WHERE deposito = ? AND articulo = ? AND serie = '2603'
        """, dep, art)

    # ============================================================
    # RESUMEN Y COMMIT
    # ============================================================
    print("\n" + "=" * 60)
    print("RESUMEN:")
    print(f"  - msg03 stock: eliminadas filas serie '2603' de remito WB {REMITO_WB}")
    print(f"  - msg03 stock: restado doble conteo de serie ' '")
    print(f"  - msg03 compras1/movi_stock: serie cambiada a ' '")
    print(f"  - msg03 movi_stock: unidades corregidas")
    print(f"  - Valijas: filas huérfanas eliminadas, stock_unidades corregido")
    print(f"  - msg01 stock: stock_unidades corregido en serie '2603'")
    print(f"\n  NOTA: Remito PIRA 35309 (ejecutable) NO fue tocado.")
    print("=" * 60)

    resp = input("\nAplicar cambios? (s/n): ").strip().lower()
    if resp == 's':
        conn.commit()
        print("COMMIT OK — cambios aplicados")
    else:
        conn.rollback()
        print("ROLLBACK — no se aplicaron cambios")

    cur.close()
    conn.close()


if __name__ == '__main__':
    run()
