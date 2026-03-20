#!/usr/bin/env python3
"""
analisis_valijas_go.py — Análisis de stock y velocidad de venta de Valijas GO
Ejecutar en Mac (conecta al 111) o en el server directamente.
"""
import pyodbc
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CONN_COMPRAS, CONN_ARTICULOS, get_conn_string
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

DEPOS_SQL = '(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)'

def main():
    # Forzar sin SSL para Mac → SQL Server 2012
    conn_str = CONN_COMPRAS
    if 'Encrypt' not in conn_str:
        conn_str += "Encrypt=no;TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str, timeout=15)
    cursor = conn.cursor()

    print("=" * 80)
    print("ANÁLISIS VALIJAS GO BY CALZALINDO")
    print("=" * 80)

    # 1. Buscar artículos de valijas GO
    print("\n── 1. ARTÍCULOS EN BASE ──")
    sql_arts = """
        SELECT a.codigo, RTRIM(a.descripcion_1) AS desc1,
               RTRIM(ISNULL(a.descripcion_4, '')) AS color,
               RTRIM(ISNULL(a.descripcion_5, '')) AS talle,
               a.marca, a.proveedor, a.precio_fabrica,
               a.codigo_sinonimo, a.estado
        FROM msgestion01art.dbo.articulo a
        WHERE (a.descripcion_1 LIKE '%VALIJA%' OR a.descripcion_1 LIKE '%GO BY%'
               OR a.descripcion_1 LIKE '%GO %VALIJA%' OR a.descripcion_1 LIKE '%RIGIDA%GO%'
               OR a.descripcion_1 LIKE '%SET%VALIJA%' OR a.descripcion_1 LIKE '%CARRY%ON%'
               OR a.descripcion_1 LIKE '%TROLLEY%')
          AND a.estado = 'V'
        ORDER BY a.descripcion_1
    """
    cursor.execute(sql_arts)
    arts = cursor.fetchall()
    cols = [d[0] for d in cursor.description]

    if not arts:
        # Intentar búsqueda más amplia por marca
        print("No encontré por descripción. Buscando por marca GO / CZL...")
        sql_marca = """
            SELECT DISTINCT m.codigo, RTRIM(m.descripcion) AS marca_desc
            FROM msgestion01art.dbo.marcas m
            WHERE m.descripcion LIKE '%GO%' OR m.descripcion LIKE '%CZL%'
               OR m.descripcion LIKE '%CALZALINDO%' OR m.descripcion LIKE '%VALIJA%'
        """
        cursor.execute(sql_marca)
        marcas = cursor.fetchall()
        print(f"Marcas encontradas: {marcas}")

        if marcas:
            marca_codes = ",".join(str(m[0]) for m in marcas)
            sql_arts2 = f"""
                SELECT a.codigo, RTRIM(a.descripcion_1) AS desc1,
                       RTRIM(ISNULL(a.descripcion_4, '')) AS color,
                       RTRIM(ISNULL(a.descripcion_5, '')) AS talle,
                       a.marca, a.proveedor, a.precio_fabrica,
                       a.codigo_sinonimo, a.estado
                FROM msgestion01art.dbo.articulo a
                WHERE a.marca IN ({marca_codes}) AND a.estado = 'V'
                ORDER BY a.descripcion_1
            """
            cursor.execute(sql_arts2)
            arts = cursor.fetchall()
            cols = [d[0] for d in cursor.description]

    if not arts:
        # Última chance: buscar todo lo que tenga "GO" en desc1
        print("Buscando por 'GO' en descripción...")
        sql_go = """
            SELECT TOP 50 a.codigo, RTRIM(a.descripcion_1) AS desc1,
                   RTRIM(ISNULL(a.descripcion_4, '')) AS color,
                   RTRIM(ISNULL(a.descripcion_5, '')) AS talle,
                   a.marca, a.proveedor, a.precio_fabrica,
                   a.codigo_sinonimo, a.estado
            FROM msgestion01art.dbo.articulo a
            WHERE a.descripcion_1 LIKE '%GO %' AND a.estado = 'V'
              AND a.descripcion_1 NOT LIKE '%ALGO%'
              AND a.descripcion_1 NOT LIKE '%LOGO%'
              AND a.descripcion_1 NOT LIKE '%CARGO%'
              AND a.descripcion_1 NOT LIKE '%GORRA%'
            ORDER BY a.descripcion_1
        """
        cursor.execute(sql_go)
        arts = cursor.fetchall()
        cols = [d[0] for d in cursor.description]

    if not arts:
        print("\n⚠️  NO SE ENCONTRARON ARTÍCULOS DE VALIJAS GO EN LA BASE.")
        print("Las valijas pueden no estar cargadas como artículos en msgestion01art.")
        conn.close()
        return

    codigos = [row[0] for row in arts]
    print(f"\nEncontrados: {len(arts)} artículos")
    print(f"{'Codigo':<10} {'Descripcion':<45} {'Color':<12} {'Talle':<6} {'Marca':<6} {'Precio':>10}")
    print("-" * 95)
    for r in arts:
        print(f"{r[0]:<10} {r[1][:44]:<45} {r[2]:<12} {r[3]:<6} {r[4]:<6} {r[6]:>10,.0f}" if r[6] else
              f"{r[0]:<10} {r[1][:44]:<45} {r[2]:<12} {r[3]:<6} {r[4]:<6} {'':>10}")

    # 2. Stock actual
    print("\n── 2. STOCK ACTUAL ──")
    filtro_cod = ",".join(str(c) for c in codigos)
    sql_stock = f"""
        SELECT s.articulo, RTRIM(a.descripcion_1) AS desc1,
               s.deposito, s.stock_actual
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE s.articulo IN ({filtro_cod})
          AND s.deposito IN {DEPOS_SQL}
          AND s.serie = ' '
        ORDER BY a.descripcion_1, s.deposito
    """
    cursor.execute(sql_stock)
    stocks = cursor.fetchall()

    stock_total = {}
    for r in stocks:
        art, desc, depo, stk = r
        if art not in stock_total:
            stock_total[art] = {'desc': desc, 'stock': 0, 'depos': {}}
        stock_total[art]['stock'] += stk
        stock_total[art]['depos'][depo] = stk

    total_pares = sum(v['stock'] for v in stock_total.values())
    print(f"\nStock total: {total_pares} unidades")
    print(f"{'Codigo':<10} {'Descripcion':<45} {'Stock':>8} {'Depositos'}")
    print("-" * 80)
    for art, v in sorted(stock_total.items(), key=lambda x: x[1]['desc']):
        depos_str = " | ".join(f"D{d}:{int(s)}" for d, s in v['depos'].items() if s != 0)
        print(f"{art:<10} {v['desc'][:44]:<45} {v['stock']:>8.0f} {depos_str}")

    # 3. Ventas últimos 3 meses
    print("\n── 3. VENTAS ──")
    hace_3 = (date.today() - relativedelta(months=3)).replace(day=1)
    hace_1 = (date.today() - relativedelta(months=1)).replace(day=1)

    sql_ventas = f"""
        SELECT v.articulo, RTRIM(a.descripcion_1) AS desc1,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS vtas,
               SUM(v.monto_facturado) AS monto,
               MIN(v.fecha) AS primera_vta,
               MAX(v.fecha) AS ultima_vta,
               COUNT(*) AS movimientos
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.articulo IN ({filtro_cod})
          AND v.codigo NOT IN (7, 36)
          AND v.fecha >= '{hace_3}'
        GROUP BY v.articulo, a.descripcion_1
        ORDER BY vtas DESC
    """
    cursor.execute(sql_ventas)
    ventas = cursor.fetchall()

    total_vendido = 0
    total_facturado = 0
    print(f"\n{'Codigo':<10} {'Descripcion':<40} {'Vtas':>6} {'Facturado':>12} {'Primera':>12} {'Ultima':>12}")
    print("-" * 95)
    for r in ventas:
        art, desc, vtas, monto, primera, ultima = r[0], r[1], r[2] or 0, r[3] or 0, r[4], r[5]
        total_vendido += vtas
        total_facturado += monto
        print(f"{art:<10} {desc[:39]:<40} {vtas:>6.0f} {monto:>12,.0f} {str(primera)[:10]:>12} {str(ultima)[:10]:>12}")

    if not ventas:
        print("Sin ventas en los últimos 3 meses.")

    # 4. Ventas por mes (para ver tendencia)
    print("\n── 4. VENTAS POR MES ──")
    sql_mensual = f"""
        SELECT YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS vtas,
               SUM(v.monto_facturado) AS monto
        FROM msgestionC.dbo.ventas1 v
        WHERE v.articulo IN ({filtro_cod})
          AND v.codigo NOT IN (7, 36)
          AND v.fecha >= DATEADD(year, -1, GETDATE())
        GROUP BY YEAR(v.fecha), MONTH(v.fecha)
        ORDER BY anio, mes
    """
    cursor.execute(sql_mensual)
    mensual = cursor.fetchall()
    for r in mensual:
        print(f"  {r[0]}-{r[1]:02d}: {r[2] or 0:>6.0f} unidades — ${r[3] or 0:>12,.0f}")

    # 5. Compras (nota de pedido / remitos de ingreso)
    print("\n── 5. COMPRAS / INGRESOS ──")
    sql_compras = f"""
        SELECT c2.codigo AS tipo, c2.letra,
               YEAR(c2.fecha_comprobante) AS anio, MONTH(c2.fecha_comprobante) AS mes,
               SUM(c1.cantidad) AS cant,
               SUM(c1.cantidad * c1.precio) AS monto
        FROM msgestionC.dbo.compras1 c1
        JOIN msgestionC.dbo.compras2 c2
             ON c1.empresa = c2.empresa AND c1.codigo = c2.codigo
             AND c1.letra = c2.letra AND c1.sucursal = c2.sucursal
             AND c1.numero = c2.numero AND c1.orden = c2.orden
        WHERE c1.articulo IN ({filtro_cod})
          AND c1.operacion = '+'
        GROUP BY c2.codigo, c2.letra, YEAR(c2.fecha_comprobante), MONTH(c2.fecha_comprobante)
        ORDER BY anio DESC, mes DESC
    """
    cursor.execute(sql_compras)
    compras = cursor.fetchall()
    total_comprado = 0
    for r in compras:
        tipo_desc = {1: 'Factura', 3: 'NC', 7: 'Remito', 36: 'Devol'}.get(r[0], f'Cod{r[0]}')
        print(f"  {r[2]}-{r[3]:02d} | {tipo_desc} {r[1]} | {r[4] or 0:>6.0f} unidades | ${r[5] or 0:>12,.0f}")
        if r[0] == 7:  # remitos = ingreso real
            total_comprado += (r[4] or 0)

    # 6. RESUMEN EJECUTIVO
    print("\n" + "=" * 80)
    print("RESUMEN EJECUTIVO — VALIJAS GO")
    print("=" * 80)
    print(f"  Stock actual:        {total_pares:>8.0f} unidades")
    print(f"  Vendido (3 meses):   {total_vendido:>8.0f} unidades")
    print(f"  Facturado (3 meses): ${total_facturado:>12,.0f}")
    if total_vendido > 0:
        dias_venta = (date.today() - hace_3).days
        vel_diaria = total_vendido / dias_venta
        vel_mensual = total_vendido / 3
        dias_cobertura = total_pares / vel_diaria if vel_diaria > 0 else 999
        ticket_prom = total_facturado / total_vendido

        print(f"  Velocidad:           {vel_mensual:>8.1f} /mes ({vel_diaria:.1f} /día)")
        print(f"  Ticket promedio:     ${ticket_prom:>12,.0f}")
        print(f"  Días de stock:       {dias_cobertura:>8.0f} días")
        print(f"  Se acaba:            {(date.today() + timedelta(days=dias_cobertura)).strftime('%d/%m/%Y')}")

        # A qué ritmo necesita vender para liquidar antes de invierno (1 mayo)
        dias_hasta_invierno = (date(2026, 5, 1) - date.today()).days
        vel_necesaria = total_pares / dias_hasta_invierno if dias_hasta_invierno > 0 else 0
        print(f"\n  ── PARA LIQUIDAR ANTES DE INVIERNO (1 mayo = {dias_hasta_invierno} días) ──")
        print(f"  Necesitas vender:    {vel_necesaria:.1f} /día ({vel_necesaria * 30:.0f} /mes)")
        print(f"  Ritmo actual:        {vel_diaria:.1f} /día")
        if vel_diaria > 0:
            ratio = vel_necesaria / vel_diaria
            if ratio > 1:
                print(f"  GAP:                 Necesitas {ratio:.1f}x más velocidad")
            else:
                print(f"  OK:                  Vas {1/ratio:.1f}x más rápido de lo necesario")
    else:
        print("  ⚠️ Sin ventas registradas — verificar si están facturadas por otro canal")

    conn.close()
    print("\nFin del análisis.")


if __name__ == "__main__":
    main()
