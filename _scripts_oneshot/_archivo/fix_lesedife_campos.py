#!/usr/bin/env python3
"""
fix_lesedife_campos.py — Completar campos faltantes de artículos LESEDIFE
=========================================================================
Los 238 artículos Lesedife fueron dados de alta por SST manualmente.
El script insertar_lesedife.py solo actualizó precios pero NO completó:
  - codigo_barra (se obtiene de la lista de precios Excel)
  - alicuota_iva1/iva2, tipo_iva
  - cuenta_compras, cuenta_ventas, cuenta_com_anti
  - calificacion, factura_por_total
  - tipo_codigo_barra, numero_maximo, stock
  - subrubro, linea, descripcion_3
  - formula (si quedó en 0)

Fuente de códigos de barra: "LISTA DE PRECIOS MARZO lesedife.XLS"
Cruza por codigo_prov (ej: "62.0100001") extraído de descripcion_1 del artículo.

EJECUTAR EN EL 111:
  py -3 fix_lesedife_campos.py                # DRY RUN
  py -3 fix_lesedife_campos.py --ejecutar     # PRODUCCION
"""

import sys
import os
import pyodbc
import socket

# Usar config.py para la conexión
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from config import CONN_ARTICULOS as CONN_ART, SERVIDOR

# -- CONSTANTES LESEDIFE -----------------------------------------------
PROVEEDOR = 42
MARCA = 42
DESCUENTO = 19      # 19% sobre precio lista
UTILIDAD_1 = 120
UTILIDAD_2 = 144
UTILIDAD_3 = 60
UTILIDAD_4 = 45

# Subrubro por prefijo de código proveedor (fallback)
SUBRUBRO_MAP = {
    "10":  37,   # mochilas/canoplas escolares
    "62":  18,   # carteras/accesorios Unicross
    "67":  18,   # carteras/accesorios Amayra
    "68":  18,   # mochilas/carteras Influencer
    "91":  37,   # cartucheras Street Wear
    "97":  37,   # cartucheras/canoplas
    "61":  18,   # accesorios Wilson
}

# Clasificación por palabras clave en descripción → (subrubro, rubro)
# subrubro: 18=carteras, 37=mochilas/escolares, 52=zapatería
# rubro: 1=dama, 2=todo, 3=hombre, 4=niño, 5=niña, 6=unisex
CLASIFICACION_DESC = [
    # Carteras/bolsos → siempre dama
    ("CARTERA",          18, 1),
    ("BOLSO",            18, 1),
    ("BANDOLERA",        18, 1),
    ("MORRAL",           18, 1),    # morral puede ser unisex pero Lesedife es dama
    ("RINONERA",         18, 6),    # riñonera unisex
    ("RIÑONERA",         18, 6),
    ("PORTANOTEBOOK",    18, 6),    # unisex
    ("PORTA NOTEBOOK",   18, 6),
    ("ORGANIZADOR",      18, 1),    # organizador de viaje → dama
    # Mochilas
    ("MOCHILA",          37, 6),    # unisex
    # Escolares
    ("CANOPLA",          37, 4),    # niños
    ("CARTUCHERA",       37, 4),    # niños
    ("LAPICERA",         37, 4),
    # Disney/Marvel → niños
    ("DISNEY",           37, 4),
    ("MARVEL",           37, 4),
    ("FROZEN",           37, 5),    # niña
    ("PRINCESAS",        37, 5),
    ("SPIDERMAN",        37, 4),    # niño
]


def cargar_lista_precios():
    """Carga la lista de precios Excel y retorna dict: codigo_prov → {barras, precio, desc}."""
    try:
        import pandas as pd
    except ImportError:
        print("  ⚠️  pandas no disponible — no se podrán cargar códigos de barra")
        return {}

    excel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "LISTA DE PRECIOS MARZO lesedife.XLS")
    if not os.path.exists(excel_path):
        print(f"  ⚠️  No se encontró: {excel_path}")
        return {}

    df = pd.read_excel(excel_path, header=None, skiprows=2)
    df.columns = ["codigo_prov", "descripcion", "codigo_barra", "precio_may", "cant_bulto"]
    df["codigo_prov"] = df["codigo_prov"].astype(str).str.strip(".").str.strip()
    df["codigo_barra"] = df["codigo_barra"].astype(str).str.strip()
    df["precio_may"] = pd.to_numeric(df["precio_may"], errors="coerce")

    mapa = {}
    for _, row in df.iterrows():
        cp = row["codigo_prov"]
        if cp and cp != "nan" and cp != "Código":
            mapa[cp] = {
                "barras": row["codigo_barra"] if row["codigo_barra"] != "nan" else "",
                "precio": row["precio_may"] if not pd.isna(row["precio_may"]) else 0,
                "desc":   str(row["descripcion"]).strip() if not pd.isna(row["descripcion"]) else "",
            }

    print(f"  Lista de precios: {len(mapa)} artículos cargados")
    return mapa


def extraer_codigo_prov(desc1):
    """Extrae el código proveedor de descripcion_1 (ej: '62.0100001 SURTIDO...' → '62.0100001')."""
    if not desc1:
        return ""
    parts = desc1.strip().split()
    if parts:
        # El código es la primera palabra, puede tener formato "62.0100001" o "67.T4016"
        cod = parts[0].strip(".")
        # Verificar que parece un código (tiene punto)
        if "." in cod:
            return cod
    return ""


def clasificar_por_descripcion(desc, codigo_prov):
    """Detecta subrubro y rubro por descripción y código proveedor.
    Retorna (subrubro, rubro)."""
    d = (desc or "").upper()
    # Primero por descripción (más preciso)
    for keyword, subrubro, rubro in CLASIFICACION_DESC:
        if keyword in d:
            return subrubro, rubro
    # Fallback por prefijo de código proveedor
    if codigo_prov:
        prefijo = codigo_prov.split(".")[0] if "." in codigo_prov else ""
        sr = SUBRUBRO_MAP.get(prefijo, 18)
        return sr, 1  # default dama para Lesedife
    return 18, 1


def main():
    dry_run = "--ejecutar" not in sys.argv

    print(f"\n{'='*70}")
    print(f"FIX LESEDIFE — Completar campos faltantes")
    print(f"Servidor: {SERVIDOR} | Modo: {'DRY RUN' if dry_run else 'PRODUCCION'}")
    print(f"{'='*70}")

    # Cargar lista de precios para códigos de barra
    lista = cargar_lista_precios()

    # Conectar y leer artículos Lesedife
    conn = pyodbc.connect(CONN_ART, timeout=10, autocommit=False)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT codigo, descripcion_1, descripcion_3, descripcion_4,
               codigo_barra, codigo_sinonimo,
               precio_fabrica, precio_costo,
               precio_1, precio_2, precio_3, precio_4,
               utilidad_1, utilidad_2, utilidad_3, utilidad_4,
               descuento,
               alicuota_iva1, alicuota_iva2, tipo_iva,
               cuenta_compras, cuenta_ventas, cuenta_com_anti,
               calificacion, factura_por_total,
               tipo_codigo_barra, numero_maximo, stock, moneda,
               formula, subrubro, linea, rubro
        FROM articulo
        WHERE proveedor = ? AND estado = 'V'
        ORDER BY codigo
    """, PROVEEDOR)
    rows = cursor.fetchall()

    if not rows:
        print("  No se encontraron artículos Lesedife.")
        conn.close()
        return

    print(f"  Artículos Lesedife en BD: {len(rows)}")

    fixed = 0
    barras_ok = 0
    precios_ok = 0
    campo_stats = {}

    for row in rows:
        codigo = row.codigo
        desc1 = (row.descripcion_1 or "").strip()
        codigo_prov = extraer_codigo_prov(desc1)
        info_lista = lista.get(codigo_prov, {})

        updates = []
        params = []

        # -- CÓDIGO DE BARRA (de la lista de precios) --
        barras_actual = str(row.codigo_barra or "").strip()
        barras_lista = info_lista.get("barras", "")
        if (not barras_actual or barras_actual == "0") and barras_lista:
            updates.append("codigo_barra = ?")
            params.append(barras_lista)
            campo_stats["codigo_barra"] = campo_stats.get("codigo_barra", 0) + 1
            barras_ok += 1

        # -- CODIGO_SINONIMO (si vacío, usar código proveedor) --
        sin_actual = str(row.codigo_sinonimo or "").strip()
        if not sin_actual and codigo_prov:
            updates.append("codigo_sinonimo = ?")
            params.append(codigo_prov)
            campo_stats["codigo_sinonimo"] = campo_stats.get("codigo_sinonimo", 0) + 1

        # -- PRECIOS (si precio_fabrica es NULL/0) --
        pf = row.precio_fabrica or 0
        precio_lista = info_lista.get("precio", 0)
        if pf == 0 and precio_lista > 0:
            pc = round(precio_lista * (1 - DESCUENTO / 100), 2)
            p1 = round(pc * (1 + UTILIDAD_1 / 100), 2)
            p2 = round(pc * (1 + UTILIDAD_2 / 100), 2)
            p3 = round(pc * (1 + UTILIDAD_3 / 100), 2)
            p4 = round(pc * (1 + UTILIDAD_4 / 100), 2)
            updates.extend([
                "precio_fabrica = ?", "precio_costo = ?", "precio_sugerido = ?",
                "precio_1 = ?", "precio_2 = ?", "precio_3 = ?", "precio_4 = ?",
                "utilidad_1 = ?", "utilidad_2 = ?", "utilidad_3 = ?", "utilidad_4 = ?",
                "descuento = ?",
            ])
            params.extend([
                precio_lista, pc, pc,
                p1, p2, p3, p4,
                UTILIDAD_1, UTILIDAD_2, UTILIDAD_3, UTILIDAD_4,
                DESCUENTO,
            ])
            campo_stats["precio_fabrica"] = campo_stats.get("precio_fabrica", 0) + 1
            precios_ok += 1
        elif pf > 0:
            # Precios existen, pero verificar utilidades
            if (row.utilidad_2 or 0) == 0:
                updates.extend([
                    "utilidad_2 = ?", "utilidad_3 = ?", "utilidad_4 = ?",
                ])
                params.extend([UTILIDAD_2, UTILIDAD_3, UTILIDAD_4])
                campo_stats["utilidades"] = campo_stats.get("utilidades", 0) + 1

        # -- CAMPOS FISCALES/CONTABLES/GESTIÓN --
        campos_default = {
            "alicuota_iva1":     (row.alicuota_iva1,     21,        "num"),
            "alicuota_iva2":     (row.alicuota_iva2,     10.5,      "num"),
            "tipo_iva":          (row.tipo_iva,           "G",       "str"),
            "cuenta_compras":    (row.cuenta_compras,     "1010601", "str"),
            "cuenta_ventas":     (row.cuenta_ventas,      "4010100", "str"),
            "cuenta_com_anti":   (row.cuenta_com_anti,    "1010601", "str"),
            "calificacion":      (row.calificacion,       "G",       "str"),
            "factura_por_total": (row.factura_por_total,  "N",       "str"),
            "tipo_codigo_barra": (row.tipo_codigo_barra,  "C",       "str"),
            "numero_maximo":     (row.numero_maximo,      "S",       "str"),
            "stock":             (row.stock,              "S",       "str"),
            "formula":           (row.formula,            1,         "num"),
        }

        for campo, (val, default, tipo) in campos_default.items():
            is_empty = False
            if tipo == "num":
                is_empty = (val is None or val == 0)
            else:
                is_empty = (val is None or str(val).strip() == "")
            if is_empty:
                updates.append(f"{campo} = ?")
                params.append(default)
                campo_stats[campo] = campo_stats.get(campo, 0) + 1

        # -- MONEDA --
        if row.moneda is None:
            updates.append("moneda = ?")
            params.append(0)
            campo_stats["moneda"] = campo_stats.get("moneda", 0) + 1

        # -- SUBRUBRO y RUBRO (por descripción) --
        sr_det, rub_det = clasificar_por_descripcion(desc1, codigo_prov)
        if (row.subrubro or 0) == 0:
            updates.append("subrubro = ?")
            params.append(sr_det)
            campo_stats["subrubro"] = campo_stats.get("subrubro", 0) + 1
        if (row.rubro or 0) == 0:
            updates.append("rubro = ?")
            params.append(rub_det)
            campo_stats["rubro"] = campo_stats.get("rubro", 0) + 1

        # -- LINEA (4 = todo el año para accesorios) --
        if (row.linea or 0) == 0:
            updates.append("linea = ?")
            params.append(4)
            campo_stats["linea"] = campo_stats.get("linea", 0) + 1

        # -- DESCRIPCION_3 --
        if not row.descripcion_3 or row.descripcion_3.strip() == "":
            if desc1:
                updates.append("descripcion_3 = ?")
                params.append(desc1[:26])
                campo_stats["descripcion_3"] = campo_stats.get("descripcion_3", 0) + 1

        # -- Aplicar --
        if updates:
            updates.append("fecha_modificacion = GETDATE()")
            sql = f"UPDATE articulo SET {', '.join(updates)} WHERE codigo = ?"
            params.append(codigo)

            if not dry_run:
                cursor.execute(sql, params)
            fixed += 1

    # Resumen
    print(f"\n  Artículos con campos faltantes: {fixed}/{len(rows)}")
    print(f"  Códigos de barra completados: {barras_ok}")
    print(f"  Precios completados: {precios_ok}")

    if campo_stats:
        print(f"\n  Detalle campos faltantes:")
        for campo, cnt in sorted(campo_stats.items(), key=lambda x: -x[1]):
            print(f"    {campo:<25} → {cnt:>5} artículos")

    if fixed == 0:
        print("\n  Todo completo.")
    elif dry_run:
        print(f"\n  [DRY RUN] {fixed} artículos necesitan fix")
        print(f"  Usar: py -3 fix_lesedife_campos.py --ejecutar")
    else:
        conn.commit()
        print(f"\n  ✅ {fixed} artículos actualizados")

    conn.close()


if __name__ == "__main__":
    main()
