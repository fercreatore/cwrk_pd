#!/usr/bin/env python3
"""
backtesting_batch.py — Backtesting masivo de familias top
=========================================================
Genera reportes de backtesting para las top 40 familias por ventas,
distribuidas entre categorías (deportivo, sandalia, casual, infantil, medias).

EJECUTAR en Mac:
  cd ~/Desktop/cowork_pedidos
  python3 _scripts_oneshot/backtesting_batch.py

Genera: _informes/backtesting/[CSR]_resultado.md por cada familia.
"""

import os
import sys
import platform
from datetime import date, timedelta
from collections import defaultdict

if platform.system() != "Windows":
    ssl_conf = os.path.join(os.path.dirname(__file__), "openssl_legacy.cnf")
    if not os.path.exists(ssl_conf):
        ssl_conf = "/tmp/openssl_legacy.cnf"
    os.environ["OPENSSL_CONF"] = ssl_conf

import pyodbc
import pandas as pd
from dateutil.relativedelta import relativedelta

# ── Conexión ──
SERVIDOR = "192.168.2.111"
DRIVER = "ODBC Driver 17 for SQL Server"
CONN_STR = (
    f"DRIVER={{{DRIVER}}};SERVER={SERVIDOR};DATABASE=msgestionC;"
    f"UID=am;PWD=dl;Connection Timeout=30;TrustServerCertificate=yes;Encrypt=no;"
)
EXCL_VENTAS = "(7,36)"
EXCL_MARCAS = "(1316,1317,1158,436)"
DEPOS_SQL = "(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)"
MESES_OI = [4, 5, 6, 7, 8, 9]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '_informes', 'backtesting')

# CSRs que ya tienen reporte (prefijos 8 dígitos de los archivos existentes)
EXISTENTES = {'65611016', '63471130', '65610998', '64171000',
              '09615110', '23649500', '11855000', '08727000', '66821872'}

# Mapeo subrubro → categoría para distribución
CATEGORIA_MAP = {
    12: 'SANDALIA', 13: 'ZUECO/CROCS', 20: 'CASUAL', 27: 'PLANTILLA',
    29: 'MEDIAS', 32: 'ACCESORIO', 48: 'DEPORTIVO', 49: 'DANZA',
    51: 'BOTA', 53: 'CASUAL', 57: 'TEXTIL', 66: 'ACCESORIO',
}

RUBRO_GENERO = {1: 'DAMAS', 3: 'HOMBRES', 4: 'NIÑOS', 5: 'NIÑAS', 6: 'UNISEX'}


def get_conn():
    return pyodbc.connect(CONN_STR, timeout=30)


def query_df(sql, conn):
    return pd.read_sql(sql, conn)


def generar_reporte(csr, info, df_hist, df_compras_hist, df_stock_m, conn):
    """Genera un reporte de backtesting completo para una familia."""
    desc = info.get('descripcion', csr)
    marca = info.get('marca_nombre', str(info.get('marca', '?')))
    subrubro = info.get('subrubro', 0)
    cat = CATEGORIA_MAP.get(subrubro, 'OTRO')
    stock_actual = info.get('stock_actual', 0)

    # ── Serie histórica por año/mes ──
    hist = df_hist[df_hist['csr'] == csr].copy()
    if hist.empty:
        return None

    # Pivot año × mes
    hist['anio'] = hist['anio'].astype(int)
    hist['mes'] = hist['mes'].astype(int)
    hist['pares'] = hist['pares'].astype(float).fillna(0)
    pivot = hist.pivot_table(index='anio', columns='mes', values='pares',
                             aggfunc='sum', fill_value=0)
    for m in range(1, 13):
        if m not in pivot.columns:
            pivot[m] = 0
    pivot = pivot[range(1, 13)]
    pivot['Total'] = pivot.sum(axis=1)

    # ── Factores estacionales (3+ años) ──
    anios_completos = [a for a in pivot.index if a >= 2022 and a <= 2025]
    if len(anios_completos) < 2:
        anios_completos = list(pivot.index)[-3:]

    if anios_completos:
        promedios_mes = {}
        for m in range(1, 13):
            vals = [float(pivot.loc[a, m]) for a in anios_completos if a in pivot.index]
            promedios_mes[m] = sum(vals) / max(len(vals), 1)
        media_global = sum(promedios_mes.values()) / 12
        if media_global > 0:
            factores = {m: round(promedios_mes[m] / media_global, 3) for m in range(1, 13)}
        else:
            factores = {m: 1.0 for m in range(1, 13)}
    else:
        factores = {m: 1.0 for m in range(1, 13)}
        media_global = 0

    # ── Ventas OI por año ──
    oi_por_anio = {}
    for a in sorted(pivot.index):
        oi = sum(float(pivot.loc[a, m]) for m in MESES_OI if m in pivot.columns)
        if oi > 0:
            oi_por_anio[a] = oi

    # ── Quiebre pre-OI2024 (abr2023-mar2024) ──
    comp_hist = df_compras_hist[df_compras_hist['csr'] == csr].copy()
    comp_dict = {}
    if not comp_hist.empty:
        for _, r in comp_hist.iterrows():
            comp_dict[(int(r['anio']), int(r['mes']))] = float(r['pares'] or 0)

    vtas_dict = {}
    for _, r in hist.iterrows():
        vtas_dict[(int(r['anio']), int(r['mes']))] = float(r['pares'] or 0)

    # Reconstruir stock hacia atrás desde stock actual hasta abr-2023
    hoy = date.today()

    # Ir desde hoy hacia atrás hasta llegar a mar-2024, reconstruyendo stock
    stock_rec = float(stock_actual)
    cursor_back = hoy.replace(day=1)
    while (cursor_back.year, cursor_back.month) > (2024, 3):
        v = vtas_dict.get((cursor_back.year, cursor_back.month), 0)
        c = comp_dict.get((cursor_back.year, cursor_back.month), 0)
        stock_rec = stock_rec + v - c
        cursor_back -= relativedelta(months=1)

    # Ahora stock_rec es el stock al inicio de mar-2024
    # Período de análisis: mar-2024 hacia atrás 12 meses
    meses_12 = []
    cursor = date(2024, 3, 1)
    for _ in range(12):
        meses_12.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)
    meses_q = 0
    meses_ok = 0
    ventas_ok = 0
    ventas_total = 0
    ventas_desest = 0
    quiebre_detalle = []

    for anio, mes in meses_12:
        v = vtas_dict.get((anio, mes), 0)
        c = comp_dict.get((anio, mes), 0)
        stock_inicio = stock_rec + v - c
        ventas_total += v
        estado = 'QUEBRADO' if stock_inicio <= 0 else 'OK'

        if stock_inicio <= 0:
            meses_q += 1
        else:
            meses_ok += 1
            ventas_ok += v
            s_t = max(factores.get(mes, 1.0), 0.1)
            ventas_desest += v / s_t

        quiebre_detalle.append({
            'anio': anio, 'mes': mes, 'ventas': v, 'compras': c,
            'stock_inicio': stock_inicio, 'estado': estado
        })
        stock_rec = stock_inicio

    pct_quiebre = meses_q / 12
    vel_ap = ventas_total / 12

    # vel_real v3
    if meses_ok > 0:
        vel_base = ventas_desest / meses_ok
    elif ventas_total > 0:
        vel_base = vel_ap * 1.15
    else:
        vel_base = 0

    if pct_quiebre > 0.5:
        factor_disp = 1.20
    elif pct_quiebre > 0.3:
        factor_disp = 1.10
    else:
        factor_disp = 1.0

    vel_real_v3 = vel_base * factor_disp

    # ── Simulación OI2024 ──
    demanda_proy = {}
    for m in MESES_OI:
        demanda_proy[m] = round(vel_real_v3 * factores.get(m, 1.0), 1)
    total_proy = round(sum(demanda_proy.values()))

    # Ventas reales OI2024
    ventas_oi24_real = {}
    total_real = 0
    for m in MESES_OI:
        v = vtas_dict.get((2024, m), 0)
        ventas_oi24_real[m] = v
        total_real += v

    # Error
    if total_real > 0:
        error_total = (total_proy - total_real) / total_real * 100
        mape_mensual = []
        for m in MESES_OI:
            if ventas_oi24_real.get(m, 0) > 0:
                err = abs(demanda_proy.get(m, 0) - ventas_oi24_real[m]) / ventas_oi24_real[m]
                mape_mensual.append(err)
        mape = round(sum(mape_mensual) / max(len(mape_mensual), 1) * 100, 1) if mape_mensual else 0
    else:
        error_total = 0
        mape = 0

    # ── Compras reales OI2024 ──
    compras_oi24 = sum(comp_dict.get((2024, m), 0) for m in range(1, 10))

    # ── Generar markdown ──
    lines = []
    lines.append(f"# Backtesting: {desc[:50]} (familia {csr})")
    lines.append(f"\n> Marca: {marca} | Categoria: {cat}")
    lines.append(f"> Stock actual: {stock_actual:.0f} pares (mar-2026)")
    lines.append(f"> Generado automaticamente: {date.today()}")
    lines.append(f"\n---\n")

    # Serie histórica
    lines.append(f"## Serie historica\n")
    header = "| Anio |" + "|".join(f" {m:>3} " for m in range(1, 13)) + "| Total |"
    sep = "|------|" + "|".join("-----" for _ in range(12)) + "|-------|"
    lines.append(header)
    lines.append(sep)
    for a in sorted(pivot.index):
        vals = "|".join(f" {int(pivot.loc[a, m]):>3} " if pivot.loc[a, m] > 0 else "   - "
                        for m in range(1, 13))
        lines.append(f"| {a} |{vals}| {int(pivot.loc[a, 'Total']):>5} |")

    total_hist = int(pivot['Total'].sum())
    anio_min = int(pivot.index.min())
    anio_max = int(pivot.index.max())
    lines.append(f"\n**Total historico: {total_hist} pares ({anio_min}-{anio_max})**\n")

    # Ventas OI por año
    if len(oi_por_anio) > 1:
        lines.append(f"### Ventas OI (abr-sep) por anio\n")
        lines.append(f"| Anio | OI pares | vs anterior |")
        lines.append(f"|------|----------|-------------|")
        prev = None
        for a in sorted(oi_por_anio.keys()):
            oi = oi_por_anio[a]
            if prev and prev > 0:
                cambio = f"{(oi/prev - 1)*100:+.1f}%"
            else:
                cambio = "-"
            lines.append(f"| {a} | {oi:>8.0f} | {cambio:>11} |")
            prev = oi
        lines.append("")

    # Factor estacional
    lines.append(f"---\n\n## Factor estacional\n")
    lines.append(f"Calculado sobre {len(anios_completos)} anios ({min(anios_completos)}-{max(anios_completos)}). "
                 f"Promedio mensual = {media_global:.1f} pares/mes.\n")
    lines.append(f"| Mes | Prom mensual | Factor s_t | Rol |")
    lines.append(f"|-----|-------------|------------|-----|")
    mes_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                   'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    for m in range(1, 13):
        f = factores[m]
        prom = promedios_mes.get(m, 0)
        if f >= 2.0:
            rol = "**PICO**"
        elif f >= 1.5:
            rol = "Temporada alta"
        elif f >= 0.8:
            rol = "Normal"
        elif f >= 0.3:
            rol = "Bajo"
        else:
            rol = "Valle"
        lines.append(f"| {mes_nombres[m-1]} | {prom:>11.1f} | {f:>10.3f} | {rol} |")

    # Concentración
    vtas_oi_prom = sum(promedios_mes.get(m, 0) for m in MESES_OI)
    vtas_total_prom = sum(promedios_mes.values())
    if vtas_total_prom > 0:
        pct_oi = vtas_oi_prom / vtas_total_prom * 100
        lines.append(f"\n**Concentracion OI (abr-sep)**: {pct_oi:.0f}% de las ventas anuales.\n")

    # Quiebre
    lines.append(f"---\n\n## Analisis de quiebre pre-OI2024\n")
    lines.append(f"| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |")
    lines.append(f"|-----|--------|---------|---------------------|--------|")
    for qd in quiebre_detalle:
        mn = mes_nombres[qd['mes']-1]
        lines.append(f"| {mn} {qd['anio']} | {qd['ventas']:>6.0f} | {qd['compras']:>7.0f} | "
                      f"{qd['stock_inicio']:>19.0f} | {qd['estado']} |")

    lines.append(f"\n- **Meses quebrados: {meses_q} de 12 ({pct_quiebre*100:.0f}%)**")
    lines.append(f"- vel_aparente = {vel_ap:.1f} pares/mes")
    lines.append(f"- vel_real v3 (desest. + disp.) = **{vel_real_v3:.1f} pares/mes**")
    lines.append(f"- Factor disponibilidad: {factor_disp}")

    # Simulación OI2024
    lines.append(f"\n---\n\n## Simulacion OI2024\n")
    lines.append(f"### Proyeccion con modelo v3\n")
    lines.append(f"| Mes | Factor s_t | Demanda proyectada | Real | Error |")
    lines.append(f"|-----|-----------|-------------------|------|-------|")
    for m in MESES_OI:
        proy = demanda_proy.get(m, 0)
        real = ventas_oi24_real.get(m, 0)
        if real > 0:
            err = f"{(proy - real) / real * 100:+.0f}%"
        elif proy > 0:
            err = "N/A (0 real)"
        else:
            err = "-"
        lines.append(f"| {mes_nombres[m-1]} | {factores[m]:>9.2f} | {proy:>17.0f} | {real:>4.0f} | {err} |")

    lines.append(f"| **Total** | | **{total_proy}** | **{total_real:.0f}** | "
                 f"**{error_total:+.1f}%** |")

    # Error cuantificado
    lines.append(f"\n---\n\n## Error cuantificado\n")
    lines.append(f"| Metrica | Modelo v3 | Real | Error |")
    lines.append(f"|---------|-----------|------|-------|")
    lines.append(f"| Demanda OI2024 | {total_proy} | {total_real:.0f} | {error_total:+.1f}% |")
    if compras_oi24 > 0:
        lines.append(f"| Compras reales | - | {compras_oi24:.0f} | - |")
    lines.append(f"| MAPE mensual | | | **{mape:.1f}%** |")
    lines.append(f"| Quiebre pre-OI | | | {pct_quiebre*100:.0f}% meses |")

    # Clasificación del error
    if mape <= 15:
        calidad = "EXCELENTE (<15%)"
    elif mape <= 25:
        calidad = "BUENO (15-25%)"
    elif mape <= 40:
        calidad = "REGULAR (25-40%)"
    else:
        calidad = "POBRE (>40%)"
    lines.append(f"\n**Calidad modelo v3: {calidad}**\n")

    # Propuesta de mejora
    lines.append(f"---\n\n## Propuesta de mejora\n")
    if pct_quiebre > 0.7:
        lines.append(f"1. **Quiebre cronico ({pct_quiebre*100:.0f}%)**: "
                     f"Priorizar reposicion urgente. La vel_real se calcula con pocos meses de datos.")
    if mape > 25:
        lines.append(f"2. **MAPE alto ({mape:.0f}%)**: Revisar si hay redistribucion intra-temporada "
                     f"o si el producto tiene tendencia fuerte (CAGR).")
    if len(oi_por_anio) >= 3:
        anios_oi = sorted(oi_por_anio.keys())
        if len(anios_oi) >= 2:
            last = oi_por_anio[anios_oi[-1]]
            prev_v = oi_por_anio[anios_oi[-2]]
            if prev_v > 0:
                cagr = (last / prev_v) - 1
                if abs(cagr) > 0.2:
                    lines.append(f"3. **Tendencia interanual**: CAGR OI = {cagr*100:+.0f}% "
                                 f"({anios_oi[-2]}→{anios_oi[-1]}). "
                                 f"{'Producto en crecimiento.' if cagr > 0 else 'Producto en baja.'}")

    lines.append(f"\n### Timing optimo")
    lines.append(f"Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).")

    return '\n'.join(lines), {
        'csr': csr, 'desc': desc[:40], 'marca': marca, 'cat': cat,
        'total_proy': total_proy, 'total_real': total_real,
        'error': error_total, 'mape': mape, 'pct_quiebre': pct_quiebre * 100,
    }


def main():
    print("Conectando a SQL Server 192.168.2.111...")
    conn = get_conn()
    print("OK\n")

    # 1. Top 60 familias por ventas 2 años
    print("1/4 — Consultando top familias por ventas...")
    sql_top = f"""
        SELECT TOP 60 LEFT(a.codigo_sinonimo, 10) AS csr,
               MAX(a.descripcion_1) AS descripcion,
               MAX(a.marca) AS marca, MAX(a.subrubro) AS subrubro,
               MAX(a.rubro) AS rubro, MAX(a.proveedor) AS proveedor,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS ventas_2a
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.marca NOT IN {EXCL_MARCAS} AND a.marca > 0
          AND a.estado = 'V' AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
          AND v.fecha >= DATEADD(year, -2, GETDATE())
        GROUP BY LEFT(a.codigo_sinonimo, 10)
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) > 50
        ORDER BY ventas_2a DESC
    """
    df_top = query_df(sql_top, conn)
    df_top['csr'] = df_top['csr'].str.strip()
    print(f"   {len(df_top)} familias encontradas")

    # Excluir existentes
    df_top = df_top[~df_top['csr'].apply(lambda c: c[:8] in EXISTENTES)]
    print(f"   {len(df_top)} después de excluir existentes")

    # Seleccionar top 40 con distribución por categoría
    df_top['cat'] = df_top['subrubro'].map(CATEGORIA_MAP).fillna('OTRO')
    selected = []
    max_per_cat = {'MEDIAS': 15, 'DEPORTIVO': 6, 'SANDALIA': 5, 'CASUAL': 5,
                   'ZUECO/CROCS': 3, 'DANZA': 3, 'ACCESORIO': 3, 'OTRO': 5,
                   'PLANTILLA': 2, 'TEXTIL': 2, 'BOTA': 2}
    cat_count = defaultdict(int)
    for _, r in df_top.iterrows():
        cat = r['cat']
        limit = max_per_cat.get(cat, 3)
        if cat_count[cat] < limit and len(selected) < 40:
            selected.append(r['csr'])
            cat_count[cat] += 1

    print(f"   {len(selected)} familias seleccionadas: {dict(cat_count)}")

    # Nombres de marca
    sql_marcas = "SELECT codigo, RTRIM(descripcion) AS nombre FROM msgestionC.dbo.marcas"
    marca_nombres = dict(query_df(sql_marcas, conn).values)

    # Stock actual
    print("2/4 — Stock actual...")
    filtro_sel = ",".join(f"'{c}'" for c in selected)
    sql_stock = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(s.stock_actual) AS stock_actual
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE LEFT(a.codigo_sinonimo, 10) IN ({filtro_sel})
          AND s.deposito IN {DEPOS_SQL}
        GROUP BY LEFT(a.codigo_sinonimo, 10)
    """
    df_stk = query_df(sql_stock, conn)
    stock_dict = {}
    for _, r in df_stk.iterrows():
        stock_dict[r['csr'].strip()] = float(r['stock_actual'] or 0)

    # 3. Serie histórica completa (ventas mensuales, todos los años)
    print("3/4 — Serie historica completa...")
    sql_hist = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND LEFT(a.codigo_sinonimo, 10) IN ({filtro_sel})
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(v.fecha), MONTH(v.fecha)
    """
    df_hist = query_df(sql_hist, conn)
    df_hist['csr'] = df_hist['csr'].str.strip()

    # Compras históricas
    sql_comp = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes,
               SUM(rc.cantidad) AS pares
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+'
          AND LEFT(a.codigo_sinonimo, 10) IN ({filtro_sel})
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(rc.fecha), MONTH(rc.fecha)
    """
    df_comp = query_df(sql_comp, conn)
    df_comp['csr'] = df_comp['csr'].str.strip()

    conn.close()
    print("   Datos cargados.\n")

    # 4. Generar reportes
    print("4/4 — Generando reportes...\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    resultados = []
    for i, csr in enumerate(selected, 1):
        r = df_top[df_top['csr'] == csr].iloc[0]
        info = {
            'descripcion': r['descripcion'] if isinstance(r['descripcion'], str) else '',
            'marca': int(r['marca']),
            'marca_nombre': marca_nombres.get(int(r['marca']), str(r['marca'])),
            'subrubro': int(r['subrubro']) if pd.notna(r['subrubro']) else 0,
            'stock_actual': stock_dict.get(csr, 0),
        }

        result = generar_reporte(csr, info, df_hist, df_comp, None, None)
        if result is None:
            print(f"   [{i}/{len(selected)}] {csr} — sin datos históricos, skip")
            continue

        md_content, metrics = result
        fname = f"{csr[:8]}_resultado.md"
        fpath = os.path.join(OUTPUT_DIR, fname)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        resultados.append(metrics)
        emoji = '✅' if metrics['mape'] <= 15 else ('⚠️' if metrics['mape'] <= 25 else '❌')
        print(f"   [{i}/{len(selected)}] {emoji} {csr} {metrics['desc'][:25]} — "
              f"MAPE {metrics['mape']:.0f}% | Error {metrics['error']:+.0f}% | "
              f"Quiebre {metrics['pct_quiebre']:.0f}%")

    # Resumen
    print(f"\n{'='*60}")
    print(f"RESUMEN: {len(resultados)} reportes generados en {OUTPUT_DIR}")
    if resultados:
        df_res = pd.DataFrame(resultados)
        excelentes = len(df_res[df_res['mape'] <= 15])
        buenos = len(df_res[(df_res['mape'] > 15) & (df_res['mape'] <= 25)])
        regulares = len(df_res[(df_res['mape'] > 25) & (df_res['mape'] <= 40)])
        pobres = len(df_res[df_res['mape'] > 40])
        print(f"  Excelentes (<15% MAPE): {excelentes}")
        print(f"  Buenos (15-25% MAPE): {buenos}")
        print(f"  Regulares (25-40% MAPE): {regulares}")
        print(f"  Pobres (>40% MAPE): {pobres}")
        print(f"  MAPE promedio: {df_res['mape'].mean():.1f}%")
        print(f"  Error total promedio: {df_res['error'].mean():+.1f}%")


if __name__ == "__main__":
    main()
