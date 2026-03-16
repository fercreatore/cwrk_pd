#!/usr/bin/env python3
"""
alta_masiva_faltantes.py
Analiza el Excel de Topper, detecta todos los artículos (SAP+talle) que faltan
en la BD, y los inserta.

Usa la misma lógica que paso6b_flujo_topper.py para determinar:
- rubro: por rango de talle (35-40 → DAMAS=1, 40-45 → HOMBRES=3, <35 → NIÑOS=4)
- subrubro: de CATEGORIA_A_SUBRUBRO
- grupo: de SUBRUBRO_A_GRUPO_DEFAULT
- sinónimo: 668 + nombre(5 chars) + color(2 dígitos) + talle(2 dígitos)
"""

import sys
import os
# Agregar raiz del proyecto al path para encontrar config.py
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyodbc
from config import CONN_COMPRAS
from paso5b_parsear_topper import parsear_topper
from paso6b_flujo_topper import (
    inferir_subrubro, inferir_grupo, inferir_codigo_color,
    nombre_a_sku, CATEGORIA_A_SUBRUBRO, SUBRUBRO_A_GRUPO_DEFAULT, COLOR_A_CODIGO
)
from paso2_buscar_articulo import buscar_por_codigo_sap


def rubro_por_talle(talle_min, talle_max):
    """
    Determina rubro según rango de talles del modelo.
    35-40 → DAMAS(1), 40-45 → HOMBRES(3), <35 → NIÑOS(4)
    """
    if talle_max <= 34:
        return 4  # NIÑOS
    elif talle_min >= 40:
        return 3  # HOMBRES
    elif talle_max <= 40:
        return 1  # DAMAS
    else:
        # Mixto — si empieza en 35+ es más DAMAS, si va hasta 45+ es más HOMBRES
        if talle_min >= 35 and talle_max <= 40:
            return 1  # DAMAS
        elif talle_min >= 39:
            return 3  # HOMBRES
        else:
            return 1  # default DAMAS para rangos ambiguos


def analizar_faltantes(ruta_excel):
    """
    Parsea el Excel y devuelve lista de artículos que faltan en la BD.
    Agrupa por (codigo_sap, color) para determinar rubro por rango de talles.
    """
    print("=" * 60)
    print("  ANÁLISIS DE ARTÍCULOS FALTANTES")
    print("=" * 60)

    # 1. Parsear Excel
    resultado = parsear_topper(ruta_excel)
    if not resultado:
        print("❌ Error parseando Excel")
        return []

    # 2. Recopilar todos los SAP+talle únicos del Excel
    articulos_excel = {}  # key: (sap, talle) → datos
    modelos_info = {}     # key: (sap, color) → {talles: set, datos}

    for pedido in resultado["pedidos"]:
        for r in pedido["renglones"]:
            sap = r["codigo_sap"]
            talle = r["talle"]
            color = r["color"]
            key = (sap, talle)

            if key not in articulos_excel:
                articulos_excel[key] = r

            modelo_key = (sap, color)
            if modelo_key not in modelos_info:
                modelos_info[modelo_key] = {
                    "talles": set(),
                    "modelo": r["modelo"],
                    "color": r["color"],
                    "genero": r["genero"],
                    "categoria": r["categoria"],
                    "precio_lista": r["precio_lista"],
                    "pvp": r["pvp"],
                }
            modelos_info[modelo_key]["talles"].add(int(talle))

    print(f"\n📊 Excel: {len(articulos_excel)} combinaciones SAP+talle únicas")
    print(f"   Modelos únicos (SAP+color): {len(modelos_info)}")

    # 3. Verificar cuáles ya existen en BD
    faltantes = []
    existentes = 0
    sap_cache = {}  # cache de búsquedas SAP

    print("\n🔍 Verificando contra BD...")

    for (sap, talle), datos in sorted(articulos_excel.items()):
        # Cache: buscar todos los talles de un SAP de una vez
        if sap not in sap_cache:
            resultados_bd = buscar_por_codigo_sap(sap)
            talles_existentes = set()
            for r in resultados_bd:
                if r.get("talle"):
                    talles_existentes.add(r["talle"].strip())
            sap_cache[sap] = {
                "talles": talles_existentes,
                "datos": resultados_bd[0] if resultados_bd else None
            }

        if talle.strip() in sap_cache[sap]["talles"]:
            existentes += 1
        else:
            faltantes.append({
                "sap": sap,
                "talle": talle,
                "datos_excel": datos,
                "modelo_existente": sap_cache[sap]["datos"],
            })

    print(f"\n📊 RESULTADO:")
    print(f"   Ya existen en BD : {existentes}")
    print(f"   Faltan crear     : {len(faltantes)}")

    # 4. Agrupar faltantes por modelo para mostrar resumen
    por_modelo = {}
    for f in faltantes:
        sap = f["sap"]
        color = f["datos_excel"]["color"]
        modelo = f["datos_excel"]["modelo"]
        key = f"{sap} {modelo} {color}"
        if key not in por_modelo:
            por_modelo[key] = {
                "sap": sap,
                "modelo": modelo,
                "color": color,
                "categoria": f["datos_excel"]["categoria"],
                "genero": f["datos_excel"]["genero"],
                "precio_lista": f["datos_excel"]["precio_lista"],
                "talles": [],
                "tiene_modelo_existente": f["modelo_existente"] is not None,
            }
        por_modelo[key]["talles"].append(f["talle"])

    print(f"\n{'─'*70}")
    print(f"  {'SAP':<7} {'MODELO':<20} {'COLOR':<25} {'TALLES':<15} {'CASO'}")
    print(f"{'─'*70}")
    for key, info in sorted(por_modelo.items()):
        talles_str = ",".join(sorted(info["talles"], key=lambda t: int(t)))
        caso = "talle nuevo" if info["tiene_modelo_existente"] else "MODELO NUEVO"
        print(f"  {info['sap']:<7} {info['modelo']:<20} {info['color'][:24]:<25} {talles_str:<15} {caso}")
    print(f"{'─'*70}")

    return faltantes, modelos_info


def insertar_faltantes(faltantes, modelos_info, dry_run=True):
    """
    Inserta todos los artículos faltantes en la BD.
    """
    if not faltantes:
        print("\n✅ No hay artículos faltantes. Todo OK.")
        return

    modo = "DRY RUN" if dry_run else "🚨 EJECUCIÓN REAL"
    print(f"\n{'='*60}")
    print(f"  INSERCIÓN DE {len(faltantes)} ARTÍCULOS — {modo}")
    print(f"{'='*60}")

    # Obtener MAX(codigo) actual
    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(codigo) FROM msgestion01art.dbo.articulo")
            max_codigo = cursor.fetchone()[0]
            print(f"  MAX(codigo) actual: {max_codigo}")
    except Exception as e:
        print(f"❌ Error obteniendo MAX(codigo): {e}")
        return

    insertados = 0
    errores = 0
    sql_insert = """
        INSERT INTO msgestion01art.dbo.articulo (
            descripcion_1, descripcion_3, descripcion_4, descripcion_5,
            codigo_sinonimo,
            subrubro, marca, linea, rubro, grupo,
            proveedor,
            precio_1, precio_2, precio_3, precio_costo,
            moneda,
            stock,
            estado, fecha_hora_creacion
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'S', 'V', GETDATE())
    """

    conn = None
    if not dry_run:
        try:
            conn = pyodbc.connect(CONN_COMPRAS, timeout=10)
        except Exception as e:
            print(f"❌ Error conectando: {e}")
            return

    for f in sorted(faltantes, key=lambda x: (x["sap"], int(x["talle"]))):
        sap = f["sap"]
        talle = f["talle"]
        datos = f["datos_excel"]
        modelo_existente = f["modelo_existente"]

        sap_padded = sap.zfill(6)
        modelo = datos["modelo"]
        color = datos["color"]
        precio_lista = datos["precio_lista"]
        pvp = datos["pvp"]
        categoria = datos["categoria"]
        genero = datos["genero"]

        # Determinar subrubro
        if modelo_existente:
            subrubro = modelo_existente["subrubro"]
            marca = modelo_existente["marca"]
            linea = modelo_existente["linea"]
        else:
            subrubro = inferir_subrubro(categoria)
            if not subrubro:
                print(f"  ❌ SAP:{sap} T:{talle} — categoría '{categoria}' no mapeada. SKIP.")
                errores += 1
                continue
            marca = 314  # TOPPER
            linea = 1    # Verano (default H1)

        # Determinar rubro por rango de talles
        modelo_key = (sap, color)
        if modelo_key in modelos_info:
            talles_set = modelos_info[modelo_key]["talles"]
            talle_min = min(talles_set)
            talle_max = max(talles_set)
            rubro = rubro_por_talle(talle_min, talle_max)
        elif modelo_existente:
            rubro = modelo_existente.get("rubro", 1)
        else:
            rubro = 1  # default DAMAS

        grupo = inferir_grupo(subrubro)

        # Sinónimo
        if modelo_existente:
            sin_ref = modelo_existente.get("codigo_sinonimo", "")
            if sin_ref and len(sin_ref) >= 10:
                sinonimo = sin_ref[:10] + str(talle).zfill(2)
            else:
                cod_color = inferir_codigo_color(color)
                sku = nombre_a_sku(modelo)
                sinonimo = f"668{sku}{cod_color}{str(talle).zfill(2)}"
        else:
            cod_color = inferir_codigo_color(color)
            sku = nombre_a_sku(modelo)
            sinonimo = f"668{sku}{cod_color}{str(talle).zfill(2)}"

        desc1 = f"{sap_padded} {color} {modelo}".strip()
        desc3 = f"{sap_padded}  {modelo}".strip()
        desc4 = color
        desc5 = str(talle)
        precio_costo = round(precio_lista * 0.50, 2)

        params = (
            desc1, desc3, desc4, desc5,
            sinonimo,
            subrubro, marca, linea, rubro, grupo,
            668,  # proveedor ALPARGATAS
            precio_lista, pvp, 0, precio_costo,
            0,  # moneda pesos
        )

        if dry_run:
            print(f"  [DRY] {desc1[:55]:<55} sin={sinonimo} R:{rubro} S:{subrubro} G:{grupo}")
            insertados += 1
        else:
            try:
                cursor = conn.cursor()
                cursor.execute(sql_insert, params)
                insertados += 1
                if insertados % 20 == 0:
                    conn.commit()
                    print(f"  ... {insertados} insertados (commit parcial)")
            except Exception as e:
                print(f"  ❌ Error SAP:{sap} T:{talle}: {e}")
                errores += 1

    # Commit final
    if not dry_run and conn:
        try:
            conn.commit()
            # Verificar MAX(codigo) nuevo
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(codigo) FROM msgestion01art.dbo.articulo")
            nuevo_max = cursor.fetchone()[0]
            print(f"\n  MAX(codigo) nuevo: {nuevo_max}")
            print(f"  Rango insertado: {max_codigo + 1} — {nuevo_max}")
        except Exception as e:
            print(f"  Error en commit final: {e}")
        finally:
            conn.close()

    print(f"\n{'='*60}")
    print(f"  RESUMEN: {insertados} insertados, {errores} errores")
    print(f"{'='*60}")


if __name__ == "__main__":
    ruta = "TOPPER CALZADO COMPLETO.xlsx"
    if len(sys.argv) > 1:
        ruta = sys.argv[1]

    faltantes, modelos_info = analizar_faltantes(ruta)

    if faltantes:
        ejecutar = "--ejecutar" in sys.argv
        insertar_faltantes(faltantes, modelos_info, dry_run=not ejecutar)
