"""
fix_stock_remito_tivory.py
==========================
Resetea y corrige stock en dep 11 para todos los artículos del
remito R 0001-12867 de Tivory (12/03/2026).

Lógica:
  1) Para cada artículo del remito, UPSERT en dep 11 serie ' ' con la
     cantidad exacta del remito.
  2) ST5877: se pone x4 por talle (24 total) — mandaron doble.
  3) LS879: se agrega 2 por talle (12 total) — no está en remito pero llegó.
  4) PWX3585: limpia stock negativo/erróneo en dep 0.
  5) PPX3941: preserva los 20 pre-existentes en dep 0.

Ejecutar en 192.168.2.111:
  py -3 fix_stock_remito_tivory.py            # DRY RUN
  py -3 fix_stock_remito_tivory.py --ejecutar
"""

import pyodbc
import sys

DRY_RUN = "--ejecutar" not in sys.argv

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
)

# =====================================================
# TARGET: stock_actual en dep 11, serie ' '
# Cantidades tomadas del remito R 0001-12867
# ST5877 duplicado (24 en vez de 12)
# LS879 agregado manualmente (12 pares)
# =====================================================
STOCK_DEP11 = {
    # AV0455 SURTIDO (12 pares) — remito
    360871: 2, 360872: 2, 360873: 2, 360874: 2, 360875: 2, 360876: 1, 360877: 1,

    # PPX3941 LILA (18 pares) — remito
    344898: 3, 344899: 4, 344900: 4, 344901: 4, 344902: 3,

    # PPX5947 ROSA (12 pares) — remito
    351759: 2, 351760: 3, 351761: 3, 351762: 2, 351763: 2,

    # PPX938 ROSA/LILA (12 pares) — remito
    146119: 2, 146120: 3, 146121: 3, 146122: 2, 146123: 2,

    # PPX942 ROSA/PLATA (12 pares) — remito
    351770: 2, 351771: 3, 351772: 3, 351773: 2, 351774: 2,

    # PWX3585 GRIS (18 pares) — remito
    344904: 3, 344905: 3, 344906: 3, 344907: 3, 344983: 3, 344984: 3,

    # SP5690 AZUL (8 pares) — remito
    351752: 2, 351753: 2, 351754: 2, 351755: 1, 351756: 1,

    # SP5690 ROJO (4 pares) — remito
    360828: 2, 360829: 2,

    # ST5877 CELESTE (24 pares) — remito dice 12 pero mandaron 24
    360761: 4, 360762: 4, 360763: 4, 360764: 4, 360765: 4, 360766: 4,

    # ST881 CELESTE (12 pares) — remito
    360767: 2, 360768: 2, 360769: 2, 360770: 2, 360771: 2, 360772: 2,

    # LS879 BLANCO AZUL (12 pares) — NO está en remito, llegó aparte
    360773: 2, 360774: 2, 360775: 2, 360776: 2, 360777: 2, 360778: 2,
}

# PPX3941 pre-existente en dep 0 (NO tocar)
PPX3941_DEP0_PRESERVAR = {344898, 344899, 344900, 344901, 344902}

# PWX3585 arts — limpiar dep 0 (tienen valores erróneos por scripts anteriores)
PWX3585_ARTS = [344904, 344905, 344906, 344907, 344983, 344984]

# Todos los artículos del remito (para limpiar dep 0 de stock fantasma)
ALL_REMITO_ARTS = set(STOCK_DEP11.keys()) - PPX3941_DEP0_PRESERVAR


def main():
    if DRY_RUN:
        print("=" * 60)
        print("  DRY RUN — no se modifica nada")
        print("  Usar: py -3 fix_stock_remito_tivory.py --ejecutar")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  EJECUTANDO EN PRODUCCIÓN")
        print("=" * 60)

    conn = pyodbc.connect(CONN_STR, autocommit=False)
    cur = conn.cursor()

    updates = 0
    inserts = 0
    cleanups = 0

    # ========================================
    # PARTE 1: UPSERT stock en dep 11
    # ========================================
    print("\n--- PARTE 1: Setear stock correcto en dep 11 ---")

    for art, qty in sorted(STOCK_DEP11.items()):
        # Ver si existe el registro
        cur.execute("""
            SELECT stock_actual FROM msgestion03.dbo.stock
            WHERE deposito = 11 AND articulo = ? AND serie = ' '
        """, art)
        row = cur.fetchone()

        if row is not None:
            current = row.stock_actual
            if current != qty:
                print(f"  Art {art}: dep11 {current} → {qty}")
                if not DRY_RUN:
                    cur.execute("""
                        UPDATE msgestion03.dbo.stock
                        SET stock_actual = ?
                        WHERE deposito = 11 AND articulo = ? AND serie = ' '
                    """, qty, art)
                updates += 1
            else:
                pass  # ya correcto, no imprimir
        else:
            print(f"  Art {art}: INSERT dep11 = {qty}")
            if not DRY_RUN:
                cur.execute("""
                    INSERT INTO msgestion03.dbo.stock
                    (deposito, articulo, serie, stock_actual)
                    VALUES (11, ?, ' ', ?)
                """, art, qty)
            inserts += 1

    print(f"  Resultado dep 11: {updates} updates, {inserts} inserts")

    # ========================================
    # PARTE 2: Limpiar dep 0 para arts del remito
    #          (excepto PPX3941 pre-existente)
    # ========================================
    print("\n--- PARTE 2: Limpiar dep 0 (stock errónero por scripts anteriores) ---")

    for art in sorted(ALL_REMITO_ARTS):
        cur.execute("""
            SELECT stock_actual FROM msgestion03.dbo.stock
            WHERE deposito = 0 AND articulo = ? AND serie = ' '
        """, art)
        row = cur.fetchone()

        if row is not None and row.stock_actual != 0:
            print(f"  Art {art}: dep0 {row.stock_actual} → 0")
            if not DRY_RUN:
                cur.execute("""
                    UPDATE msgestion03.dbo.stock
                    SET stock_actual = 0
                    WHERE deposito = 0 AND articulo = ? AND serie = ' '
                """, art)
            cleanups += 1

    # PPX3941 en dep 0 — verificar que se preserva
    print("\n  PPX3941 dep 0 (preservado):")
    for art in sorted(PPX3941_DEP0_PRESERVAR):
        cur.execute("""
            SELECT stock_actual FROM msgestion03.dbo.stock
            WHERE deposito = 0 AND articulo = ? AND serie = ' '
        """, art)
        row = cur.fetchone()
        stock_val = row.stock_actual if row else 0
        print(f"    Art {art}: dep0 = {stock_val} (no se toca)")

    print(f"\n  Cleanups dep 0: {cleanups}")

    # ========================================
    # PARTE 3: Limpiar serie '26030001' residual
    # ========================================
    print("\n--- PARTE 3: Limpiar serie '26030001' residual ---")

    all_arts = sorted(STOCK_DEP11.keys())
    placeholders = ','.join(['?'] * len(all_arts))

    cur.execute(f"""
        SELECT deposito, articulo, serie, stock_actual
        FROM msgestion03.dbo.stock
        WHERE articulo IN ({placeholders})
        AND serie != ' ' AND stock_actual != 0
    """, *all_arts)
    series_malas = cur.fetchall()

    if series_malas:
        for s in series_malas:
            print(f"  Art {s.articulo}: dep{s.deposito} serie='{s.serie.strip()}' stock={s.stock_actual} → 0")
            if not DRY_RUN:
                cur.execute("""
                    UPDATE msgestion03.dbo.stock
                    SET stock_actual = 0
                    WHERE deposito = ? AND articulo = ? AND serie = ?
                """, s.deposito, s.articulo, s.serie)
        print(f"  {len(series_malas)} series limpiadas")
    else:
        print("  No hay series fantasma, OK")

    # ========================================
    # RESUMEN
    # ========================================
    print("\n" + "=" * 60)

    total_pares = sum(STOCK_DEP11.values())
    print(f"Target: {len(STOCK_DEP11)} artículos, {total_pares} pares en dep 11")

    if DRY_RUN:
        print(f"\nDRY RUN completado:")
        print(f"  - dep 11: {updates} updates + {inserts} inserts")
        print(f"  - dep 0 cleanups: {cleanups}")
        print(f"  - series fantasma: {len(series_malas)}")
        print("Ejecutar con --ejecutar para aplicar cambios")
        conn.rollback()
    else:
        conn.commit()
        print(f"\nEJECUTADO OK:")
        print(f"  - dep 11: {updates} updates + {inserts} inserts")
        print(f"  - dep 0 cleanups: {cleanups}")
        print(f"  - series fantasma: {len(series_malas)}")

    conn.close()


if __name__ == "__main__":
    main()
