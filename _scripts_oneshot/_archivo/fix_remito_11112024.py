#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix remito R 1-11112024 (GO by CZL, 12/mar/2026)
El remito se creo parcialmente: compras2/compras1/movi_stock/stock OK
pero pedico1_entregas y pedico1.cantidad_entregada no se actualizaron.

Ejecutar en 111: py -3 _scripts_oneshot/fix_remito_11112024.py
"""
import pyodbc
import sys

CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes;"
)

# Los 3 items del remito: pedido 49, orden 28
# Cada uno entrego 1 unidad a H4 (msgestion03)
ITEMS = [
    # (ped_renglon, articulo, cantidad, precio)
    (1, 359231, 1, 27000),   # VALIJA NEGRA 17"
    (2, 359233, 1, 31500),   # VALIJA NEGRA 19"
    (3, 359235, 1, 36000),   # VALIJA NEGRA 21"
]

PED_SUCURSAL = 0
PED_NUMERO = 49
PED_ORDEN = 28
DEPOSITO = 11
FECHA = '2026-03-12'
BASE = 'msgestion03'  # H4


def main():
    dry_run = '--ejecutar' not in sys.argv
    if dry_run:
        print("=== MODO DRY-RUN (agregar --ejecutar para grabar) ===\n")

    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    for renglon, articulo, cantidad, precio in ITEMS:
        monto = precio * cantidad
        print(f"Renglon {renglon}: art {articulo}, cant {cantidad}, ${monto:,.0f}")

        # UPSERT pedico1_entregas
        sql_check = f"""
        SELECT cantidad FROM {BASE}.dbo.pedico1_entregas
        WHERE codigo=8 AND letra='X' AND sucursal={PED_SUCURSAL}
          AND numero={PED_NUMERO} AND orden={PED_ORDEN} AND renglon={renglon}
        """
        cursor.execute(sql_check)
        row = cursor.fetchone()

        if row:
            cant_actual = row[0]
            print(f"  pedico1_entregas: YA EXISTE con cant={cant_actual}, sumando {cantidad}")
            sql_pe = f"""
            UPDATE {BASE}.dbo.pedico1_entregas
            SET cantidad = ISNULL(cantidad, 0) + {cantidad},
                fecha_entrega = '{FECHA}'
            WHERE codigo=8 AND letra='X' AND sucursal={PED_SUCURSAL}
              AND numero={PED_NUMERO} AND orden={PED_ORDEN} AND renglon={renglon}
            """
        else:
            print(f"  pedico1_entregas: NO EXISTE, insertando")
            sql_pe = f"""
            INSERT INTO {BASE}.dbo.pedico1_entregas (
                codigo, letra, sucursal, numero, orden,
                renglon, articulo, cantidad, deposito, fecha_entrega
            ) VALUES (
                8, 'X', {PED_SUCURSAL}, {PED_NUMERO}, {PED_ORDEN},
                {renglon}, {articulo}, {cantidad}, {DEPOSITO}, '{FECHA}'
            )
            """

        if not dry_run:
            cursor.execute(sql_pe)
            print(f"  pedico1_entregas: OK")

        # UPDATE pedico1.cantidad_entregada
        sql_upd = f"""
        UPDATE {BASE}.dbo.pedico1
        SET cantidad_entregada = ISNULL(cantidad_entregada, 0) + {cantidad},
            monto_entregado = ISNULL(monto_entregado, 0) + {monto}
        WHERE codigo = 8 AND letra = 'X'
          AND sucursal = {PED_SUCURSAL} AND numero = {PED_NUMERO}
          AND orden = {PED_ORDEN} AND renglon = {renglon}
        """
        if not dry_run:
            cursor.execute(sql_upd)
            print(f"  pedico1 UPDATE: OK")
        else:
            print(f"  pedico1 UPDATE: (dry-run)")

    if not dry_run:
        conn.commit()
        print("\n=== COMMIT OK ===")
    else:
        print("\n=== DRY-RUN completado. Ejecutar con --ejecutar para grabar ===")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    main()
