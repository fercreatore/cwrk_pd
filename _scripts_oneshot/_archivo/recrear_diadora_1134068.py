#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Recrear pedido DIADORA #1134068 que fue borrado accidentalmente.
pedico1/pedico2 son tablas COMPARTIDAS — se insertan en msgestion03.
Los artículos 360527-360546 YA EXISTEN, solo recreamos pedico2+pedico1.
Se marca como ENTREGADO (cantidad_entregada = cantidad) porque ya se cargó remito.

Ejecutar en 111: py -3 recrear_diadora_1134068.py [--ejecutar]
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
ORDEN = 1
CODIGO = 8
LETRA = 'X'
SUCURSAL = 1
PROVEEDOR = 614
DENOMINACION = "CALZADOS BLANCO S.A."
FECHA = '2026-03-05'
OBSERVACIONES = "Factura A 0023-00062015 Calzados Blanco (Diadora). Remito 0024-00066200. 4 modelos, 48 pares. Bonif 5%."
BASE = 'msgestion03'

# 20 renglones: (renglon, articulo, cantidad, precio)
RENGLONES = [
    # CONSTANZA 2116 NEGRO/NEGRO/PINK T37-41
    (1,  360527, 2, 36841.57),   # T37
    (2,  360528, 3, 36841.57),   # T38
    (3,  360529, 3, 36841.57),   # T39
    (4,  360530, 2, 36841.57),   # T40
    (5,  360531, 2, 36841.57),   # T41
    # PROTON 2669 NEGRO/AZUL/CORAL T36-40
    (6,  360532, 2, 36841.57),   # T36
    (7,  360533, 3, 36841.57),   # T37
    (8,  360534, 3, 36841.57),   # T38
    (9,  360535, 2, 36841.57),   # T39
    (10, 360536, 2, 36841.57),   # T40
    # CHRONOS 2684 NEGRO/CORAL T36-40
    (11, 360537, 2, 39999.47),   # T36
    (12, 360538, 3, 39999.47),   # T37
    (13, 360539, 3, 39999.47),   # T38
    (14, 360540, 2, 39999.47),   # T39
    (15, 360541, 2, 39999.47),   # T40
    # RIVER 2690 NEGRO/PINK T36-40
    (16, 360542, 2, 31578.42),   # T36
    (17, 360543, 3, 31578.42),   # T37
    (18, 360544, 3, 31578.42),   # T38
    (19, 360545, 2, 31578.42),   # T39
    (20, 360546, 2, 31578.42),   # T40
]


def main():
    dry_run = '--ejecutar' not in sys.argv
    if dry_run:
        print("=== MODO DRY-RUN (agregar --ejecutar para grabar) ===\n")

    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    # Verificar que no existe ya
    cursor.execute(f"SELECT COUNT(*) FROM {BASE}.dbo.pedico2 WHERE codigo={CODIGO} AND letra='{LETRA}' AND numero={NUMERO}")
    cnt = cursor.fetchone()[0]
    if cnt > 0:
        print(f"  PEDIDO {NUMERO} YA EXISTE en {BASE} ({cnt} cabeceras). Abortando.")
        return

    # Calcular totales
    total_pares = sum(r[2] for r in RENGLONES)
    total_monto = sum(r[2] * r[3] for r in RENGLONES)
    print(f"Pedido #{NUMERO}: {len(RENGLONES)} renglones, {total_pares} pares, ${total_monto:,.0f}")

    # INSERT pedico2 (cabecera)
    sql_p2 = f"""
    INSERT INTO {BASE}.dbo.pedico2 (
        codigo, letra, sucursal, numero, orden,
        cuenta, denominacion, fecha_comprobante, fecha_vencimiento,
        estado, usuario, observaciones
    ) VALUES (
        {CODIGO}, '{LETRA}', {SUCURSAL}, {NUMERO}, {ORDEN},
        {PROVEEDOR}, '{DENOMINACION}', '{FECHA}', '{FECHA}',
        'V', 'COWORK', '{OBSERVACIONES}'
    )
    """
    print(f"\n1. INSERT pedico2 cabecera")
    if not dry_run:
        cursor.execute(sql_p2)
        print(f"   OK")

    # INSERT pedico1 (renglones) - marcados como ENTREGADOS
    print(f"\n2. INSERT pedico1 ({len(RENGLONES)} renglones)")
    for reng, art, cant, precio in RENGLONES:
        monto = round(cant * precio, 2)
        sql_p1 = f"""
        INSERT INTO {BASE}.dbo.pedico1 (
            codigo, letra, sucursal, numero, orden, renglon,
            articulo, cantidad, precio,
            cantidad_entregada, monto_entregado,
            estado, cuenta
        ) VALUES (
            {CODIGO}, '{LETRA}', {SUCURSAL}, {NUMERO}, {ORDEN}, {reng},
            {art}, {cant}, {precio},
            {cant}, {monto},
            'V', {PROVEEDOR}
        )
        """
        if not dry_run:
            cursor.execute(sql_p1)
        print(f"   Reng {reng:2d}: art {art}, cant {cant}, ${precio:,.2f} (entregado={cant})")

    # INSERT pedico1_entregas (vinculación con remito)
    print(f"\n3. INSERT pedico1_entregas ({len(RENGLONES)} registros)")
    for reng, art, cant, precio in RENGLONES:
        sql_pe = f"""
        INSERT INTO {BASE}.dbo.pedico1_entregas (
            codigo, letra, sucursal, numero, orden,
            renglon, articulo, cantidad, deposito, fecha_entrega
        ) VALUES (
            {CODIGO}, '{LETRA}', {SUCURSAL}, {NUMERO}, {ORDEN},
            {reng}, {art}, {cant}, 11, '{FECHA}'
        )
        """
        if not dry_run:
            cursor.execute(sql_pe)
        print(f"   Reng {reng:2d}: art {art}, entregado {cant}")

    if not dry_run:
        conn.commit()
        print(f"\n=== COMMIT OK — Pedido #{NUMERO} recreado con {total_pares} pares (entregado) ===")
    else:
        print(f"\n=== DRY-RUN completado. Ejecutar con --ejecutar ===")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    main()
