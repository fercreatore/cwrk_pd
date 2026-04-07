# -*- coding: utf-8 -*-
"""
Conexión a SQL Server via pyodbc.
Pool de conexiones simple con context manager.
Lee las mismas bases que web2py (msgestionC, omicronvt, msgestion01art).
"""
import pyodbc
from contextlib import contextmanager
from config import settings

DRIVER = "{ODBC Driver 17 for SQL Server}"


def _build_conn_str(database: str = None) -> str:
    """
    Build connection string. For cross-DB queries, connect to the PRIMARY database
    (typically omicronvt) and use 3-part names (database.dbo.table) for remote tables.
    """
    db = database or settings.DB_ANALITICA
    return (
        f"DRIVER={DRIVER};"
        f"SERVER={settings.DB_SERVER},{settings.DB_PORT};"
        f"DATABASE={db};"
        f"UID={settings.DB_USER};"
        f"PWD={settings.DB_PASSWORD};"
        f"Encrypt=no;"
    )


@contextmanager
def get_db(database: str = None):
    """
    Context manager que devuelve un cursor con READ UNCOMMITTED.
    Uso:
        with get_db('omicronvt') as cursor:
            cursor.execute("SELECT ...")
            rows = cursor.fetchall()
    """
    conn = pyodbc.connect(_build_conn_str(database))
    try:
        cursor = conn.cursor()
        cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _rows_to_dicts(cursor) -> list:
    """Convierte el resultado de un cursor pyodbc a lista de dicts."""
    if cursor.description is None:
        return []
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def query(sql: str, database: str = None, params: tuple = None) -> list:
    """Ejecuta SQL y retorna lista de dicts. Soporta parámetros (?, ?, ...)."""
    with get_db(database) as cur:
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        return _rows_to_dicts(cur)


def execute(sql: str, database: str = None, params: tuple = None) -> int:
    """Ejecuta SQL de escritura y retorna rowcount. Soporta parámetros."""
    with get_db(database) as cur:
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        return cur.rowcount


def execute_returning_id(sql: str, database: str = None, params: tuple = None) -> int:
    """Ejecuta INSERT y retorna el ID generado via SCOPE_IDENTITY()."""
    with get_db(database) as cur:
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        cur.execute("SELECT SCOPE_IDENTITY() AS id")
        row = cur.fetchone()
        return int(row[0]) if row else None


# ── Shortcuts ────────────────────────────────────────────
def query_omicronvt(sql: str, params: tuple = None) -> list:
    return query(sql, settings.DB_ANALITICA, params)

def query_msgestionC(sql: str, params: tuple = None) -> list:
    return query(sql, settings.DB_COMPRAS, params)

def query_articulos(sql: str, params: tuple = None) -> list:
    return query(sql, settings.DB_ARTICULOS, params)

def query_auth(sql: str, params: tuple = None) -> list:
    return query(sql, settings.DB_AUTH, params)
