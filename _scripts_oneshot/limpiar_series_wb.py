"""
limpiar_series_wb.py
Limpia el campo serie de registros creados por nuestro codigo web (usuario='WB')
en movi_stock, y consolida filas de stock con series sucias ('2603','26030001','26030002')
hacia serie=''.

NO TOCA compras1 del ERP nativo (host_creacion DELL-SVR / DESKTOP-5LNKDR1).

Ejecutar en el 111:
  py -3 limpiar_series_wb.py --dry-run
  py -3 limpiar_series_wb.py --ejecutar
"""

import sys
import pyodbc
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("limpiar_series")

# Conexion directa al 111 (produccion)
CONN = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestionC;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes;"
)

SERIES_SUCIAS = ("'2603'", "'26030001'", "'26030002'")
SERIES_IN = "(" + ",".join(SERIES_SUCIAS) + ")"

BASES = [
    ("msgestion01", "CALZALINDO"),
    ("msgestion03", "H4"),
]


def limpiar(dry_run=True):
    conn = pyodbc.connect(CONN, timeout=10)
    conn.autocommit = False
    cursor = conn.cursor()

    total_cambios = 0

    for base, empresa in BASES:
        log.info(f"\n{'='*60}")
        log.info(f"BASE: {base} ({empresa})")
        log.info(f"{'='*60}")

        # ── 1. MOVI_STOCK: limpiar serie de registros WB ──────────
        sql_count_ms = f"""
            SELECT serie, COUNT(*) AS n
            FROM {base}.dbo.movi_stock
            WHERE usuario = 'WB' AND serie != ''
            GROUP BY serie
        """
        cursor.execute(sql_count_ms)
        rows_ms = cursor.fetchall()
        for row in rows_ms:
            log.info(f"  movi_stock serie='{row.serie}': {row.n} registros")
            total_cambios += row.n

        if not dry_run:
            sql_upd_ms = f"""
                UPDATE {base}.dbo.movi_stock
                SET serie = ''
                WHERE usuario = 'WB' AND serie != ''
            """
            cursor.execute(sql_upd_ms)
            log.info(f"  >> UPDATE movi_stock: {cursor.rowcount} filas limpiadas")

        # ── 2. STOCK: consolidar series sucias a serie='' ──────────
        # Para cada articulo+deposito con serie sucia:
        #   - Si ya existe fila con serie='': sumar stock_actual y borrar la sucia
        #   - Si no existe: cambiar serie a ''
        sql_stock_sucias = f"""
            SELECT deposito, articulo, serie,
                   ISNULL(stock_actual, 0) AS stock_actual,
                   ISNULL(stock_unidades, 0) AS stock_unidades
            FROM {base}.dbo.stock
            WHERE serie IN {SERIES_IN}
            ORDER BY deposito, articulo, serie
        """
        cursor.execute(sql_stock_sucias)
        rows_stk = cursor.fetchall()

        if not rows_stk:
            log.info(f"  stock: sin filas con series sucias")
        else:
            log.info(f"  stock: {len(rows_stk)} filas con series sucias")

        for row in rows_stk:
            dep, art, serie, stk, stk_u = row.deposito, row.articulo, row.serie, row.stock_actual, row.stock_unidades
            total_cambios += 1

            # Verificar si ya existe fila con serie=''
            cursor.execute(f"""
                SELECT stock_actual, stock_unidades
                FROM {base}.dbo.stock
                WHERE deposito = ? AND articulo = ? AND serie = ''
            """, (dep, art))
            fila_vacia = cursor.fetchone()

            if fila_vacia:
                log.info(f"    dep={dep} art={art} serie='{serie}' stk={stk}"
                         f" -> SUMAR a serie='' (actual={fila_vacia.stock_actual}) y BORRAR")
                if not dry_run:
                    cursor.execute(f"""
                        UPDATE {base}.dbo.stock
                        SET stock_actual = ISNULL(stock_actual, 0) + ?,
                            stock_unidades = ISNULL(stock_unidades, 0) + ?
                        WHERE deposito = ? AND articulo = ? AND serie = ''
                    """, (stk, stk_u, dep, art))
                    cursor.execute(f"""
                        DELETE FROM {base}.dbo.stock
                        WHERE deposito = ? AND articulo = ? AND serie = ?
                    """, (dep, art, serie))
            else:
                log.info(f"    dep={dep} art={art} serie='{serie}' stk={stk}"
                         f" -> RENOMBRAR a serie=''")
                if not dry_run:
                    cursor.execute(f"""
                        UPDATE {base}.dbo.stock
                        SET serie = ''
                        WHERE deposito = ? AND articulo = ? AND serie = ?
                    """, (dep, art, serie))

    # ── RESUMEN ────────────────────────────────────────────────
    log.info(f"\n{'='*60}")
    if dry_run:
        log.info(f"DRY RUN: {total_cambios} cambios pendientes. Ejecutar con --ejecutar")
    else:
        conn.commit()
        log.info(f"EJECUTADO: {total_cambios} cambios aplicados y commiteados")

    conn.close()


if __name__ == "__main__":
    if "--ejecutar" in sys.argv:
        confirm = input("Confirmar limpieza de series en produccion (s/n): ")
        if confirm.lower() == "s":
            limpiar(dry_run=False)
        else:
            log.info("Cancelado.")
    else:
        log.info("=== DRY RUN (usar --ejecutar para aplicar) ===")
        limpiar(dry_run=True)
