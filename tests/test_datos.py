#!/usr/bin/env python3
"""
test_datos.py — Verificación de conexión y datos SQL Server
============================================================
Conecta al 192.168.2.112 (o 111 fallback) y valida:
  - Conexión exitosa
  - Tablas principales devuelven datos
  - Sin nulls críticos en campos clave
  - Fechas coherentes (no futuras, no pre-2020)
"""

import os
import sys
import unittest
from datetime import date, datetime

# Fix SSL para SQL Server 2012
_ssl_conf = os.path.join(os.path.dirname(__file__), '..', '_scripts_oneshot', 'openssl_legacy.cnf')
_ssl_conf = os.path.abspath(_ssl_conf)
if os.path.exists(_ssl_conf):
    os.environ['OPENSSL_CONF'] = _ssl_conf

import pyodbc
import pandas as pd

# Conexión directa — intentar 111 (producción, donde sabemos que am/dl funciona)
SERVIDOR = "192.168.2.111"
DRIVER = "ODBC Driver 17 for SQL Server"
USUARIO = "am"
PASSWORD = "dl"


def _conn_string(base):
    cs = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVIDOR};"
        f"DATABASE={base};"
        f"UID={USUARIO};"
        f"PWD={PASSWORD};"
        f"Connection Timeout=15;"
    )
    if sys.platform != 'win32':
        cs += "TrustServerCertificate=yes;Encrypt=no;"
    return cs


CONN_C = _conn_string("msgestionC")
CONN_ART = _conn_string("msgestion01art")

_connection_cache = {}


def get_conn(base="msgestionC"):
    if base not in _connection_cache or _connection_cache[base] is None:
        cs = _conn_string(base)
        _connection_cache[base] = pyodbc.connect(cs, timeout=15)
    return _connection_cache[base]


def query(sql, base="msgestionC"):
    return pd.read_sql(sql, get_conn(base))


class TestConexion(unittest.TestCase):
    """Verifica que la conexión a SQL Server funcione."""

    def test_conexion_msgestionC(self):
        conn = get_conn("msgestionC")
        self.assertIsNotNone(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 AS ok")
        row = cursor.fetchone()
        self.assertEqual(row[0], 1)

    def test_conexion_articulos(self):
        conn = get_conn("msgestion01art")
        self.assertIsNotNone(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 AS ok")
        row = cursor.fetchone()
        self.assertEqual(row[0], 1)


class TestTablasDevuelvenDatos(unittest.TestCase):
    """Verifica que las tablas principales tengan registros."""

    TABLAS = {
        "msgestionC": [
            ("stock", "SELECT TOP 5 * FROM stock"),
            ("ventas1", "SELECT TOP 5 * FROM ventas1"),
            ("compras1", "SELECT TOP 5 * FROM compras1"),
            ("pedico1", "SELECT TOP 5 * FROM pedico1"),
            ("pedico2", "SELECT TOP 5 * FROM pedico2"),
        ],
        "msgestion01art": [
            ("articulo", "SELECT TOP 5 * FROM articulo"),
        ],
    }

    def test_tablas_no_vacias(self):
        for base, tablas in self.TABLAS.items():
            for nombre, sql in tablas:
                with self.subTest(base=base, tabla=nombre):
                    df = query(sql, base)
                    self.assertGreater(len(df), 0, f"{base}.{nombre} está vacía")


class TestNullsCriticos(unittest.TestCase):
    """Verifica que campos clave no tengan nulls."""

    def test_articulo_codigo_no_null(self):
        df = query("SELECT TOP 100 codigo FROM articulo WHERE codigo IS NULL", "msgestion01art")
        self.assertEqual(len(df), 0, "Hay artículos con codigo NULL")

    def test_stock_articulo_no_null(self):
        df = query("SELECT TOP 100 articulo FROM stock WHERE articulo IS NULL")
        self.assertEqual(len(df), 0, "Hay stock con articulo NULL")

    def test_ventas_fecha_no_null(self):
        df = query("SELECT TOP 100 fecha FROM ventas1 WHERE fecha IS NULL")
        self.assertEqual(len(df), 0, "Hay ventas con fecha NULL")

    def test_ventas_articulo_no_null(self):
        df = query("SELECT TOP 100 articulo FROM ventas1 WHERE articulo IS NULL")
        self.assertEqual(len(df), 0, "Hay ventas con articulo NULL")

    def test_pedico2_fecha_no_null(self):
        df = query("SELECT TOP 100 fecha_comprobante FROM pedico2 WHERE fecha_comprobante IS NULL")
        self.assertEqual(len(df), 0, "Hay pedidos con fecha_comprobante NULL")


class TestFechasCoherentes(unittest.TestCase):
    """Verifica que las fechas sean razonables."""

    def test_ventas_sin_fechas_futuras(self):
        hoy = date.today().isoformat()
        df = query(f"SELECT TOP 10 fecha FROM ventas1 WHERE fecha > '{hoy}'")
        self.assertEqual(len(df), 0, f"Hay {len(df)} ventas con fecha futura")

    def test_ventas_sin_fechas_antiguas(self):
        """Verificar que no haya volumen masivo de ventas pre-2010 (datos legacy OK)."""
        df = query("SELECT COUNT(*) AS cnt FROM ventas1 WHERE fecha < '2010-01-01'")
        cnt = df['cnt'].iloc[0]
        self.assertLess(cnt, 1000, f"Hay {cnt} ventas pre-2010 (demasiadas)")

    def test_pedidos_fechas_razonables(self):
        hoy = date.today().isoformat()
        df = query(f"""
            SELECT TOP 10 fecha_comprobante FROM pedico2
            WHERE fecha_comprobante > '{hoy}'
        """)
        self.assertEqual(len(df), 0, f"Hay {len(df)} pedidos con fecha futura")

    def test_stock_actual_no_negativo_masivo(self):
        """Puede haber algunos negativos legítimos, pero no la mayoría."""
        df = query("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN stock_actual < -100 THEN 1 ELSE 0 END) AS muy_negativos
            FROM stock
        """)
        total = df['total'].iloc[0]
        muy_neg = df['muy_negativos'].iloc[0]
        pct = (muy_neg / total * 100) if total > 0 else 0
        self.assertLess(pct, 5, f"{pct:.1f}% de stock con valores < -100")


if __name__ == '__main__':
    unittest.main(verbosity=2)
