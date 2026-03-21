#!/usr/bin/env python3
"""
Tests automáticos para app_reposicion.py
=========================================
Ejecuta queries y lógica core SIN depender de Streamlit.
Conecta al 111 vía pyodbc con el fix de OpenSSL legacy.

Uso:
    OPENSSL_CONF=/tmp/openssl_legacy.cnf python3 tests/test_reposicion.py

O sin variable (el script intenta crearla automáticamente):
    python3 tests/test_reposicion.py
"""
import os
import sys
import time
import traceback

# Fix OpenSSL para SQL Server 2012 (TLS 1.0)
_openssl_cnf = "/tmp/openssl_legacy.cnf"
if not os.path.exists(_openssl_cnf):
    with open(_openssl_cnf, "w") as f:
        f.write(
            "openssl_conf = openssl_init\n"
            "[openssl_init]\nssl_conf = ssl_sect\n"
            "[ssl_sect]\nsystem_default = system_default_sect\n"
            "[system_default_sect]\nMinProtocol = TLSv1\n"
            "CipherString = DEFAULT:@SECLEVEL=0\n"
        )
if "OPENSSL_CONF" not in os.environ:
    os.environ["OPENSSL_CONF"] = _openssl_cnf

import pyodbc
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# ── Setup: agregar raíz al path para importar config ──────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from config import get_conn_string

# ── Constantes (idénticas a app_reposicion.py) ─────────────────
DEPOS_SQL = "(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)"
EXCL_VENTAS = "(7,36)"
EXCL_MARCAS_GASTOS = "(1316,1317,1158,436)"
MESES_HISTORIA = 12

# ── Conexión ──────────────────────────────────────────────────
CONN_STR = get_conn_string("msgestionC")
_conn = None


def get_conn():
    global _conn
    if _conn is None:
        _conn = pyodbc.connect(CONN_STR, timeout=15)
    return _conn


def query_df(sql):
    return pd.read_sql(sql, get_conn())


# ══════════════════════════════════════════════════════════════
# TEST FRAMEWORK
# ══════════════════════════════════════════════════════════════
results = []


def test(name):
    """Decorador para registrar tests."""
    def decorator(func):
        def wrapper():
            t0 = time.time()
            try:
                func()
                elapsed = time.time() - t0
                results.append(("PASS", name, f"{elapsed:.1f}s", ""))
            except Exception as e:
                elapsed = time.time() - t0
                tb = traceback.format_exc()
                # Extraer línea relevante
                lines = tb.strip().split("\n")
                short = lines[-1] if lines else str(e)
                results.append(("FAIL", name, f"{elapsed:.1f}s", short))
        wrapper._test_name = name
        return wrapper
    return decorator


# ══════════════════════════════════════════════════════════════
# 1. TESTS DE CONEXIÓN
# ══════════════════════════════════════════════════════════════

@test("Conexión pyodbc al 111")
def test_conexion():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 AS ok")
    row = cur.fetchone()
    assert row[0] == 1, "SELECT 1 no retornó 1"


@test("Tabla articulo existe y tiene datos")
def test_tabla_articulo():
    df = query_df("SELECT TOP 1 codigo, descripcion_1 FROM msgestion01art.dbo.articulo")
    assert len(df) == 1, "Tabla articulo vacía"
    assert "codigo" in df.columns


@test("Tabla stock existe y tiene datos")
def test_tabla_stock():
    df = query_df(f"SELECT TOP 1 articulo, stock_actual FROM msgestionC.dbo.stock WHERE deposito IN {DEPOS_SQL}")
    assert len(df) == 1, "Tabla stock vacía"


@test("Tabla ventas1 existe y tiene datos recientes")
def test_tabla_ventas():
    desde = (date.today() - relativedelta(months=3)).isoformat()
    df = query_df(f"SELECT TOP 1 articulo, cantidad, fecha FROM msgestionC.dbo.ventas1 WHERE fecha >= '{desde}'")
    assert len(df) == 1, "Sin ventas recientes (3 meses)"


@test("Tabla compras1 existe y tiene datos recientes")
def test_tabla_compras():
    desde = (date.today() - relativedelta(months=6)).isoformat()
    df = query_df(f"SELECT TOP 1 articulo, cantidad, fecha FROM msgestionC.dbo.compras1 WHERE fecha >= '{desde}'")
    assert len(df) == 1, "Sin compras recientes (6 meses)"


# ══════════════════════════════════════════════════════════════
# 2. TESTS DE FUNCIONES CORE (lógica replicada sin Streamlit)
# ══════════════════════════════════════════════════════════════

@test("cargar_marcas_dict: retorna dict no vacío desde msgestionC")
def test_marcas_dict():
    df = query_df("SELECT codigo, RTRIM(ISNULL(descripcion,'')) AS desc1 FROM msgestionC.dbo.marcas")
    assert len(df) > 100, f"Solo {len(df)} marcas, esperado >100"
    # Verificar que no haya descripciones vacías en las primeras 50
    primeras = df.head(50)
    vacias = primeras[primeras["desc1"].str.strip() == ""]
    assert len(vacias) < 10, f"{len(vacias)} marcas sin descripción en top 50"


@test("cargar_marcas_dict: marca 515 = ELEMENTO (no vacía)")
def test_marca_515():
    df = query_df("SELECT descripcion FROM msgestionC.dbo.marcas WHERE codigo = 515")
    assert len(df) == 1, "Marca 515 no existe"
    desc = df.iloc[0]["descripcion"].strip()
    assert desc != "", "Marca 515 tiene descripción vacía"
    assert desc == "ELEMENTO", f"Marca 515 = '{desc}', esperado 'ELEMENTO'"


@test("cargar_mapa_surtido: query ejecuta sin error")
def test_mapa_surtido_query():
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    sql = f"""
        SELECT TOP 5
            a.rubro AS genero_cod, a.subrubro AS sub_cod,
            COUNT(DISTINCT LEFT(a.codigo_sinonimo, 10)) AS modelos,
            SUM(ISNULL(s.stk, 0)) AS stock_total,
            SUM(ISNULL(v.vtas, 0)) AS ventas_12m
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stk
            FROM msgestionC.dbo.stock WHERE deposito IN {DEPOS_SQL}
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN (
            SELECT articulo,
                   SUM(CASE WHEN operacion='+' THEN cantidad
                            WHEN operacion='-' THEN -cantidad END) AS vtas
            FROM msgestionC.dbo.ventas1
            WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}'
            GROUP BY articulo
        ) v ON v.articulo = a.codigo
        WHERE a.estado = 'V' AND a.rubro IN (1,3,4,5,6)
          AND a.subrubro IS NOT NULL AND a.subrubro > 0
          AND LEN(a.codigo_sinonimo) >= 10
          AND (ISNULL(s.stk, 0) > 0 OR ISNULL(v.vtas, 0) > 0)
        GROUP BY a.rubro, a.subrubro
        HAVING SUM(ISNULL(v.vtas, 0)) > 0
    """
    df = query_df(sql)
    assert len(df) > 0, "Mapa surtido retornó 0 filas"
    for col in ["genero_cod", "sub_cod", "modelos", "stock_total", "ventas_12m"]:
        assert col in df.columns, f"Falta columna {col}"


@test("analizar_quiebre_batch: lógica completa con artículo real")
def test_quiebre_batch():
    # Buscar un artículo con ventas recientes
    desde = (date.today() - relativedelta(months=6)).replace(day=1)
    df_cs = query_df(f"""
        SELECT TOP 1 RTRIM(a.codigo_sinonimo) AS cs
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS} AND v.fecha >= '{desde}'
          AND LEN(RTRIM(a.codigo_sinonimo)) >= 10
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
    """)
    assert len(df_cs) == 1, "No se encontró artículo con ventas para testear"
    cs = df_cs.iloc[0]["cs"].strip()

    # Replicar lógica de analizar_quiebre_batch
    hoy = date.today()
    desde_q = (hoy - relativedelta(months=MESES_HISTORIA)).replace(day=1)
    filtro = f"'{cs}'"

    df_stock = query_df(f"""
        SELECT RTRIM(a.codigo_sinonimo) AS codigo_sinonimo,
               ISNULL(SUM(s.stock_actual), 0) AS stock
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE a.codigo_sinonimo IN ({filtro}) AND s.deposito IN {DEPOS_SQL}
        GROUP BY a.codigo_sinonimo
    """)

    df_ventas = query_df(f"""
        SELECT RTRIM(a.codigo_sinonimo) AS codigo_sinonimo,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.codigo_sinonimo IN ({filtro}) AND v.fecha >= '{desde_q}'
        GROUP BY a.codigo_sinonimo, YEAR(v.fecha), MONTH(v.fecha)
    """)

    df_compras = query_df(f"""
        SELECT RTRIM(a.codigo_sinonimo) AS codigo_sinonimo,
               SUM(rc.cantidad) AS cant,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+' AND a.codigo_sinonimo IN ({filtro})
          AND rc.fecha >= '{desde_q}'
        GROUP BY a.codigo_sinonimo, YEAR(rc.fecha), MONTH(rc.fecha)
    """)

    # Reconstruir quiebre
    stock_actual = float(df_stock.iloc[0]["stock"]) if len(df_stock) > 0 else 0
    v_dict = {}
    for _, r in df_ventas.iterrows():
        v_dict[(int(r["anio"]), int(r["mes"]))] = float(r["cant"] or 0)
    c_dict = {}
    for _, r in df_compras.iterrows():
        c_dict[(int(r["anio"]), int(r["mes"]))] = float(r["cant"] or 0)

    meses_lista = []
    cursor = hoy.replace(day=1)
    for _ in range(MESES_HISTORIA):
        meses_lista.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    stock_fin = stock_actual
    meses_ok = 0
    ventas_ok = 0
    for anio, mes in meses_lista:
        v = v_dict.get((anio, mes), 0)
        c = c_dict.get((anio, mes), 0)
        stock_inicio = stock_fin + v - c
        if stock_inicio > 0:
            meses_ok += 1
            ventas_ok += v
        stock_fin = stock_inicio

    vel_real = ventas_ok / max(meses_ok, 1) if meses_ok > 0 else 0
    assert vel_real >= 0, f"vel_real negativa: {vel_real}"
    # No puede ser NaN o None
    assert vel_real == vel_real, "vel_real es NaN"


# ══════════════════════════════════════════════════════════════
# 3. TESTS DE QUERIES SQL PROBLEMÁTICAS
# ══════════════════════════════════════════════════════════════

@test("Query descripcion_5 con filtro ISNUMERIC seguro (no CAST FLOAT)")
def test_descripcion_5_isnumeric():
    """El fix reemplazó CAST(FLOAT) por CAST(INT) con filtros NOT LIKE."""
    sql = f"""
        SELECT TOP 10 RTRIM(a.descripcion_5) AS talle, COUNT(*) AS n
        FROM msgestion01art.dbo.articulo a
        WHERE a.estado = 'V' AND a.rubro IN (1,3,4,5,6)
          AND RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
          AND CASE WHEN RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
                   THEN CAST(a.descripcion_5 AS INT) END BETWEEN 17 AND 50
        GROUP BY RTRIM(a.descripcion_5)
        ORDER BY COUNT(*) DESC
    """
    df = query_df(sql)
    assert len(df) > 0, "Query de talles retornó 0 filas"
    # Verificar que todos son enteros válidos entre 17-50
    for _, r in df.iterrows():
        talle = int(r["talle"])
        assert 17 <= talle <= 50, f"Talle {talle} fuera de rango 17-50"


@test("Query ventas con exclusión código 7 y 36")
def test_ventas_exclusion():
    desde = (date.today() - relativedelta(months=3)).isoformat()
    sql = f"""
        SELECT TOP 5 v.codigo, COUNT(*) AS n
        FROM msgestionC.dbo.ventas1 v
        WHERE v.fecha >= '{desde}' AND v.codigo NOT IN {EXCL_VENTAS}
        GROUP BY v.codigo ORDER BY COUNT(*) DESC
    """
    df = query_df(sql)
    assert len(df) > 0, "Sin ventas post-exclusión"
    codigos = df["codigo"].tolist()
    assert 7 not in codigos, "Código 7 (remito interno) no fue excluido"
    assert 36 not in codigos, "Código 36 (remito interno) no fue excluido"


@test("Query compras operacion +/- no falla")
def test_compras_operacion():
    desde = (date.today() - relativedelta(months=6)).isoformat()
    sql = f"""
        SELECT TOP 5 rc.operacion, SUM(rc.cantidad) AS total
        FROM msgestionC.dbo.compras1 rc
        WHERE rc.fecha >= '{desde}'
        GROUP BY rc.operacion
    """
    df = query_df(sql)
    assert len(df) > 0, "Sin compras recientes"
    ops = df["operacion"].str.strip().tolist()
    assert "+" in ops, "No hay compras con operacion '+'"


@test("Query tkey (talle concatenado) no retorna NULLs")
def test_tkey_no_null():
    """Verifica que el tkey concatenado no genera NULLs que rompan .strip()"""
    desde = (date.today() - relativedelta(months=6)).replace(day=1)
    sql = f"""
        SELECT TOP 20
            CAST(a.rubro AS VARCHAR) + '_' + CAST(a.subrubro AS VARCHAR) + '_' + RTRIM(a.descripcion_5) AS tkey,
            COUNT(*) AS n
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.estado = 'V' AND a.rubro IN (1,3,4,5,6)
          AND RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
          AND CASE WHEN RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
                   THEN CAST(a.descripcion_5 AS INT) END BETWEEN 17 AND 50
          AND v.fecha >= '{desde}'
        GROUP BY CAST(a.rubro AS VARCHAR) + '_' + CAST(a.subrubro AS VARCHAR) + '_' + RTRIM(a.descripcion_5)
        ORDER BY COUNT(*) DESC
    """
    df = query_df(sql)
    assert len(df) > 0, "tkey query retornó 0 filas"
    nulls = df["tkey"].isna().sum()
    assert nulls == 0, f"{nulls} filas con tkey NULL"


@test("Query calcular_alertas_talles completa (calzado_filter)")
def test_alertas_talles_query():
    """Ejecuta la query principal de calcular_alertas_talles sin error."""
    desde = (date.today() - relativedelta(months=MESES_HISTORIA)).replace(day=1)
    calzado_filter = f"""
        a.estado = 'V' AND a.rubro IN (1,3,4,5,6)
          AND RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
          AND CASE WHEN RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
                   THEN CAST(a.descripcion_5 AS INT) END BETWEEN 17 AND 50
    """
    sql = f"""
        SELECT TOP 10 a.rubro AS genero_cod, a.subrubro AS sub_cod,
            RTRIM(a.descripcion_5) AS talle,
            COUNT(DISTINCT a.codigo) AS modelos,
            SUM(ISNULL(s.stk, 0)) AS stock,
            SUM(ISNULL(v.vtas, 0)) AS vtas_12m
        FROM msgestion01art.dbo.articulo a
        INNER JOIN msgestion01.dbo.regla_talle_subrubro rt
            ON rt.codigo_subrubro = a.subrubro AND rt.tipo_talle = 'CALZADO'
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stk
            FROM msgestionC.dbo.stock WHERE deposito IN {DEPOS_SQL}
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN (
            SELECT articulo,
                   SUM(CASE WHEN operacion='+' THEN cantidad
                            WHEN operacion='-' THEN -cantidad END) AS vtas
            FROM msgestionC.dbo.ventas1
            WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}'
            GROUP BY articulo
        ) v ON v.articulo = a.codigo
        WHERE {calzado_filter}
          AND (ISNULL(s.stk, 0) > 0 OR ISNULL(v.vtas, 0) > 0)
        GROUP BY a.rubro, a.subrubro, RTRIM(a.descripcion_5)
        HAVING SUM(ISNULL(v.vtas, 0)) > 0
    """
    df = query_df(sql)
    assert len(df) > 0, "Query de alertas talles retornó 0 filas"
    # Verificar que talle es numérico y dentro de rango
    for _, r in df.iterrows():
        t = int(r["talle"])
        assert 17 <= t <= 50, f"Talle {t} fuera de rango"


@test("cargar_talles_categoria(1, 49): query completa sin error")
def test_talles_categoria():
    """Ejecuta las 3 queries de cargar_talles_categoria para rubro=1, subrubro=49."""
    desde = (date.today() - relativedelta(months=MESES_HISTORIA)).replace(day=1)
    talle_expr = """COALESCE(
            NULLIF(RTRIM(a.descripcion_5), ''),
            CASE WHEN ISNUMERIC(RIGHT(RTRIM(a.codigo_sinonimo), 2)) = 1
                 THEN RIGHT(RTRIM(a.codigo_sinonimo), 2) END
        )"""

    # Query base
    sql = f"""
        SELECT TOP 10 {talle_expr} AS talle,
            COUNT(DISTINCT a.codigo) AS modelos,
            SUM(ISNULL(s.stk, 0)) AS stock,
            SUM(ISNULL(v.vtas, 0)) AS vtas_12m
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stk
            FROM msgestionC.dbo.stock WHERE deposito IN {DEPOS_SQL}
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN (
            SELECT articulo,
                   SUM(CASE WHEN operacion='+' THEN cantidad
                            WHEN operacion='-' THEN -cantidad END) AS vtas
            FROM msgestionC.dbo.ventas1
            WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}'
            GROUP BY articulo
        ) v ON v.articulo = a.codigo
        WHERE a.estado = 'V' AND a.rubro = 1 AND a.subrubro = 49
          AND (ISNULL(s.stk, 0) > 0 OR ISNULL(v.vtas, 0) > 0)
        GROUP BY {talle_expr}
        HAVING {talle_expr} IS NOT NULL
    """
    df = query_df(sql)
    # Puede estar vacío si subrubro 49 no tiene datos — eso es OK
    if len(df) > 0:
        assert "talle" in df.columns
        # Verificar que no hay None en talle
        nulls = df["talle"].isna().sum()
        assert nulls == 0, f"{nulls} talles NULL en resultado"


@test("vel_real_articulo: tabla existe (si ya se ejecutó fase 1)")
def test_vel_real_tabla():
    """Verifica si omicronvt.dbo.vel_real_articulo existe. WARN si no."""
    try:
        df = query_df("SELECT TOP 1 codigo, vel_real, factor_quiebre FROM omicronvt.dbo.vel_real_articulo")
        assert len(df) == 1, "Tabla existe pero está vacía"
    except Exception as e:
        if "Invalid object name" in str(e):
            # No es error, es que aún no se ejecutó fase 1
            raise AssertionError("WARN: vel_real_articulo no existe aún (ejecutar crear_tabla_vel_real.py)")
        raise


# ══════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════

def run_all():
    # Recolectar tests
    tests = []
    for name, obj in list(globals().items()):
        if callable(obj) and hasattr(obj, "_test_name"):
            tests.append(obj)

    print(f"{'='*65}")
    print(f"  TEST SUITE: app_reposicion.py")
    print(f"  Server: 192.168.2.111 | {len(tests)} tests")
    print(f"{'='*65}")
    print()

    for t in tests:
        sys.stdout.write(f"  {t._test_name:55s} ")
        sys.stdout.flush()
        t()
        status, name, elapsed, error = results[-1]
        if status == "PASS":
            print(f"✅ {elapsed}")
        else:
            is_warn = error.startswith("AssertionError: WARN:")
            if is_warn:
                print(f"⚠️  {elapsed}")
                print(f"     {error.split('WARN: ')[-1]}")
            else:
                print(f"❌ {elapsed}")
                print(f"     {error}")

    # Resumen
    print()
    print(f"{'='*65}")
    passed = sum(1 for s, *_ in results if s == "PASS")
    failed = [r for r in results if r[0] == "FAIL"]
    warns = [r for r in failed if "WARN:" in r[3]]
    real_fails = [r for r in failed if "WARN:" not in r[3]]

    print(f"  ✅ {passed} PASS  |  ❌ {len(real_fails)} FAIL  |  ⚠️  {len(warns)} WARN")

    if real_fails:
        print()
        print("  FALLOS:")
        for _, name, _, error in real_fails:
            print(f"    ❌ {name}")
            print(f"       {error}")

    print(f"{'='*65}")
    return len(real_fails)


if __name__ == "__main__":
    exit_code = run_all()
    if _conn:
        _conn.close()
    sys.exit(exit_code)
