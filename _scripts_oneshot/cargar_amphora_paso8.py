#!/usr/bin/env python3
"""
cargar_amphora_paso8.py — Carga Amphora AW2026 usando paso8_carga_factura
=========================================================================
Usa procesar_factura() + crear_pedido_desde_factura() que tienen
todos los campos correctos (precios, sinónimos, utilidades, IVA, etc.)

32 items, 53 pares del Excel AMPHORA 2026.xlsx

PRE-REQUISITO: correr limpiar_amphora.py primero

EJECUTAR EN EL 111:
  cd C:\cowork_pedidos
  py -3 _scripts_oneshot\cargar_amphora_paso8.py --dry-run
  py -3 _scripts_oneshot\cargar_amphora_paso8.py --ejecutar
"""

import sys
import os

# Agregar raiz al path para importar paso8
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from paso8_carga_factura import Factura, LineaFactura, procesar_factura, crear_pedido_desde_factura

# -- DATOS DE FACTURA AMPHORA AW2026 ------------------------------------
# Amphora son carteras/mochilas/bandoleras: 1 articulo = 1 "talle" (tamaño)
# Talle para sinonimo: 01=riñonera/banano, 02=bandolera, 03=mochila, 04=cartera, 05=portanotebook

TALLE_MAP = {
    "BANANO": "01", "RINONERA": "01",
    "BANDOLERA": "02",
    "MOCHILA": "03",
    "CARTERA": "04",
    "PORTA NOTEBOOK": "05",
}

COLOR_MAP = {
    "NEGRO": "01", "BLANCO": "02", "BEIGE": "05",
    "CAMEL": "07", "TAUPE": "08", "CAFE": "10",
    "CAFE OSCURO": "13", "BLANCO ESPECIAL": "57",
}

def det_talle(desc):
    d = desc.upper()
    if "PORTA NOTEBOOK" in d: return "05"
    for k, v in TALLE_MAP.items():
        if k in d: return v
    return "04"

def det_color_code(desc):
    d = desc.upper()
    for c in ["CAFE OSCURO", "BLANCO ESPECIAL", "NEGRO", "BLANCO", "BEIGE", "CAMEL", "TAUPE", "CAFE"]:
        if c in d: return COLOR_MAP[c]
    return "01"

def det_color_name(desc):
    d = desc.upper()
    for c in ["CAFE OSCURO", "BLANCO ESPECIAL", "NEGRO", "BLANCO", "BEIGE", "CAMEL", "TAUPE", "CAFE"]:
        if c in d: return c
    return "NEGRO"

def det_modelo(desc):
    """Primera palabra = nombre del modelo."""
    return desc.split()[0].upper()

# (barcode, descripcion, cantidad, precio)
ITEMS = [
    ("04042423200001",  "AMARANTA MOCHILA NEGRO",                      2, 42000),
    ("04036421460001",  "ANGELA CARTERA DOS ASAS NEGRO",               2, 44500),
    ("04036421460008",  "ANGELA CARTERA DOS ASAS TAUPE",               1, 44500),
    ("040424027701",    "BENIN CARTERA PORTA NOTEBOOK NEGRO",          2, 54500),
    ("040423407501",    "CAMELEON BANANO NEGRO",                        2, 39500),
    ("04036421760001",  "CHARLOTE MOCHILA NEGRO",                      2, 39500),
    ("04036421760013",  "CHARLOTE MOCHILA CAFE OSCURO",                1, 39500),
    ("04036421780001",  "CHARLOTE BANDOLERA NEGRO",                    2, 37000),
    ("04036421780013",  "CHARLOTE BANDOLERA CAFE OSCURO",              1, 37000),
    ("040433905201",    "CHIARA BANDOLERA NEGRO",                      2, 39500),
    ("04043423450001",  "ELIZA CARTERA DOS ASAS NEGRO",                2, 44500),
    ("04043423450005",  "ELIZA CARTERA DOS ASAS BEIGE",                2, 44500),
    ("040424026901",    "INGLATERRA BANDOLERA NEGRO",                  2, 39500),
    ("04036421820001",  "JENIFER CARTERA DOS ASAS TRES DIV NEGRO",     2, 49500),
    ("04036421820010",  "JENIFER CARTERA DOS ASAS TRES DIV CAFE",      1, 49500),
    ("04006421040001",  "JULIA CARTERA DOS ASAS NEGRO",                2, 39500),
    ("040422745501",    "KIRKLI MOCHILA NEGRO",                        2, 44500),
    ("04043423500001",  "MACARENA MOCHILA NEGRO",                      1, 42000),
    ("04043423500013",  "MACARENA MOCHILA CAFE OSCURO",                1, 42000),
    ("04043423530001",  "MAGDALENA CARTERA DOS ASAS NEGRO",            2, 44500),
    ("04043423550001",  "MAGDALENA BANDOLERA NEGRO",                   2, 39500),
    ("04043423550057",  "MAGDALENA BANDOLERA BLANCO ESPECIAL",         1, 39500),
    ("040434035401",    "MAGGIE CARTERA DOS ASAS NEGRO",               2, 44500),
    ("040434035405",    "MAGGIE CARTERA DOS ASAS BEIGE",               1, 44500),
    ("040434035413",    "MAGGIE CARTERA DOS ASAS CAFE OSCURO",         1, 44500),
    ("04043424100001",  "MAIDA CARTERA CORTE RECTO NEGRO",             2, 44500),
    ("04043424100007",  "MAIDA CARTERA CORTE RECTO CAMEL",             1, 44500),
    ("04043424100013",  "MAIDA CARTERA CORTE RECTO CAFE OSCURO",       1, 44500),
    ("04043423900001",  "MARGARET CARTERA DOS ASAS NEGRO",             2, 44500),
    ("04043423900010",  "MARGARET CARTERA DOS ASAS CAFE",              2, 44500),
    ("04043423970001",  "MARGOT CARTERA DOS ASAS NEGRO",               2, 44500),
    ("04043423970013",  "MARGOT CARTERA DOS ASAS CAFE OSCURO",         2, 44500),
]


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    # Construir Factura con LineaFactura por cada item
    factura = Factura(
        proveedor_id=44,
        proveedor_nombre="AMPHORA",
        marca_id=44,
        numero_factura="A 00015-00009639",
        fecha=date(2026, 3, 16),
        tipo_comprobante="NP",
        observaciones="AMPHORA AW2026 — 32 arts, 53 uds",
    )

    for barcode, desc, cant, precio in ITEMS:
        modelo = det_modelo(desc)
        color = det_color_name(desc)
        talle = det_talle(desc)

        factura.lineas.append(LineaFactura(
            modelo=modelo,
            descripcion=desc,
            color=color,
            talle=talle,
            cantidad=cant,
            precio_unitario=precio,
            codigo_barra_fabricante=barcode,
            codigo_producto=modelo,
            descripcion_1=desc,
            descripcion_3=desc[:26],
        ))

    total_pares = factura.total_pares
    total_neto = factura.total

    print(f"\n{'='*70}")
    print(f"AMPHORA AW2026 — CARGA VIA PASO 8")
    print(f"{'='*70}")
    print(f"  Items:  {len(factura.lineas)}")
    print(f"  Pares:  {total_pares}")
    print(f"  Neto:   ${total_neto:,.0f}")
    print(f"  Modo:   {'DRY-RUN' if dry_run else 'PRODUCCION'}")
    print(f"{'='*70}")

    for i, l in enumerate(factura.lineas, 1):
        print(f"  {i:2d}. {l.modelo:12s} {l.color:17s} T{l.talle} x{l.cantidad} ${l.precio_unitario:,.0f}  BC:{l.codigo_barra_fabricante}")

    print(f"\n  TOTAL: {total_pares} pares — ${total_neto:,.0f}")

    if dry_run:
        print(f"\n  [DRY RUN] No se escribio nada.")
        print(f"  Para ejecutar: py -3 _scripts_oneshot\\cargar_amphora_paso8.py --ejecutar")
        return

    # PASO 1: Procesar factura (buscar/crear artículos)
    print(f"\n--- PASO 1: Procesar factura (buscar/crear articulos) ---")
    resultado = procesar_factura(factura)

    print(f"\n  Resultado:")
    print(f"    Exitosos:  {resultado['exitosos']}/{len(factura.lineas)}")
    print(f"    Creados:   {resultado['articulos_creados']}")
    print(f"    Existentes:{resultado['articulos_existentes']}")
    print(f"    Fallidos:  {resultado['fallidos']}")
    if resultado['errores']:
        for e in resultado['errores']:
            print(f"    ERROR: {e}")

    if resultado['fallidos'] > 0:
        print(f"\n  HAY ERRORES. No se crea pedido.")
        resp = input("  Crear pedido con los exitosos? (s/N): ").strip().lower()
        if resp != "s":
            print("  Cancelado.")
            sys.exit(0)

    # PASO 2: Crear nota de pedido
    print(f"\n--- PASO 2: Crear nota de pedido ---")
    pedido = crear_pedido_desde_factura(
        factura, resultado,
        tipo="NP",
        empresa="H4",
        deposito=11,
        dry_run=False,
    )

    print(f"\n{'='*70}")
    if pedido.get("numero"):
        print(f"  PEDIDO #{pedido['numero']} CREADO OK")
        print(f"  {pedido.get('renglones', '?')} renglones, {total_pares} pares")
    else:
        print(f"  ERROR creando pedido: {pedido.get('error', 'desconocido')}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
