"""
Base de datos de señales de demanda.

Tabla SQLite centralizada que consolida señales de múltiples fuentes:
WhatsApp, TiendaNube, Google Trends, Bot Linda, presupuestos ERP.

USO:
    from multicanal.demanda_db import registrar_señal, consultar_top, DB_PATH

    registrar_señal(
        fuente='whatsapp', tipo='consulta_producto',
        producto_desc='pantufla rosa cerrada', talle='38',
        tiene_stock=0, tiene_foto=0, publicado_tn=0,
        raw_text='Hola tenés pantuflas rosas en 38?'
    )

    top = consultar_top(dias=30, limit=20)
"""

import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'demanda.db')


def _conn():
    return sqlite3.connect(DB_PATH)


def inicializar():
    """Crea la tabla si no existe."""
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS demanda_señales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            fuente TEXT NOT NULL,
            tipo TEXT NOT NULL,
            familia_id TEXT,
            producto_desc TEXT,
            talle TEXT,
            cantidad INTEGER DEFAULT 1,
            tiene_stock INTEGER,
            tiene_foto INTEGER,
            publicado_tn INTEGER,
            raw_text TEXT,
            conversation_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_demanda_fecha
        ON demanda_señales(fecha)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_demanda_fuente
        ON demanda_señales(fuente)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_demanda_producto
        ON demanda_señales(producto_desc)
    """)
    conn.commit()
    conn.close()


def registrar_señal(fuente, tipo, producto_desc=None, familia_id=None,
                    talle=None, cantidad=1, tiene_stock=None,
                    tiene_foto=None, publicado_tn=None, raw_text=None,
                    conversation_id=None, fecha=None):
    """Registra una señal de demanda."""
    inicializar()
    conn = _conn()
    conn.execute("""
        INSERT INTO demanda_señales
            (fecha, fuente, tipo, familia_id, producto_desc, talle,
             cantidad, tiene_stock, tiene_foto, publicado_tn, raw_text, conversation_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        fecha or datetime.now().strftime('%Y-%m-%d'),
        fuente, tipo, familia_id, producto_desc, talle,
        cantidad, tiene_stock, tiene_foto, publicado_tn,
        raw_text, conversation_id
    ))
    conn.commit()
    conn.close()


def consultar_top(dias=30, limit=20, fuente=None):
    """
    Top productos más demandados en los últimos N días.
    Agrupa por producto_desc y cuenta señales.
    """
    inicializar()
    conn = _conn()
    conn.row_factory = sqlite3.Row
    desde = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

    sql = """
        SELECT producto_desc, talle,
               COUNT(*) as señales,
               GROUP_CONCAT(DISTINCT fuente) as fuentes,
               MIN(tiene_stock) as min_stock,
               MIN(tiene_foto) as min_foto,
               MIN(publicado_tn) as min_publicado,
               MAX(fecha) as ultima_fecha
        FROM demanda_señales
        WHERE fecha >= ?
    """
    params = [desde]
    if fuente:
        sql += " AND fuente = ?"
        params.append(fuente)

    sql += """
        GROUP BY producto_desc, talle
        ORDER BY señales DESC
        LIMIT ?
    """
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def consultar_sin_atender(dias=30):
    """
    Señales de demanda donde NO teníamos stock, foto, o publicación.
    Estas son las oportunidades de mejora.
    """
    inicializar()
    conn = _conn()
    conn.row_factory = sqlite3.Row
    desde = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

    rows = conn.execute("""
        SELECT producto_desc, talle,
               COUNT(*) as señales,
               GROUP_CONCAT(DISTINCT fuente) as fuentes,
               SUM(CASE WHEN tiene_stock = 0 THEN 1 ELSE 0 END) as veces_sin_stock,
               SUM(CASE WHEN tiene_foto = 0 THEN 1 ELSE 0 END) as veces_sin_foto,
               SUM(CASE WHEN publicado_tn = 0 THEN 1 ELSE 0 END) as veces_sin_publicar
        FROM demanda_señales
        WHERE fecha >= ?
        AND (tiene_stock = 0 OR tiene_foto = 0 OR publicado_tn = 0)
        GROUP BY producto_desc, talle
        ORDER BY señales DESC
        LIMIT 50
    """, (desde,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def stats(dias=30):
    """Estadísticas generales."""
    inicializar()
    conn = _conn()
    desde = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

    total = conn.execute(
        "SELECT COUNT(*) FROM demanda_señales WHERE fecha >= ?", (desde,)
    ).fetchone()[0]

    por_fuente = conn.execute("""
        SELECT fuente, COUNT(*) as n
        FROM demanda_señales WHERE fecha >= ?
        GROUP BY fuente ORDER BY n DESC
    """, (desde,)).fetchall()

    por_tipo = conn.execute("""
        SELECT tipo, COUNT(*) as n
        FROM demanda_señales WHERE fecha >= ?
        GROUP BY tipo ORDER BY n DESC
    """, (desde,)).fetchall()

    conn.close()
    return {
        'total': total,
        'por_fuente': dict(por_fuente),
        'por_tipo': dict(por_tipo),
    }
