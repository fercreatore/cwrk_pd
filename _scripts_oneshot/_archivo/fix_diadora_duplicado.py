#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix pedido DIADORA #1134068 duplicado.
El pedido existe en msgestion01 Y msgestion03 — debe estar SOLO en msgestion03 (H4).
Eliminamos pedico2 + pedico1 + pedico1_entregas de msgestion01.

Ejecutar en 111: py -3 fix_diadora_duplicado.py [--ejecutar]
"""
import pyodbc
import sys

CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes;"
)

NUMERO = 1134068
CODIGO = 8
LETRA = 'X'
ORDEN = 1
BASE_BORRAR = 'msgestion01'  # el duplicado
BASE_MANTENER = 'msgestion03'  # el correcto


def main():
    dry_run = '--ejecutar' not in sys.argv
    if dry_run:
        print("=== MODO DRY-RUN (agregar --ejecutar para grabar) ===\n")

    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    # Verificar que existe en ambas bases
    for base in [BASE_BORRAR, BASE_MANTENER]:
        cursor.execute(
            "SELECT COUNT(*) FROM {}.dbo.pedico1 WHERE codigo={} AND letra='{}' AND numero={}".format(
                base, CODIGO, LETRA, NUMERO))
        cnt = cursor.fetchone()[0]
        print(f"  {base}.pedico1: {cnt} renglones")

    # 1. Borrar pedico1_entregas de msgestion01
    sql_del_entregas = """
    DELETE FROM {b}.dbo.pedico1_entregas
    WHERE codigo={cod} AND letra='{let}' AND numero={num}
    """.format(b=BASE_BORRAR, cod=CODIGO, let=LETRA, num=NUMERO)
    print(f"\n1. DELETE pedico1_entregas de {BASE_BORRAR}")
    if not dry_run:
        cursor.execute(sql_del_entregas)
        print(f"   Eliminados: {cursor.rowcount} registros")
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM {}.dbo.pedico1_entregas WHERE codigo={} AND letra='{}' AND numero={}".format(
                BASE_BORRAR, CODIGO, LETRA, NUMERO))
        cnt = cursor.fetchone()[0]
        print(f"   Se eliminarian: {cnt} registros")

    # 2. Borrar pedico1 de msgestion01
    sql_del_p1 = """
    DELETE FROM {b}.dbo.pedico1
    WHERE codigo={cod} AND letra='{let}' AND numero={num}
    """.format(b=BASE_BORRAR, cod=CODIGO, let=LETRA, num=NUMERO)
    print(f"\n2. DELETE pedico1 de {BASE_BORRAR}")
    if not dry_run:
        cursor.execute(sql_del_p1)
        print(f"   Eliminados: {cursor.rowcount} renglones")
    else:
        print(f"   Se eliminarian: 20 renglones")

    # 3. Borrar pedico2 de msgestion01
    sql_del_p2 = """
    DELETE FROM {b}.dbo.pedico2
    WHERE codigo={cod} AND letra='{let}' AND numero={num}
    """.format(b=BASE_BORRAR, cod=CODIGO, let=LETRA, num=NUMERO)
    print(f"\n3. DELETE pedico2 de {BASE_BORRAR}")
    if not dry_run:
        cursor.execute(sql_del_p2)
        print(f"   Eliminados: {cursor.rowcount} cabeceras")
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM {}.dbo.pedico2 WHERE codigo={} AND letra='{}' AND numero={}".format(
                BASE_BORRAR, CODIGO, LETRA, NUMERO))
        cnt = cursor.fetchone()[0]
        print(f"   Se eliminarian: {cnt} cabeceras")

    # 4. Verificar que msgestion03 queda intacto
    cursor.execute(
        "SELECT COUNT(*) FROM {}.dbo.pedico1 WHERE codigo={} AND letra='{}' AND numero={}".format(
            BASE_MANTENER, CODIGO, LETRA, NUMERO))
    cnt = cursor.fetchone()[0]
    print(f"\n4. Verificacion {BASE_MANTENER}.pedico1: {cnt} renglones (debe ser 20)")

    if not dry_run:
        conn.commit()
        print("\n=== COMMIT OK - Duplicado eliminado de msgestion01 ===")
    else:
        print("\n=== DRY-RUN completado. Ejecutar con --ejecutar para borrar ===")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    main()
