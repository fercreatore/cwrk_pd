# paso1_verificar_bd.py
# Verifica la conexión a SQL Server y muestra la estructura real de:
#   - pedico1  (detalle de pedidos de compra)
#   - pedico2  (cabecera de pedidos de compra)
#   - articulo (maestro de artículos)
#
# EJECUTAR: python paso1_verificar_bd.py
# GUARDAR OUTPUT en: resultado_paso1.txt

import pyodbc
from config import CONN_COMPRAS, CONN_ARTICULOS

def get_columnas(conn_str, base, tabla):
    """Devuelve las columnas de una tabla con tipo y si acepta NULL."""
    sql = f"""
        SELECT 
            c.COLUMN_NAME,
            c.DATA_TYPE,
            c.CHARACTER_MAXIMUM_LENGTH,
            c.IS_NULLABLE,
            c.COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_NAME = '{tabla}'
        ORDER BY c.ORDINAL_POSITION
    """
    try:
        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            return rows
    except Exception as e:
        return f"ERROR: {e}"


def mostrar_columnas(base, tabla, conn_str):
    print(f"\n{'='*60}")
    print(f"  {base}.dbo.{tabla}")
    print(f"{'='*60}")
    resultado = get_columnas(conn_str, base, tabla)
    if isinstance(resultado, str):
        print(resultado)
        return
    for col in resultado:
        nombre, tipo, largo, nullable, default = col
        largo_str = f"({largo})" if largo else ""
        null_str  = "NULL" if nullable == "YES" else "NOT NULL"
        def_str   = f"  DEFAULT={default}" if default else ""
        print(f"  {nombre:<40} {tipo}{largo_str:<15} {null_str}{def_str}")
    print(f"  → Total: {len(resultado)} columnas")


def verificar_ejemplo_articulo():
    """Muestra 3 artículos para entender cómo se usa descripcion_5 (talle)."""
    sql = """
        SELECT TOP 3 
            codigo, descripcion_1, codigo_sinonimo, 
            descripcion_5, subrubro, marca, linea
        FROM articulo
        WHERE descripcion_5 IS NOT NULL 
          AND LEN(codigo_sinonimo) > 3
          AND subrubro > 0
    """
    print(f"\n{'='*60}")
    print("  EJEMPLO DE ARTÍCULOS (para verificar campo talle)")
    print(f"{'='*60}")
    try:
        with pyodbc.connect(CONN_ARTICULOS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for r in rows:
                print(f"\n  codigo        : {r[0]}")
                print(f"  descripcion_1 : {r[1]}")
                print(f"  codigo_sinonimo: {r[2]}")
                print(f"  descripcion_5 : {r[3]}  ← ¿este es el talle?")
                print(f"  subrubro      : {r[4]}")
                print(f"  marca         : {r[5]}")
                print(f"  linea         : {r[6]}")
    except Exception as e:
        print(f"  ERROR: {e}")


def verificar_agrupador_subrubro():
    """Muestra algunos registros del agrupador para verificar mapeo industria."""
    from config import CONN_ANALITICA
    sql = "SELECT TOP 10 id, nombre, subrubros_codigo FROM agrupador_subrubro ORDER BY id"
    print(f"\n{'='*60}")
    print("  AGRUPADOR SUBRUBRO → INDUSTRIA (primeros 10)")
    print(f"{'='*60}")
    try:
        with pyodbc.connect(CONN_ANALITICA, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for r in cursor.fetchall():
                print(f"  id={r[0]:<3} {r[1]:<25} subrubros: {r[2]}")
    except Exception as e:
        print(f"  ERROR: {e}")


if __name__ == "__main__":
    print("\n🔍 VERIFICANDO CONEXIÓN Y ESTRUCTURA DE BASE DE DATOS")
    print("  Servidor: 192.168.2.111")

    # ── pedico2 (cabecera) ──
    mostrar_columnas("msgestionC", "pedico2", CONN_COMPRAS)

    # ── pedico1 (detalle) ──
    mostrar_columnas("msgestionC", "pedico1", CONN_COMPRAS)

    # ── articulo ──
    mostrar_columnas("msgestion01art", "articulo", CONN_ARTICULOS)

    # ── ejemplo artículos ──
    verificar_ejemplo_articulo()

    # ── agrupador ──
    verificar_agrupador_subrubro()

    print("\n✅ Paso 1 completo. Guardar este output en resultado_paso1.txt")
    print("   y compartirlo antes de continuar con los pasos siguientes.\n")
