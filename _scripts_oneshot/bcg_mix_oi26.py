#!/usr/bin/env python3
"""
bcg_mix_oi26.py — Análisis BCG de mix de productos OI26
Ejecuta queries de margen, rotación y gap para generar informe BCG.
"""
import os, sys, platform, json
from datetime import date
from decimal import Decimal

if platform.system() != "Windows":
    ssl_conf = "/tmp/openssl_legacy.cnf"
    if not os.path.exists(ssl_conf):
        with open(ssl_conf, "w") as f:
            f.write("[openssl_init]\nssl_conf = ssl_sect\n[ssl_sect]\nsystem_default = system_default_sect\n[system_default_sect]\nMinProtocol = TLSv1\nCipherString = DEFAULT@SECLEVEL=0\n")
    os.environ["OPENSSL_CONF"] = ssl_conf

import pyodbc

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.2.111;DATABASE=msgestionC;UID=am;PWD=dl;Connection Timeout=15;TrustServerCertificate=yes;Encrypt=no;"

def run():
    conn = pyodbc.connect(CONN_STR, timeout=15)
    cur = conn.cursor()
    results = {}

    # Q1+Q2 COMBINED: ALL marcas con margen Y rotación (monto > 500k para relevancia)
    print("Q1+Q2: Margen + Rotacion combinado...")
    cur.execute("""
        SELECT
          RTRIM(m.descripcion) as marca, a.marca as cod_marca,
          SUM(v.cantidad) as uds_vendidas,
          SUM(v.monto_facturado) as venta_total,
          SUM(v.precio_costo * v.cantidad) as costo_total,
          CASE WHEN SUM(v.monto_facturado) > 0
            THEN (SUM(v.monto_facturado) - SUM(v.precio_costo * v.cantidad)) * 100.0 / SUM(v.monto_facturado)
            ELSE 0 END as margen_pct,
          ISNULL(st.stock_total, 0) as stock_actual,
          CASE WHEN ISNULL(st.stock_total, 0) > 0
            THEN CAST(SUM(v.cantidad) AS FLOAT) / st.stock_total
            ELSE 999 END as rotacion
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        LEFT JOIN msgestionC.dbo.marcas m ON m.codigo = a.marca
        LEFT JOIN (
          SELECT a2.marca, SUM(s.stock_actual) as stock_total
          FROM msgestionC.dbo.stock s
          JOIN msgestion01art.dbo.articulo a2 ON a2.codigo = s.articulo
          WHERE s.deposito IN (0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)
          GROUP BY a2.marca
        ) st ON st.marca = a.marca
        WHERE v.fecha >= DATEADD(MONTH, -12, GETDATE())
          AND v.codigo NOT IN (7, 36)
          AND a.marca NOT IN (1316, 1317, 1158, 436)
          AND a.marca > 0
          AND v.operacion = '+'
          AND v.cantidad > 0
        GROUP BY RTRIM(m.descripcion), a.marca, st.stock_total
        HAVING SUM(v.monto_facturado) > 500000
        ORDER BY SUM(v.monto_facturado) DESC
    """)
    cols_combined = [d[0] for d in cur.description]
    results["q_combined"] = [dict(zip(cols_combined, row)) for row in cur.fetchall()]
    print(f"  -> {len(results['q_combined'])} marcas")

    # Q3: Gap OI26 (ventas abr-ago 2025 como proxy demanda)
    print("Q3: Gap OI26...")
    cur.execute("""
        SELECT
          RTRIM(m.descripcion) as marca, a.marca as cod_marca,
          SUM(v.cantidad) as vtas_oi25,
          ISNULL(st.stock_total, 0) as stock_actual,
          ISNULL(ped.pares_pend, 0) as pedidos_pend,
          SUM(v.cantidad) - ISNULL(st.stock_total, 0) - ISNULL(ped.pares_pend, 0) as gap_simple
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        LEFT JOIN msgestionC.dbo.marcas m ON m.codigo = a.marca
        LEFT JOIN (
          SELECT a2.marca, SUM(s.stock_actual) as stock_total
          FROM msgestionC.dbo.stock s
          JOIN msgestion01art.dbo.articulo a2 ON a2.codigo = s.articulo
          WHERE s.deposito IN (0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)
          GROUP BY a2.marca
        ) st ON st.marca = a.marca
        LEFT JOIN (
          SELECT a3.marca, SUM(p1.cantidad - ISNULL(p1.cantidad_facturada,0)) as pares_pend
          FROM msgestion03.dbo.pedico1 p1
          JOIN msgestion03.dbo.pedico2 p2 ON p2.numero = p1.numero AND p2.codigo = p1.codigo AND p2.letra = p1.letra AND p2.sucursal = p1.sucursal
          JOIN msgestion01art.dbo.articulo a3 ON a3.codigo = p1.articulo
          WHERE p2.estado = 'V' AND p1.cantidad > ISNULL(p1.cantidad_facturada, 0)
          GROUP BY a3.marca
        ) ped ON ped.marca = a.marca
        WHERE v.fecha >= '2025-04-01' AND v.fecha < '2025-09-01'
          AND v.codigo NOT IN (7, 36)
          AND a.marca NOT IN (1316, 1317, 1158, 436)
          AND a.marca > 0
          AND v.operacion = '+'
          AND v.cantidad > 0
        GROUP BY RTRIM(m.descripcion), a.marca, st.stock_total, ped.pares_pend
        HAVING SUM(v.monto_facturado) > 100000
        ORDER BY gap_simple DESC
    """)
    cols3 = [d[0] for d in cur.description]
    results["q3_gap"] = [dict(zip(cols3, row)) for row in cur.fetchall()]
    print(f"  -> {len(results['q3_gap'])} marcas")

    # Q4: Factor quiebre (vel_real_articulo)
    print("Q4: Factor quiebre...")
    try:
        cur.execute("""
            SELECT a.marca, RTRIM(m.descripcion) as denominacion,
              AVG(CAST(vra.factor_quiebre AS FLOAT)) as factor_quiebre_prom,
              AVG(CAST(vra.meses_quebrado AS FLOAT) / CASE WHEN (vra.meses_con_stock + vra.meses_quebrado) > 0
                THEN CAST((vra.meses_con_stock + vra.meses_quebrado) AS FLOAT) ELSE 1.0 END) as pct_quiebre_prom,
              AVG(CAST(vra.vel_real AS FLOAT)) as vel_real_prom,
              AVG(CAST(vra.vel_aparente AS FLOAT)) as vel_aparente_prom,
              COUNT(*) as articulos
            FROM omicronvt.dbo.vel_real_articulo vra
            JOIN msgestion01art.dbo.articulo a ON LEFT(a.codigo_sinonimo, 10) = vra.codigo
            LEFT JOIN msgestionC.dbo.marcas m ON m.codigo = a.marca
            WHERE a.marca NOT IN (1316, 1317, 1158, 436)
            GROUP BY a.marca, RTRIM(m.descripcion)
            HAVING COUNT(*) >= 3
            ORDER BY factor_quiebre_prom DESC
        """)
        cols4 = [d[0] for d in cur.description]
        results["q4_quiebre"] = [dict(zip(cols4, row)) for row in cur.fetchall()]
        print(f"  -> {len(results['q4_quiebre'])} marcas")
    except Exception as e:
        print(f"  -> vel_real_articulo no disponible: {e}")
        results["q4_quiebre"] = None

    conn.close()

    def default_handler(o):
        if isinstance(o, Decimal):
            return float(o)
        if hasattr(o, 'isoformat'):
            return o.isoformat()
        try:
            return float(o)
        except:
            return str(o)

    out = os.path.join(os.path.dirname(__file__), "bcg_data.json")
    with open(out, "w") as f:
        json.dump(results, f, default=default_handler, indent=2)
    print(f"\nDatos guardados en {out}")

if __name__ == "__main__":
    run()
