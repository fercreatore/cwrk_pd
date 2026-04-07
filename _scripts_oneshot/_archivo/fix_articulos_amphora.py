#!/usr/bin/env python3
"""
fix_articulos_amphora.py
========================
Completa los campos faltantes de los 21 artículos Amphora AW2026
que fueron insertados con solo 12 campos (faltaban precios, IVA,
cuentas contables, descripcion_3/4, etc.)

Artículos afectados: proveedor=44, marca=44 (los más recientes)

EJECUTAR EN EL 111:
  py -3 fix_articulos_amphora.py            # DRY RUN
  py -3 fix_articulos_amphora.py --ejecutar
"""

import sys
import pyodbc
import socket
from datetime import date

# -- AUTO-DETECT SERVER vs MAC -----------------------------------------
_hostname = socket.gethostname().upper()
if _hostname in ("DELL-SVR", "DELLSVR"):
    SERVIDOR = "localhost"
    DRIVER = "ODBC Driver 17 for SQL Server"
    EXTRAS = ""
else:
    SERVIDOR = "192.168.2.111"
    DRIVER = "ODBC Driver 18 for SQL Server"
    EXTRAS = "TrustServerCertificate=yes;Encrypt=no;"

CONN_STR = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVIDOR};"
    f"DATABASE=msgestion01art;"
    f"UID=am;PWD=dl;"
    f"{EXTRAS}"
)

# -- CONSTANTES Amphora ------------------------------------------------
PROVEEDOR = 44
MARCA = 44
UTILIDAD_1 = 100
UTILIDAD_2 = 124
UTILIDAD_3 = 60
UTILIDAD_4 = 45

# Colores posibles en descripciones Amphora
_COLORES = [
    "CAFE OSCURO", "BLANCO ESPECIAL",
    "NEGRO", "CAFE", "TAUPE", "BLANCO", "MARRON", "GRIS", "NATURAL", "BEIGE",
]


def extraer_color(desc):
    d = (desc or "").upper()
    for c in _COLORES:
        if d.endswith(c):
            return c
    parts = d.split()
    return parts[-1] if parts else ""


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    print(f"\n{'='*70}")
    print(f"FIX ARTÍCULOS AMPHORA — Completar campos faltantes")
    print(f"Servidor: {SERVIDOR} | Modo: {'DRY-RUN' if dry_run else 'PRODUCCION'}")
    print(f"{'='*70}")

    conn = pyodbc.connect(CONN_STR, timeout=10, autocommit=False)
    cursor = conn.cursor()

    # Buscar artículos Amphora con campos vacíos
    cursor.execute("""
        SELECT codigo, descripcion_1, descripcion_3, descripcion_4, descripcion_5,
               codigo_sinonimo, codigo_barra,
               precio_fabrica, precio_costo, precio_1, precio_2, precio_3, precio_4,
               utilidad_1, utilidad_2, utilidad_3, utilidad_4,
               alicuota_iva1, tipo_iva, formula, calificacion,
               cuenta_compras, subrubro, linea, tipo_codigo_barra,
               numero_maximo, stock, factura_por_total
        FROM articulo
        WHERE proveedor = ? AND marca = ?
        ORDER BY codigo
    """, PROVEEDOR, MARCA)
    rows = cursor.fetchall()

    if not rows:
        print("  No se encontraron artículos Amphora.")
        conn.close()
        return

    print(f"\n  Encontrados: {len(rows)} artículos Amphora")

    fixed = 0
    for row in rows:
        codigo = row.codigo
        desc1 = (row.descripcion_1 or "").strip()
        needs_fix = False
        updates = []
        params = []

        # Verificar campos faltantes
        if not row.descripcion_3:
            updates.append("descripcion_3 = ?")
            params.append(desc1[:26])
            needs_fix = True

        if not row.descripcion_4:
            color = extraer_color(desc1)
            updates.append("descripcion_4 = ?")
            params.append(color)
            needs_fix = True

        if not row.codigo_barra and row.codigo_sinonimo:
            updates.append("codigo_barra = ?")
            params.append(row.codigo_sinonimo)
            needs_fix = True

        pf = row.precio_fabrica or 0
        if pf == 0 and (row.precio_4 or 0) > 0:
            # precio_4 fue usado como precio_fabrica en la inserción original
            pf = row.precio_4
            updates.append("precio_fabrica = ?")
            params.append(pf)
            needs_fix = True

        pc = pf  # sin descuento para Amphora
        if (row.precio_costo or 0) == 0 and pf > 0:
            updates.append("precio_costo = ?")
            params.append(pc)
            updates.append("precio_sugerido = ?")
            params.append(pc)
            needs_fix = True

        if (row.precio_1 or 0) == 0 and pf > 0:
            p1 = round(pc * (1 + UTILIDAD_1 / 100), 2)
            p2 = round(pc * (1 + UTILIDAD_2 / 100), 2)
            p3 = round(pc * (1 + UTILIDAD_3 / 100), 2)
            updates.append("precio_1 = ?")
            params.append(p1)
            updates.append("precio_2 = ?")
            params.append(p2)
            updates.append("precio_3 = ?")
            params.append(p3)
            needs_fix = True

        if (row.utilidad_2 or 0) == 0:
            updates.append("utilidad_2 = ?")
            params.append(UTILIDAD_2)
            updates.append("utilidad_3 = ?")
            params.append(UTILIDAD_3)
            updates.append("utilidad_4 = ?")
            params.append(UTILIDAD_4)
            needs_fix = True

        if (row.alicuota_iva1 or 0) == 0:
            updates.append("alicuota_iva1 = ?")
            params.append(21)
            updates.append("alicuota_iva2 = ?")
            params.append(10.5)
            needs_fix = True

        if not row.tipo_iva or row.tipo_iva.strip() == '':
            updates.append("tipo_iva = ?")
            params.append('G')
            needs_fix = True

        if (row.formula or 0) == 0:
            updates.append("formula = ?")
            params.append(1)
            needs_fix = True

        if not row.calificacion or row.calificacion.strip() == '':
            updates.append("calificacion = ?")
            params.append('G')
            needs_fix = True

        if not row.cuenta_compras or row.cuenta_compras.strip() == '':
            updates.append("cuenta_compras = ?")
            params.append('1010601')
            updates.append("cuenta_ventas = ?")
            params.append('4010100')
            updates.append("cuenta_com_anti = ?")
            params.append('1010601')
            needs_fix = True

        if (row.subrubro or 0) == 0:
            updates.append("subrubro = ?")
            params.append(18)  # carteras/accesorios
            needs_fix = True

        if (row.linea or 0) == 0:
            updates.append("linea = ?")
            params.append(4)  # todo el año
            needs_fix = True

        if not row.tipo_codigo_barra or row.tipo_codigo_barra.strip() == '':
            updates.append("tipo_codigo_barra = ?")
            params.append('C')
            needs_fix = True

        if not row.numero_maximo or row.numero_maximo.strip() == '':
            updates.append("numero_maximo = ?")
            params.append('S')
            needs_fix = True

        if not row.stock or row.stock.strip() == '':
            updates.append("stock = ?")
            params.append('S')
            needs_fix = True

        if not row.factura_por_total or row.factura_por_total.strip() == '':
            updates.append("factura_por_total = ?")
            params.append('N')
            needs_fix = True

        # Siempre actualizar fecha_modificacion
        if needs_fix:
            updates.append("fecha_modificacion = GETDATE()")
            updates.append("usuario = 'COWORK'")

            sql = f"UPDATE articulo SET {', '.join(updates)} WHERE codigo = ?"
            params.append(codigo)

            if dry_run:
                color = extraer_color(desc1)
                print(f"  [{codigo}] {desc1[:40]:<40} → {len(updates)-2} campos a completar (color={color})")
            else:
                cursor.execute(sql, params)
                print(f"  [{codigo}] {desc1[:40]:<40} → {len(updates)-2} campos actualizados")
            fixed += 1

    if fixed == 0:
        print("\n  Todos los artículos ya están completos.")
    elif dry_run:
        print(f"\n  [DRY RUN] {fixed}/{len(rows)} artículos necesitan fix")
        print(f"  Usar: py -3 fix_articulos_amphora.py --ejecutar")
    else:
        conn.commit()
        print(f"\n  ✅ {fixed}/{len(rows)} artículos actualizados")

    conn.close()


if __name__ == "__main__":
    main()
