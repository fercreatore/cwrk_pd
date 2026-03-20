#!/usr/bin/env python3
"""
analisis_stock.py — Análisis profundo de inconsistencias de stock
=================================================================
Compara msgestion01.dbo.stock vs msgestion03.dbo.stock y cruza con
movi_stock, compras1, ventas1 para detectar problemas.

EJECUTAR EN EL 111:
  py -3 analisis_stock.py
  py -3 analisis_stock.py --detalle       ← muestra artículos individuales
  py -3 analisis_stock.py --exportar      ← exporta CSV con todo
"""

import sys
import os
import pyodbc
import socket
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

_hostname = socket.gethostname().upper()
if _hostname in ("DELL-SVR", "DELLSVR"):
    SERVIDOR = "localhost"
    DRIVER = "ODBC Driver 17 for SQL Server"
    EXTRAS = ""
else:
    SERVIDOR = "192.168.2.111"
    DRIVER = "ODBC Driver 17 for SQL Server"
    EXTRAS = "TrustServerCertificate=yes;Encrypt=no;"

CONN = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVIDOR};"
    f"DATABASE=msgestionC;"
    f"UID=am;PWD=dl;"
    f"{EXTRAS}"
)

detalle = "--detalle" in sys.argv
exportar = "--exportar" in sys.argv


def sep(titulo):
    print(f"\n{'='*70}")
    print(f"  {titulo}")
    print(f"{'='*70}")


def main():
    print(f"Conectando a {SERVIDOR}...")
    conn = pyodbc.connect(CONN, timeout=15)
    cur = conn.cursor()
    print("OK\n")

    resultados = {}

    # ══════════════════════════════════════════════════════════════
    # 1. STOCK NEGATIVO
    # ══════════════════════════════════════════════════════════════
    sep("1. STOCK NEGATIVO")
    for base, empresa in [("msgestion01", "CALZALINDO"), ("msgestion03", "H4")]:
        cur.execute(f"""
            SELECT COUNT(*) as cant,
                   SUM(s.stock_actual) as total_neg,
                   MIN(s.stock_actual) as peor
            FROM {base}.dbo.stock s
            WHERE s.stock_actual < 0 AND s.serie = ' '
        """)
        r = cur.fetchone()
        print(f"  {empresa:12s} ({base}): {r.cant:>5} artículos con stock negativo | total={r.total_neg or 0:>8.0f} | peor={r.peor or 0:.0f}")
        resultados[f"neg_{empresa}"] = r.cant

        if detalle and r.cant > 0:
            cur.execute(f"""
                SELECT TOP 20 s.articulo, s.stock_actual, s.deposito,
                       a.descripcion_1, a.proveedor
                FROM {base}.dbo.stock s
                LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
                WHERE s.stock_actual < 0 AND s.serie = ' '
                ORDER BY s.stock_actual ASC
            """)
            for row in cur.fetchall():
                desc = (row.descripcion_1 or "")[:40]
                print(f"    [{row.articulo:>6}] dep={row.deposito} stock={row.stock_actual:>6.0f} prov={row.proveedor or '?':>4} {desc}")

    # ══════════════════════════════════════════════════════════════
    # 2. SERIE RESUMEN vs SUMA DE SERIES MENSUALES
    # ══════════════════════════════════════════════════════════════
    sep("2. SERIE RESUMEN (' ') vs SUMA DE SERIES MENSUALES")
    for base, empresa in [("msgestion01", "CALZALINDO"), ("msgestion03", "H4")]:
        cur.execute(f"""
            SELECT COUNT(*) as cant
            FROM (
                SELECT s_res.deposito, s_res.articulo,
                       s_res.stock_actual as resumen,
                       ISNULL(sm.suma_series, 0) as suma_series,
                       s_res.stock_actual - ISNULL(sm.suma_series, 0) as dif
                FROM {base}.dbo.stock s_res
                LEFT JOIN (
                    SELECT deposito, articulo, SUM(stock_actual) as suma_series
                    FROM {base}.dbo.stock
                    WHERE serie <> ' ' AND serie <> ''
                    GROUP BY deposito, articulo
                ) sm ON sm.deposito = s_res.deposito AND sm.articulo = s_res.articulo
                WHERE s_res.serie = ' '
                  AND ABS(s_res.stock_actual - ISNULL(sm.suma_series, 0)) > 0.01
            ) x
        """)
        cnt = cur.fetchone().cant
        print(f"  {empresa:12s}: {cnt:>5} artículos donde resumen <> suma de series")
        resultados[f"serie_mismatch_{empresa}"] = cnt

        if detalle and cnt > 0:
            cur.execute(f"""
                SELECT TOP 20 s_res.deposito, s_res.articulo,
                       s_res.stock_actual as resumen,
                       ISNULL(sm.suma_series, 0) as suma_series,
                       s_res.stock_actual - ISNULL(sm.suma_series, 0) as dif,
                       a.descripcion_1
                FROM {base}.dbo.stock s_res
                LEFT JOIN (
                    SELECT deposito, articulo, SUM(stock_actual) as suma_series
                    FROM {base}.dbo.stock
                    WHERE serie <> ' ' AND serie <> ''
                    GROUP BY deposito, articulo
                ) sm ON sm.deposito = s_res.deposito AND sm.articulo = s_res.articulo
                LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = s_res.articulo
                WHERE s_res.serie = ' '
                  AND ABS(s_res.stock_actual - ISNULL(sm.suma_series, 0)) > 0.01
                ORDER BY ABS(s_res.stock_actual - ISNULL(sm.suma_series, 0)) DESC
            """)
            for row in cur.fetchall():
                desc = (row.descripcion_1 or "")[:35]
                print(f"    [{row.articulo:>6}] dep={row.deposito} resumen={row.resumen:>6.0f} suma_series={row.suma_series:>6.0f} dif={row.dif:>+6.0f} {desc}")

    # ══════════════════════════════════════════════════════════════
    # 3. STOCK EN BASE01 vs BASE03 — DUPLICADOS
    # ══════════════════════════════════════════════════════════════
    sep("3. MISMO ARTÍCULO CON STOCK EN AMBAS BASES (duplicados)")
    cur.execute("""
        SELECT COUNT(*) as cant
        FROM msgestion01.dbo.stock s1
        INNER JOIN msgestion03.dbo.stock s3
            ON s1.articulo = s3.articulo
            AND s1.deposito = s3.deposito
            AND s1.serie = s3.serie
        WHERE s1.serie = ' '
          AND (s1.stock_actual <> 0 OR s3.stock_actual <> 0)
    """)
    cnt = cur.fetchone().cant
    print(f"  Artículos con stock en AMBAS bases: {cnt}")
    resultados["duplicados_ambas_bases"] = cnt

    if detalle and cnt > 0:
        cur.execute("""
            SELECT TOP 20 s1.articulo, s1.deposito,
                   s1.stock_actual as stock_01,
                   s3.stock_actual as stock_03,
                   s1.stock_actual + s3.stock_actual as total,
                   a.descripcion_1, a.proveedor
            FROM msgestion01.dbo.stock s1
            INNER JOIN msgestion03.dbo.stock s3
                ON s1.articulo = s3.articulo
                AND s1.deposito = s3.deposito
                AND s1.serie = s3.serie
            LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = s1.articulo
            WHERE s1.serie = ' '
              AND (s1.stock_actual <> 0 OR s3.stock_actual <> 0)
            ORDER BY ABS(s1.stock_actual) + ABS(s3.stock_actual) DESC
        """)
        for row in cur.fetchall():
            desc = (row.descripcion_1 or "")[:35]
            print(f"    [{row.articulo:>6}] dep={row.deposito} base01={row.stock_01:>5.0f} base03={row.stock_03:>5.0f} total={row.total:>5.0f} prov={row.proveedor or '?':>4} {desc}")

    # ══════════════════════════════════════════════════════════════
    # 4. STOCK SIN ARTÍCULO EN MAESTRO
    # ══════════════════════════════════════════════════════════════
    sep("4. STOCK DE ARTÍCULOS QUE NO EXISTEN EN MAESTRO")
    for base, empresa in [("msgestion01", "CALZALINDO"), ("msgestion03", "H4")]:
        cur.execute(f"""
            SELECT COUNT(*) as cant
            FROM {base}.dbo.stock s
            LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
            WHERE s.serie = ' ' AND s.stock_actual <> 0 AND a.codigo IS NULL
        """)
        cnt = cur.fetchone().cant
        print(f"  {empresa:12s}: {cnt:>5} registros de stock sin artículo en maestro")
        resultados[f"huerfanos_{empresa}"] = cnt

    # ══════════════════════════════════════════════════════════════
    # 5. DEPÓSITO 0 (stock mal asignado)
    # ══════════════════════════════════════════════════════════════
    sep("5. STOCK EN DEPÓSITO 0 (mal asignado)")
    for base, empresa in [("msgestion01", "CALZALINDO"), ("msgestion03", "H4")]:
        cur.execute(f"""
            SELECT COUNT(*) as cant, SUM(s.stock_actual) as total
            FROM {base}.dbo.stock s
            WHERE s.deposito = 0 AND s.serie = ' ' AND s.stock_actual <> 0
        """)
        r = cur.fetchone()
        print(f"  {empresa:12s}: {r.cant:>5} artículos en depósito 0 | total unidades={r.total or 0:.0f}")
        resultados[f"dep0_{empresa}"] = r.cant

    # ══════════════════════════════════════════════════════════════
    # 6. REMITOS SIN MOVIMIENTO DE STOCK
    # ══════════════════════════════════════════════════════════════
    sep("6. REMITOS (cod=7) SIN MOVIMIENTO DE STOCK")
    for base, empresa in [("msgestion01", "CALZALINDO"), ("msgestion03", "H4")]:
        cur.execute(f"""
            SELECT COUNT(DISTINCT c2.numero) as cant
            FROM {base}.dbo.compras2 c2
            LEFT JOIN {base}.dbo.movi_stock ms
                ON ms.codigo_comprobante = c2.codigo
                AND ms.letra_comprobante = c2.letra
                AND ms.sucursal_comprobante = c2.sucursal
                AND ms.numero_comprobante = c2.numero
                AND ms.orden = c2.orden
            WHERE c2.codigo = 7 AND c2.estado = 'V'
              AND ms.articulo IS NULL
        """)
        cnt = cur.fetchone().cant
        print(f"  {empresa:12s}: {cnt:>5} remitos sin movimiento de stock")
        resultados[f"remitos_sin_movi_{empresa}"] = cnt

    # ══════════════════════════════════════════════════════════════
    # 7. STOCK RECALCULADO vs ACTUAL (movi_stock)
    # Suma de movimientos debería dar el stock actual
    # ══════════════════════════════════════════════════════════════
    sep("7. STOCK RECALCULADO (movi_stock) vs STOCK ACTUAL")
    for base, empresa in [("msgestion01", "CALZALINDO"), ("msgestion03", "H4")]:
        cur.execute(f"""
            SELECT COUNT(*) as cant
            FROM (
                SELECT ms.articulo, ms.deposito,
                       SUM(CASE WHEN ms.operacion = '+' THEN ms.cantidad
                                WHEN ms.operacion = '-' THEN -ms.cantidad
                                ELSE 0 END) as stock_calc,
                       s.stock_actual as stock_real,
                       SUM(CASE WHEN ms.operacion = '+' THEN ms.cantidad
                                WHEN ms.operacion = '-' THEN -ms.cantidad
                                ELSE 0 END) - ISNULL(s.stock_actual, 0) as dif
                FROM {base}.dbo.movi_stock ms
                LEFT JOIN {base}.dbo.stock s
                    ON s.articulo = ms.articulo
                    AND s.deposito = ms.deposito
                    AND s.serie = ' '
                GROUP BY ms.articulo, ms.deposito, s.stock_actual
                HAVING ABS(SUM(CASE WHEN ms.operacion = '+' THEN ms.cantidad
                                    WHEN ms.operacion = '-' THEN -ms.cantidad
                                    ELSE 0 END) - ISNULL(s.stock_actual, 0)) > 0.5
            ) x
        """)
        cnt = cur.fetchone().cant
        print(f"  {empresa:12s}: {cnt:>5} artículos donde movi_stock <> stock actual")
        resultados[f"movi_vs_stock_{empresa}"] = cnt

        if detalle and cnt > 0:
            cur.execute(f"""
                SELECT TOP 15 x.articulo, x.deposito, x.stock_calc, x.stock_real, x.dif,
                       a.descripcion_1, a.proveedor
                FROM (
                    SELECT ms.articulo, ms.deposito,
                           SUM(CASE WHEN ms.operacion = '+' THEN ms.cantidad
                                    WHEN ms.operacion = '-' THEN -ms.cantidad
                                    ELSE 0 END) as stock_calc,
                           s.stock_actual as stock_real,
                           SUM(CASE WHEN ms.operacion = '+' THEN ms.cantidad
                                    WHEN ms.operacion = '-' THEN -ms.cantidad
                                    ELSE 0 END) - ISNULL(s.stock_actual, 0) as dif
                    FROM {base}.dbo.movi_stock ms
                    LEFT JOIN {base}.dbo.stock s
                        ON s.articulo = ms.articulo
                        AND s.deposito = ms.deposito
                        AND s.serie = ' '
                    GROUP BY ms.articulo, ms.deposito, s.stock_actual
                    HAVING ABS(SUM(CASE WHEN ms.operacion = '+' THEN ms.cantidad
                                        WHEN ms.operacion = '-' THEN -ms.cantidad
                                        ELSE 0 END) - ISNULL(s.stock_actual, 0)) > 0.5
                ) x
                LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = x.articulo
                ORDER BY ABS(x.dif) DESC
            """)
            for row in cur.fetchall():
                desc = (row.descripcion_1 or "")[:35]
                print(f"    [{row.articulo:>6}] dep={row.deposito} calc={row.stock_calc:>6.0f} real={row.stock_real or 0:>6.0f} dif={row.dif:>+6.0f} {desc}")

    # ══════════════════════════════════════════════════════════════
    # 8. RESUMEN GENERAL DE STOCK
    # ══════════════════════════════════════════════════════════════
    sep("8. RESUMEN GENERAL")
    for base, empresa in [("msgestion01", "CALZALINDO"), ("msgestion03", "H4")]:
        cur.execute(f"""
            SELECT COUNT(DISTINCT articulo) as arts,
                   SUM(stock_actual) as total_uds,
                   SUM(CASE WHEN stock_actual > 0 THEN 1 ELSE 0 END) as con_stock,
                   SUM(CASE WHEN stock_actual = 0 THEN 1 ELSE 0 END) as sin_stock,
                   SUM(CASE WHEN stock_actual < 0 THEN 1 ELSE 0 END) as negativos,
                   COUNT(DISTINCT deposito) as depositos
            FROM {base}.dbo.stock
            WHERE serie = ' '
        """)
        r = cur.fetchone()
        print(f"  {empresa:12s}: {r.arts:>6} artículos | {r.total_uds or 0:>8.0f} uds totales | "
              f"con_stock={r.con_stock:>5} | sin_stock={r.sin_stock:>5} | negativos={r.negativos:>4} | "
              f"depósitos={r.depositos}")

    # ══════════════════════════════════════════════════════════════
    # RESUMEN FINAL
    # ══════════════════════════════════════════════════════════════
    sep("RESUMEN DE INCONSISTENCIAS")
    total_issues = 0
    for k, v in sorted(resultados.items()):
        if v > 0:
            print(f"  {k:40s}: {v:>6}")
            total_issues += v
    if total_issues == 0:
        print("  No se encontraron inconsistencias.")
    else:
        print(f"\n  TOTAL REGISTROS CON PROBLEMAS: {total_issues}")

    conn.close()
    print(f"\n  Análisis completado.")


if __name__ == "__main__":
    main()
