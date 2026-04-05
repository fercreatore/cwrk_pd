"""Acceso a PostgreSQL clz_productos + tracking de publicaciones TN."""
import json
import os
import sqlite3
import time
from datetime import datetime

import psycopg2

# Importar la conexión PG que ya existe en imagenes.py
from multicanal.imagenes import PG_CONN_STRING


# ── Ruta tracking SQLite ──
_DB_PATH = os.path.join(os.path.dirname(__file__), 'publicaciones.db')

BATCH = 500


# ═══════════════════════════════════════════════════════════════
#  Lectura PostgreSQL
# ═══════════════════════════════════════════════════════════════

def obtener_stock_pg(codigos_sinonimo: list, depositos: list = None) -> dict:
    """
    Dado un listado de codigos_sinonimo, devuelve {codigo_sinonimo: stock_total}.
    Procesa en batches de 500. Stock negativo se clampea a 0.
    """
    if not codigos_sinonimo:
        return {}

    if depositos is None:
        depositos = [0, 1]

    resultado = {}
    conn = psycopg2.connect(PG_CONN_STRING)
    try:
        cur = conn.cursor()
        for i in range(0, len(codigos_sinonimo), BATCH):
            lote = codigos_sinonimo[i:i + BATCH]

            cur.execute("""
                SELECT pv.codigo_sinonimo,
                       COALESCE(SUM(pvs.stock_actual), 0) AS stock_total
                FROM producto_variantes pv
                JOIN producto_variante_stock pvs ON pvs.variante_id = pv.id
                WHERE pv.codigo_sinonimo = ANY(%s)
                  AND pvs.deposito = ANY(%s)
                  AND pv.activo = true
                GROUP BY pv.codigo_sinonimo
            """, (lote, depositos))

            for row in cur.fetchall():
                sku = row[0].strip() if row[0] else ''
                stock = int(round(row[1]))
                if sku:
                    resultado[sku] = max(stock, 0)
    finally:
        conn.close()

    return resultado


def obtener_precios_pg(codigos_sinonimo: list) -> dict:
    """
    Dado un listado de codigos_sinonimo, devuelve
    {sku: {'precio': float, 'precio_oferta': float|None}}.
    """
    if not codigos_sinonimo:
        return {}

    resultado = {}
    conn = psycopg2.connect(PG_CONN_STRING)
    try:
        cur = conn.cursor()
        for i in range(0, len(codigos_sinonimo), BATCH):
            lote = codigos_sinonimo[i:i + BATCH]

            cur.execute("""
                SELECT codigo_sinonimo, precio, precio_oferta
                FROM producto_variantes
                WHERE codigo_sinonimo = ANY(%s)
                  AND precio > 0
                  AND activo = true
            """, (lote,))

            for row in cur.fetchall():
                sku = row[0].strip() if row[0] else ''
                if sku:
                    resultado[sku] = {
                        'precio': float(row[1]),
                        'precio_oferta': float(row[2]) if row[2] else None,
                    }
    finally:
        conn.close()

    return resultado


def listar_depositos() -> list:
    """
    Lista depósitos con variantes y stock > 0.
    Retorna lista de dicts: [{'deposito': int, 'variantes': int, 'stock_total': int}, ...]
    """
    conn = psycopg2.connect(PG_CONN_STRING)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT deposito, COUNT(DISTINCT variante_id) as variantes,
                   SUM(stock_actual) as stock_total
            FROM producto_variante_stock
            WHERE stock_actual > 0 AND deposito >= 0
            GROUP BY deposito
            ORDER BY deposito
        """)
        return [
            {
                'deposito': row[0],
                'variantes': int(row[1]),
                'stock_total': int(round(row[2])),
            }
            for row in cur.fetchall()
        ]
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
#  Tracking publicaciones TN (SQLite)
# ═══════════════════════════════════════════════════════════════

def _init_tracking_db():
    """Crea la tabla tn_sync en SQLite si no existe."""
    conn = sqlite3.connect(_DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tn_sync (
                producto_base TEXT PRIMARY KEY,
                tn_product_id INTEGER,
                variant_map TEXT DEFAULT '{}',
                last_stock_sync TEXT,
                last_price_sync TEXT,
                status TEXT DEFAULT 'published',
                tags TEXT DEFAULT 'sync:cowork',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def registrar_sync(producto_base: str, tn_product_id: int, variant_map: dict):
    """Registra o actualiza un producto sincronizado con TN."""
    _init_tracking_db()
    ahora = datetime.now().isoformat()
    conn = sqlite3.connect(_DB_PATH)
    try:
        conn.execute("""
            INSERT INTO tn_sync (producto_base, tn_product_id, variant_map, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(producto_base) DO UPDATE SET
                tn_product_id = excluded.tn_product_id,
                variant_map = excluded.variant_map,
                updated_at = excluded.updated_at
        """, (producto_base, tn_product_id, json.dumps(variant_map), ahora, ahora))
        conn.commit()
    finally:
        conn.close()


def obtener_variant_map(producto_base: str) -> dict:
    """Retorna el variant_map de un producto, o {} si no existe."""
    _init_tracking_db()
    conn = sqlite3.connect(_DB_PATH)
    try:
        row = conn.execute(
            "SELECT variant_map FROM tn_sync WHERE producto_base = ?",
            (producto_base,)
        ).fetchone()
        return json.loads(row[0]) if row else {}
    finally:
        conn.close()


def obtener_publicados() -> list:
    """Retorna todos los registros con status='published' como lista de dicts."""
    _init_tracking_db()
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM tn_sync WHERE status = 'published'"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def marcar_eliminado(producto_base: str):
    """Marca un producto como eliminado (status='deleted')."""
    _init_tracking_db()
    ahora = datetime.now().isoformat()
    conn = sqlite3.connect(_DB_PATH)
    try:
        conn.execute(
            "UPDATE tn_sync SET status = 'deleted', updated_at = ? WHERE producto_base = ?",
            (ahora, producto_base)
        )
        conn.commit()
    finally:
        conn.close()


def actualizar_timestamp_sync(producto_base: str, tipo: str = 'stock'):
    """
    Actualiza el timestamp de última sincronización.
    tipo: 'stock' o 'precio'.
    """
    _init_tracking_db()
    ahora = datetime.now().isoformat()
    campo = 'last_stock_sync' if tipo == 'stock' else 'last_price_sync'
    conn = sqlite3.connect(_DB_PATH)
    try:
        conn.execute(
            f"UPDATE tn_sync SET {campo} = ?, updated_at = ? WHERE producto_base = ?",
            (ahora, ahora, producto_base)
        )
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
#  Main — testing standalone
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=== Test pg_productos ===")
    # Test stock
    stock = obtener_stock_pg(['272220004835'], depositos=[0, 1])
    print(f"Stock: {stock}")
    # Test precios
    precios = obtener_precios_pg(['272220004835'])
    print(f"Precios: {precios}")
    # Test depositos
    deps = listar_depositos()
    print(f"Depositos: {deps}")
    # Test tracking
    _init_tracking_db()
    print("Tracking DB OK")
