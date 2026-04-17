"""
autorepo/insertar_transferencia.py

Genera el movimiento de SALIDA origen→198 para una propuesta aprobada.
El movimiento de ENTRADA 198→destino lo hace el operador al recibir
(mismo proceso que las transferencias manuales SS/SST).

También registra cada línea en clz_ventas_mysql.stock_transferencias (MySQL 109)
para que aparezca como "Pendiente-Guia" en la app del 109.

Patrón ERP: codigo=87, letra='X', sucursal=1, tipo_nota=NULL
"""
import logging
from datetime import date
from contextlib import contextmanager

import pyodbc

log = logging.getLogger("autorepo.transferencia")

CODIGO_TRANSFERENCIA  = 87
LETRA_TRANSFERENCIA   = "X"
SUCURSAL_TRANSFERENCIA = 1
DEPOSITO_TRANSITO     = 198          # depósito "en camino"
USUARIO_AUTOREPO      = "COWORK"

_BASE_POR_EMPRESA = {
    "H4":         "MSGESTION03",
    "CALZALINDO": "MSGESTION01",
}

_EMPRESA_POR_DEPOSITO = {
    0:  "CALZALINDO",
    2:  "CALZALINDO",
    6:  "CALZALINDO",
    7:  "CALZALINDO",
    8:  "CALZALINDO",
    11: "CALZALINDO",
}

# Mapeo dep ERP → (sucursal_id, nro_suc) en clz_ventas_mysql.sucursales
_SUCURSAL_POR_DEPOSITO: dict = {
    0:  (1,  0),
    2:  (3,  2),
    6:  (6,  6),
    7:  (7,  7),
    8:  (8,  8),
    11: (13, 11),
}

MYSQL_109 = {
    "host": "192.168.2.109",
    "user": "root",
    "password": "cagr$2011",
    "database": "clz_ventas_mysql",
    "charset": "utf8mb4",
}


@contextmanager
def _conn(conn_string):
    cn = pyodbc.connect(conn_string, autocommit=False)
    try:
        yield cn
        cn.commit()
    except Exception:
        cn.rollback()
        raise
    finally:
        cn.close()


def _base_para_deposito(deposito: int) -> str:
    empresa = _EMPRESA_POR_DEPOSITO.get(deposito, "CALZALINDO")
    return _BASE_POR_EMPRESA.get(empresa, "MSGESTION01")


def _get_proximo_numero_orden(cur, base: str) -> tuple:
    cur.execute(f"""
        SELECT ISNULL(MAX(numero), 0) + 1, ISNULL(MAX(orden), 0) + 1
        FROM {base}.dbo.movistoc2
        WHERE codigo = {CODIGO_TRANSFERENCIA}
          AND letra = '{LETRA_TRANSFERENCIA}'
          AND sucursal = {SUCURSAL_TRANSFERENCIA}
    """)
    row = cur.fetchone()
    return int(row[0]), int(row[1])


def _get_sinonimo_barra(cur, articulo: int) -> tuple:
    """Retorna (codigo_sinonimo, codigo_barra) del artículo."""
    cur.execute(
        "SELECT ISNULL(codigo_sinonimo, ''), ISNULL(CAST(codigo_barra AS VARCHAR), '') "
        "FROM msgestion01art.dbo.articulo WHERE codigo = ?",
        articulo,
    )
    row = cur.fetchone()
    return (row[0], row[1]) if row else ("", "")


def insertar_salida_transito(
    propuesta_id: int,
    deposito_emisor: int,
    deposito_receptor_final: int,
    lineas: list,       # [{articulo, descripcion, cantidad, precio_costo}]
    conn_string: str,
    obs: str = "",
) -> dict:
    """
    Inserta movistoc2+movistoc1: origen → depósito 198 (tránsito).
    El receptor_final se graba en observaciones para que el operador
    sepa a dónde va cuando lo recibe.

    Retorna {'base', 'numero', 'orden', 'renglones'}.
    """
    base = _base_para_deposito(deposito_emisor)
    hoy  = date.today().strftime("%Y-%m-%d")
    obs_final = f"AUTOREPO #{propuesta_id} → dep{deposito_receptor_final} {obs}".strip()[:80]

    sql_cab = f"""
        INSERT INTO {base}.dbo.movistoc2
            (codigo, letra, sucursal, numero, orden,
             deposito_emisor, deposito_receptor,
             fecha_comprobante, fecha_proceso, fecha_contable,
             estado, estado_stock, estado_desglose,
             copias, contabiliza, usuario, observaciones,
             moneda, valor_dolar, tipo_nota)
        VALUES
            ({CODIGO_TRANSFERENCIA},'{LETRA_TRANSFERENCIA}',{SUCURSAL_TRANSFERENCIA},?,?,
             {deposito_emisor},{DEPOSITO_TRANSITO},
             '{hoy}','{hoy}','{hoy}',
             'V','S','',
             1,'N','{USUARIO_AUTOREPO}',?,
             0,1,NULL)
    """

    sql_det = f"""
        INSERT INTO {base}.dbo.movistoc1
            (codigo, letra, sucursal, numero, orden, renglon,
             articulo, descripcion, cantidad, precio,
             deposito_emisor, deposito_receptor,
             estado, estado_stock, estado_desglose,
             calificacion, moneda, valor_dolar,
             precio_egreso, consignacion_emisor, codigo_sinonimo)
        VALUES
            ({CODIGO_TRANSFERENCIA},'{LETRA_TRANSFERENCIA}',{SUCURSAL_TRANSFERENCIA},?,?,?,
             ?,?,?,?,
             {deposito_emisor},{DEPOSITO_TRANSITO},
             'V','S','I',
             'G',0,1,
             0,'N',?)
    """

    with _conn(conn_string) as cn:
        cur = cn.cursor()
        numero, orden = _get_proximo_numero_orden(cur, base)

        cur.execute(sql_cab, numero, orden, obs_final)

        for renglon, ln in enumerate(lineas, start=1):
            sinonimo, barra = _get_sinonimo_barra(cur, ln["articulo"])
            ln["sinonimo"] = sinonimo
            ln["codigo_barra"] = barra
            cur.execute(
                sql_det,
                numero, orden, renglon,
                int(ln["articulo"]),
                str(ln.get("descripcion", ""))[:60],
                int(ln["cantidad"]),
                float(ln.get("precio_costo", 0)),
                sinonimo,
            )

    log.info(
        "Salida transito: prop#%d dep%d->198->dep%d base=%s num=%d ord=%d rengs=%d",
        propuesta_id, deposito_emisor, deposito_receptor_final,
        base, numero, orden, len(lineas),
    )

    # Registrar en MySQL 109 para que aparezca en la app del 109
    try:
        _registrar_en_mysql_109(
            propuesta_id=propuesta_id,
            deposito_emisor=deposito_emisor,
            deposito_receptor_final=deposito_receptor_final,
            lineas=lineas,
            movistoc_numero=numero,
        )
    except Exception as e:
        log.warning("No se pudo registrar en MySQL 109 (no bloquea): %s", e)

    return {"base": base, "numero": numero, "orden": orden, "renglones": len(lineas)}


def _registrar_en_mysql_109(
    propuesta_id: int,
    deposito_emisor: int,
    deposito_receptor_final: int,
    lineas: list,
    movistoc_numero: int,
) -> None:
    """
    Inserta una fila por línea en clz_ventas_mysql.stock_transferencias.
    Usa pymysql si está disponible, sino intenta mysqlclient.
    """
    try:
        import pymysql
        _mysql_connect = lambda: pymysql.connect(**MYSQL_109)
    except ImportError:
        try:
            import MySQLdb as _mdb
            _mysql_connect = lambda: _mdb.connect(
                host=MYSQL_109["host"], user=MYSQL_109["user"],
                passwd=MYSQL_109["password"], db=MYSQL_109["database"],
                charset=MYSQL_109["charset"],
            )
        except ImportError:
            log.warning("pymysql y MySQLdb no disponibles; omitiendo registro en 109")
            return

    suc_emisor = _SUCURSAL_POR_DEPOSITO.get(deposito_emisor)
    suc_receptor = _SUCURSAL_POR_DEPOSITO.get(deposito_receptor_final)
    if suc_emisor is None or suc_receptor is None:
        log.warning(
            "Deposito no mapeado a sucursal MySQL: emisor=%d receptor=%d",
            deposito_emisor, deposito_receptor_final,
        )
        return

    desde_id, mg_desde = suc_emisor
    hacia_id, mg_hacia = suc_receptor
    hoy = date.today().isoformat()
    obs_mysql = f"AUTOREPO #{propuesta_id} mov#{movistoc_numero}"

    sql = """
        INSERT INTO stock_transferencias
            (referencia, fecha, fecha_sola, codigo, codigo_sinonimo, codigo_barra,
             cantidad, reversa, desde, hacia, mg_desde, mg_hacia,
             estado, obs, traspaso, vendedor)
        VALUES
            (%s, NOW(), %s, %s, %s, %s,
             %s, 'F', %s, %s, %s, %s,
             'Pendiente-Guia', %s, 'F', 1)
    """

    cn = _mysql_connect()
    try:
        cur = cn.cursor()
        for ln in lineas:
            cur.execute(sql, (
                obs_mysql,
                hoy,
                str(ln["articulo"]),
                str(ln.get("sinonimo", "")),
                str(ln.get("codigo_barra", "")),
                int(ln["cantidad"]),
                desde_id, hacia_id, mg_desde, mg_hacia,
                obs_mysql,
            ))
        cn.commit()
        log.info(
            "MySQL 109: %d filas insertadas en stock_transferencias para prop#%d",
            len(lineas), propuesta_id,
        )
    finally:
        cn.close()
