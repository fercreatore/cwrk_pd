#!/usr/bin/env python3
"""
fix_campos_articulos.py — Completa campos faltantes en artículos
================================================================
Script genérico que detecta y completa campos vacíos/NULL en artículos
de msgestion01art.dbo.articulo.

Puede filtrar por proveedor, marca, rango de códigos, o todos.

CAMPOS OBLIGATORIOS (checklist — ver CHECKLIST_ALTA_ARTICULOS.md):
  Fiscal:     alicuota_iva1=21, alicuota_iva2=10.5, tipo_iva='G'
  Contable:   cuenta_compras='1010601', cuenta_ventas='4010100', cuenta_com_anti='1010601'
  Pricing:    precio_fabrica, precio_costo, precio_sugerido, precio_1/2/3/4
              utilidad_1/2/3/4, descuento, formula=1
  Clasificac: calificacion='G', subrubro, linea, grupo
  Gestión:    tipo_codigo_barra='C', numero_maximo='S', stock='S',
              factura_por_total='N', moneda=0
  Audit:      usuario, abm='A', fecha_alta

EJECUTAR EN EL 111:
  py -3 fix_campos_articulos.py --proveedor 42            # Lesedife dry-run
  py -3 fix_campos_articulos.py --proveedor 44            # Amphora dry-run
  py -3 fix_campos_articulos.py --proveedor 42 --ejecutar # Lesedife real
  py -3 fix_campos_articulos.py --todos                   # TODOS los artículos
"""

import sys
import pyodbc
import socket
import argparse

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

# -- DEFAULTS para campos faltantes ------------------------------------
DEFAULTS = {
    "alicuota_iva1":     21,
    "alicuota_iva2":     10.5,
    "tipo_iva":          "G",
    "cuenta_compras":    "1010601",
    "cuenta_ventas":     "4010100",
    "cuenta_com_anti":   "1010601",
    "calificacion":      "G",
    "factura_por_total": "N",
    "tipo_codigo_barra": "C",
    "numero_maximo":     "S",
    "stock":             "S",
    "moneda":            0,
    "formula":           1,
}

# Campos que verificamos si están vacíos/NULL
CAMPOS_CHECK = list(DEFAULTS.keys()) + [
    "precio_fabrica", "precio_costo", "precio_1",
    "utilidad_2", "utilidad_3", "utilidad_4",
    "subrubro", "linea", "descripcion_3", "descripcion_4",
]


def main():
    parser = argparse.ArgumentParser(description="Completar campos faltantes en artículos")
    parser.add_argument("--proveedor", type=int, help="Filtrar por número de proveedor")
    parser.add_argument("--marca", type=int, help="Filtrar por marca")
    parser.add_argument("--desde", type=int, help="Desde código artículo")
    parser.add_argument("--hasta", type=int, help="Hasta código artículo")
    parser.add_argument("--todos", action="store_true", help="Revisar TODOS los artículos")
    parser.add_argument("--ejecutar", action="store_true", help="Ejecutar (default: dry-run)")
    args = parser.parse_args()

    dry_run = not args.ejecutar

    if not args.proveedor and not args.marca and not args.desde and not args.todos:
        print("Usar: --proveedor N, --marca N, --desde/--hasta N, o --todos")
        print("Ejemplo: py -3 fix_campos_articulos.py --proveedor 42")
        sys.exit(1)

    # Construir WHERE
    where_parts = ["estado = 'V'"]
    where_params = []
    if args.proveedor:
        where_parts.append("proveedor = ?")
        where_params.append(args.proveedor)
    if args.marca:
        where_parts.append("marca = ?")
        where_params.append(args.marca)
    if args.desde:
        where_parts.append("codigo >= ?")
        where_params.append(args.desde)
    if args.hasta:
        where_parts.append("codigo <= ?")
        where_params.append(args.hasta)

    where_clause = " AND ".join(where_parts)

    print(f"\n{'='*70}")
    print(f"FIX CAMPOS ARTÍCULOS — {'DRY RUN' if dry_run else 'EJECUCIÓN'}")
    print(f"Servidor: {SERVIDOR}")
    print(f"Filtro: {where_clause} {where_params}")
    print(f"{'='*70}")

    conn = pyodbc.connect(CONN_STR, timeout=10, autocommit=False)
    cursor = conn.cursor()

    # Leer artículos
    campos_select = ", ".join([
        "codigo", "descripcion_1", "descripcion_3", "descripcion_4",
        "proveedor", "marca", "precio_fabrica", "precio_costo",
        "precio_1", "precio_2", "precio_3", "precio_4",
        "utilidad_1", "utilidad_2", "utilidad_3", "utilidad_4",
        "alicuota_iva1", "alicuota_iva2", "tipo_iva",
        "cuenta_compras", "cuenta_ventas", "cuenta_com_anti",
        "calificacion", "factura_por_total",
        "tipo_codigo_barra", "numero_maximo", "stock", "moneda",
        "formula", "subrubro", "linea",
    ])

    sql = f"SELECT {campos_select} FROM articulo WHERE {where_clause} ORDER BY codigo"
    cursor.execute(sql, where_params)
    rows = cursor.fetchall()

    if not rows:
        print("  No se encontraron artículos con ese filtro.")
        conn.close()
        return

    print(f"  Artículos encontrados: {len(rows)}")

    # Analizar y fijar
    fixed_count = 0
    campo_stats = {}  # campo → count de faltantes

    for row in rows:
        codigo = row.codigo
        updates = []
        params = []

        # Campos con default fijo
        for campo, default in DEFAULTS.items():
            val = getattr(row, campo, None)
            is_empty = (val is None or
                        (isinstance(val, (int, float)) and val == 0) or
                        (isinstance(val, str) and val.strip() == ''))
            if is_empty:
                updates.append(f"{campo} = ?")
                params.append(default)
                campo_stats[campo] = campo_stats.get(campo, 0) + 1

        # descripcion_3 (si vacío, usar desc_1[:26])
        if not row.descripcion_3 or row.descripcion_3.strip() == '':
            desc1 = (row.descripcion_1 or "").strip()
            if desc1:
                updates.append("descripcion_3 = ?")
                params.append(desc1[:26])
                campo_stats["descripcion_3"] = campo_stats.get("descripcion_3", 0) + 1

        if updates:
            updates.append("fecha_modificacion = GETDATE()")
            sql_update = f"UPDATE articulo SET {', '.join(updates)} WHERE codigo = ?"
            params.append(codigo)

            if not dry_run:
                cursor.execute(sql_update, params)

            fixed_count += 1

    # Resumen
    print(f"\n  Artículos con campos faltantes: {fixed_count}/{len(rows)}")
    if campo_stats:
        print(f"\n  Campos faltantes (top):")
        for campo, cnt in sorted(campo_stats.items(), key=lambda x: -x[1]):
            print(f"    {campo:<25} → {cnt:>5} artículos")

    if fixed_count == 0:
        print("\n  Todos los artículos están completos.")
    elif dry_run:
        print(f"\n  [DRY RUN] {fixed_count} artículos necesitan fix")
        print(f"  Agregar --ejecutar para aplicar")
    else:
        conn.commit()
        print(f"\n  ✅ {fixed_count} artículos actualizados")

    conn.close()


if __name__ == "__main__":
    main()
