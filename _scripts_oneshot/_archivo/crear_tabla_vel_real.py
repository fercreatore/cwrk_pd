"""
Genera script SQL para crear y poblar omicronvt.dbo.vel_real_articulo.

Conecta a réplica 112 (solo SELECT), calcula vel_real con la misma lógica
que analizar_quiebre_batch() de app_reposicion.py (algoritmo v3), y genera
un .sql con los INSERTs listos para ejecutar en el 111.

Algoritmo v3 incluye:
  - Desestacionalización mensual (factores calculados por artículo)
  - factor_disp: corrección por demanda latente reprimida
  - Fallback 100% quiebre: vel_aparente × 1.15
  - std_mensual: desvío estándar de meses con stock
  - ventas_perdidas: estimación de ventas en meses quebrados
  - vel_real_con_perdidas: velocidad incluyendo ventas estimadas perdidas

Uso:
    python crear_tabla_vel_real.py              # genera .sql en la misma carpeta
    python crear_tabla_vel_real.py --output /tmp/vel_real.sql
"""
import os
import sys
import argparse
import platform
from datetime import date
from dateutil.relativedelta import relativedelta

import numpy as np
import pyodbc
import pandas as pd

# ── Fix SSL para SQL Server 2012 (TLS 1.0) ──────────────────
_is_windows = platform.system() == "Windows"
if not _is_windows:
    _ssl_conf = "/tmp/openssl_legacy.cnf"
    if not os.path.exists(_ssl_conf):
        with open(_ssl_conf, "w") as _f:
            _f.write(
                "openssl_conf = openssl_init\n"
                "[openssl_init]\nssl_conf = ssl_sect\n"
                "[ssl_sect]\nsystem_default = system_default_sect\n"
                "[system_default_sect]\n"
                "MinProtocol = TLSv1\nCipherString = DEFAULT@SECLEVEL=0\n"
            )
    os.environ.setdefault("OPENSSL_CONF", _ssl_conf)

# ── Conexión a producción 111 (solo SELECT) ──────────────────
# Nota: el 112 (réplica) no tiene confirmado el login am/dl.
# El 111 acepta am/dl y las queries son solo SELECT, sin riesgo.
SERVIDOR_REPLICA = "192.168.2.111"
USUARIO = "am"
PASSWORD = "dl"

_DRIVER = "ODBC Driver 17 for SQL Server"


def get_replica_conn(base="msgestionC"):
    conn_str = (
        f"DRIVER={{{_DRIVER}}};"
        f"SERVER={SERVIDOR_REPLICA};"
        f"DATABASE={base};"
        f"UID={USUARIO};"
        f"PWD={PASSWORD};"
        f"Connection Timeout=15;"
    )
    if not _is_windows:
        conn_str += "TrustServerCertificate=yes;Encrypt=no;"
    return pyodbc.connect(conn_str)


# ── Constantes (mismas que app_reposicion.py) ─────────────────
DEPOS_SQL = '(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)'
EXCL_VENTAS = '(7,36)'
EXCL_MARCAS_GASTOS = '(1316,1317,1158,436)'
MESES_HISTORIA = 12
BATCH_SIZE = 100  # procesar de a 100 artículos (500 causaba TCP reset en queries largas)


# ── Factores estacionales globales (fallback cuando no hay historia) ─────────
# Fuente: ESTACIONALIDAD_MENSUAL en app_reposicion.py
ESTACIONALIDAD_MENSUAL = {
    1: 0.88, 2: 1.04, 3: 0.74, 4: 0.73, 5: 0.93, 6: 1.05,
    7: 0.98, 8: 0.92, 9: 0.93, 10: 1.22, 11: 1.04, 12: 1.51,
}


def factor_estacional_batch(codigos_sinonimo, conn, anios=3):
    """
    Calcula factores estacionales por artículo en batch.
    Adaptado de _factor_estacional_batch_cached() en app_reposicion.py
    para usar pyodbc directo (sin Streamlit, sin caché).

    Retorna dict {cs: {mes(1..12): factor_float}}

    Lógica:
      - Suma ventas de los últimos `anios` años por (codigo_sinonimo, mes)
      - Calcula factor = ventas_mes / media_mensual
      - Si factores son "planos" (todos 0.8-1.2), usa ESTACIONALIDAD_MENSUAL global
      - Si el artículo no tiene historia suficiente, usa ESTACIONALIDAD_MENSUAL global
    """
    if not codigos_sinonimo:
        return {}

    desde = (date.today() - relativedelta(years=anios)).replace(month=1, day=1)
    filtro = ",".join(f"'{c}'" for c in codigos_sinonimo)

    sql = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND LEFT(a.codigo_sinonimo, 10) IN ({filtro})
          AND v.fecha >= '{desde}'
        GROUP BY LEFT(a.codigo_sinonimo, 10), MONTH(v.fecha)
    """
    df = pd.read_sql(sql, conn)

    resultados = {}
    for cs in codigos_sinonimo:
        if df.empty:
            resultados[cs] = dict(ESTACIONALIDAD_MENSUAL)
            continue

        df_cs = df[df['csr'].str.strip() == cs]
        if df_cs.empty:
            resultados[cs] = dict(ESTACIONALIDAD_MENSUAL)
            continue

        ventas_mes = {}
        for _, r in df_cs.iterrows():
            ventas_mes[int(r['mes'])] = float(r['cant'] or 0)

        media = sum(ventas_mes.values()) / max(len(ventas_mes), 1)
        if media <= 0:
            resultados[cs] = dict(ESTACIONALIDAD_MENSUAL)
            continue

        factors = {m: round(ventas_mes.get(m, media) / media, 3)
                   for m in range(1, 13)}

        # Si factores son planos (sin estacionalidad real), usar global
        is_flat = all(0.8 <= v <= 1.2 for v in factors.values())
        if is_flat:
            resultados[cs] = dict(ESTACIONALIDAD_MENSUAL)
        else:
            resultados[cs] = factors

    return resultados


def obtener_articulos_activos(conn):
    """
    Obtiene todos los codigo_sinonimo (LEFT 10) con ventas en los últimos 12 meses.
    Excluye marcas de gastos y codigos internos.
    Usa LEFT(a.codigo_sinonimo, 10) para alinear con el algoritmo v3.
    """
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    sql = f"""
        SELECT DISTINCT LEFT(a.codigo_sinonimo, 10) AS codigo_sinonimo
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND v.fecha >= '{desde}'
          AND a.codigo_sinonimo IS NOT NULL
          AND a.codigo_sinonimo <> ''
          AND LEN(RTRIM(a.codigo_sinonimo)) >= 5
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
    """
    df = pd.read_sql(sql, conn)
    return df['codigo_sinonimo'].str.strip().tolist()


def analizar_quiebre_batch_replica(codigos_sinonimo, conn, meses=MESES_HISTORIA):
    """
    Algoritmo v3 de analizar_quiebre_batch() de app_reposicion.py,
    adaptado para conexión directa pyodbc (sin Streamlit session_state).

    Mejoras v3 sobre v1:
      - Desestacionalización: ventas de cada mes OK divididas por su factor estacional
      - factor_disp: 1.20 si pct_quiebre>50%, 1.10 si >30%, 1.0 si no
      - Fallback 100% quiebre: vel_aparente * 1.15 (en lugar de vel_aparente plana)
      - std_mensual: np.std() de ventas mensuales en meses con stock
      - ventas_perdidas: segunda pasada — estima ventas en meses quebrados
      - vel_real_con_perdidas: (ventas_total + ventas_perdidas) / meses

    SQL usa LEFT(a.codigo_sinonimo, 10) para alinear con el matching de v3.
    """
    if not codigos_sinonimo:
        return {}

    hoy = date.today()
    desde = (hoy - relativedelta(months=meses)).replace(day=1)
    filtro = ",".join(f"'{c}'" for c in codigos_sinonimo)

    # 1. Stock actual (LEFT 10 para matchear con CSR truncado)
    sql_stock = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               ISNULL(SUM(s.stock_actual), 0) AS stock
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE LEFT(a.codigo_sinonimo, 10) IN ({filtro})
          AND s.deposito IN {DEPOS_SQL}
        GROUP BY LEFT(a.codigo_sinonimo, 10)
    """
    df_stock = pd.read_sql(sql_stock, conn)
    stock_dict = {}
    for _, r in df_stock.iterrows():
        stock_dict[r['csr'].strip()] = float(r['stock'])

    # 2. Ventas mensuales (LEFT 10)
    sql_ventas = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND LEFT(a.codigo_sinonimo, 10) IN ({filtro})
          AND v.fecha >= '{desde}'
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(v.fecha), MONTH(v.fecha)
    """
    df_ventas = pd.read_sql(sql_ventas, conn)

    # 3. Compras mensuales (LEFT 10)
    sql_compras = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(rc.cantidad) AS cant,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+'
          AND LEFT(a.codigo_sinonimo, 10) IN ({filtro})
          AND rc.fecha >= '{desde}'
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(rc.fecha), MONTH(rc.fecha)
    """
    df_compras = pd.read_sql(sql_compras, conn)

    # Organizar en dicts
    ventas_by_cs = {}
    for _, r in df_ventas.iterrows():
        cs = r['csr'].strip()
        ventas_by_cs.setdefault(cs, {})[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    compras_by_cs = {}
    for _, r in df_compras.iterrows():
        cs = r['csr'].strip()
        compras_by_cs.setdefault(cs, {})[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    # Lista de meses hacia atrás (de más reciente a más antiguo)
    meses_lista = []
    cursor = hoy.replace(day=1)
    for _ in range(meses):
        meses_lista.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    # Pre-calcular factores estacionales para todos los artículos del batch
    factores_est = factor_estacional_batch(codigos_sinonimo, conn)

    # Reconstruir quiebre para cada codigo_sinonimo
    resultados = {}
    for cs in codigos_sinonimo:
        stock_actual = stock_dict.get(cs, 0)
        v_dict = ventas_by_cs.get(cs, {})
        c_dict = compras_by_cs.get(cs, {})
        f_est = factores_est.get(cs, {m: 1.0 for m in range(1, 13)})

        stock_fin = stock_actual
        meses_q = 0
        meses_ok = 0
        ventas_total = 0
        ventas_ok = 0
        ventas_desest = 0      # ventas desestacionalizadas (meses OK)
        ventas_meses_ok = []   # para calcular std_mensual

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
                ventas_meses_ok.append(v)
                # Desestacionalizar: dividir ventas por factor del mes
                s_t = max(f_est.get(mes, 1.0), 0.1)
                ventas_desest += v / s_t

            stock_fin = stock_inicio

        vel_ap = ventas_total / max(meses, 1)

        # vel_real v3: desestacionalizada + corrección disponibilidad
        pct_q = meses_q / max(meses, 1)
        if meses_ok > 0:
            vel_base = ventas_desest / meses_ok
        elif ventas_total > 0:
            # Quiebre 100%: fallback vel_aparente × 1.15
            vel_base = vel_ap * 1.15
        else:
            vel_base = 0.0

        # Factor corrección por disponibilidad (demanda latente reprimida)
        if pct_q > 0.5:
            factor_disp = 1.20
        elif pct_q > 0.3:
            factor_disp = 1.10
        else:
            factor_disp = 1.0

        vel_real = vel_base * factor_disp

        # Desvío estándar mensual (solo meses no quebrados)
        std_mes = float(np.std(ventas_meses_ok)) if ventas_meses_ok else 0.0

        # ── Segunda pasada: estimación de ventas perdidas ──
        # Para cada mes quebrado, estimar cuánto se habría vendido
        # usando vel_base ajustada por estacionalidad del mes
        ventas_perdidas = 0.0
        if meses_ok > 0 and vel_base > 0:
            stock_fin2 = stock_actual
            for anio, mes in meses_lista:
                v = v_dict.get((anio, mes), 0)
                c = c_dict.get((anio, mes), 0)
                stock_inicio_check = stock_fin2 + v - c
                if stock_inicio_check <= 0:
                    # Mes quebrado: estimar ventas esperadas
                    factor_mes = max(f_est.get(mes, 1.0), 0.1)
                    ventas_esperadas = vel_base * factor_mes
                    ventas_perdidas += max(0.0, ventas_esperadas - v)
                stock_fin2 = stock_inicio_check

        vel_real_con_perdidas = round((ventas_total + ventas_perdidas) / max(meses, 1), 2)
        factor_quiebre = round(vel_real / vel_ap, 3) if vel_ap > 0 else 1.0

        resultados[cs] = {
            'vel_aparente':           round(vel_ap, 2),
            'vel_real':               round(vel_real, 2),
            'vel_base_desest':        round(vel_base, 2),
            'factor_disp':            factor_disp,
            'meses_ok':               meses_ok,
            'meses_quebrado':         meses_q,
            'factor_quiebre':         factor_quiebre,
            'std_mensual':            round(std_mes, 2),
            'ventas_perdidas':        round(ventas_perdidas),
            'vel_real_con_perdidas':  vel_real_con_perdidas,
        }

    return resultados


def escape_sql(s):
    """Escapa comillas simples para SQL."""
    return s.replace("'", "''")


def generar_script(output_path):
    """Genera el script SQL completo."""
    print("Conectando a réplica 112...")
    conn = get_replica_conn()

    print("Obteniendo artículos activos con ventas últimos 12 meses...")
    codigos = obtener_articulos_activos(conn)
    print(f"  → {len(codigos)} artículos encontrados")

    if not codigos:
        print("ERROR: No se encontraron artículos. Verificar conexión.")
        sys.exit(1)

    # Procesar en batches
    all_results = {}
    n_batches = (len(codigos) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(codigos), BATCH_SIZE):
        batch = codigos[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"  Batch {batch_num}/{n_batches}: procesando {len(batch)} artículos...")
        results = analizar_quiebre_batch_replica(batch, conn)
        all_results.update(results)

    conn.close()
    print(f"  → {len(all_results)} artículos procesados con éxito")

    # Generar SQL
    fecha_calculo = date.today().isoformat()

    lines = []
    lines.append("-- ============================================================")
    lines.append("-- vel_real_articulo — Velocidad real corregida por quiebre (algoritmo v3)")
    lines.append(f"-- Generado: {fecha_calculo}")
    lines.append(f"-- Artículos: {len(all_results)}")
    lines.append("-- Fuente: analizar_quiebre_batch() v3 de app_reposicion.py")
    lines.append("-- v3: desestacionalización, factor_disp, std_mensual, ventas_perdidas")
    lines.append("-- EJECUTAR EN: 192.168.2.111 (producción)")
    lines.append("-- ============================================================")
    lines.append("")
    lines.append("USE omicronvt;")
    lines.append("GO")
    lines.append("")

    # CREATE TABLE
    lines.append("IF OBJECT_ID('dbo.vel_real_articulo', 'U') IS NOT NULL")
    lines.append("    DROP TABLE dbo.vel_real_articulo;")
    lines.append("GO")
    lines.append("")
    lines.append("CREATE TABLE dbo.vel_real_articulo (")
    lines.append("    codigo                VARCHAR(20)   NOT NULL,  -- codigo_sinonimo (LEFT 10)")
    lines.append("    vel_aparente          DECIMAL(10,2) NOT NULL,  -- ventas_total / meses")
    lines.append("    vel_real              DECIMAL(10,2) NOT NULL,  -- vel_base_desest * factor_disp")
    lines.append("    vel_base_desest       FLOAT         NOT NULL,  -- velocidad desestacionalizada (v3)")
    lines.append("    factor_disp           FLOAT         NOT NULL,  -- 1.20/1.10/1.0 por pct_quiebre")
    lines.append("    meses_con_stock       INT           NOT NULL,  -- meses sin quiebre")
    lines.append("    meses_quebrado        INT           NOT NULL,  -- meses con stock_inicio <= 0")
    lines.append("    factor_quiebre        DECIMAL(8,3)  NOT NULL,  -- vel_real / vel_aparente")
    lines.append("    std_mensual           FLOAT         NOT NULL,  -- desvío estándar meses OK")
    lines.append("    ventas_perdidas       FLOAT         NOT NULL,  -- ventas estimadas en meses quebrados")
    lines.append("    vel_real_con_perdidas FLOAT         NOT NULL,  -- (ventas_total+ventas_perdidas)/meses")
    lines.append("    fecha_calculo         DATE          NOT NULL,  -- cuándo se calculó")
    lines.append("    CONSTRAINT PK_vel_real_articulo PRIMARY KEY (codigo)")
    lines.append(");")
    lines.append("GO")
    lines.append("")

    # INSERTs en batches de 100 — incluye columnas v3
    insert_prefix = ("INSERT INTO dbo.vel_real_articulo "
                     "(codigo, vel_aparente, vel_real, vel_base_desest, factor_disp, "
                     "meses_con_stock, meses_quebrado, factor_quiebre, "
                     "std_mensual, ventas_perdidas, vel_real_con_perdidas, "
                     "fecha_calculo) VALUES")

    batch_values = []
    count = 0
    for cs, data in sorted(all_results.items()):
        val = (
            f"('{escape_sql(cs)}', "
            f"{data['vel_aparente']}, "
            f"{data['vel_real']}, "
            f"{data['vel_base_desest']}, "
            f"{data['factor_disp']}, "
            f"{data['meses_ok']}, "
            f"{data['meses_quebrado']}, "
            f"{data['factor_quiebre']}, "
            f"{data['std_mensual']}, "
            f"{data['ventas_perdidas']}, "
            f"{data['vel_real_con_perdidas']}, "
            f"'{fecha_calculo}')"
        )
        batch_values.append(val)
        count += 1

        if count % 100 == 0:
            lines.append(insert_prefix)
            lines.append(",\n".join(batch_values) + ";")
            lines.append("")
            batch_values = []

    # Último batch
    if batch_values:
        lines.append(insert_prefix)
        lines.append(",\n".join(batch_values) + ";")
        lines.append("")

    lines.append("GO")
    lines.append("")

    # Índice y stats
    lines.append("-- Índice para JOINs desde calce/presupuesto (incluye columnas v3)")
    lines.append("CREATE INDEX IX_vel_real_factor ON dbo.vel_real_articulo (codigo)")
    lines.append("    INCLUDE (vel_real, vel_real_con_perdidas, factor_quiebre, factor_disp);")
    lines.append("GO")
    lines.append("")
    lines.append(f"PRINT 'vel_real_articulo (v3): {len(all_results)} registros insertados';")
    lines.append("GO")

    # Escribir archivo
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    print(f"\nScript generado: {output_path}")
    print(f"  {len(all_results)} registros")
    print(f"  Ejecutar en 111: sqlcmd -S localhost -d omicronvt -i \"{os.path.basename(output_path)}\"")

    # Stats resumen
    quebrados = sum(1 for d in all_results.values() if d['meses_quebrado'] > 6)
    factor_alto = sum(1 for d in all_results.values() if d['factor_quiebre'] > 2.0)
    con_disp = sum(1 for d in all_results.values() if d['factor_disp'] > 1.0)
    perdidas_total = sum(d['ventas_perdidas'] for d in all_results.values())
    print(f"\n  Stats:")
    print(f"    Artículos con >50% quiebre: {quebrados} ({quebrados*100//max(len(all_results),1)}%)")
    print(f"    Artículos con factor >2x: {factor_alto} (vel_real es más del doble de vel_aparente)")
    print(f"    Artículos con factor_disp activo (>1.0): {con_disp}")
    print(f"    Total ventas_perdidas estimadas: {perdidas_total:.0f} pares")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera script SQL para tabla vel_real_articulo")
    parser.add_argument("--output", "-o", default=None,
                        help="Ruta del archivo SQL de salida")
    args = parser.parse_args()

    if args.output is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        args.output = os.path.join(script_dir, f"vel_real_articulo_{date.today().strftime('%Y%m%d')}.sql")

    generar_script(args.output)
