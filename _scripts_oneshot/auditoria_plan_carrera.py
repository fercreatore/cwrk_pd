"""
auditoria_plan_carrera.py — Auditoria de roles y plan de carrera H4/Calzalindo
===============================================================================
Corre en servidor 111 con: py -3 C:\\cowork_pedidos\\_scripts_oneshot\\auditoria_plan_carrera.py
O en Mac (lectura de replica 111): python3 auditoria_plan_carrera.py

Que hace:
  1. Lee todos los viajantes con ventas en 2022-2025
  2. Cruza con sueldos de moviempl1 (cod=10)
  3. Detecta el rol actual de cada viajante segun patron sueldo/venta:
       - vendedor_activo       : vendiendo regularmente hoy
       - estrella              : vendedor de alto volumen y consistencia
       - encargado_activo      : sueldo continuo, venta casi cero (cambio de funcion)
       - encargado_sospechoso  : cayo >80% en venta, sueldo siguio
       - canal_digital         : deposito 1 (ML + TN)
       - en_formacion          : < 12 meses activos, tendencia creciente
       - latente               : vendio bien, hace 3+ meses sin actividad
       - salida                : sueldo Y venta ambos en cero hace 3+ meses
       - comisionista_pura     : vende sin sueldo registrado
  4. Califica cada nivel segun el framework de plan de carrera
  5. Identifica puestos vacios en cada local
  6. Exporta CSV + informe MD con el plan de carrera y las brechas

Salidas:
  - C:\\cowork_pedidos\\_informes\\auditoria_plan_carrera_YYYYMM.csv
  - C:\\cowork_pedidos\\_informes\\PLAN_CARRERA.md (sobreescribe)
"""

import os
import sys
import platform
import textwrap
from datetime import datetime, date

import pyodbc
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# SSL fix (igual que benchmark)
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
# Conexion
# ---------------------------------------------------------------------------
SERVIDOR = "192.168.2.111"
USUARIO  = "am"
PASSWORD = "dl"
DRIVER   = "SQL Server" if _is_windows else "ODBC Driver 17 for SQL Server"

def conectar(base="msgestion01"):
    conn_str = (
        "DRIVER={%s};"
        "SERVER=%s;"
        "DATABASE=%s;"
        "UID=%s;"
        "PWD=%s;"
        "Connection Timeout=30;"
    ) % (DRIVER, SERVIDOR, base, USUARIO, PASSWORD)
    if not _is_windows:
        conn_str += "TrustServerCertificate=yes;Encrypt=no;"
    return pyodbc.connect(conn_str)

# ---------------------------------------------------------------------------
# Rutas de salida
# ---------------------------------------------------------------------------
_HOY = datetime.now().strftime("%Y%m")
if _is_windows:
    _BASE_OUT = r"C:\cowork_pedidos\_informes"
else:
    _BASE_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_informes")

OUTPUT_CSV = os.path.join(_BASE_OUT, "auditoria_plan_carrera_%s.csv" % _HOY)
OUTPUT_MD  = os.path.join(_BASE_OUT, "PLAN_CARRERA.md")

# ---------------------------------------------------------------------------
# MARCO DEL PLAN DE CARRERA
# Niveles, criterios, KPIs y rangos salariales (en pesos, base abr-2026)
# ---------------------------------------------------------------------------
NIVELES_CARRERA = {
    1: {
        "nombre":   "Vendedor/a Junior",
        "criterios_acceso": [
            "Menos de 6 meses activos en el ERP",
            "Score benchmark < 40 o sin datos suficientes",
        ],
        "kpis": [
            "Ventas mensuales > $2M/mes (deflactado)",
            "Asistencia y puntualidad",
            "Manejo del sistema de facturacion",
        ],
        "salario_rango": "$600k - $900k/mes",
        "condicion_avance": "6 meses activos + score benchmark >= 40 + aprobacion encargado",
        "tipo_contrato": "Relacion de dependencia o comision con anticipo fijo",
    },
    2: {
        "nombre":   "Vendedor/a Promedio",
        "criterios_acceso": [
            "6-18 meses activos",
            "Score benchmark 40-59 (clasificacion Promedio o En desarrollo creciente)",
        ],
        "kpis": [
            "Ventas mensuales > $4M/mes (deflactado)",
            "Margen >= 48%",
            "Consistencia (1-CV) > 0.40",
            "Asistencia sin ausentismo cronico",
        ],
        "salario_rango": "$900k - $1.4M/mes",
        "condicion_avance": "Score benchmark >= 60 + 12 meses consecutivos activos + recomendacion encargado",
        "tipo_contrato": "Relacion de dependencia + comision sobre ticket",
    },
    3: {
        "nombre":   "Vendedor/a Senior / Solido",
        "criterios_acceso": [
            "12+ meses activos",
            "Score benchmark 60-79 (clasificacion Solido)",
        ],
        "kpis": [
            "Ventas mensuales > $8M/mes (deflactado)",
            "Margen >= 49%",
            "Consistencia > 0.50",
            "Tendencia estable o positiva",
        ],
        "salario_rango": "$1.4M - $2.2M/mes",
        "condicion_avance": "Score >= 80 (Estrella) por 2 trimestres consecutivos, O decision de migrar a Encargado/Especialista",
        "tipo_contrato": "Relacion de dependencia + comision progresiva por tramos",
    },
    4: {
        "nombre":   "Vendedor/a Estrella",
        "criterios_acceso": [
            "Score benchmark >= 80 por 2 trimestres",
            "Volumen > P75 de su deposito",
        ],
        "kpis": [
            "Ventas mensuales > P75 del deposito (deflactado)",
            "Margen > mediana del deposito",
            "Consistencia > 0.60",
            "Score compuesto >= 80",
        ],
        "salario_rango": "$2.2M - $3.5M/mes (sueldo + comision variable)",
        "condicion_avance": "Por eleccion: puede optar por Encargado de local o Especialista canal digital",
        "tipo_contrato": "Comision pura o sueldo base reducido + comision agresiva. Fee >= 8% sobre venta neta.",
    },
    5: {
        "nombre":   "Encargado/a de Local",
        "criterios_acceso": [
            "Historial previo como Vendedor Senior o Estrella",
            "Designacion formal por direccion",
        ],
        "kpis": [
            "Conversion del local (% visitas que compran)",
            "Ticket promedio del local",
            "Ausentismo del equipo (dias perdidos / dias laborables)",
            "Diferencias de inventario < 0.5% mensual",
            "Satisfaction del equipo (encuesta semestral)",
            "NO se mide venta individual propia",
        ],
        "salario_rango": "$2.5M - $4M/mes fijo + bonus por KPIs de local",
        "condicion_avance": "N/A — es el techo de la rama de tienda fisica. Puede derivar a Gerencia.",
        "tipo_contrato": "Relacion de dependencia. Sueldo fijo + bonus trimestral por cumplimiento KPIs local.",
    },
    6: {
        "nombre":   "Especialista Canal Digital",
        "criterios_acceso": [
            "Historial en ventas presenciales O habilidades digitales demostradas",
            "Designacion por direccion",
        ],
        "kpis": [
            "GMV total (ML + TiendaNube)",
            "Unidades despachadas / mes",
            "Tasa de devoluciones (objetivo < 5%)",
            "Calificacion promedio ML (objetivo >= 98%)",
            "Publicaciones activas y posicionamiento",
            "NO se compara con vendedores de piso en ningun metrica",
        ],
        "salario_rango": "$2M - $3.5M/mes",
        "condicion_avance": "N/A — especialista de canal. Puede derivar a Gerencia.",
        "tipo_contrato": "Relacion de dependencia. Sueldo fijo + bonus por GMV.",
    },
}

# ---------------------------------------------------------------------------
# PASO 1: Cargar series mensuales viajante x mes (ventas + sueldo)
# ---------------------------------------------------------------------------

SQL_SERIES = """
SELECT
    v.viajante,
    YEAR(v.fecha)  AS anio,
    MONTH(v.fecha) AS mes,
    SUM(CASE
        WHEN v.codigo = 1 THEN CAST(v.total_item AS FLOAT) * CAST(v.cantidad AS FLOAT)
        ELSE              -CAST(v.total_item AS FLOAT) * CAST(v.cantidad AS FLOAT)
    END) AS venta_neta,
    SUM(CAST(v.cantidad AS FLOAT)) AS pares
FROM {bd}.dbo.ventas1 v WITH (NOLOCK)
WHERE v.codigo IN (1, 3)
  AND v.viajante NOT IN (7, 36)
  AND YEAR(v.fecha) >= 2022
GROUP BY v.viajante, YEAR(v.fecha), MONTH(v.fecha)
"""

SQL_SUELDOS = """
SELECT
    m.numero_cuenta AS viajante,
    YEAR(m.fecha_contable)  AS anio,
    MONTH(m.fecha_contable) AS mes,
    SUM(CAST(m.importe AS FLOAT)) AS sueldo
FROM {bd}.dbo.moviempl1 m WITH (NOLOCK)
WHERE m.codigo_movimiento = 10
  AND YEAR(m.fecha_contable) >= 2022
GROUP BY m.numero_cuenta, YEAR(m.fecha_contable), MONTH(m.fecha_contable)
"""

SQL_NOMBRES = """
SELECT codigo AS viajante, descripcion AS nombre
FROM msgestion01.dbo.viajantes WITH (NOLOCK)
"""

SQL_DEPOSITO = """
SELECT
    viajante,
    deposito,
    SUM(CASE
        WHEN codigo=1 THEN CAST(total_item AS FLOAT)*CAST(cantidad AS FLOAT)
        ELSE              -CAST(total_item AS FLOAT)*CAST(cantidad AS FLOAT)
    END) AS venta_dep
FROM msgestion01.dbo.ventas1 WITH (NOLOCK)
WHERE codigo IN (1,3) AND viajante NOT IN (7,36)
  AND YEAR(fecha) >= 2024
GROUP BY viajante, deposito
"""

SQL_DEPOSITO_03 = SQL_DEPOSITO.replace("msgestion01", "msgestion03")

SQL_CONFIG = """
SELECT viajante_codigo, nombre, tipo, deposito_principal, observaciones
FROM omicronvt.dbo.viajante_config WITH (NOLOCK)
WHERE activo = 1
"""

def _sql(conn, sql):
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    cur.close()
    return pd.DataFrame([list(r) for r in rows], columns=cols)


# ---------------------------------------------------------------------------
# PASO 2: Detectar rol de cada viajante
# ---------------------------------------------------------------------------

def _ult_mes_activo(serie, col):
    """Devuelve el ultimo periodo (anio, mes) donde col > 0."""
    activos = serie[serie[col] > 0]
    if activos.empty:
        return None
    ultima = activos.sort_values(["anio", "mes"]).iloc[-1]
    return (int(ultima["anio"]), int(ultima["mes"]))

def _meses_desde(periodo, ahora=None):
    """Cuantos meses han pasado desde el periodo dado hasta hoy."""
    if periodo is None:
        return 999
    if ahora is None:
        ahora = (datetime.now().year, datetime.now().month)
    return (ahora[0] - periodo[0]) * 12 + (ahora[1] - periodo[1])

def _pico_venta(serie):
    """Devuelve la venta maxima mensual historica (ultimos 36 meses)."""
    return serie["venta_neta"].clip(lower=0).max()

def _promedio_venta_activos(serie, n_ultimos=6):
    """Promedio de venta de los ultimos n meses donde vendio algo."""
    activos = serie[serie["venta_neta"] > 0].sort_values(["anio", "mes"]).tail(n_ultimos)
    if activos.empty:
        return 0.0
    return activos["venta_neta"].mean()

def _meses_activos_total(serie):
    return int((serie["venta_neta"] > 0).sum())

def _meses_sueldo(serie):
    return int((serie["sueldo"] > 0).sum())

def _sueldo_reciente(serie, n=3):
    """Promedio de sueldo en los ultimos n meses con registro."""
    ult = serie.sort_values(["anio", "mes"]).tail(n)
    return ult["sueldo"].mean()

def detectar_rol(viajante, serie, config_row=None):
    """
    Clasifica al viajante en un rol del plan de carrera.
    serie: DataFrame con columnas anio, mes, venta_neta, sueldo
    config_row: fila de viajante_config si existe

    Retorna dict con rol, nivel, confianza, notas
    """
    ahora = (datetime.now().year, datetime.now().month)

    # Si ya esta en config con tipo definido, respetarlo salvo 'individual'
    if config_row is not None:
        tipo_config = str(config_row.get("tipo", "individual"))
        if tipo_config == "encargado":
            return {
                "rol": "encargado_activo",
                "nivel": 5,
                "confianza": "config",
                "nota": config_row.get("observaciones", ""),
            }
        if tipo_config == "ml":
            return {
                "rol": "canal_digital",
                "nivel": 6,
                "confianza": "config",
                "nota": "Canal ML/TN — benchmark separado",
            }
        if tipo_config in ("excluido", "grupal"):
            return {
                "rol": tipo_config,
                "nivel": 0,
                "confianza": "config",
                "nota": config_row.get("observaciones", ""),
            }

    # No en config (o tipo='individual') — detectar por patron
    ult_venta = _ult_mes_activo(serie, "venta_neta")
    ult_sueldo = _ult_mes_activo(serie, "sueldo")
    meses_sin_venta = _meses_desde(ult_venta, ahora)
    meses_sin_sueldo = _meses_desde(ult_sueldo, ahora)
    pico = _pico_venta(serie)
    venta_reciente = _promedio_venta_activos(serie, 6)
    meses_activos = _meses_activos_total(serie)
    tiene_sueldo = _meses_sueldo(serie) > 0
    sueldo_rec = _sueldo_reciente(serie, 3)

    # Canal digital: deposito 1 dominante
    if config_row is not None and config_row.get("deposito_principal") == 1:
        return {
            "rol": "canal_digital",
            "nivel": 6,
            "confianza": "alta",
            "nota": "Deposito principal = 1 (ML/TN)",
        }

    # Salida definitiva: sin venta Y sin sueldo hace 3+ meses
    if meses_sin_venta >= 3 and meses_sin_sueldo >= 3:
        return {
            "rol": "salida",
            "nivel": 0,
            "confianza": "alta",
            "nota": "Ultimo periodo activo: %s/%02d" % (ult_venta or ("?", 0)),
        }

    # Encargado activo: sueldo continuo + venta < 20% del pico hace 3+ meses
    if (meses_sin_sueldo == 0 and sueldo_rec > 0
            and pico > 1_000_000
            and venta_reciente < pico * 0.20
            and meses_sin_venta >= 3):
        return {
            "rol": "encargado_activo",
            "nivel": 5,
            "confianza": "media",
            "nota": "Venta actual %.0f%% del pico historico. Posible cambio de funcion." % (
                venta_reciente / pico * 100 if pico > 0 else 0),
        }

    # Encargado sospechoso: sueldo siguio subiendo mientras venta bajo >70%
    serie_ord = serie.sort_values(["anio", "mes"])
    pico_idx = serie_ord["venta_neta"].idxmax() if not serie_ord.empty else None
    if pico_idx is not None:
        pico_mes = serie_ord.loc[pico_idx]
        post_pico = serie_ord.loc[pico_idx:]
        if len(post_pico) >= 4:
            venta_post = post_pico["venta_neta"].clip(lower=0).mean()
            sueldo_post = post_pico["sueldo"].mean()
            sueldo_pre  = serie_ord.loc[:pico_idx]["sueldo"].mean()
            if (venta_post < pico * 0.30
                    and sueldo_post > sueldo_pre * 0.80
                    and meses_sin_venta >= 2):
                return {
                    "rol": "encargado_sospechoso",
                    "nivel": 5,
                    "confianza": "baja",
                    "nota": "Venta cayo >70%% del pico mientras sueldo se mantuvo. Verificar manualmente.",
                }

    # Comisionista pura: vende activamente sin sueldo registrado
    if meses_sin_venta < 3 and not tiene_sueldo and venta_reciente > 500_000:
        return {
            "rol": "comisionista_pura",
            "nivel": 4,
            "confianza": "alta",
            "nota": "Vende sin sueldo en moviempl1. Posible freelance/comisionista.",
        }

    # Vendedor latente: tuvo actividad pero lleva 3-12 meses sin vender
    if 3 <= meses_sin_venta < 12 and pico > 500_000:
        return {
            "rol": "latente",
            "nivel": 2,
            "confianza": "media",
            "nota": "Sin ventas hace %d meses. Pico historico $%s" % (
                meses_sin_venta, "{:,.0f}".format(pico)),
        }

    # En formacion: poco historial
    if meses_activos < 6:
        return {
            "rol": "en_formacion",
            "nivel": 1,
            "confianza": "alta",
            "nota": "%d meses activos. Evaluacion temprana." % meses_activos,
        }

    # Activo — clasificar por volumen
    if meses_sin_venta < 3:
        if venta_reciente >= 15_000_000:
            return {
                "rol": "estrella",
                "nivel": 4,
                "confianza": "alta",
                "nota": "Venta reciente promedio $%s/mes" % "{:,.0f}".format(venta_reciente),
            }
        elif venta_reciente >= 6_000_000:
            return {
                "rol": "senior_solido",
                "nivel": 3,
                "confianza": "alta",
                "nota": "Venta reciente $%s/mes" % "{:,.0f}".format(venta_reciente),
            }
        elif venta_reciente >= 2_000_000:
            return {
                "rol": "promedio",
                "nivel": 2,
                "confianza": "alta",
                "nota": "Venta reciente $%s/mes" % "{:,.0f}".format(venta_reciente),
            }
        else:
            return {
                "rol": "junior",
                "nivel": 1,
                "confianza": "media",
                "nota": "Venta reciente baja: $%s/mes" % "{:,.0f}".format(venta_reciente),
            }

    return {
        "rol": "sin_clasificar",
        "nivel": 0,
        "confianza": "baja",
        "nota": "No encaja en ningun patron conocido.",
    }


# ---------------------------------------------------------------------------
# PASO 3: Calcular ratio sueldo/venta (equidad del modelo)
# ---------------------------------------------------------------------------

def ratio_sueldo_venta(serie, n_ultimos=6):
    """
    Calcula el ratio sueldo_mensual / venta_mensual en los ultimos n meses.
    Si el ratio > 0.15 (vendedor paga mas del 15% de su venta en sueldo),
    el modelo puede ser deficitario.
    """
    ult = serie.sort_values(["anio", "mes"]).tail(n_ultimos)
    v = ult["venta_neta"].clip(lower=0).sum()
    s = ult["sueldo"].sum()
    if v == 0:
        return np.nan
    return s / v


# ---------------------------------------------------------------------------
# PASO 4: Calcular nivel actual y brecha al siguiente
# ---------------------------------------------------------------------------

NIVEL_THRESHOLDS = {
    # (venta_reciente_min, meses_activos_min, consistencia_min)
    1: (0,         0,  0.0),
    2: (2_000_000, 6,  0.35),
    3: (6_000_000, 12, 0.45),
    4: (15_000_000, 18, 0.55),
    5: (None, None, None),  # Encargado — por designacion
    6: (None, None, None),  # Digital — por designacion
}


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("AUDITORIA PLAN DE CARRERA — H4/Calzalindo")
    print("Generado: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 70)

    conn = conectar("msgestion01")

    # -- Nombres viajantes ---------------------------------------------------
    print("\n[1] Cargando nombres de viajantes...")
    df_nombres = _sql(conn, SQL_NOMBRES)
    vjt_nombres = dict(zip(df_nombres["viajante"], df_nombres["nombre"].str.strip()))

    # -- Config (si existe) --------------------------------------------------
    print("[2] Leyendo viajante_config...")
    try:
        df_config = _sql(conn, SQL_CONFIG)
        config_map = {int(r["viajante_codigo"]): r for _, r in df_config.iterrows()}
        print("    %d registros en viajante_config." % len(config_map))
    except Exception as e:
        config_map = {}
        print("    AVISO: viajante_config no existe o error: %s" % e)

    # -- Series ventas (01 + 03) --------------------------------------------
    print("[3] Cargando series de ventas 2022-2025...")
    df_v01 = _sql(conn, SQL_SERIES.format(bd="msgestion01"))
    try:
        df_v03 = _sql(conn, SQL_SERIES.format(bd="msgestion03"))
        df_ventas = pd.concat([df_v01, df_v03], ignore_index=True)
        df_ventas = (
            df_ventas.groupby(["viajante", "anio", "mes"])
            .agg(venta_neta=("venta_neta", "sum"), pares=("pares", "sum"))
            .reset_index()
        )
    except Exception:
        df_ventas = df_v01.rename(columns={"venta_neta": "venta_neta"})
    print("    %d filas viajante-mes de ventas." % len(df_ventas))

    # -- Series sueldos (msgestion01 + msgestion02 gerenciales) --------------
    print("[4] Cargando series de sueldos...")
    df_s01 = _sql(conn, SQL_SUELDOS.format(bd="msgestion01"))
    try:
        df_s02 = _sql(conn, SQL_SUELDOS.format(bd="msgestion02"))
        df_sueldos = pd.concat([df_s01, df_s02], ignore_index=True)
        df_sueldos = (
            df_sueldos.groupby(["viajante", "anio", "mes"])["sueldo"]
            .sum().reset_index()
        )
        print("    %d filas viajante-mes de sueldos (01+02 gerenciales)." % len(df_sueldos))
    except Exception as e:
        df_sueldos = df_s01
        print("    %d filas (solo 01, error en 02: %s)." % (len(df_sueldos), e))

    # -- Deposito principal --------------------------------------------------
    print("[5] Calculando deposito principal por viajante (2024-2025)...")
    try:
        df_dep01 = _sql(conn, SQL_DEPOSITO)
        df_dep03 = _sql(conn, SQL_DEPOSITO_03)
        df_dep = pd.concat([df_dep01, df_dep03], ignore_index=True)
        df_dep = df_dep.groupby(["viajante", "deposito"])["venta_dep"].sum().reset_index()
        dep_principal = (
            df_dep.sort_values("venta_dep", ascending=False)
            .groupby("viajante")
            .first()
            .reset_index()[["viajante", "deposito"]]
            .rename(columns={"deposito": "deposito_principal"})
        )
    except Exception:
        dep_principal = pd.DataFrame(columns=["viajante", "deposito_principal"])

    dep_map = dict(zip(dep_principal["viajante"], dep_principal["deposito_principal"]))

    # -- Merge ventas + sueldos ---------------------------------------------
    print("[6] Combinando ventas y sueldos...")
    df_merge = pd.merge(
        df_ventas,
        df_sueldos,
        on=["viajante", "anio", "mes"],
        how="outer",
    ).fillna({"venta_neta": 0.0, "sueldo": 0.0, "pares": 0.0})

    viajantes_todos = df_merge["viajante"].unique()
    print("    %d viajantes distintos en el dataset." % len(viajantes_todos))

    # -- Detectar rol -------------------------------------------------------
    print("[7] Detectando rol de cada viajante...")
    resultados = []

    for vjt in sorted(viajantes_todos):
        serie = df_merge[df_merge["viajante"] == vjt].copy()
        cfg   = config_map.get(int(vjt))
        cfg_d = dict(cfg) if cfg is not None else None

        det = detectar_rol(vjt, serie, cfg_d)

        pico     = _pico_venta(serie)
        vta_rec  = _promedio_venta_activos(serie, 6)
        sueldo_r = _sueldo_reciente(serie, 3)
        ratio    = ratio_sueldo_venta(serie, 6)
        m_act    = _meses_activos_total(serie)
        dep      = dep_map.get(vjt, -1)

        ult_venta = _ult_mes_activo(serie, "venta_neta")
        ult_sueldo = _ult_mes_activo(serie, "sueldo")

        resultados.append({
            "viajante":          vjt,
            "nombre":            vjt_nombres.get(vjt, str(vjt)).strip(),
            "deposito_principal": dep,
            "rol_detectado":     det["rol"],
            "nivel_carrera":     det["nivel"],
            "confianza":         det["confianza"],
            "nota_rol":          det["nota"],
            "venta_pico_hist":   pico,
            "venta_mensual_rec": vta_rec,
            "sueldo_mensual_rec": sueldo_r,
            "ratio_sueldo_venta": ratio,
            "meses_activos_total": m_act,
            "ult_mes_venta":     "%d/%02d" % ult_venta if ult_venta else "-",
            "ult_mes_sueldo":    "%d/%02d" % ult_sueldo if ult_sueldo else "-",
        })

    df_res = pd.DataFrame(resultados)

    # -- Exportar CSV -------------------------------------------------------
    print("\n[8] Exportando CSV...")
    os.makedirs(_BASE_OUT, exist_ok=True)
    df_res.to_csv(OUTPUT_CSV, sep=";", decimal=",", encoding="utf-8-sig",
                  index=False, float_format="%.0f")
    print("    CSV: %s" % OUTPUT_CSV)

    # -- Resumen por rol ----------------------------------------------------
    print("\n" + "=" * 70)
    print("DISTRIBUCION DE ROLES")
    print("=" * 70)

    rol_order = [
        "estrella", "senior_solido", "promedio", "en_formacion", "junior",
        "comisionista_pura", "latente",
        "encargado_activo", "encargado_sospechoso",
        "canal_digital",
        "salida", "excluido", "grupal", "sin_clasificar",
    ]
    rol_counts = df_res["rol_detectado"].value_counts()
    for rol in rol_order:
        n = rol_counts.get(rol, 0)
        if n > 0:
            print("  %-28s %3d" % (rol, n))

    # -- Alerta: encargados sospechosos -------------------------------------
    sospechosos = df_res[df_res["rol_detectado"] == "encargado_sospechoso"]
    if not sospechosos.empty:
        print("\n" + "=" * 70)
        print("ENCARGADOS SOSPECHOSOS — VERIFICAR MANUALMENTE")
        print("=" * 70)
        for _, r in sospechosos.iterrows():
            print("  %-25s (vj %4d)  dep %2s  sueldo $%s/mes  %s" % (
                r["nombre"][:24], r["viajante"], r["deposito_principal"],
                "{:,.0f}".format(r["sueldo_mensual_rec"]),
                r["nota_rol"][:60]))

    # -- Alerta: ratio sueldo/venta alto ------------------------------------
    ratio_alto = df_res[
        (df_res["ratio_sueldo_venta"].notna()) &
        (df_res["ratio_sueldo_venta"] > 0.15) &
        (df_res["rol_detectado"].isin(["promedio", "senior_solido", "estrella"]))
    ].sort_values("ratio_sueldo_venta", ascending=False)

    if not ratio_alto.empty:
        print("\n" + "=" * 70)
        print("VENDEDORES ACTIVOS CON RATIO SUELDO/VENTA > 15%% (potencialmente deficitarios)")
        print("=" * 70)
        print("  %-25s %5s  %9s  %9s  %6s" % ("Nombre", "Vj", "Venta/mes", "Sueldo/mes", "Ratio"))
        print("  " + "-" * 65)
        for _, r in ratio_alto.head(15).iterrows():
            print("  %-25s %5d  %9s  %9s  %5.1f%%" % (
                r["nombre"][:24], r["viajante"],
                "${:,.0f}".format(r["venta_mensual_rec"]),
                "${:,.0f}".format(r["sueldo_mensual_rec"]),
                r["ratio_sueldo_venta"] * 100,
            ))

    # -- Puestos vacios por deposito ----------------------------------------
    print("\n" + "=" * 70)
    print("PUESTOS VACIOS POR DEPOSITO (latentes + salidas con pico > $3M)")
    print("=" * 70)
    vacias = df_res[
        (df_res["rol_detectado"].isin(["latente", "salida"])) &
        (df_res["venta_pico_hist"] > 3_000_000)
    ].sort_values(["deposito_principal", "venta_pico_hist"], ascending=[True, False])

    if not vacias.empty:
        for dep, grupo in vacias.groupby("deposito_principal"):
            print("\n  Deposito %s:" % dep)
            for _, r in grupo.iterrows():
                print("    %-25s  pico $%s  ult venta %s  (%s)" % (
                    r["nombre"][:24],
                    "{:,.0f}".format(r["venta_pico_hist"]),
                    r["ult_mes_venta"],
                    r["rol_detectado"],
                ))

    # -- Canal digital ------------------------------------------------------
    canal = df_res[df_res["rol_detectado"] == "canal_digital"]
    if not canal.empty:
        print("\n" + "=" * 70)
        print("CANAL DIGITAL (dep 1 — ML + TiendaNube)")
        print("=" * 70)
        for _, r in canal.iterrows():
            print("  %-25s (vj %4d)  sueldo $%s/mes  %s" % (
                r["nombre"][:24], r["viajante"],
                "{:,.0f}".format(r["sueldo_mensual_rec"]),
                r["nota_rol"][:50]))

    # -- Generar PLAN_CARRERA.md --------------------------------------------
    print("\n[9] Generando PLAN_CARRERA.md...")
    _escribir_md(df_res, vjt_nombres)
    print("    MD:  %s" % OUTPUT_MD)

    print("\n" + "=" * 70)
    print("Auditoria completa.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# GENERADOR MARKDOWN
# ---------------------------------------------------------------------------

def _escribir_md(df_res, vjt_nombres):
    """Escribe el informe PLAN_CARRERA.md."""

    hoy = datetime.now().strftime("%Y-%m-%d")

    lines = []
    lines.append("# Plan de Carrera — H4 / Calzalindo")
    lines.append("> Generado: %s" % hoy)
    lines.append("> Fuente: ventas1 2022-2025 + moviempl1 + benchmark_viajantes.py")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Seccion 1: Marco conceptual
    lines.append("## 1. Marco del Plan de Carrera")
    lines.append("")
    lines.append("H4/Calzalindo tiene tres ramas de desarrollo para su personal comercial:")
    lines.append("")
    lines.append("```")
    lines.append("                      [DIRECCION]")
    lines.append("                           |")
    lines.append("         +-----------------+-----------------+")
    lines.append("         |                 |                 |")
    lines.append("   [ENCARGADO]     [CANAL DIGITAL]   [COMPRAS/ADMIN]")
    lines.append("   Nivel 5         Nivel 6            (Mati, Mariana)")
    lines.append("         |                 |")
    lines.append("   [ESTRELLA] -----> puede derivar a cualquier rama")
    lines.append("   Nivel 4")
    lines.append("         |")
    lines.append("   [SENIOR/SOLIDO]")
    lines.append("   Nivel 3")
    lines.append("         |")
    lines.append("   [PROMEDIO]")
    lines.append("   Nivel 2")
    lines.append("         |")
    lines.append("   [JUNIOR]")
    lines.append("   Nivel 1")
    lines.append("```")
    lines.append("")
    lines.append("> **Regla critica**: cuando alguien sube a Encargado o Canal Digital,")
    lines.append("> sus KPIs CAMBIAN. NO se compara con vendedores de piso.")
    lines.append("")

    # Seccion 2: Niveles
    lines.append("## 2. Niveles y Criterios")
    lines.append("")

    for nivel, info in NIVELES_CARRERA.items():
        lines.append("### Nivel %d — %s" % (nivel, info["nombre"]))
        lines.append("")
        lines.append("**Criterios de acceso:**")
        for c in info["criterios_acceso"]:
            lines.append("- %s" % c)
        lines.append("")
        lines.append("**KPIs de evaluacion:**")
        for k in info["kpis"]:
            lines.append("- %s" % k)
        lines.append("")
        lines.append("**Rango salarial:** %s" % info["salario_rango"])
        lines.append("")
        lines.append("**Condicion de avance:** %s" % info["condicion_avance"])
        lines.append("")
        lines.append("**Tipo de contrato sugerido:** %s" % info["tipo_contrato"])
        lines.append("")
        lines.append("---")
        lines.append("")

    # Seccion 3: Diagnostico actual
    lines.append("## 3. Diagnostico Actual por Vendedora")
    lines.append("")

    activos_roles = [
        "estrella", "senior_solido", "promedio", "en_formacion", "junior",
        "comisionista_pura",
    ]
    df_activos = df_res[df_res["rol_detectado"].isin(activos_roles)].sort_values(
        ["deposito_principal", "nivel_carrera"], ascending=[True, False]
    )

    lines.append("| Viajante | Nombre | Dep | Rol detectado | Nivel | Venta rec $/mes | Sueldo rec $/mes | Ratio S/V |")
    lines.append("|----------|--------|-----|--------------|-------|----------------|-----------------|-----------|")
    for _, r in df_activos.iterrows():
        ratio_str = "%.1f%%" % (r["ratio_sueldo_venta"] * 100) if not pd.isna(r["ratio_sueldo_venta"]) else "-"
        lines.append("| %d | %s | %s | %s | %d | $%s | $%s | %s |" % (
            r["viajante"],
            r["nombre"][:28],
            r["deposito_principal"],
            r["rol_detectado"],
            r["nivel_carrera"],
            "{:,.0f}".format(r["venta_mensual_rec"]),
            "{:,.0f}".format(r["sueldo_mensual_rec"]),
            ratio_str,
        ))
    lines.append("")

    # Seccion 4: Encargados y canal digital
    lines.append("## 4. Encargados y Canal Digital")
    lines.append("")

    encargados = df_res[df_res["rol_detectado"].isin(["encargado_activo", "encargado_sospechoso", "canal_digital"])]
    if not encargados.empty:
        lines.append("| Viajante | Nombre | Dep | Rol | Sueldo rec | Nota |")
        lines.append("|----------|--------|-----|-----|-----------|------|")
        for _, r in encargados.iterrows():
            lines.append("| %d | %s | %s | %s | $%s | %s |" % (
                r["viajante"],
                r["nombre"][:28],
                r["deposito_principal"],
                r["rol_detectado"],
                "{:,.0f}".format(r["sueldo_mensual_rec"]),
                r["nota_rol"][:60],
            ))
    lines.append("")

    # Seccion 5: Puestos vacios
    lines.append("## 5. Puestos Vacios o en Riesgo")
    lines.append("")
    vacias = df_res[
        (df_res["rol_detectado"].isin(["latente", "salida"])) &
        (df_res["venta_pico_hist"] > 2_000_000)
    ].sort_values("venta_pico_hist", ascending=False)

    if not vacias.empty:
        lines.append("| Viajante | Nombre | Dep | Estado | Pico historico | Ult venta |")
        lines.append("|----------|--------|-----|--------|----------------|-----------|")
        for _, r in vacias.iterrows():
            lines.append("| %d | %s | %s | %s | $%s | %s |" % (
                r["viajante"],
                r["nombre"][:28],
                r["deposito_principal"],
                r["rol_detectado"],
                "{:,.0f}".format(r["venta_pico_hist"]),
                r["ult_mes_venta"],
            ))
    lines.append("")

    # Seccion 6: Ratio sueldo/venta
    lines.append("## 6. Alerta Modelo Retributivo (ratio sueldo / venta > 15%%)")
    lines.append("")
    lines.append("Un vendedor cuyo sueldo fijo supera el 15%% de su venta mensual puede")
    lines.append("estar generando un costo que no se justifica con comision variable.")
    lines.append("Umbral optimo: sueldo <= 10%% de la venta mensual.")
    lines.append("")
    ratio_alto = df_res[
        (df_res["ratio_sueldo_venta"].notna()) &
        (df_res["ratio_sueldo_venta"] > 0.15) &
        (df_res["rol_detectado"].isin(["promedio", "senior_solido", "estrella", "junior", "en_formacion"]))
    ].sort_values("ratio_sueldo_venta", ascending=False)
    if not ratio_alto.empty:
        lines.append("| Viajante | Nombre | Venta/mes | Sueldo/mes | Ratio |")
        lines.append("|----------|--------|-----------|-----------|-------|")
        for _, r in ratio_alto.head(20).iterrows():
            lines.append("| %d | %s | $%s | $%s | %.1f%% |" % (
                r["viajante"],
                r["nombre"][:28],
                "{:,.0f}".format(r["venta_mensual_rec"]),
                "{:,.0f}".format(r["sueldo_mensual_rec"]),
                r["ratio_sueldo_venta"] * 100,
            ))
    lines.append("")

    # Seccion 7: Acciones recomendadas
    lines.append("## 7. Acciones Recomendadas")
    lines.append("")
    n_enc_sosp = len(df_res[df_res["rol_detectado"] == "encargado_sospechoso"])
    n_latentes  = len(df_res[df_res["rol_detectado"] == "latente"])
    n_junior    = len(df_res[df_res["rol_detectado"].isin(["junior", "en_formacion"])])
    n_ratio_mal = len(ratio_alto)

    lines.append("| Prioridad | Accion | N impactados |")
    lines.append("|-----------|--------|-------------|")
    lines.append("| P0 | Formalizar encargados en viajante_config (tipo=encargado) | %d sospechosos |" % n_enc_sosp)
    lines.append("| P0 | Confirmar codigo de Belen (canal digital dep 1) | 1 |")
    lines.append("| P1 | Ejecutar crear_viajante_config.sql en produccion | — |")
    lines.append("| P1 | Revisar vendedores con ratio sueldo/venta > 15%% | %d |" % n_ratio_mal)
    lines.append("| P1 | Contactar latentes con pico > $3M — saber si vuelven | %d |" % n_latentes)
    lines.append("| P2 | Definir KPIs formales para encargados (conversion local, etc.) | — |")
    lines.append("| P2 | Disenar esquema de comision progresiva por nivel | — |")
    lines.append("| P2 | Evaluar juniors con plan de 90 dias | %d |" % n_junior)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Fuentes: ventas1 2022-2025, moviempl1, auditoria_plan_carrera.py*")

    # Escribir archivo
    with open(OUTPUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    main()
