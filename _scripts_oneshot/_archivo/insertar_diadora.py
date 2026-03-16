#!/usr/bin/env python3
"""
insertar_diadora.py — Alta de artículos + Nota de pedido DIADORA (Calzados Blanco S.A.)
========================================================================================
Factura A 0023-00062015 del 05/03/2026
Remito: 0024-00066200
Proveedor: 614 (CALZADOS BLANCO S.A.)
Empresa: H4 → MSGESTION03
Desc comercial sistema: 5% (bonificación de factura)

4 modelos × 5 talles = 20 artículos, 48 pares total:
  CONSTANZA 2116 — NEGRO/NEGRO/PINK — T37-41 (2-3-3-2-2) — $36,841.57
  PROTON    2669 — NEGRO/AZUL/CORAL — T36-40 (2-3-3-2-2) — $36,841.57
  CHRONOS   2684 — NEGRO/CORAL      — T36-40 (2-3-3-2-2) — $39,999.47
  RIVER     2690 — NEGRO/PINK       — T36-40 (2-3-3-2-2) — $31,578.42

EJECUTAR EN EL 111:
  py -3 insertar_diadora.py                ← dry-run (muestra sin escribir)
  py -3 insertar_diadora.py --ejecutar     ← escribe en producción
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONN_COMPRAS, PROVEEDORES

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════

PROVEEDOR    = 614
DENOMINACION = "CALZADOS BLANCO S.A."
EMPRESA      = "H4"
MARCA        = 675       # DIADORA (en tabla marcas)
SUBRUBRO     = 47       # Running
RUBRO        = 1        # DAMAS (zapatillas mujer — talles 36-41, colores rosa/coral)
LINEA        = 2        # Invierno
GRUPO        = "15"     # MACRAME (running = macrame)

FECHA_FACTURA  = date(2026, 3, 5)
FECHA_ENTREGA  = date(2026, 3, 5)   # ya recibido (viene con factura/remito)

# Factura A 0023-00062015
OBSERVACIONES = ("Factura A 0023-00062015 Calzados Blanco (Diadora). "
                 "Remito 0024-00066200. 4 modelos, 48 pares. Bonif 5%.")

# ══════════════════════════════════════════════════════════════
# ARTÍCULOS A CREAR
# ══════════════════════════════════════════════════════════════

MODELOS = [
    {
        "ref":    "2116",
        "nombre": "CONSTANZA",
        "color":  "NEGRO/NEGRO/PINK",
        "precio": 36841.57,
        "talles": ["37", "38", "39", "40", "41"],
        "curva":  [2, 3, 3, 2, 2],
    },
    {
        "ref":    "2669",
        "nombre": "PROTON",
        "color":  "NEGRO/AZUL/CORAL",
        "precio": 36841.57,
        "talles": ["36", "37", "38", "39", "40"],
        "curva":  [2, 3, 3, 2, 2],
    },
    {
        "ref":    "2684",
        "nombre": "CHRONOS",
        "color":  "NEGRO/CORAL",
        "precio": 39999.47,
        "talles": ["36", "37", "38", "39", "40"],
        "curva":  [2, 3, 3, 2, 2],
    },
    {
        "ref":    "2690",
        "nombre": "RIVER",
        "color":  "NEGRO/PINK",
        "precio": 31578.42,
        "talles": ["36", "37", "38", "39", "40"],
        "curva":  [2, 3, 3, 2, 2],
    },
]


def construir_descripcion_1(ref, color, nombre):
    """Formato: REF COLOR NOMBRE ZAPA DEP (como arts existentes prov 614)"""
    return f"{ref} {color} {nombre} ZAPA DEP DIADORA"


# ══════════════════════════════════════════════════════════════
# FASE 1: ALTA DE ARTÍCULOS
# ══════════════════════════════════════════════════════════════

def fase1_alta_articulos(dry_run=True):
    """Crea los 20 artículos Diadora usando paso2_buscar_articulo.dar_de_alta()."""
    from paso2_buscar_articulo import dar_de_alta

    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 1: ALTA DE 20 ARTÍCULOS DIADORA — {modo}")
    print(f"{'='*70}")

    articulos_creados = {}  # {(ref, talle): codigo}
    total = 0
    errores = 0

    # Utilidades del proveedor 614 (de config.py).
    # Descuento 5% = bonificación que viene en la factura.
    # precio_fabrica = precio unitario de factura (sin bonif)
    # precio_costo = precio_fabrica × 0.95
    prov = PROVEEDORES[PROVEEDOR]
    DESCUENTO = 5   # ← 5% bonificación de factura

    for modelo in MODELOS:
        ref = modelo["ref"]
        precio_fab = modelo["precio"]
        precio_costo = round(precio_fab * (1 - DESCUENTO / 100), 4)

        print(f"\n  Modelo: {modelo['nombre']} {ref} — {modelo['color']}")
        print(f"    Precio fábrica: ${precio_fab:,.2f}")
        print(f"    Descuento:      {DESCUENTO}%")
        print(f"    Precio costo:   ${precio_costo:,.2f}")
        print(f"    Precio 1 (ctdo):${round(precio_costo * (1 + prov['utilidad_1']/100), 2):,.2f}")

        for talle, cant in zip(modelo["talles"], modelo["curva"]):
            desc1 = construir_descripcion_1(ref, modelo["color"], modelo["nombre"])
            desc3 = f"{ref} {modelo['nombre']} ZAPA DEP DIADORA"
            desc4 = modelo["color"]
            sinonimo = f"614{ref}{talle.zfill(3)}"

            datos = {
                "descripcion_1":    desc1,
                "descripcion_3":    desc3,
                "descripcion_4":    desc4,
                "descripcion_5":    talle,
                "codigo_sinonimo":  sinonimo,
                "subrubro":         SUBRUBRO,
                "marca":            MARCA,
                "linea":            LINEA,
                "rubro":            RUBRO,
                "grupo":            GRUPO,
                "proveedor":        PROVEEDOR,
                "codigo_proveedor": ref,
                "precio_fabrica":   precio_fab,
                "descuento":        DESCUENTO,
                "descuento_1":      0,
                "descuento_2":      0,
                "precio_costo":     precio_costo,
                "precio_sugerido":  round(precio_costo, 2),
                "utilidad_1":       prov["utilidad_1"],
                "utilidad_2":       prov["utilidad_2"],
                "utilidad_3":       prov["utilidad_3"],
                "utilidad_4":       prov["utilidad_4"],
                "precio_1":         round(precio_costo * (1 + prov["utilidad_1"] / 100), 2),
                "precio_2":         round(precio_costo * (1 + prov["utilidad_2"] / 100), 2),
                "precio_3":         round(precio_costo * (1 + prov["utilidad_3"] / 100), 2),
                "precio_4":         round(precio_costo * (1 + prov["utilidad_4"] / 100), 2),
                "formula":          prov["formula"],
            }

            codigo = dar_de_alta(datos, dry_run=dry_run)
            if codigo and codigo > 0:
                articulos_creados[(ref, talle)] = codigo
                total += 1
            elif codigo == -1:  # dry_run
                articulos_creados[(ref, talle)] = -1
                total += 1
            else:
                errores += 1

    print(f"\n  Resumen Fase 1: {total} artículos {'simulados' if dry_run else 'creados'}, {errores} errores")
    return articulos_creados


# ══════════════════════════════════════════════════════════════
# FASE 2: INSERTAR NOTA DE PEDIDO
# ══════════════════════════════════════════════════════════════

def fase2_insertar_pedido(articulos_creados, dry_run=True):
    """Inserta la nota de pedido con los 20 renglones (48 pares)."""
    from paso4_insertar_pedido import insertar_pedido

    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 2: NOTA DE PEDIDO DIADORA — {modo}")
    print(f"{'='*70}")

    # Anti-duplicado
    if not dry_run:
        import pyodbc as _pyo
        _c = _pyo.connect(CONN_COMPRAS)
        _cur = _c.cursor()
        _cur.execute(
            "SELECT numero FROM MSGESTION03.dbo.pedico2 "
            "WHERE codigo=8 AND cuenta=614 AND observaciones LIKE '%0023-00062015%'"
        )
        _dup = _cur.fetchone()
        _c.close()
        if _dup:
            print(f"  ⚠️  YA EXISTE pedido para Factura 0023-00062015 → #{_dup[0]}")
            print(f"  → SALTANDO para evitar duplicado")
            return _dup[0]

    cabecera = {
        "empresa":           EMPRESA,
        "cuenta":            PROVEEDOR,
        "denominacion":      DENOMINACION,
        "fecha_comprobante": FECHA_FACTURA,
        "fecha_entrega":     FECHA_ENTREGA,
        "observaciones":     OBSERVACIONES,
    }

    renglones = []
    for modelo in MODELOS:
        ref = modelo["ref"]
        for talle, cant in zip(modelo["talles"], modelo["curva"]):
            codigo = articulos_creados.get((ref, talle))
            if not codigo:
                print(f"  ⚠️  Sin código para {ref} T{talle} — saltando")
                continue

            desc = construir_descripcion_1(ref, modelo["color"], modelo["nombre"])

            renglones.append({
                "articulo":        codigo if codigo > 0 else 0,
                "descripcion":     desc[:60],
                "codigo_sinonimo": "",
                "cantidad":        cant,
                "precio":          modelo["precio"],
            })

    total_pares = sum(r["cantidad"] for r in renglones)
    total_bruto = sum(r["cantidad"] * r["precio"] for r in renglones)

    print(f"  Renglones: {len(renglones)}")
    print(f"  Total pares: {total_pares}")
    print(f"  Total bruto: ${total_bruto:,.0f}")
    print(f"  Bonif 5%: -${total_bruto * 0.05:,.0f}")
    print(f"  Subtotal neto: ${total_bruto * 0.95:,.0f}")

    if renglones:
        num = insertar_pedido(cabecera, renglones, dry_run=dry_run)
        print(f"  → Pedido Diadora: número {num}")
        return num
    else:
        print(f"  ⚠️  No hay renglones para insertar")
        return None


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    dry_run = "--ejecutar" not in sys.argv

    if dry_run:
        print("=" * 70)
        print("  MODO DRY-RUN — No se escribe nada en la BD")
        print("  Agregar --ejecutar para escribir de verdad")
        print("=" * 70)
    else:
        print("=" * 70)
        print("  ⚠️  MODO EJECUCIÓN REAL — SE VA A ESCRIBIR EN LA BD")
        print("=" * 70)

    # Fase 1: Alta de artículos
    arts = fase1_alta_articulos(dry_run=dry_run)

    # Fase 2: Nota de pedido
    if arts:
        fase2_insertar_pedido(arts, dry_run=dry_run)
    else:
        print("\n  ❌ No se crearon artículos — no se puede crear pedido")

    print(f"\n{'='*70}")
    print(f"  {'DRY-RUN completado' if dry_run else 'EJECUCIÓN completada'}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
