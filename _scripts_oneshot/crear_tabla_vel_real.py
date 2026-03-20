"""
Genera script SQL para crear y poblar omicronvt.dbo.vel_real_articulo.

Conecta a réplica 112 (solo SELECT), calcula vel_real con la misma lógica
que analizar_quiebre_batch() de app_reposicion.py, y genera un .sql con
los INSERTs listos para ejecutar en el 111.

Uso:
    python crear_tabla_vel_real.py              # genera .sql en la misma carpeta
    python crear_tabla_vel_real.py --output /tmp/vel_real.sql
"""
import os
import sys
import argparse
from datetime import date
from dateutil.relativedelta import relativedelta

import pyodbc
import pandas as pd

# ── Conexión a RÉPLICA (solo SELECT) ──────────────────────────
SERVIDOR_REPLICA = "192.168.2.112"
USUARIO = "am"
PASSWORD = "dl"

# Detectar driver disponible
import platform
_is_windows = platform.system() == "Windows"
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
BATCH_SIZE = 500  # procesar de a 500 artículos


def obtener_articulos_activos(conn):
    """
    Obtiene todos los codigo_sinonimo con ventas en los últimos 12 meses.
    Excluye marcas de gastos y codigos internos.
    """
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    sql = f"""
        SELECT DISTINCT RTRIM(a.codigo_sinonimo) AS codigo_sinonimo
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
    Réplica de analizar_quiebre_batch() de app_reposicion.py,
    pero usando conexión directa a réplica (sin Streamlit session_state).
    """
    if not codigos_sinonimo:
        return {}

    hoy = date.today()
    desde = (hoy - relativedelta(months=meses)).replace(day=1)
    filtro = ",".join(f"'{c}'" for c in codigos_sinonimo)

    # 1. Stock actual
    sql_stock = f"""
        SELECT RTRIM(a.codigo_sinonimo) AS codigo_sinonimo,
               ISNULL(SUM(s.stock_actual), 0) AS stock
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE a.codigo_sinonimo IN ({filtro})
          AND s.deposito IN {DEPOS_SQL}
        GROUP BY a.codigo_sinonimo
    """
    df_stock = pd.read_sql(sql_stock, conn)
    stock_dict = {r['codigo_sinonimo'].strip(): float(r['stock'])
                  for _, r in df_stock.iterrows()}

    # 2. Ventas mensuales
    sql_ventas = f"""
        SELECT RTRIM(a.codigo_sinonimo) AS codigo_sinonimo,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.codigo_sinonimo IN ({filtro})
          AND v.fecha >= '{desde}'
        GROUP BY a.codigo_sinonimo, YEAR(v.fecha), MONTH(v.fecha)
    """
    df_ventas = pd.read_sql(sql_ventas, conn)

    # 3. Compras mensuales
    sql_compras = f"""
        SELECT RTRIM(a.codigo_sinonimo) AS codigo_sinonimo,
               SUM(rc.cantidad) AS cant,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+'
          AND a.codigo_sinonimo IN ({filtro})
          AND rc.fecha >= '{desde}'
        GROUP BY a.codigo_sinonimo, YEAR(rc.fecha), MONTH(rc.fecha)
    """
    df_compras = pd.read_sql(sql_compras, conn)

    # Organizar en dicts
    ventas_by_cs = {}
    for _, r in df_ventas.iterrows():
        cs = r['codigo_sinonimo'].strip()
        ventas_by_cs.setdefault(cs, {})[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    compras_by_cs = {}
    for _, r in df_compras.iterrows():
        cs = r['codigo_sinonimo'].strip()
        compras_by_cs.setdefault(cs, {})[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    # Lista de meses hacia atrás
    meses_lista = []
    cursor = hoy.replace(day=1)
    for _ in range(meses):
        meses_lista.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    # Reconstruir quiebre
    resultados = {}
    for cs in codigos_sinonimo:
        stock_actual = stock_dict.get(cs, 0)
        v_dict = ventas_by_cs.get(cs, {})
        c_dict = compras_by_cs.get(cs, {})

        stock_fin = stock_actual
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

        vel_ap = ventas_total / max(meses, 1)
        vel_real = ventas_ok / max(meses_ok, 1) if meses_ok > 0 else vel_ap
        factor = vel_real / vel_ap if vel_ap > 0 else 1.0

        resultados[cs] = {
            'vel_aparente': round(vel_ap, 2),
            'vel_real': round(vel_real, 2),
            'meses_ok': meses_ok,
            'meses_quebrado': meses_q,
            'factor_quiebre': round(factor, 3),
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
    lines.append("-- vel_real_articulo — Velocidad real corregida por quiebre")
    lines.append(f"-- Generado: {fecha_calculo}")
    lines.append(f"-- Artículos: {len(all_results)}")
    lines.append("-- Fuente: analizar_quiebre_batch() de app_reposicion.py")
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
    lines.append("    codigo            VARCHAR(20)   NOT NULL,  -- codigo_sinonimo")
    lines.append("    vel_aparente      DECIMAL(10,2) NOT NULL,  -- ventas_total / meses")
    lines.append("    vel_real          DECIMAL(10,2) NOT NULL,  -- ventas_ok / meses_ok")
    lines.append("    meses_con_stock   INT           NOT NULL,  -- meses sin quiebre")
    lines.append("    meses_quebrado    INT           NOT NULL,  -- meses con stock_inicio <= 0")
    lines.append("    factor_quiebre    DECIMAL(8,3)  NOT NULL,  -- vel_real / vel_aparente")
    lines.append("    fecha_calculo     DATE          NOT NULL,  -- cuándo se calculó")
    lines.append("    CONSTRAINT PK_vel_real_articulo PRIMARY KEY (codigo)")
    lines.append(");")
    lines.append("GO")
    lines.append("")

    # INSERTs en batches de 100
    insert_prefix = ("INSERT INTO dbo.vel_real_articulo "
                     "(codigo, vel_aparente, vel_real, meses_con_stock, "
                     "meses_quebrado, factor_quiebre, fecha_calculo) VALUES")

    batch_values = []
    count = 0
    for cs, data in sorted(all_results.items()):
        val = (f"('{escape_sql(cs)}', {data['vel_aparente']}, {data['vel_real']}, "
               f"{data['meses_ok']}, {data['meses_quebrado']}, "
               f"{data['factor_quiebre']}, '{fecha_calculo}')")
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
    lines.append("-- Índice para JOINs desde calce/presupuesto")
    lines.append("CREATE INDEX IX_vel_real_factor ON dbo.vel_real_articulo (codigo) INCLUDE (vel_real, factor_quiebre);")
    lines.append("GO")
    lines.append("")
    lines.append(f"PRINT 'vel_real_articulo: {len(all_results)} registros insertados';")
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
    print(f"\n  Stats:")
    print(f"    Artículos con >50% quiebre: {quebrados} ({quebrados*100//max(len(all_results),1)}%)")
    print(f"    Artículos con factor >2x: {factor_alto} (vel_real es más del doble de vel_aparente)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera script SQL para tabla vel_real_articulo")
    parser.add_argument("--output", "-o", default=None,
                        help="Ruta del archivo SQL de salida")
    args = parser.parse_args()

    if args.output is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        args.output = os.path.join(script_dir, f"vel_real_articulo_{date.today().strftime('%Y%m%d')}.sql")

    generar_script(args.output)
