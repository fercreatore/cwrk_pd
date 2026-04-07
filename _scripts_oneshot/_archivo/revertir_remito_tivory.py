"""
revertir_remito_tivory.py
=========================
Revierte COMPLETAMENTE el remito Tivory (compras2 codigo=7, numero=12867, base03).

Ejecutar en 192.168.2.111:
  py -3 revertir_remito_tivory.py            # DRY RUN
  py -3 revertir_remito_tivory.py --ejecutar
"""

import pyodbc
import sys

DRY_RUN = "--ejecutar" not in sys.argv

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
)

# Artículos del remito con cantidades
REMITO = {
    146119: 2, 146120: 3, 146121: 3, 146122: 2, 146123: 2,
    344898: 3, 344899: 4, 344900: 4, 344901: 4, 344902: 3,
    344904: 3, 344905: 3, 344906: 3, 344907: 3, 344983: 3, 344984: 3,
    351752: 2, 351753: 2, 351754: 2, 351755: 1, 351756: 1,
    351759: 2, 351760: 3, 351761: 3, 351762: 2, 351763: 2,
    351770: 2, 351771: 3, 351772: 3, 351773: 2, 351774: 2,
    360761: 2, 360762: 2, 360763: 2, 360764: 2, 360765: 2, 360766: 2,
    360767: 2, 360768: 2, 360769: 2, 360770: 2, 360771: 2, 360772: 2,
    360828: 2, 360829: 2,
    360871: 2, 360872: 2, 360873: 2, 360874: 2, 360875: 2, 360876: 1, 360877: 1,
}

PRE_EXISTENTES = {
    146119, 146120, 146121, 146122, 146123,
    344898, 344899, 344900, 344901, 344902,
    344904, 344905, 344906, 344907, 344983, 344984,
    351752, 351753, 351754, 351755, 351756,
    351759, 351760, 351761, 351762, 351763,
    351770, 351771, 351772, 351773, 351774,
}

NUEVOS = set(REMITO.keys()) - PRE_EXISTENTES
ALL_ARTS = sorted(REMITO.keys())


def log(msg):
    print(msg, flush=True)


def main():
    if DRY_RUN:
        log("=" * 60)
        log("  DRY RUN — no se modifica nada")
        log("  Usar: py -3 revertir_remito_tivory.py --ejecutar")
        log("=" * 60)
    else:
        log("=" * 60)
        log("  EJECUTANDO EN PRODUCCION")
        log("=" * 60)

    log("\nConectando...")
    conn = pyodbc.connect(CONN_STR, autocommit=False)
    cur = conn.cursor()

    # Timeout de 10 segundos para evitar cuelgues por locks
    cur.execute("SET LOCK_TIMEOUT 10000")
    log("Conectado. Lock timeout = 10s")

    total_pares = sum(REMITO.values())
    log(f"\nRemito: compras2 cod=7 num=12867 base03")
    log(f"Articulos: {len(REMITO)} ({len(PRE_EXISTENTES)} pre + {len(NUEVOS)} nuevos)")
    log(f"Pares total: {total_pares}")

    # ============================================
    # PASO 1: Borrar compras1
    # ============================================
    log(f"\n--- PASO 1: Borrar compras1 base03 ---")
    log("  Contando...")
    cur.execute("""
        SELECT COUNT(*) AS cnt FROM msgestion03.dbo.compras1
        WHERE codigo = 7 AND numero = 12867 AND serie = '26030001'
    """)
    cnt = cur.fetchone().cnt
    log(f"  Renglones encontrados: {cnt}")

    if not DRY_RUN and cnt > 0:
        log("  Borrando...")
        cur.execute("""
            DELETE FROM msgestion03.dbo.compras1
            WHERE codigo = 7 AND numero = 12867 AND serie = '26030001'
        """)
        log(f"  BORRADOS: {cur.rowcount}")
    log("  PASO 1 OK")

    # ============================================
    # PASO 2: Borrar compras2
    # ============================================
    log(f"\n--- PASO 2: Borrar compras2 base03 ---")
    log("  Contando...")
    cur.execute("""
        SELECT COUNT(*) AS cnt FROM msgestion03.dbo.compras2
        WHERE codigo = 7 AND numero = 12867
    """)
    cnt = cur.fetchone().cnt
    log(f"  Cabeceras encontradas: {cnt}")

    if not DRY_RUN and cnt > 0:
        log("  Borrando...")
        cur.execute("""
            DELETE FROM msgestion03.dbo.compras2
            WHERE codigo = 7 AND numero = 12867
        """)
        log(f"  BORRADAS: {cur.rowcount}")
    log("  PASO 2 OK")

    # ============================================
    # PASO 3: movi_stock — SALTEADO
    # ============================================
    log(f"\n--- PASO 3: movi_stock --- SALTEADO")
    log("  movi_stock es auditoria, no afecta stock real.")
    log("  La tabla se traba con el ERP activo.")
    log("  Si se quiere limpiar despues, hacerlo manual desde SSMS.")
    total_movi = 0

    # ============================================
    # PASO 4: Limpiar stock base01 dep 0/6/8/11
    # ============================================
    log(f"\n--- PASO 4: Limpiar stock base01 ---")
    fixed_01 = 0

    for art in ALL_ARTS:
        cur.execute("""
            SELECT deposito, stock_actual FROM msgestion01.dbo.stock
            WHERE articulo = ? AND serie = ' ' AND stock_actual <> 0
            AND deposito IN (0, 6, 8, 11)
        """, art)
        rows = cur.fetchall()

        for row in rows:
            log(f"  base01 dep{row.deposito} art {art}: {row.stock_actual} -> 0")
            if not DRY_RUN:
                cur.execute("""
                    UPDATE msgestion01.dbo.stock
                    SET stock_actual = 0
                    WHERE deposito = ? AND articulo = ? AND serie = ' '
                """, row.deposito, art)
            fixed_01 += 1

    log(f"  Total: {fixed_01}")
    log("  PASO 4 OK")

    # ============================================
    # PASO 5: Corregir stock base03 dep 11
    # ============================================
    log(f"\n--- PASO 5: Corregir stock base03 dep 11 ---")
    fixed_03 = 0

    for art in ALL_ARTS:
        cant_remito = REMITO[art]
        cur.execute("""
            SELECT stock_actual FROM msgestion03.dbo.stock
            WHERE deposito = 11 AND articulo = ? AND serie = ' '
        """, art)
        row = cur.fetchone()

        if row is None:
            continue

        actual = row.stock_actual
        nuevo_val = 0 if art in NUEVOS else actual - cant_remito

        if actual == nuevo_val:
            continue

        log(f"  base03 dep11 art {art}: {actual} -> {nuevo_val}")

        if not DRY_RUN:
            cur.execute("""
                UPDATE msgestion03.dbo.stock
                SET stock_actual = ?
                WHERE deposito = 11 AND articulo = ? AND serie = ' '
            """, nuevo_val, art)
        fixed_03 += 1

    log(f"  Total: {fixed_03}")
    log("  PASO 5 OK")

    # ============================================
    # PASO 6: Borrar stock serie '26030001'
    # ============================================
    log(f"\n--- PASO 6: Borrar stock serie '26030001' ---")
    deleted_serie = 0

    for art in ALL_ARTS:
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM msgestion03.dbo.stock
            WHERE articulo = ? AND serie = '26030001'
        """, art)
        cnt = cur.fetchone().cnt
        if cnt > 0:
            log(f"  base03 art {art}: {cnt} registros serie 26030001")
            if not DRY_RUN:
                cur.execute("""
                    DELETE FROM msgestion03.dbo.stock
                    WHERE articulo = ? AND serie = '26030001'
                """, art)
            deleted_serie += cnt

    log(f"  Total borrados: {deleted_serie}")
    log("  PASO 6 OK")

    # ============================================
    # RESUMEN
    # ============================================
    log(f"\n{'='*60}")
    log(f"  RESUMEN")
    log(f"{'='*60}")
    log(f"  compras1 borrados: paso 1")
    log(f"  compras2 borrados: paso 2")
    log(f"  movi_stock borrados: {total_movi}")
    log(f"  stock base01 limpiados: {fixed_01}")
    log(f"  stock base03 corregidos: {fixed_03}")
    log(f"  stock serie 26030001 borrados: {deleted_serie}")

    if not DRY_RUN:
        log("\n  Haciendo COMMIT...")
        conn.commit()
        log("  COMMIT OK")

        # Verificación rápida PPX3941
        log(f"\n--- Verificacion PPX3941 ---")
        log(f"{'Art':>8} | {'b01 d11':>8} | {'b03 d11':>8} | {'Consol':>7}")
        log("-" * 45)
        for art in [344898, 344899, 344900, 344901, 344902]:
            cur.execute("""
                SELECT
                    (SELECT ISNULL(stock_actual,0) FROM msgestion01.dbo.stock
                     WHERE articulo=? AND deposito=11 AND serie=' ') AS b01,
                    (SELECT ISNULL(stock_actual,0) FROM msgestion03.dbo.stock
                     WHERE articulo=? AND deposito=11 AND serie=' ') AS b03
            """, art, art)
            r = cur.fetchone()
            log(f"{art:>8} | {r.b01:>8} | {r.b03:>8} | {r.b01+r.b03:>7}")
    else:
        log("\n  (dry run - nada modificado)")

    cur.close()
    conn.close()
    log("\nFin.")


if __name__ == "__main__":
    main()
