#!/usr/bin/env python3
"""
insertar_atomik_runflex.py — Alta artículos + Nota de pedido ATOMIK RUNFLEX
============================================================================
Proveedor: 594 (VICBOR SRL / Atomik)
Empresa: H4 → MSGESTION03

2 Facturas:
  Fact A 00043-00188989 (09/03/2026) — Remito 00038-00354912 — 96 pares
  Fact A 00043-00189020 (10/03/2026) — Remito 00038-00354974 — 24 pares

Precio unitario: $54,000 | Desc línea: 50.05% | Bonif factura: 6%
Desc combinado: 53.05% → precio_costo = $25,353.00

4 colores × talles = 23 artículos, 120 pares total:
  MUJ CREMA  T35-40 (1-2-3-3-2-1×2) = 24 pares
  HOM TOPO   T41-45 (2-3-3-2-2×2)   = 24 pares
  MUJ MENTA  T35-40 (1-2-3-3-2-1×2) = 24 pares
  MUJ NEGRO  T35-40 (1-2-3-3-2-1×4) = 48 pares

EJECUTAR EN EL 111:
  py -3 insertar_atomik_runflex.py                ← dry-run
  py -3 insertar_atomik_runflex.py --ejecutar     ← escribe en producción
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONN_COMPRAS

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════

PROVEEDOR    = 594
DENOMINACION = "VICBOR SRL"
EMPRESA      = "H4"
MARCA        = 594       # ATOMIK (en tabla marcas)
SUBRUBRO     = 47        # Running
GRUPO        = "15"      # MACRAME
LINEA        = 2         # Invierno

FECHA_FACTURA  = date(2026, 3, 9)    # primera factura
FECHA_ENTREGA  = date(2026, 3, 10)   # última entrega

# Precios
PRECIO_FABRICA = 54000.00
DESC_LINEA     = 50.05     # descuento por línea en factura
DESC_BONIF     = 6.00      # bonificación 6% sobre subtotal
# Combinado: 1 - (1-0.5005)*(1-0.06) = 53.047%
DESC_COMBINADO = round((1 - (1 - DESC_LINEA/100) * (1 - DESC_BONIF/100)) * 100, 2)
PRECIO_COSTO   = round(PRECIO_FABRICA * (1 - DESC_COMBINADO/100), 4)

# Utilidades (de artículos running existentes prov 594: ENERLITE)
UTILIDAD_1 = 120    # contado
UTILIDAD_2 = 144    # lista
UTILIDAD_3 = 60     # intermedio
UTILIDAD_4 = 45     # mayorista
FORMULA    = 1

OBSERVACIONES = ("Fact A 00043-00188989 (09/03) + 00043-00189020 (10/03). "
                 "VICBOR SRL (Atomik). RUNFLEX 4 colores, 120 pares. "
                 "Desc 50.05% + bonif 6%.")

# ══════════════════════════════════════════════════════════════
# MODELOS
# ══════════════════════════════════════════════════════════════

MODELOS = [
    {
        "nombre": "RUNFLEX",
        "color":  "CREMA",
        "tipo":   "MUJ",
        "rubro":  1,           # DAMAS
        "talles": ["35", "36", "37", "38", "39", "40"],
        "curva":  [2, 4, 6, 6, 4, 2],     # 1-2-3-3-2-1 × 2 packs
    },
    {
        "nombre": "RUNFLEX",
        "color":  "TOPO",
        "tipo":   "HOM",
        "rubro":  3,           # HOMBRES
        "talles": ["41", "42", "43", "44", "45"],
        "curva":  [4, 6, 6, 4, 4],         # 2-3-3-2-2 × 2 packs
    },
    {
        "nombre": "RUNFLEX",
        "color":  "MENTA",
        "tipo":   "MUJ",
        "rubro":  1,           # DAMAS
        "talles": ["35", "36", "37", "38", "39", "40"],
        "curva":  [2, 4, 6, 6, 4, 2],     # 1-2-3-3-2-1 × 2 packs
    },
    {
        "nombre": "RUNFLEX",
        "color":  "NEGRO",
        "tipo":   "MUJ",
        "rubro":  1,           # DAMAS
        "talles": ["35", "36", "37", "38", "39", "40"],
        "curva":  [4, 8, 12, 12, 8, 4],   # 1-2-3-3-2-1 × 4 packs
    },
]


def construir_descripcion_1(color, tipo):
    """Formato estilo existentes: RUNFLEX COLOR ZAPA DEP ACORD ATOMIK"""
    return f"RUNFLEX {color} ZAPA DEP ACORD {tipo} ATOMIK"


# ══════════════════════════════════════════════════════════════
# FASE 1: ALTA DE ARTÍCULOS
# ══════════════════════════════════════════════════════════════

def fase1_alta_articulos(dry_run=True):
    """Crea los 23 artículos RUNFLEX usando paso2_buscar_articulo.dar_de_alta()."""
    from paso2_buscar_articulo import dar_de_alta

    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 1: ALTA DE 23 ARTÍCULOS ATOMIK RUNFLEX — {modo}")
    print(f"{'='*70}")
    print(f"  Precio fábrica:   ${PRECIO_FABRICA:,.2f}")
    print(f"  Desc combinado:   {DESC_COMBINADO}% (línea {DESC_LINEA}% + bonif {DESC_BONIF}%)")
    print(f"  Precio costo:     ${PRECIO_COSTO:,.2f}")

    articulos_creados = {}
    total = 0
    errores = 0

    for modelo in MODELOS:
        color = modelo["color"]
        tipo = modelo["tipo"]
        rubro = modelo["rubro"]

        print(f"\n  {modelo['nombre']} {tipo} {color} — rubro={rubro} — talles {modelo['talles'][0]}-{modelo['talles'][-1]}")
        print(f"    Precio 1 (ctdo): ${round(PRECIO_COSTO * (1 + UTILIDAD_1/100), 2):,.2f}")

        for talle, cant in zip(modelo["talles"], modelo["curva"]):
            desc1 = construir_descripcion_1(color, tipo)
            desc3 = f"RUNFLEX {tipo} ZAPA DEP ACORD ATOMIK"
            desc4 = color
            sinonimo = f"594RF{color[:3]}{talle.zfill(3)}"

            datos = {
                "descripcion_1":    desc1,
                "descripcion_3":    desc3,
                "descripcion_4":    desc4,
                "descripcion_5":    talle,
                "codigo_sinonimo":  sinonimo,
                "subrubro":         SUBRUBRO,
                "marca":            MARCA,
                "linea":            LINEA,
                "rubro":            rubro,
                "grupo":            GRUPO,
                "proveedor":        PROVEEDOR,
                "codigo_proveedor": "RUNFLEX",
                "precio_fabrica":   PRECIO_FABRICA,
                "descuento":        DESC_COMBINADO,
                "descuento_1":      0,
                "descuento_2":      0,
                "precio_costo":     PRECIO_COSTO,
                "precio_sugerido":  round(PRECIO_COSTO, 2),
                "utilidad_1":       UTILIDAD_1,
                "utilidad_2":       UTILIDAD_2,
                "utilidad_3":       UTILIDAD_3,
                "utilidad_4":       UTILIDAD_4,
                "precio_1":         round(PRECIO_COSTO * (1 + UTILIDAD_1 / 100), 2),
                "precio_2":         round(PRECIO_COSTO * (1 + UTILIDAD_2 / 100), 2),
                "precio_3":         round(PRECIO_COSTO * (1 + UTILIDAD_3 / 100), 2),
                "precio_4":         round(PRECIO_COSTO * (1 + UTILIDAD_4 / 100), 2),
                "formula":          FORMULA,
            }

            codigo = dar_de_alta(datos, dry_run=dry_run)
            if codigo and codigo > 0:
                articulos_creados[(color, talle)] = codigo
                total += 1
            elif codigo == -1:
                articulos_creados[(color, talle)] = -1
                total += 1
            else:
                errores += 1

    print(f"\n  Resumen Fase 1: {total} artículos {'simulados' if dry_run else 'creados'}, {errores} errores")
    return articulos_creados


# ══════════════════════════════════════════════════════════════
# FASE 2: INSERTAR NOTA DE PEDIDO
# ══════════════════════════════════════════════════════════════

def fase2_insertar_pedido(articulos_creados, dry_run=True):
    """Inserta la nota de pedido con los 23 renglones (120 pares)."""
    from paso4_insertar_pedido import insertar_pedido

    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 2: NOTA DE PEDIDO ATOMIK RUNFLEX — {modo}")
    print(f"{'='*70}")

    # Anti-duplicado
    if not dry_run:
        import pyodbc as _pyo
        _c = _pyo.connect(CONN_COMPRAS)
        _cur = _c.cursor()
        _cur.execute(
            "SELECT numero FROM MSGESTION03.dbo.pedico2 "
            "WHERE codigo=8 AND cuenta=594 AND observaciones LIKE '%00043-00188989%'"
        )
        _dup = _cur.fetchone()
        _c.close()
        if _dup:
            print(f"  ⚠️  YA EXISTE pedido para Fact 00043-00188989 → #{_dup[0]}")
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
        color = modelo["color"]
        for talle, cant in zip(modelo["talles"], modelo["curva"]):
            codigo = articulos_creados.get((color, talle))
            if not codigo:
                print(f"  ⚠️  Sin código para {color} T{talle} — saltando")
                continue

            desc = construir_descripcion_1(color, modelo["tipo"])

            renglones.append({
                "articulo":        codigo if codigo > 0 else 0,
                "descripcion":     desc[:60],
                "codigo_sinonimo": "",
                "cantidad":        cant,
                "precio":          PRECIO_FABRICA,
            })

    total_pares = sum(r["cantidad"] for r in renglones)
    total_bruto = sum(r["cantidad"] * r["precio"] for r in renglones)

    print(f"  Renglones: {len(renglones)}")
    print(f"  Total pares: {total_pares}")
    print(f"  Total bruto: ${total_bruto:,.0f}")
    print(f"  Desc línea 50.05%: -${total_bruto * DESC_LINEA/100:,.0f}")
    print(f"  Subtotal: ${total_bruto * (1-DESC_LINEA/100):,.0f}")
    print(f"  Bonif 6%: -${total_bruto * (1-DESC_LINEA/100) * DESC_BONIF/100:,.0f}")
    neto = total_bruto * (1 - DESC_LINEA/100) * (1 - DESC_BONIF/100)
    print(f"  Neto: ${neto:,.0f}")

    if renglones:
        num = insertar_pedido(cabecera, renglones, dry_run=dry_run)
        print(f"  → Pedido RUNFLEX: número {num}")
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

    print(f"\n  Desc combinado calculado: {DESC_COMBINADO}%")
    print(f"  Precio costo: ${PRECIO_COSTO:,.2f}")

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
