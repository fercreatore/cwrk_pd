"""
benchmark_viajantes.py — Benchmark de desempeño de viajantes H4/Calzalindo
===========================================================================
Corre en servidor 111 con: py -3 benchmark_viajantes.py
Desde: C:\\cowork_pedidos\\_scripts_oneshot\\

Qué hace:
  1. Calcula deflactor inflacionario (precio promedio por par, base dic-2025)
  2. Extrae métricas mensuales por viajante 2022-2025 y aplica deflactor
  3. Extrae mix de producto por viajante (rubros 1,3,4,5,6) 2024-2025
  4. Extrae mix por subrubro (deportes vs calzado clásico)
  5. Lee sueldos desde moviempl1
  6. Lee nombres de viajantes
  7. Calcula KPIs, Z-scores, percentiles y score compuesto en pandas
  8. Exporta CSV y muestra tabla resumen en consola

Notas técnicas:
  - pyodbc, driver "SQL Server" (SQL Server 2012 RTM, sin TRY_CAST)
  - Depósito 1 = ML/Glam → excluido del benchmark principal
  - Viajantes 7 y 36 = remitos internos → excluidos siempre
"""

import os
import sys
import platform
import textwrap
from datetime import datetime

import pyodbc
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Fix SSL: SQL Server 2012 usa TLS 1.0, incompatible con OpenSSL 3.x
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Conexión
# ---------------------------------------------------------------------------
SERVIDOR = "192.168.2.111"
USUARIO  = "am"
PASSWORD = "dl"
# En Windows usamos el driver nativo; en Mac/Linux el ODBC 17
DRIVER   = "SQL Server" if _is_windows else "ODBC Driver 17 for SQL Server"

# Base por defecto para vistas combinadas
BD_COMPRAS = "msgestionC"

def conectar(base=BD_COMPRAS):
    """Retorna conexión pyodbc a la base indicada en el servidor 111."""
    conn_str = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVIDOR};"
        f"DATABASE={base};"
        f"UID={USUARIO};"
        f"PWD={PASSWORD};"
        "Connection Timeout=30;"
    )
    if not _is_windows:
        conn_str += "TrustServerCertificate=yes;Encrypt=no;"
    return pyodbc.connect(conn_str)


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------
if _is_windows:
    OUTPUT_PATH = r"C:\cowork_pedidos\_informes\benchmark_viajantes_2025.csv"
else:
    # En Mac se guarda local para pruebas
    OUTPUT_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "_informes",
        "benchmark_viajantes_2025.csv",
    )

# ---------------------------------------------------------------------------
# Exclusiones dinamicas desde omicronvt.dbo.viajante_config
# ---------------------------------------------------------------------------
# Fallback hardcodeado: viajantes 7 y 36 (remitos internos) + 1 (duenio).
# En main() se intenta leer la tabla; si falla, se usa este default.
_EXCLUIR_FALLBACK = (
    # Remitos internos
    7, 36,
    # Directivos y personal no comercial
    1,    # Fernando Calaianov
    4,    # Guille Calaianov
    9,    # Tamara Calaianov
    50,   # Leo Calaianov
    323,  # Patricia Calaianov
    740,  # Luciano Lanthier
    755,  # Mati Rodriguez
    1136, # Gonzalo Bernardi
    1148, # Emanuel Cisneros
    # Cuentas REFUERZO (grupales historicas ingresantes)
    20, 21, 22, 23, 24, 25, 26, 28, 29, 30,
    # Cuentas grupales activas
    65,   # ASESORAS CENTRAL
    # Operadores canal digital (ML + TiendaNube, dep 1) — benchmark separado
    545,  # Bilicich Tomas (responsable ML+TN)
    # Encargados de local — su caida de venta refleja cambio de rol, no performance
    68,   # Galvan Tamara (encargada)
    # PENDIENTE: confirmar codigos de otros encargados
)


def _cargar_excluidos(conn):
    """
    Lee viajante_config en omicronvt y retorna una tupla de codigos
    cuyo tipo es 'excluido' o 'grupal' y estan activos.
    Fallback a _EXCLUIR_FALLBACK si la tabla no existe o hay error.
    """
    sql = (
        "SELECT viajante_codigo, tipo "
        "FROM omicronvt.dbo.viajante_config WITH (NOLOCK) "
        "WHERE tipo IN ('excluido', 'grupal', 'encargado', 'ml') AND activo = 1"
    )
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        if rows:
            codigos = tuple(int(r[0]) for r in rows)
            print("  viajante_config: %d codigos excluidos/grupales cargados." % len(codigos))
            return codigos
        else:
            print("  AVISO: viajante_config vacia. Usando fallback %s." % str(_EXCLUIR_FALLBACK))
            return _EXCLUIR_FALLBACK
    except Exception as e:
        print("  AVISO: No se pudo leer viajante_config (%s). Usando fallback %s." % (e, str(_EXCLUIR_FALLBACK)))
        return _EXCLUIR_FALLBACK


def _excluir_sql(codigos):
    """Convierte tupla de codigos en clausula SQL: NOT IN (7, 36, ...)"""
    if len(codigos) == 1:
        return "viajante <> %d" % codigos[0]
    return "viajante NOT IN (%s)" % ", ".join(str(c) for c in codigos)


# ---------------------------------------------------------------------------
# PASO 1: Deflactor inflacionario
# ---------------------------------------------------------------------------
# Precio promedio por par mes a mes desde ventas1 (2020-2025).
# Usamos codigo=1 (ventas) y excluimos remitos internos y grupales.
# deposito IN (0,1,2,6,7,8,9,15) = tiendas propias + web, excluye depositos intermedios.
# SQL Server 2012: no hay TRY_CAST -- todas las columnas son numericas nativas aqui.
# {excluir_in} se reemplaza en main() con la clausula dinamica.

SQL_DEFLACTOR = """
SELECT
    YEAR(fecha)  AS anio,
    MONTH(fecha) AS mes,
    SUM(CAST(total_item AS FLOAT) * CAST(cantidad AS FLOAT))
        / NULLIF(SUM(CAST(cantidad AS FLOAT)), 0) AS precio_medio_par
FROM ventas1
WHERE codigo = 1
  AND {excluir_in}
  AND deposito IN (0, 1, 2, 6, 7, 8, 9, 15)
  AND fecha >= '2020-01-01'
GROUP BY YEAR(fecha), MONTH(fecha)
ORDER BY anio, mes
"""

# ---------------------------------------------------------------------------
# PASO 2: Métricas mensuales por viajante (2022-2025)
# ---------------------------------------------------------------------------
# codigo=1 → venta; codigo=3 → nota de crédito (devolución).
# venta_neta = facturado - devuelto; pares y tickets idem.
# Se agrupa por viajante + año + mes + deposito para poder separar canales.

SQL_METRICAS = """
SELECT
    vv.viajante,
    YEAR(vv.fecha)  AS anio,
    MONTH(vv.fecha) AS mes,
    vv.deposito,
    SUM(CASE WHEN vv.codigo = 1
             THEN CAST(vv.total_item AS FLOAT) * CAST(vv.cantidad AS FLOAT)
             ELSE 0 END)
    - SUM(CASE WHEN vv.codigo = 3
              THEN CAST(vv.total_item AS FLOAT) * CAST(vv.cantidad AS FLOAT)
              ELSE 0 END)                                          AS venta_neta,
    SUM(CASE WHEN vv.codigo = 1
             THEN CAST(vv.precio_costo AS FLOAT) * CAST(vv.cantidad AS FLOAT)
             ELSE 0 END)
    - SUM(CASE WHEN vv.codigo = 3
              THEN CAST(vv.precio_costo AS FLOAT) * CAST(vv.cantidad AS FLOAT)
              ELSE 0 END)                                          AS costo_neto,
    SUM(CASE WHEN vv.codigo = 1
             THEN CAST(vv.cantidad AS FLOAT)
             ELSE 0 END)
    - SUM(CASE WHEN vv.codigo = 3
              THEN CAST(vv.cantidad AS FLOAT)
              ELSE 0 END)                                          AS pares,
    COUNT(DISTINCT CASE WHEN vv.codigo = 1 THEN vv.numero END)
    - COUNT(DISTINCT CASE WHEN vv.codigo = 3 THEN vv.numero END)  AS tickets
FROM ventas1 vv
WHERE vv.codigo IN (1, 3)
  AND {excluir_in}
  AND vv.viajante > 0
  AND vv.deposito IN (0, 1, 2, 6, 7, 8, 9, 15)
  AND vv.fecha >= '2022-01-01'
GROUP BY vv.viajante, YEAR(vv.fecha), MONTH(vv.fecha), vv.deposito
ORDER BY vv.viajante, anio, mes, vv.deposito
"""

# ---------------------------------------------------------------------------
# PASO 3: Mix de producto por rubro (2024-2025)
# ---------------------------------------------------------------------------
# Rubros: 1=DAMAS, 3=HOMBRES, 4=NIÑOS, 5=NIÑAS, 6=UNISEX
# JOIN con msgestion01art para traer rubro del artículo.

SQL_MIX_RUBRO = """
SELECT
    vv.viajante,
    a.rubro,
    SUM(CAST(vv.total_item AS FLOAT) * CAST(vv.cantidad AS FLOAT)) AS venta_rubro
FROM ventas1 vv
JOIN msgestion01art.dbo.articulo a ON a.codigo = vv.articulo
WHERE vv.codigo IN (1, 3)
  AND {excluir_in}
  AND vv.viajante > 0
  AND vv.deposito IN (0, 1, 2, 6, 7, 8, 9, 15)
  AND vv.fecha >= '2024-01-01'
  AND a.rubro IN (1, 3, 4, 5, 6)
GROUP BY vv.viajante, a.rubro
"""

# ---------------------------------------------------------------------------
# PASO 4: Mix por subrubro (para clasificación deportes vs calzado clásico)
# ---------------------------------------------------------------------------

SQL_MIX_SUBRUBRO = """
SELECT
    vv.viajante,
    a.rubro,
    a.subrubro,
    SUM(CAST(vv.total_item AS FLOAT) * CAST(vv.cantidad AS FLOAT)) AS venta_subrubro
FROM ventas1 vv
JOIN msgestion01art.dbo.articulo a ON a.codigo = vv.articulo
WHERE vv.codigo IN (1, 3)
  AND {excluir_in}
  AND vv.viajante > 0
  AND vv.deposito IN (0, 1, 2, 6, 7, 8, 9, 15)
  AND vv.fecha >= '2024-01-01'
GROUP BY vv.viajante, a.rubro, a.subrubro
"""

# Mapa subrubro → industria (fuente: omicronvt.dbo.map_subrubro_industria)
# Documentación completa: _informes/MAPA_SUBRUBROS.md
SUBRUBRO_INDUSTRIA = {
    # Zapatería — calzado clásico y de moda
    1:  'Zapatería',   # ALPARGATAS
    2:  'Zapatería',   # BORCEGOS
    3:  'Zapatería',   # MAQUILLAJE
    4:  'Zapatería',
    5:  'Zapatería',   # CHATA
    6:  'Zapatería',   # CHINELA
    7:  'Zapatería',   # MOCASINES
    8:  'Zapatería',
    9:  'Zapatería',
    11: 'Zapatería',   # OJOTAS
    12: 'Zapatería',   # SANDALIAS
    13: 'Zapatería',   # ZUECOS
    14: 'Zapatería',   # BORCEGOS (variante)
    15: 'Zapatería',   # BOTAS
    16: 'Zapatería',
    17: 'Zapatería',   # GUILLERMINA
    20: 'Zapatería',   # ZAPATO DE VESTIR
    21: 'Zapatería',   # CASUAL
    34: 'Zapatería',
    35: 'Zapatería',   # PANCHA
    37: 'Zapatería',   # FRANCISCANA
    38: 'Zapatería',   # MERREL
    40: 'Zapatería',   # NAUTICO
    41: 'Zapatería',
    42: 'Zapatería',
    43: 'Zapatería',
    44: 'Zapatería',
    56: 'Zapatería',   # FIESTA
    60: 'Zapatería',   # PANTUFLA
    # Deportes — calzado deportivo especializado
    10: 'Deportes',    # ACC. DEPORTIVOS
    19: 'Deportes',    # BOTINES TAPON
    22: 'Deportes',    # CANILLERA
    33: 'Deportes',    # PELOTAS
    45: 'Deportes',    # BOTINES PISTA
    47: 'Deportes',    # ZAPATILLA RUNNING
    48: 'Deportes',    # ZAPATILLA TENNIS
    49: 'Deportes',    # ZAPATILLA TRAINING
    50: 'Deportes',    # ZAPATILLA BASKET
    51: 'Deportes',    # ZAPATILLA OUTDOOR
    53: 'Deportes',    # ZAPATILLA SKATER
    54: 'Deportes',    # BOTIN INDOOR
    59: 'Deportes',    # ROLLER/PATIN
    # Mixto_Zap_Dep — lifestyle / sneaker urbano
    52: 'Mixto_Zap_Dep',   # ZAPATILLA CASUAL
    55: 'Mixto_Zap_Dep',   # ZAPATILLA SNEAKERS
    # Marroquinería
    18: 'Marroquinería',   # CARTERAS
    24: 'Marroquinería',   # PARAGUAS
    25: 'Marroquinería',   # MOCHILAS
    26: 'Marroquinería',   # BILLETERAS
    30: 'Marroquinería',   # BOLSOS
    31: 'Marroquinería',
    39: 'Marroquinería',   # ACC. MARRO
    58: 'Marroquinería',   # CINTOS
    68: 'Marroquinería',   # VALIJAS
    # Indumentaria
    23: 'Indumentaria',    # PANTALON
    46: 'Indumentaria',    # CAMPERAS
    57: 'Indumentaria',    # REMERAS
    61: 'Indumentaria',    # BUZO
    62: 'Indumentaria',    # CALZA
    63: 'Indumentaria',    # MALLA
    # Cosmética — accesorios de cuidado / insumos
    27: 'Cosmética',       # PLANTILLAS
    28: 'Cosmética',       # CORDONES
    29: 'Cosmética',       # MEDIAS
    32: 'Cosmética',       # COSMETICA DE CALZADO
    # Ferretero — seguridad laboral y lluvia
    64: 'Ferretero',       # ZAPATO DE TRABAJO
    65: 'Ferretero',       # BOTA DE LLUVIA
    # Otros
    67: 'Zapatería',       # PROMO FIN DE TEMPORADA
}

# ---------------------------------------------------------------------------
# PASO 5: Sueldos — promedio mensual desde moviempl1
# ---------------------------------------------------------------------------
# codigo_movimiento=10 = haber de sueldo. Se divide entre meses distintos
# para obtener el promedio mensual. numero_cuenta se mapea a viajante
# manualmente más abajo (o via tabla de empleados si existe).

SQL_SUELDOS = """
SELECT
    numero_cuenta,
    SUM(CAST(importe AS FLOAT))
        / NULLIF(COUNT(DISTINCT CAST(fecha_contable AS DATE)), 0) AS sueldo_mensual_prom
FROM msgestion01.dbo.moviempl1
WHERE codigo_movimiento = 10
  AND fecha_contable >= '2024-01-01'
GROUP BY numero_cuenta
"""

# ---------------------------------------------------------------------------
# PASO 6: Nombres de viajantes
# ---------------------------------------------------------------------------

SQL_VIAJANTES = """
SELECT codigo, descripcion FROM viajantes
"""


# ===========================================================================
# Funciones auxiliares
# ===========================================================================

def percentil_grupo(series):
    """Calcula percentil de cada valor dentro de su propio Series usando scipy
    si está disponible, o numpy como fallback."""
    try:
        from scipy.stats import percentileofscore
        return series.apply(
            lambda x: percentileofscore(series.dropna().values, x, kind="rank")
            if not pd.isna(x) else np.nan
        )
    except ImportError:
        # Fallback numpy: rank normalizado
        vals = series.values.astype(float)
        result = np.full(len(vals), np.nan)
        mask = ~np.isnan(vals)
        if mask.sum() > 1:
            ranked = pd.Series(vals[mask]).rank(pct=True) * 100
            result[mask] = ranked.values
        return pd.Series(result, index=series.index)


def zscore_serie(series):
    """Z-score robusto: (x - mean) / std. Retorna NaN si std=0."""
    mu  = series.mean()
    std = series.std()
    if std == 0 or pd.isna(std):
        return pd.Series(np.nan, index=series.index)
    return (series - mu) / std


def slope_lineal(values):
    """Retorna pendiente de regresión lineal simple sobre un array 1D.
    Retorna np.nan si hay menos de 2 puntos no-NaN."""
    arr = np.array(values, dtype=float)
    mask = ~np.isnan(arr)
    if mask.sum() < 2:
        return np.nan
    x = np.arange(len(arr))[mask]
    y = arr[mask]
    # polyfit grado 1: [slope, intercept]
    coeffs = np.polyfit(x, y, 1)
    return float(coeffs[0])


def clasificar(score):
    """Clasifica score compuesto (0-100) en categoría de desempeño."""
    if pd.isna(score):
        return "Sin datos"
    if score >= 80:
        return "Estrella"
    if score >= 60:
        return "Solido"
    if score >= 40:
        return "Promedio"
    if score >= 25:
        return "En desarrollo"
    return "Bajo"


# ===========================================================================
# Main
# ===========================================================================

def main():
    print("=" * 70)
    print("BENCHMARK VIAJANTES H4/CALZALINDO")
    print(f"Ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # Conexion
    # -----------------------------------------------------------------------
    print("\n[1/8] Conectando a SQL Server 111...")
    try:
        conn = conectar(BD_COMPRAS)
    except Exception as e:
        print("  ERROR de conexion: %s" % e)
        sys.exit(1)
    print("  OK.")

    # -----------------------------------------------------------------------
    # Exclusiones dinamicas desde viajante_config
    # -----------------------------------------------------------------------
    print("\n  Cargando exclusiones desde omicronvt.dbo.viajante_config...")
    codigos_excluir = _cargar_excluidos(conn)
    excluir_in      = _excluir_sql(codigos_excluir)
    print("  Clausula de exclusion: %s" % excluir_in)

    # Inyectar la clausula dinamica en todos los SQL que usan {excluir_in}
    sql_deflactor   = SQL_DEFLACTOR.replace("{excluir_in}",   excluir_in)
    sql_metricas    = SQL_METRICAS.replace("{excluir_in}",    excluir_in)
    sql_mix_rubro   = SQL_MIX_RUBRO.replace("{excluir_in}",   excluir_in)
    sql_mix_subrubro = SQL_MIX_SUBRUBRO.replace("{excluir_in}", excluir_in)

    # -----------------------------------------------------------------------
    # PASO 1: Deflactor
    # -----------------------------------------------------------------------
    print("\n[2/8] Calculando deflactor inflacionario (2020-2025)...")
    df_deflactor = pd.read_sql(sql_deflactor, conn)
    print(f"  Filas: {len(df_deflactor)}")

    # Precio de diciembre 2025 como base
    precio_dic2025 = df_deflactor.loc[
        (df_deflactor["anio"] == 2025) & (df_deflactor["mes"] == 12),
        "precio_medio_par",
    ]
    if precio_dic2025.empty or precio_dic2025.iloc[0] == 0 or pd.isna(precio_dic2025.iloc[0]):
        # Fallback: usar el último mes disponible
        last_row = df_deflactor.dropna(subset=["precio_medio_par"]).iloc[-1]
        precio_base = last_row["precio_medio_par"]
        print(f"  AVISO: dic-2025 no disponible. Usando base: {last_row['anio']}-{last_row['mes']:02d} "
              f"= ${precio_base:,.0f}")
    else:
        precio_base = precio_dic2025.iloc[0]
        print(f"  Precio base dic-2025: ${precio_base:,.0f}")

    # Calcular deflactor: ratio base/periodo (>1 en el pasado = infla hacia adelante)
    df_deflactor["deflactor"] = precio_base / df_deflactor["precio_medio_par"].replace(0, np.nan)
    df_deflactor["periodo"] = (
        df_deflactor["anio"].astype(str) + "-"
        + df_deflactor["mes"].astype(str).str.zfill(2)
    )
    deflactor_map = df_deflactor.set_index(["anio", "mes"])["deflactor"].to_dict()
    print(f"  Rango deflactor: {df_deflactor['deflactor'].min():.2f} – {df_deflactor['deflactor'].max():.2f}")

    # -----------------------------------------------------------------------
    # PASO 2: Métricas mensuales por viajante
    # -----------------------------------------------------------------------
    print("\n[3/8] Extrayendo metricas mensuales por viajante (2022-2025)...")
    df_met = pd.read_sql(sql_metricas, conn)
    print("  Filas: %d | Viajantes: %d" % (len(df_met), df_met['viajante'].nunique()))

    # Aplicar deflactor: multiplicar venta_neta y costo_neto por el factor
    df_met["deflactor"] = df_met.apply(
        lambda r: deflactor_map.get((r["anio"], r["mes"]), np.nan), axis=1
    )
    df_met["venta_real"] = df_met["venta_neta"] * df_met["deflactor"]
    df_met["costo_real"] = df_met["costo_neto"] * df_met["deflactor"]

    # -----------------------------------------------------------------------
    # PASO 3: Mix de rubro
    # -----------------------------------------------------------------------
    print("\n[4/8] Extrayendo mix de producto por rubro (2024-2025)...")
    df_rubro = pd.read_sql(sql_mix_rubro, conn)
    print("  Filas: %d" % len(df_rubro))

    # -----------------------------------------------------------------------
    # PASO 4: Mix por subrubro
    # -----------------------------------------------------------------------
    print("\n[5/8] Extrayendo mix por subrubro (2024-2025)...")
    df_subrubro = pd.read_sql(sql_mix_subrubro, conn)
    print("  Filas: %d" % len(df_subrubro))

    # -----------------------------------------------------------------------
    # PASO 5: Sueldos
    # -----------------------------------------------------------------------
    print("\n[6/8] Extrayendo sueldos desde moviempl1...")
    try:
        conn_01 = conectar("msgestion01")
        df_sueldos = pd.read_sql(SQL_SUELDOS, conn_01)
        conn_01.close()
        print(f"  Filas: {len(df_sueldos)}")
    except Exception as e:
        print(f"  AVISO: No se pudo leer sueldos ({e}). Se omiten.")
        df_sueldos = pd.DataFrame(columns=["numero_cuenta", "sueldo_mensual_prom"])

    # -----------------------------------------------------------------------
    # PASO 6: Nombres viajantes
    # -----------------------------------------------------------------------
    print("\n[7/8] Extrayendo nombres de viajantes...")
    df_vjt = pd.read_sql(SQL_VIAJANTES, conn)
    conn.close()
    vjt_nombres = df_vjt.set_index("codigo")["descripcion"].to_dict()
    print(f"  Viajantes en tabla: {len(df_vjt)}")

    # -----------------------------------------------------------------------
    # PASO 7: Cálculos en pandas
    # -----------------------------------------------------------------------
    print("\n[8/8] Calculando KPIs, scores y benchmarks...")

    # -- Excluir depósito 1 (ML/Glam) del benchmark principal ---------------
    # Se conserva en los datos pero se marca; el score se calcula sin él.
    df_bench = df_met[df_met["deposito"] != 1].copy()

    # -- Determinar depósito principal por viajante -------------------------
    # Es el depósito donde cada viajante hizo ≥ 60% de su venta total.
    dep_venta = (
        df_bench.groupby(["viajante", "deposito"])["venta_neta"]
        .sum()
        .reset_index()
    )
    dep_total = dep_venta.groupby("viajante")["venta_neta"].sum().rename("total_venta")
    dep_venta = dep_venta.join(dep_total, on="viajante")
    dep_venta["pct_dep"] = dep_venta["venta_neta"] / dep_venta["total_venta"].replace(0, np.nan)
    dep_principal = (
        dep_venta.sort_values("pct_dep", ascending=False)
        .drop_duplicates("viajante")
        .set_index("viajante")[["deposito", "pct_dep"]]
        .rename(columns={"deposito": "deposito_principal", "pct_dep": "pct_dep_principal"})
    )

    # -- Filtrar: viajantes con ≥ 6 meses activos ---------------------------
    # "Mes activo" = mes con venta_neta > 0
    meses_activos = (
        df_bench[df_bench["venta_neta"] > 0]
        .groupby("viajante")[["anio", "mes"]]
        .apply(lambda g: g.drop_duplicates().shape[0])
        .rename("meses_activos")
    )

    viajantes_validos = meses_activos[meses_activos >= 6].index

    # -- Últimos 6 meses: venta mensual real promedio -----------------------
    # Ordenar todos los periodos disponibles y tomar los últimos 6 activos
    df_bench_sorted = df_bench.sort_values(["viajante", "anio", "mes"])

    def ultimos_6_prom(grupo):
        activos = grupo[grupo["venta_real"] > 0].tail(6)
        if activos.empty:
            return np.nan
        return activos["venta_real"].sum() / len(activos)

    venta_u6 = (
        df_bench_sorted.groupby("viajante")
        .apply(ultimos_6_prom)
        .rename("venta_mensual_real")
    )

    # -- Margen ponderado global por viajante -------------------------------
    totales = df_bench.groupby("viajante").agg(
        venta_total_real=("venta_real", "sum"),
        costo_total_real=("costo_real", "sum"),
        pares_total=("pares", "sum"),
        tickets_total=("tickets", "sum"),
    )
    totales["pct_margen"] = (
        (totales["venta_total_real"] - totales["costo_total_real"])
        / totales["venta_total_real"].replace(0, np.nan)
        * 100
    )

    # -- Pares por ticket y tickets por mes ---------------------------------
    totales["pares_por_ticket"] = totales["pares_total"] / totales["tickets_total"].replace(0, np.nan)
    totales = totales.join(meses_activos)
    totales["tickets_por_mes"] = totales["tickets_total"] / totales["meses_activos"].replace(0, np.nan)

    # -- Tendencia: slope de regresión sobre los últimos 12 meses -----------
    # Agrupamos por viajante+periodo (anio,mes) sumando depósitos

    df_agg_mensual = (
        df_bench.groupby(["viajante", "anio", "mes"])["venta_real"]
        .sum()
        .reset_index()
        .sort_values(["viajante", "anio", "mes"])
    )

    def calcular_tendencia(grupo):
        u12 = grupo.tail(12)["venta_real"].values
        return slope_lineal(u12)

    tendencia = (
        df_agg_mensual.groupby("viajante")
        .apply(calcular_tendencia)
        .rename("tendencia")
    )

    # -- Consistencia: 1 - cv (coef. de variación) sobre meses activos ------
    def calcular_consistencia(grupo):
        activos = grupo[grupo["venta_real"] > 0]["venta_real"]
        if len(activos) < 2:
            return np.nan
        mu  = activos.mean()
        std = activos.std()
        if mu == 0:
            return np.nan
        return 1.0 - (std / mu)

    consistencia = (
        df_agg_mensual.groupby("viajante")
        .apply(calcular_consistencia)
        .rename("consistencia")
    )

    # -- Armar DataFrame base -----------------------------------------------
    df_kpi = pd.DataFrame(index=viajantes_validos)
    df_kpi.index.name = "viajante"
    df_kpi = df_kpi.join(dep_principal)
    df_kpi = df_kpi.join(venta_u6)
    df_kpi = df_kpi.join(totales[["pct_margen", "pares_por_ticket", "tickets_por_mes",
                                   "venta_total_real", "pares_total", "tickets_total",
                                   "meses_activos"]])
    df_kpi = df_kpi.join(tendencia)
    df_kpi = df_kpi.join(consistencia)

    # -- Mix de rubro -------------------------------------------------------
    RUBROS = {1: "damas", 3: "hombres", 4: "ninos", 5: "ninas", 6: "unisex"}
    rubro_total = df_rubro.groupby("viajante")["venta_rubro"].sum().rename("total_rubro")
    df_rubro2 = df_rubro.join(rubro_total, on="viajante")
    df_rubro2["pct_rubro"] = df_rubro2["venta_rubro"] / df_rubro2["total_rubro"].replace(0, np.nan)
    rubro_pivot = df_rubro2.pivot_table(
        index="viajante", columns="rubro", values="pct_rubro", fill_value=0.0
    )
    rubro_pivot.columns = [f"pct_{RUBROS.get(c, str(c))}" for c in rubro_pivot.columns]
    # Asegurar que existan las columnas aunque el rubro no tenga datos
    for col in ["pct_damas", "pct_hombres", "pct_ninos", "pct_ninas", "pct_unisex"]:
        if col not in rubro_pivot.columns:
            rubro_pivot[col] = 0.0

    df_kpi = df_kpi.join(rubro_pivot, how="left")

    # Rubro principal (el de mayor %)
    cols_rubro = [c for c in df_kpi.columns if c.startswith("pct_") and c[4:] in RUBROS.values()]
    if cols_rubro:
        df_kpi["rubro_principal"] = df_kpi[cols_rubro].idxmax(axis=1).str.replace("pct_", "")
    else:
        df_kpi["rubro_principal"] = np.nan

    # -- Industria principal por viajante -----------------------------------
    # Se calcula desde df_subrubro: para cada viajante, la industria del
    # subrubro con mayor venta (usando SUBRUBRO_INDUSTRIA definido arriba).
    # Industrias: Zapatería, Deportes, Mixto_Zap_Dep, Marroquinería,
    #             Indumentaria, Cosmética, Ferretero.
    df_subrubro["industria"] = df_subrubro["subrubro"].map(SUBRUBRO_INDUSTRIA).fillna("Sin clasificar")
    ind_por_vjt = (
        df_subrubro.groupby(["viajante", "industria"])["venta_subrubro"]
        .sum()
        .reset_index()
    )
    ind_total = ind_por_vjt.groupby("viajante")["venta_subrubro"].sum().rename("total_ind")
    ind_por_vjt = ind_por_vjt.join(ind_total, on="viajante")
    ind_por_vjt["pct_industria"] = ind_por_vjt["venta_subrubro"] / ind_por_vjt["total_ind"].replace(0, np.nan)

    industria_principal = (
        ind_por_vjt[ind_por_vjt["industria"] != "Sin clasificar"]
        .sort_values("pct_industria", ascending=False)
        .drop_duplicates("viajante")
        .set_index("viajante")[["industria", "pct_industria"]]
        .rename(columns={"industria": "industria_principal", "pct_industria": "pct_industria_principal"})
    )
    df_kpi = df_kpi.join(industria_principal, how="left")

    # Tabla industria pivot: % por industria por viajante
    ind_pivot = ind_por_vjt.pivot_table(
        index="viajante", columns="industria", values="pct_industria", fill_value=0.0
    )
    industrias_cols = ["Zapatería", "Deportes", "Mixto_Zap_Dep", "Marroquinería",
                       "Indumentaria", "Cosmética", "Ferretero"]
    for ind_col in industrias_cols:
        safe = f"pct_ind_{ind_col.lower().replace('_', '').replace('é', 'e').replace('í', 'i').replace('ó', 'o')}"
        df_kpi[safe] = ind_pivot[ind_col] if ind_col in ind_pivot.columns else 0.0

    # -- Sueldos: join por numero_cuenta ------------------------------------
    # Actualmente no hay tabla que mapee viajante→numero_cuenta directamente.
    # Se agrega la columna para completar a mano o extender más adelante.
    df_kpi["sueldo_mensual_prom"] = np.nan  # placeholder

    # -- Z-scores dentro del grupo (mismo deposito_principal) ---------------
    metricas_z = ["venta_mensual_real", "pct_margen", "pares_por_ticket"]
    for metrica in metricas_z:
        col_z = f"z_{metrica}"
        df_kpi[col_z] = np.nan
        for dep, grupo in df_kpi.groupby("deposito_principal"):
            idx = grupo.index
            df_kpi.loc[idx, col_z] = zscore_serie(grupo[metrica]).values

    # -- Percentiles dentro del grupo (mismo deposito_principal) ------------
    metricas_pct = ["venta_mensual_real", "pct_margen", "pares_por_ticket", "consistencia"]
    for metrica in metricas_pct:
        col_p = f"pctil_{metrica}"
        df_kpi[col_p] = np.nan
        for dep, grupo in df_kpi.groupby("deposito_principal"):
            idx = grupo.index
            df_kpi.loc[idx, col_p] = percentil_grupo(grupo[metrica]).values

    # -- Score compuesto ----------------------------------------------------
    # 40% venta real | 30% margen | 15% pares/ticket | 15% consistencia
    df_kpi["score_compuesto"] = (
        0.40 * df_kpi["pctil_venta_mensual_real"].fillna(0)
        + 0.30 * df_kpi["pctil_pct_margen"].fillna(0)
        + 0.15 * df_kpi["pctil_pares_por_ticket"].fillna(0)
        + 0.15 * df_kpi["pctil_consistencia"].fillna(0)
    )

    # -- Clasificación ------------------------------------------------------
    df_kpi["clasificacion"] = df_kpi["score_compuesto"].apply(clasificar)

    # -- Nombres -----------------------------------------------------------
    df_kpi["nombre"] = df_kpi.index.map(vjt_nombres).fillna("Sin nombre")

    # Reordenar columnas para el CSV
    cols_orden = [
        "nombre",
        "deposito_principal", "pct_dep_principal",
        "meses_activos",
        "venta_mensual_real", "venta_total_real",
        "pct_margen",
        "pares_por_ticket", "tickets_por_mes",
        "tendencia", "consistencia",
        "rubro_principal",
        "pct_damas", "pct_hombres", "pct_ninos", "pct_ninas", "pct_unisex",
        "industria_principal", "pct_industria_principal",
        "pct_ind_zapateria", "pct_ind_deportes", "pct_ind_mixtozapdep",
        "pct_ind_marroquineria", "pct_ind_indumentaria",
        "pct_ind_cosmetica", "pct_ind_ferretero",
        "sueldo_mensual_prom",
        "z_venta_mensual_real", "z_pct_margen", "z_pares_por_ticket",
        "pctil_venta_mensual_real", "pctil_pct_margen",
        "pctil_pares_por_ticket", "pctil_consistencia",
        "score_compuesto", "clasificacion",
    ]
    cols_presentes = [c for c in cols_orden if c in df_kpi.columns]
    df_out = df_kpi[cols_presentes].copy()
    df_out.index.name = "viajante"

    # -- Flags de outliers estadisticos (no excluir, solo marcar) -----------
    df_out["flag_volumen_outlier"] = df_out.get("z_venta_mensual_real", pd.Series(dtype=float)).abs() > 3.0
    df_out["flag_margen_anomalo"]  = (
        (df_out.get("pct_margen", pd.Series(dtype=float)) < 30)
        | (df_out.get("pct_margen", pd.Series(dtype=float)) > 65)
    )
    df_out["flag_ppt_alto"]   = df_out.get("pares_por_ticket", pd.Series(dtype=float)) > 10
    df_out["flag_estacional"] = df_out.get("consistencia", pd.Series(dtype=float)) < 0.40

    # -- Arquetipo -----------------------------------------------------------
    df_out["arquetipo"] = df_out.apply(asignar_arquetipo, axis=1)

    # -----------------------------------------------------------------------
    # PASO 8: Output
    # -----------------------------------------------------------------------

    # -- Exportar CSV -------------------------------------------------------
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df_out.to_csv(OUTPUT_PATH, sep=";", decimal=",", encoding="utf-8-sig", float_format="%.2f")
    print(f"\n  CSV exportado: {OUTPUT_PATH}")

    # -- Tabla P25/P50/P75/P90 por deposito ---------------------------------
    print("\n" + "=" * 70)
    print("BENCHMARKS P25 / P50 / P75 / P90 POR DEPOSITO")
    print("=" * 70)

    metricas_bench = {
        "venta_mensual_real": "Venta mensual real $",
        "pct_margen":         "Margen %",
        "pares_por_ticket":   "Pares/ticket",
        "tickets_por_mes":    "Tickets/mes",
        "consistencia":       "Consistencia",
    }

    for dep, grupo in df_out.groupby("deposito_principal"):
        print(f"\n  Deposito {int(dep)} — {len(grupo)} viajantes")
        print(f"  {'Metrica':<25} {'P25':>10} {'P50':>10} {'P75':>10} {'P90':>10}")
        print(f"  {'-'*65}")
        for col, label in metricas_bench.items():
            if col not in grupo.columns:
                continue
            serie = grupo[col].dropna()
            if serie.empty:
                continue
            p25, p50, p75, p90 = np.percentile(serie, [25, 50, 75, 90])
            if col == "pct_margen":
                print(f"  {label:<25} {p25:>9.1f}% {p50:>9.1f}% {p75:>9.1f}% {p90:>9.1f}%")
            elif col in ("pares_por_ticket", "tickets_por_mes", "consistencia"):
                print(f"  {label:<25} {p25:>10.2f} {p50:>10.2f} {p75:>10.2f} {p90:>10.2f}")
            else:
                print(f"  {label:<25} {p25:>10,.0f} {p50:>10,.0f} {p75:>10,.0f} {p90:>10,.0f}")

    # -- Top 10 por score compuesto -----------------------------------------
    print("\n" + "=" * 70)
    print("TOP 10 VIAJANTES POR SCORE COMPUESTO")
    print("=" * 70)
    top10 = df_out.sort_values("score_compuesto", ascending=False).head(10)
    print(f"\n  {'#':<3} {'Vj':>4} {'Nombre':<25} {'Dep':>4} {'Score':>7} "
          f"{'Vta/mes':>12} {'Margen':>7} {'P/Tkt':>6} {'Clasif'}")
    print(f"  {'-'*85}")
    for i, (vj, row) in enumerate(top10.iterrows(), 1):
        nombre = str(row.get("nombre", ""))[:24]
        dep    = int(row["deposito_principal"]) if not pd.isna(row.get("deposito_principal")) else "-"
        score  = f"{row['score_compuesto']:.1f}" if not pd.isna(row.get("score_compuesto")) else "-"
        vta    = f"${row['venta_mensual_real']:,.0f}" if not pd.isna(row.get("venta_mensual_real")) else "-"
        margen = f"{row['pct_margen']:.1f}%" if not pd.isna(row.get("pct_margen")) else "-"
        ppt    = f"{row['pares_por_ticket']:.1f}" if not pd.isna(row.get("pares_por_ticket")) else "-"
        clasif = row.get("clasificacion", "-")
        print(f"  {i:<3} {vj:>4} {nombre:<25} {str(dep):>4} {score:>7} {vta:>12} "
              f"{margen:>7} {ppt:>6} {clasif}")

    # -- Distribución de clasificaciones ------------------------------------
    print("\n" + "=" * 70)
    print("DISTRIBUCION DE CLASIFICACIONES")
    print("=" * 70)
    clasif_counts = df_out["clasificacion"].value_counts()
    total_vjt = len(df_out)
    for cat in ["Estrella", "Solido", "Promedio", "En desarrollo", "Bajo", "Sin datos"]:
        n = clasif_counts.get(cat, 0)
        pct = n / total_vjt * 100 if total_vjt > 0 else 0
        barra = "#" * int(pct / 2)
        print(f"  {cat:<15} {n:>3} ({pct:>5.1f}%)  {barra}")

    # -- Hallazgos principales ----------------------------------------------
    print("\n" + "=" * 70)
    print("HALLAZGOS PRINCIPALES")
    print("=" * 70)

    estrellas = df_out[df_out["clasificacion"] == "Estrella"]
    bajos     = df_out[df_out["clasificacion"] == "Bajo"]
    tendencia_pos = df_out[df_out["tendencia"] > 0]
    tendencia_neg = df_out[df_out["tendencia"] < 0]

    print(f"\n  - Viajantes evaluados:      {len(df_out)}")
    print(f"  - Estrellas (score ≥80):    {len(estrellas)}")
    print(f"  - Bajo desempeno (<25):     {len(bajos)}")
    print(f"  - Tendencia positiva:       {len(tendencia_pos)} viajantes")
    print(f"  - Tendencia negativa:       {len(tendencia_neg)} viajantes")

    if not estrellas.empty:
        top_star = estrellas.sort_values("score_compuesto", ascending=False).iloc[0]
        print(f"\n  Mejor score: {vjt_nombres.get(top_star.name, top_star.name)} "
              f"({top_star.name}) — score {top_star['score_compuesto']:.1f}")

    vta_mediana_global = df_out["venta_mensual_real"].median()
    margen_mediano_global = df_out["pct_margen"].median()
    if not pd.isna(vta_mediana_global):
        print(f"  Venta mensual mediana global: ${vta_mediana_global:,.0f} (pesos dic-2025)")
    if not pd.isna(margen_mediano_global):
        print(f"  Margen mediano global:        {margen_mediano_global:.1f}%")

    # Rubro dominante por deposito
    if "rubro_principal" in df_out.columns:
        print("\n  Rubro dominante por deposito:")
        for dep, grupo in df_out.groupby("deposito_principal"):
            rubro_dep = grupo["rubro_principal"].value_counts()
            if not rubro_dep.empty:
                print(f"    Dep {int(dep)}: {rubro_dep.index[0]} ({rubro_dep.iloc[0]} viajantes)")

    # Industria principal por viajante
    if "industria_principal" in df_out.columns:
        print("\n  Industria principal por viajante (mix de subrubro):")
        ind_counts = df_out["industria_principal"].value_counts()
        for ind, n in ind_counts.items():
            pct = n / len(df_out) * 100
            print(f"    {ind:<20} {n:>3} viajantes ({pct:.0f}%)")

    # -- Distribucion por arquetipo -----------------------------------------
    if "arquetipo" in df_out.columns:
        print("\n" + "=" * 70)
        print("DISTRIBUCION POR ARQUETIPO")
        print("=" * 70)
        arq_counts = df_out["arquetipo"].value_counts()
        for arq, n in arq_counts.items():
            pct = n / len(df_out) * 100
            print(f"  {arq:<30} {n:>3} ({pct:>5.1f}%)")

    # -- Flags activos -------------------------------------------------------
    flags = {
        "flag_volumen_outlier": "Outlier de volumen (Z>3)",
        "flag_margen_anomalo":  "Margen anomalo (<30% o >65%)",
        "flag_ppt_alto":        "Pares/ticket > 10",
        "flag_estacional":      "Baja consistencia (<0.40)",
    }
    flags_activos = {k: v for k, v in flags.items() if k in df_out.columns and df_out[k].sum() > 0}
    if flags_activos:
        print("\n" + "=" * 70)
        print("FLAGS DE OUTLIERS")
        print("=" * 70)
        for flag_col, flag_label in flags_activos.items():
            sub = df_out[df_out[flag_col] == True]
            nombres_flag = [
                str(vjt_nombres.get(vj, vj)) for vj in sub.index
            ]
            print(f"\n  {flag_label} ({len(sub)} viajantes):")
            for nombre_f in nombres_flag[:10]:
                print(f"    - {nombre_f}")

    print("\n" + "=" * 70)
    print("Listo.")
    print("=" * 70)


def asignar_arquetipo(row):
    """
    Asigna un arquetipo a cada viajante basado en clasificacion + industria
    + consistencia + volumen. Llama despues de calcular score_compuesto.
    Ver ARQUETIPOS_VIAJANTES.md para la logica completa.
    """
    clasif     = row.get("clasificacion", "") or ""
    industria  = str(row.get("industria_principal", "") or "")
    consistencia = row.get("consistencia", 0) or 0
    venta        = row.get("venta_mensual_real", 0) or 0
    tendencia    = row.get("tendencia", 0) or 0

    if clasif in ("Estrella", "Solido") and venta > 12_000_000:
        return "Generalista Voluminosa"
    if clasif == "Estrella" and "Deporte" in industria:
        return "Estrella Deportes"
    if clasif in ("Estrella", "Solido") and "Zapater" in industria and consistencia > 0.60:
        return "Zapaterista Estable"
    if clasif == "Solido" and consistencia > 0.55:
        if tendencia > 200_000:
            return "Solida en Formacion"
        return "Generalista Mixta Estable"
    if clasif == "Promedio":
        return "Promedio Estacional"
    if clasif in ("En desarrollo", "Bajo"):
        return "En Evaluacion"
    return "Sin clasificar"


if __name__ == "__main__":
    main()
