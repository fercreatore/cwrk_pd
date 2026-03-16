#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FIX COMPLETO DIADORA — Corrige stock triplicado + recrea pedido #1134068.

Problema: el remito se intentó cargar varias veces, cada intento sumó stock
pero falló en pedico1_entregas (PK violation). El stock quedó triplicado.

Acciones:
1. Para cada artículo DIADORA (360527-360546):
   - DELETE todos los registros de stock en msgestion03
   - INSERT uno solo con la cantidad correcta (de compras1)
2. Recrear pedido #1134068 en pedico2+pedico1 (marcado como entregado)
3. Verificar pedico1_entregas

Ejecutar en 111: py -3 fix_diadora_completo.py [--ejecutar]
"""
import pyodbc
import sys

CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes;"
)

BASE = 'msgestion03'
DEPOSITO = 11
ARTS_INICIO = 360527
ARTS_FIN = 360546

# Pedido
NUMERO = 1134068
ORDEN = 1
CODIGO = 8
LETRA = 'X'
SUCURSAL = 1
PROVEEDOR = 614
DENOMINACION = "CALZADOS BLANCO S.A."
FECHA = '2026-03-05'
OBSERVACIONES = "Factura A 0023-00062015 Calzados Blanco (Diadora). Remito 0024-00066200. 4 modelos, 48 pares. Bonif 5%."

# 20 renglones: (renglon, articulo, cantidad, precio)
RENGLONES = [
    (1,  360527, 2, 36841.57),
    (2,  360528, 3, 36841.57),
    (3,  360529, 3, 36841.57),
    (4,  360530, 2, 36841.57),
    (5,  360531, 2, 36841.57),
    (6,  360532, 2, 36841.57),
    (7,  360533, 3, 36841.57),
    (8,  360534, 3, 36841.57),
    (9,  360535, 2, 36841.57),
    (10, 360536, 2, 36841.57),
    (11, 360537, 2, 39999.47),
    (12, 360538, 3, 39999.47),
    (13, 360539, 3, 39999.47),
    (14, 360540, 2, 39999.47),
    (15, 360541, 2, 39999.47),
    (16, 360542, 2, 31578.42),
    (17, 360543, 3, 31578.42),
    (18, 360544, 3, 31578.42),
    (19, 360545, 2, 31578.42),
    (20, 360546, 2, 31578.42),
]


def main():
    dry_run = '--ejecutar' not in sys.argv
    if dry_run:
        print("=== MODO DRY-RUN (agregar --ejecutar para grabar) ===\n")

    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    # ============================================================
    # PARTE 1: FIX STOCK
    # ============================================================
    print("=" * 60)
    print("PARTE 1: CORREGIR STOCK DIADORA (360527-360546)")
    print("=" * 60)

    # Obtener cantidades reales de compras1
    cursor.execute(f"""
        SELECT articulo, SUM(
            CASE WHEN operacion = '+' THEN CAST(cantidad AS INT)
                 WHEN operacion = '-' THEN -CAST(cantidad AS INT)
                 ELSE 0 END
        ) AS stock_real
        FROM {BASE}.dbo.compras1
        WHERE articulo BETWEEN {ARTS_INICIO} AND {ARTS_FIN}
        GROUP BY articulo
    """)
    stock_real = {row[0]: row[1] for row in cursor.fetchall()}

    for art in range(ARTS_INICIO, ARTS_FIN + 1):
        # Ver stock actual
        cursor.execute(f"""
            SELECT serie, CAST(stock_actual AS INT) as stk
            FROM {BASE}.dbo.stock
            WHERE articulo = {art} AND deposito = {DEPOSITO}
        """)
        filas = cursor.fetchall()
        stk_total = sum(f[1] for f in filas)
        stk_correcto = stock_real.get(art, 0)

        if stk_total != stk_correcto or len(filas) > 1:
            print(f"  Art {art}: stock actual={stk_total} ({len(filas)} filas) -> correcto={stk_correcto}")

            if not dry_run:
                # Borrar todos los registros de stock
                cursor.execute(f"""
                    DELETE FROM {BASE}.dbo.stock
                    WHERE articulo = {art} AND deposito = {DEPOSITO}
                """)
                # Insertar uno solo con la cantidad correcta (serie del remito)
                if stk_correcto > 0:
                    cursor.execute(f"""
                        INSERT INTO {BASE}.dbo.stock (deposito, articulo, stock_actual, serie, stock_unidades)
                        VALUES ({DEPOSITO}, {art}, {stk_correcto}, '2603', {stk_correcto})
                    """)
                print(f"         CORREGIDO -> {stk_correcto}")
        else:
            print(f"  Art {art}: OK (stock={stk_total})")

    # ============================================================
    # PARTE 2: RECREAR PEDIDO #1134068
    # ============================================================
    print(f"\n{'=' * 60}")
    print(f"PARTE 2: RECREAR PEDIDO #{NUMERO}")
    print("=" * 60)

    # Verificar que no existe
    cursor.execute(f"""
        SELECT COUNT(*) FROM {BASE}.dbo.pedico2
        WHERE codigo={CODIGO} AND letra='{LETRA}' AND numero={NUMERO}
    """)
    cnt = cursor.fetchone()[0]
    if cnt > 0:
        print(f"  Pedido {NUMERO} YA EXISTE ({cnt} cabeceras). Saltando.")
    else:
        total_pares = sum(r[2] for r in RENGLONES)
        print(f"  Inserting: {len(RENGLONES)} renglones, {total_pares} pares")

        # INSERT pedico2
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
        if not dry_run:
            cursor.execute(sql_p2)
            print("  pedico2 OK")

        # INSERT pedico1
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

        print(f"  pedico1 OK ({len(RENGLONES)} renglones)")

        # INSERT pedico1_entregas
        for reng, art, cant, precio in RENGLONES:
            # Verificar si ya existe
            cursor.execute(f"""
                SELECT COUNT(*) FROM {BASE}.dbo.pedico1_entregas
                WHERE codigo={CODIGO} AND letra='{LETRA}'
                  AND sucursal={SUCURSAL} AND numero={NUMERO}
                  AND orden={ORDEN} AND renglon={reng}
            """)
            if cursor.fetchone()[0] > 0:
                continue  # Ya existe, saltar

            sql_pe = f"""
            INSERT INTO {BASE}.dbo.pedico1_entregas (
                codigo, letra, sucursal, numero, orden,
                renglon, articulo, cantidad, deposito, fecha_entrega
            ) VALUES (
                {CODIGO}, '{LETRA}', {SUCURSAL}, {NUMERO}, {ORDEN},
                {reng}, {art}, {cant}, {DEPOSITO}, '{FECHA}'
            )
            """
            if not dry_run:
                cursor.execute(sql_pe)

        print(f"  pedico1_entregas OK")

    # COMMIT
    if not dry_run:
        conn.commit()
        print(f"\n=== COMMIT OK ===")
    else:
        print(f"\n=== DRY-RUN completado. Ejecutar con --ejecutar ===")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    main()
