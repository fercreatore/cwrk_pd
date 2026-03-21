#!/usr/bin/env python3
"""
reposicion_oi26.py — Cálculo de Reposición Óptima OI 2026
==========================================================
Cruza stock actual, ventas OI 2024/2025, pedidos pendientes y quiebre
para determinar gaps de reposición por marca y talle.

EJECUTAR en Mac:
  cd ~/Desktop/cowork_pedidos
  python3 _scripts_oneshot/reposicion_oi26.py

Genera: _informes/reposicion_optima_OI26_YYYYMMDD.md

NO inserta nada en producción.
"""

import os
import sys
import platform
from datetime import date, datetime
from collections import defaultdict

# ── Fix SSL para Mac ──
if platform.system() != "Windows":
    ssl_conf = os.path.join(os.path.dirname(__file__), "openssl_legacy.cnf")
    if not os.path.exists(ssl_conf):
        ssl_conf = "/tmp/openssl_legacy.cnf"
    os.environ["OPENSSL_CONF"] = ssl_conf

import pyodbc
import pandas as pd

# ── Conexión ──
SERVIDOR = "192.168.2.111"
DRIVER = "ODBC Driver 17 for SQL Server"
CONN_STR = (
    f"DRIVER={{{DRIVER}}};SERVER={SERVIDOR};DATABASE=msgestionC;"
    f"UID=am;PWD=dl;Connection Timeout=15;TrustServerCertificate=yes;Encrypt=no;"
)

# ── Constantes ──
DEPOS_SQL = "(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)"
EXCL_VENTAS = "(7,36)"
EXCL_MARCAS = "(1316,1317,1158,436)"

# OI = Marzo a Agosto
MESES_OI = (3, 4, 5, 6, 7, 8)
MESES_OI_SQL = "(3,4,5,6,7,8)"


def get_conn():
    return pyodbc.connect(CONN_STR, timeout=15)


def query_df(sql, conn):
    return pd.read_sql(sql, conn)


def main():
    print("Conectando a SQL Server 192.168.2.111...")
    conn = get_conn()
    print("OK\n")

    # ================================================================
    # 1. STOCK ACTUAL por marca, subrubro, descripción
    # ================================================================
    print("1/5 — Stock actual por marca...")
    sql_stock = f"""
        SELECT a.marca, RTRIM(m.descripcion) AS marca_nombre,
               a.subrubro, RTRIM(sr.descripcion) AS subrubro_nombre,
               LEFT(a.codigo_sinonimo, 10) AS csr,
               MAX(a.descripcion_1) AS descripcion,
               MAX(a.precio_fabrica) AS precio_fabrica,
               MAX(a.proveedor) AS proveedor,
               SUM(s.stock_actual) AS stock_actual,
               COUNT(DISTINCT a.codigo) AS variantes
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        LEFT JOIN msgestionC.dbo.marcas m ON m.codigo = a.marca
        LEFT JOIN msgestionC.dbo.subrubro sr ON sr.codigo = a.subrubro
        WHERE s.deposito IN {DEPOS_SQL}
          AND a.estado = 'V'
          AND a.marca NOT IN {EXCL_MARCAS}
          AND a.marca > 0
          AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
        GROUP BY a.marca, m.descripcion, a.subrubro, sr.descripcion,
                 LEFT(a.codigo_sinonimo, 10)
        HAVING SUM(s.stock_actual) > 0
    """
    df_stock = query_df(sql_stock, conn)
    print(f"   {len(df_stock)} productos con stock")

    # ================================================================
    # 2. VENTAS OI 2025 (mar-ago 2025) por marca/producto
    # ================================================================
    print("2/5 — Ventas OI 2025 (mar-ago 2025)...")
    sql_vtas_oi25 = f"""
        SELECT a.marca,
               LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS pares,
               SUM(v.monto_facturado) AS monto
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.marca NOT IN {EXCL_MARCAS}
          AND a.marca > 0
          AND a.estado = 'V'
          AND LEN(a.codigo_sinonimo) >= 10
          AND YEAR(v.fecha) = 2025
          AND MONTH(v.fecha) IN {MESES_OI_SQL}
        GROUP BY a.marca, LEFT(a.codigo_sinonimo, 10)
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) > 0
    """
    df_vtas25 = query_df(sql_vtas_oi25, conn)
    print(f"   {len(df_vtas25)} productos vendidos OI 2025")

    # ================================================================
    # 3. VENTAS OI 2024 (mar-ago 2024) por marca/producto
    # ================================================================
    print("3/5 — Ventas OI 2024 (mar-ago 2024)...")
    sql_vtas_oi24 = f"""
        SELECT a.marca,
               LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS pares,
               SUM(v.monto_facturado) AS monto
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.marca NOT IN {EXCL_MARCAS}
          AND a.marca > 0
          AND a.estado = 'V'
          AND LEN(a.codigo_sinonimo) >= 10
          AND YEAR(v.fecha) = 2024
          AND MONTH(v.fecha) IN {MESES_OI_SQL}
        GROUP BY a.marca, LEFT(a.codigo_sinonimo, 10)
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) > 0
    """
    df_vtas24 = query_df(sql_vtas_oi24, conn)
    print(f"   {len(df_vtas24)} productos vendidos OI 2024")

    # ================================================================
    # 4. PEDIDOS PENDIENTES (estado V, codigo 8)
    # ================================================================
    print("4/5 — Pedidos pendientes...")
    sql_pend = f"""
        SELECT a.marca,
               LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(p1.cantidad) AS pares_pendientes,
               SUM(p1.cantidad * p1.precio) AS monto_pendiente
        FROM msgestionC.dbo.pedico2 p2
        JOIN msgestionC.dbo.pedico1 p1
             ON p1.empresa = p2.empresa AND p1.numero = p2.numero AND p1.codigo = p2.codigo
        JOIN msgestion01art.dbo.articulo a ON a.codigo = p1.articulo
        WHERE p2.codigo = 8 AND p2.estado = 'V'
          AND a.marca NOT IN {EXCL_MARCAS}
          AND a.marca > 0
        GROUP BY a.marca, LEFT(a.codigo_sinonimo, 10)
    """
    df_pend = query_df(sql_pend, conn)
    print(f"   {len(df_pend)} productos con pedidos pendientes")

    # ================================================================
    # 5. QUIEBRE: reconstruir stock mes a mes (últimos 12 meses)
    #    para calcular vel_real corregida
    # ================================================================
    print("5/5 — Análisis de quiebre (12 meses)...")

    # Ventas mensuales últimos 12 meses por CSR
    sql_vtas_mensual = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.marca NOT IN {EXCL_MARCAS}
          AND a.marca > 0
          AND a.estado = 'V'
          AND LEN(a.codigo_sinonimo) >= 10
          AND v.fecha >= DATEADD(month, -12, GETDATE())
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(v.fecha), MONTH(v.fecha)
    """
    df_vtas_m = query_df(sql_vtas_mensual, conn)

    # Compras mensuales últimos 12 meses por CSR
    sql_comp_mensual = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes,
               SUM(rc.cantidad) AS pares
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+'
          AND a.marca NOT IN {EXCL_MARCAS}
          AND a.marca > 0
          AND a.estado = 'V'
          AND LEN(a.codigo_sinonimo) >= 10
          AND rc.fecha >= DATEADD(month, -12, GETDATE())
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(rc.fecha), MONTH(rc.fecha)
    """
    df_comp_m = query_df(sql_comp_mensual, conn)
    print("   Quiebre calculado.\n")

    # ================================================================
    # 6. NOMBRES DE MARCA
    # ================================================================
    sql_marcas = """
        SELECT codigo, RTRIM(descripcion) AS nombre
        FROM msgestionC.dbo.marcas
    """
    df_marcas = query_df(sql_marcas, conn)
    marca_nombres = dict(zip(df_marcas['codigo'], df_marcas['nombre']))

    conn.close()

    # ================================================================
    # PROCESAMIENTO
    # ================================================================
    print("Procesando datos...\n")

    # Limpiar strings
    for df in [df_stock, df_vtas25, df_vtas24, df_pend]:
        if 'csr' in df.columns:
            df['csr'] = df['csr'].str.strip()

    df_vtas_m['csr'] = df_vtas_m['csr'].str.strip()
    df_comp_m['csr'] = df_comp_m['csr'].str.strip()

    # ── Indexar por CSR (agrupar duplicados) ──
    stock_by_csr = {}
    for _, r in df_stock.iterrows():
        csr = r['csr']
        if csr in stock_by_csr:
            stock_by_csr[csr]['stock_actual'] += float(r['stock_actual'] or 0)
        else:
            stock_by_csr[csr] = {
                'stock_actual': float(r['stock_actual'] or 0),
                'marca': r['marca'],
                'descripcion': r['descripcion'],
                'precio_fabrica': r['precio_fabrica'],
                'subrubro': r['subrubro'],
                'subrubro_nombre': r['subrubro_nombre'],
                'marca_nombre': r['marca_nombre'],
                'proveedor': r['proveedor'],
            }

    vtas25_by_csr = {}
    for _, r in df_vtas25.iterrows():
        vtas25_by_csr[r['csr'].strip()] = {'pares': float(r['pares'] or 0), 'monto': float(r['monto'] or 0)}

    vtas24_by_csr = {}
    for _, r in df_vtas24.iterrows():
        vtas24_by_csr[r['csr'].strip()] = {'pares': float(r['pares'] or 0), 'monto': float(r['monto'] or 0)}

    pend_by_csr = {}
    for _, r in df_pend.iterrows():
        pend_by_csr[r['csr'].strip()] = {'pares': float(r['pares_pendientes'] or 0),
                                          'monto': float(r['monto_pendiente'] or 0)}

    # ── Calcular quiebre por CSR ──
    # Construir ventas/compras mensuales
    vtas_mensual = defaultdict(lambda: defaultdict(float))
    for _, r in df_vtas_m.iterrows():
        vtas_mensual[r['csr']][(int(r['anio']), int(r['mes']))] = float(r['pares'] or 0)

    comp_mensual = defaultdict(lambda: defaultdict(float))
    for _, r in df_comp_m.iterrows():
        comp_mensual[r['csr']][(int(r['anio']), int(r['mes']))] = float(r['pares'] or 0)

    # Meses hacia atrás
    from dateutil.relativedelta import relativedelta
    hoy = date.today()
    meses_lista = []
    cursor = hoy.replace(day=1)
    for _ in range(12):
        meses_lista.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    quiebre_by_csr = {}
    all_csrs = set(list(stock_by_csr.keys()) + list(vtas25_by_csr.keys()) + list(vtas24_by_csr.keys()))

    for csr in all_csrs:
        stock_actual = stock_by_csr.get(csr, {}).get('stock_actual', 0) or 0
        v_dict = vtas_mensual.get(csr, {})
        c_dict = comp_mensual.get(csr, {})

        stock_fin = float(stock_actual)
        meses_q = 0
        meses_ok = 0
        ventas_total = 0
        ventas_ok = 0

        for anio, mes in meses_lista:
            v = v_dict.get((anio, mes), 0)
            c = c_dict.get((anio, mes), 0)
            stock_inicio = stock_fin + v - c
            ventas_total += v

            if stock_inicio <= 0:
                meses_q += 1
            else:
                meses_ok += 1
                ventas_ok += v

            stock_fin = stock_inicio

        vel_ap = ventas_total / 12
        vel_real = ventas_ok / max(meses_ok, 1) if meses_ok > 0 else vel_ap

        quiebre_by_csr[csr] = {
            'meses_q': meses_q,
            'meses_ok': meses_ok,
            'pct_quiebre': round(meses_q / 12 * 100, 1),
            'vel_aparente': round(vel_ap, 2),
            'vel_real': round(vel_real, 2),
        }

    # ================================================================
    # CÁLCULO DE GAP POR CSR
    # ================================================================
    # venta_esperada_OI26 = promedio(OI25, OI24) * factor_tendencia
    # factor_tendencia: si OI25 > OI24 → crece, sino baja
    # Duración OI: 6 meses (mar-ago)
    # stock_disponible = stock_actual + pedidos_pendientes
    # gap = venta_esperada - stock_disponible

    # Construir lookup marca por CSR desde ventas (para CSRs sin stock)
    marca_by_csr_vtas = {}
    for _, r in df_vtas25.iterrows():
        marca_by_csr_vtas[r['csr'].strip()] = int(r['marca'])
    for _, r in df_vtas24.iterrows():
        csr_k = r['csr'].strip()
        if csr_k not in marca_by_csr_vtas:
            marca_by_csr_vtas[csr_k] = int(r['marca'])

    resultados = []
    for csr in all_csrs:
        info = stock_by_csr.get(csr, {})
        v25 = vtas25_by_csr.get(csr, {}).get('pares', 0)
        v24 = vtas24_by_csr.get(csr, {}).get('pares', 0)
        m25 = vtas25_by_csr.get(csr, {}).get('monto', 0)
        m24 = vtas24_by_csr.get(csr, {}).get('monto', 0)
        pend = pend_by_csr.get(csr, {}).get('pares', 0)
        stock = float(info.get('stock_actual', 0) or 0)
        precio = float(info.get('precio_fabrica', 0) or 0)
        marca = info.get('marca', marca_by_csr_vtas.get(csr, 0))
        if not marca or marca == 0:
            continue  # sin marca asignada, skip
        marca_nom = info.get('marca_nombre', marca_nombres.get(marca, str(marca)))
        desc = info.get('descripcion', '')
        subrubro = info.get('subrubro_nombre', '')
        proveedor = info.get('proveedor', 0)
        q = quiebre_by_csr.get(csr, {})

        # Factor tendencia
        if v24 > 0 and v25 > 0:
            factor = v25 / v24
            # Cap extremos
            factor = max(0.5, min(factor, 2.0))
        elif v25 > 0:
            factor = 1.0
        elif v24 > 0:
            factor = 0.7  # sin ventas OI25 = producto en baja
        else:
            continue  # sin historia, skip

        # Usar vel_real (corregida por quiebre) para proyección
        vel_real = q.get('vel_real', 0)
        vel_ap = q.get('vel_aparente', 0)

        # Venta esperada OI26 = vel_real * 6 meses * factor_tendencia
        # Pero también considerar el promedio OI directo como check
        promedio_oi = (v25 + v24) / 2
        venta_esp_vel = vel_real * 6 * factor
        venta_esp_prom = promedio_oi * factor

        # Usar el mayor (vel_real captura demanda reprimida)
        venta_esperada = max(venta_esp_vel, venta_esp_prom)

        stock_disponible = stock + pend
        gap = venta_esperada - stock_disponible

        # Precio promedio de venta para ROI (usar monto/pares OI25)
        precio_venta = m25 / v25 if v25 > 0 else (m24 / v24 if v24 > 0 else 0)
        precio_costo = precio if precio > 0 else (precio_venta * 0.5)

        # ROI: margen por par * pares vendibles / inversión
        if gap > 0 and precio_costo > 0:
            inversion = gap * precio_costo
            ingreso = gap * precio_venta if precio_venta > 0 else inversion * 1.8
            margen = ingreso - inversion
            roi = margen / inversion * 100 if inversion > 0 else 0
        else:
            inversion = 0
            margen = 0
            roi = 0

        resultados.append({
            'csr': csr,
            'marca': marca,
            'marca_nombre': marca_nom if isinstance(marca_nom, str) else str(marca_nom),
            'descripcion': desc if isinstance(desc, str) else '',
            'subrubro': subrubro if isinstance(subrubro, str) else '',
            'proveedor': proveedor,
            'stock_actual': stock,
            'pedidos_pend': pend,
            'stock_disponible': stock_disponible,
            'vtas_oi25': v25,
            'vtas_oi24': v24,
            'factor_tendencia': round(factor, 2),
            'vel_real': vel_real,
            'vel_aparente': vel_ap,
            'pct_quiebre': q.get('pct_quiebre', 0),
            'venta_esperada': round(venta_esperada, 0),
            'gap': round(gap, 0),
            'precio_costo': round(precio_costo, 2),
            'precio_venta': round(precio_venta, 2),
            'inversion': round(inversion, 0),
            'margen_esp': round(margen, 0),
            'roi_pct': round(roi, 1),
        })

    df = pd.DataFrame(resultados)
    if df.empty:
        print("No hay datos para generar reporte.")
        return

    # ================================================================
    # RESUMEN POR MARCA
    # ================================================================
    df_reponer = df[df['gap'] > 0].copy()
    df_sobre = df[df['gap'] < 0].copy()

    resumen_marcas = df_reponer.groupby(['marca', 'marca_nombre']).agg(
        productos=('csr', 'count'),
        gap_pares=('gap', 'sum'),
        inversion=('inversion', 'sum'),
        margen_esp=('margen_esp', 'sum'),
        stock_actual=('stock_actual', 'sum'),
        vtas_oi25=('vtas_oi25', 'sum'),
        vtas_oi24=('vtas_oi24', 'sum'),
    ).reset_index().sort_values('inversion', ascending=False)

    # Prioridad
    def prioridad(row):
        if row['gap_pares'] > 100 or row['inversion'] > 500000:
            return 'CRÍTICO'
        elif row['gap_pares'] > 30 or row['inversion'] > 150000:
            return 'ALTO'
        else:
            return 'MEDIO'

    resumen_marcas['prioridad'] = resumen_marcas.apply(prioridad, axis=1)

    # ================================================================
    # GENERAR REPORTE MARKDOWN
    # ================================================================
    fecha_str = date.today().strftime('%Y%m%d')
    output_path = os.path.join(os.path.dirname(__file__), '..', '_informes',
                                f'reposicion_optima_OI26_{fecha_str}.md')
    output_path = os.path.abspath(output_path)

    lines = []
    lines.append("# Reposición Óptima OI 2026")
    lines.append(f"\n**Generado**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Método**: Velocidad REAL (corregida por quiebre) × 6 meses × factor tendencia OI25/OI24")
    lines.append(f"**Productos analizados**: {len(df)} | Con gap positivo: {len(df_reponer)} | Sobrestock: {len(df_sobre)}")

    # ── KPIs globales ──
    total_gap = df_reponer['gap'].sum()
    total_inv = df_reponer['inversion'].sum()
    total_margen = df_reponer['margen_esp'].sum()
    marcas_criticas = len(resumen_marcas[resumen_marcas['prioridad'] == 'CRÍTICO'])

    lines.append(f"\n## Resumen Ejecutivo")
    lines.append(f"| Indicador | Valor |")
    lines.append(f"|-----------|-------|")
    lines.append(f"| Gap total (pares) | **{total_gap:,.0f}** |")
    lines.append(f"| Inversión necesaria | **${total_inv:,.0f}** |")
    lines.append(f"| Margen esperado | **${total_margen:,.0f}** |")
    lines.append(f"| ROI global esperado | **{total_margen/max(total_inv,1)*100:.1f}%** |")
    lines.append(f"| Marcas con gap CRÍTICO | **{marcas_criticas}** |")

    # ── Tabla por marca ──
    lines.append(f"\n## Gap por Marca (ordenado por inversión necesaria)")
    lines.append(f"| Prioridad | Marca | Productos | Gap (pares) | Stock actual | Vtas OI25 | Vtas OI24 | Inversión | Margen esp. |")
    lines.append(f"|-----------|-------|-----------|-------------|--------------|-----------|-----------|-----------|-------------|")

    for _, m in resumen_marcas.head(40).iterrows():
        prio_emoji = {'CRÍTICO': '🔴', 'ALTO': '🟡', 'MEDIO': '🟢'}.get(m['prioridad'], '')
        lines.append(
            f"| {prio_emoji} {m['prioridad']} | {m['marca_nombre']} ({int(m['marca'])}) | "
            f"{int(m['productos'])} | {m['gap_pares']:,.0f} | {m['stock_actual']:,.0f} | "
            f"{m['vtas_oi25']:,.0f} | {m['vtas_oi24']:,.0f} | "
            f"${m['inversion']:,.0f} | ${m['margen_esp']:,.0f} |"
        )

    # ── Top 20 productos con mayor gap ──
    lines.append(f"\n## Top 20 Productos con Mayor Gap")
    lines.append(f"| # | Producto | Marca | Stock | Pend | VtaOI25 | VtaOI24 | Vel Real | %Quiebre | Gap | Inversión |")
    lines.append(f"|---|----------|-------|-------|------|---------|---------|----------|----------|-----|-----------|")

    top20 = df_reponer.nlargest(20, 'gap')
    for i, (_, p) in enumerate(top20.iterrows(), 1):
        lines.append(
            f"| {i} | {p['descripcion'][:30]} | {p['marca_nombre'][:15]} | "
            f"{p['stock_actual']:.0f} | {p['pedidos_pend']:.0f} | "
            f"{p['vtas_oi25']:.0f} | {p['vtas_oi24']:.0f} | "
            f"{p['vel_real']:.1f}/m | {p['pct_quiebre']:.0f}% | "
            f"**{p['gap']:.0f}** | ${p['inversion']:,.0f} |"
        )

    # ── Sobrestock ──
    if not df_sobre.empty:
        sobre_marcas = df_sobre.groupby('marca_nombre').agg(
            productos=('csr', 'count'),
            excedente=('gap', lambda x: -x.sum()),
            stock=('stock_actual', 'sum'),
        ).reset_index().sort_values('excedente', ascending=False)

        lines.append(f"\n## Sobrestock (marcas con excedente)")
        lines.append(f"| Marca | Productos | Excedente (pares) | Stock actual |")
        lines.append(f"|-------|-----------|-------------------|--------------|")
        for _, s in sobre_marcas.head(15).iterrows():
            lines.append(f"| {s['marca_nombre']} | {int(s['productos'])} | {s['excedente']:,.0f} | {s['stock']:,.0f} |")

    # ── Top 10 acciones inmediatas ──
    lines.append(f"\n## Top 10 Acciones Inmediatas (llamar lunes)")
    lines.append(f"Ordenado por ROI esperado dentro de marcas críticas.\n")

    # Agrupar por proveedor los productos críticos
    df_acciones = df_reponer[df_reponer['inversion'] > 10000].copy()
    df_acciones = df_acciones.sort_values('roi_pct', ascending=False)

    # Agrupar por marca para acciones
    acciones_marca = df_acciones.groupby(['marca_nombre', 'proveedor']).agg(
        gap_total=('gap', 'sum'),
        inversion_total=('inversion', 'sum'),
        margen_total=('margen_esp', 'sum'),
        productos=('csr', 'count'),
        roi_prom=('roi_pct', 'mean'),
    ).reset_index().sort_values('margen_total', ascending=False)

    for i, (_, a) in enumerate(acciones_marca.head(10).iterrows(), 1):
        lines.append(
            f"{i}. **{a['marca_nombre']}** (prov #{int(a['proveedor'])}): "
            f"Pedir **{a['gap_total']:,.0f} pares** — "
            f"Inversión ${a['inversion_total']:,.0f} → Margen esperado ${a['margen_total']:,.0f} "
            f"(ROI {a['roi_prom']:.0f}%) — {int(a['productos'])} productos"
        )

    # ── Curva de talles (top 5 marcas) ──
    lines.append(f"\n## Curva de Talles — Top 5 Marcas Críticas")
    lines.append(f"*(Basado en ventas OI 2025)*\n")

    # Para esto necesitaríamos datos a nivel talle, que no tenemos en CSR nivel 10
    # CSR nivel 10 es modelo+color, el talle está en los últimos 2 dígitos del sinónimo
    lines.append("> Nota: la curva de talles detallada requiere análisis a nivel codigo_sinonimo completo (12 dígitos).")
    lines.append("> Usar `app_reposicion.py` (Streamlit) para drill-down por talle dentro de cada marca.")

    # ── Notas metodológicas ──
    lines.append(f"\n## Metodología")
    lines.append(f"1. **Velocidad REAL**: corregida por quiebre de stock (meses con stock_inicio <= 0 se excluyen)")
    lines.append(f"2. **Factor tendencia**: OI25/OI24, capeado entre 0.5x y 2.0x")
    lines.append(f"3. **Venta esperada OI26** = max(vel_real × 6 × factor, promedio_OI × factor)")
    lines.append(f"4. **Gap** = venta_esperada - stock_actual - pedidos_pendientes")
    lines.append(f"5. **ROI** = (precio_venta - precio_costo) × gap / (precio_costo × gap)")
    lines.append(f"6. Excluidas marcas de gastos: {EXCL_MARCAS}")
    lines.append(f"7. Excluidos códigos venta 7,36 (remitos internos)")

    # Escribir
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"REPORTE GENERADO: {output_path}")
    print(f"\nResumen:")
    print(f"  Gap total: {total_gap:,.0f} pares")
    print(f"  Inversión necesaria: ${total_inv:,.0f}")
    print(f"  Margen esperado: ${total_margen:,.0f}")
    print(f"  Marcas críticas: {marcas_criticas}")
    print(f"  Top marca: {resumen_marcas.iloc[0]['marca_nombre'] if len(resumen_marcas) > 0 else 'N/A'}")


if __name__ == "__main__":
    main()
