#!/usr/bin/env python3
"""
insertar_piccadilly.py — Alta artículos + Nota de pedido PICCADILLY OI26
========================================================================
Proveedor: 713 (DISTRINANDO MODA S.A.)
Marca: 656 (PICCADILLY)
Empresa: H4 → MSGESTION03

2 Órdenes de Venta combinadas en 1 nota de pedido:
  OV 806,126 — STOCK Piccadilly abril entrega — 5 cajas M12 35/40
  OV 806,124 — PICCADILLY LÍNEA OI26         — 19 cajas M12 36/41

Condiciones: Contado 7% desc. - 30 días neto

21 modelos/colores × 6 talles c/u = hasta 126 artículos nuevos
24 cajas × 12 pares = 288 pares total

Subtotal OV 806,126: $2,638,776.00
Subtotal OV 806,124: $12,778,686.00
Total neto:          $15,417,462.00

EJECUTAR EN EL 111:
  py -3 insertar_piccadilly.py                ← dry-run
  py -3 insertar_piccadilly.py --ejecutar     ← escribe en producción
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONN_COMPRAS

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════

PROVEEDOR    = 713
DENOMINACION = "DISTRINANDO MODA S.A."
EMPRESA      = "H4"
MARCA        = 656       # PICCADILLY (en tabla marcas)
LINEA        = 2         # Invierno (OI26)

FECHA_PEDIDO  = date(2026, 3, 12)
FECHA_ENTREGA = date(2026, 4, 14)   # primera entrega según OV

# Descuento: 7% contado
DESCUENTO = 7.0

# Utilidades (de artículos Piccadilly existentes)
UTILIDAD_1 = 100    # contado
UTILIDAD_2 = 124    # lista
UTILIDAD_3 = 60     # intermedio
UTILIDAD_4 = 45     # mayorista
FORMULA    = 1

OBSERVACIONES = ("OV 806124 LINEA + OV 806126 STOCK. "
                 "PICCADILLY OI26. 24 cajas, 288 pares. "
                 "Distrinando Moda. Contado 7% desc.")

# ══════════════════════════════════════════════════════════════
# MODELOS — 21 combos modelo/color
# ══════════════════════════════════════════════════════════════
# subrubros: 15=bota, 5=zapato cerrado, 35=pancha, 51=zapa urbana, 52=zapatilla

MODELOS = [
    # ── OV 806,126 STOCK (M12 35/40, curva 1-2-3-3-2-1) ──
    {
        "modelo": "117106", "color": "NEGRO",
        "desc_corta": "117106 NEGRO BOTA T/GOND COST HEBILLA",
        "subrubro": 15, "grupo": "5",
        "precio": 49999.50,
        "talles": ["35","36","37","38","39","40"],
        "curva": [2, 4, 6, 6, 4, 2],   # 2 cajas
    },
    {
        "modelo": "117124", "color": "NEGRO MATELASSE",
        "desc_corta": "117124 NEGRO MATELASSE BOTA T/GOND CIERRE",
        "subrubro": 15, "grupo": "5",
        "precio": 44999.50,
        "talles": ["35","36","37","38","39","40"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "117124", "color": "MADEIRA MATELASSE",
        "desc_corta": "117124 MADEIRA MATELASSE BOTA T/GOND CIERRE",
        "subrubro": 15, "grupo": "5",
        "precio": 44999.50,
        "talles": ["35","36","37","38","39","40"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "143219", "color": "NEGRO",
        "desc_corta": "143219 NEGRO BOTA BAJA LINHO",
        "subrubro": 15, "grupo": "5",
        "precio": 29900.00,
        "talles": ["35","36","37","38","39","40"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    # ── OV 806,124 LÍNEA (M12 36/41, curva 1-2-3-3-2-1) ──
    {
        "modelo": "110202", "color": "NEGRO CROCO",
        "desc_corta": "110202 NEGRO CROCO LAURA SLT FORRADO",
        "subrubro": 5, "grupo": "5",
        "precio": 63599.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "110202", "color": "CONHAQUE CROCO",
        "desc_corta": "110202 CONHAQUE CROCO LAURA SLT FORRADO",
        "subrubro": 5, "grupo": "5",
        "precio": 63599.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "143247", "color": "NEGRO",
        "desc_corta": "143247 NEGRO IVONE BOTA BAJA LINHO",
        "subrubro": 15, "grupo": "5",
        "precio": 41899.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "143248", "color": "NEGRO BRULE",
        "desc_corta": "143248 NEGRO/BRULE IVONE BOTA BAJA",
        "subrubro": 15, "grupo": "5",
        "precio": 41899.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "143248", "color": "NUDE FENDI",
        "desc_corta": "143248 NUDE/FENDI IVONE BOTA BAJA",
        "subrubro": 15, "grupo": "5",
        "precio": 41899.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "653021", "color": "CACAU",
        "desc_corta": "653021 CACAU LECI CERRADO PONTILHADO",
        "subrubro": 5, "grupo": "5",
        "precio": 64799.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "653021", "color": "NEGRO",
        "desc_corta": "653021 NEGRO LECI CERRADO PONTILHADO",
        "subrubro": 5, "grupo": "5",
        "precio": 64799.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [2, 4, 6, 6, 4, 2],   # 2 cajas
    },
    {
        "modelo": "653027", "color": "CACAU TRAMA",
        "desc_corta": "653027 CACAU TRAMA LECI CERRADO",
        "subrubro": 5, "grupo": "5",
        "precio": 67899.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "653027", "color": "NEGRO TRAMA",
        "desc_corta": "653027 NEGRO TRAMA LECI CERRADO",
        "subrubro": 5, "grupo": "5",
        "precio": 67899.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [2, 4, 6, 6, 4, 2],   # 2 cajas
    },
    {
        "modelo": "940011", "color": "NEGRO ELASTICO",
        "desc_corta": "940011 NEGRO ELASTICO CANELADO PVC",
        "subrubro": 5, "grupo": "5",
        "precio": 61699.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "949017", "color": "BRULE MARFIM",
        "desc_corta": "949017 BRULE/MARFIM FASCITE PANCHA",
        "subrubro": 35, "grupo": "5",
        "precio": 44999.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "949017", "color": "NEGRO",
        "desc_corta": "949017 NEGRO FASCITE PANCHA",
        "subrubro": 35, "grupo": "5",
        "precio": 44999.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "949030", "color": "BLANCO PLATEADO",
        "desc_corta": "949030 BLANCO/PLATEADO FASCITE ZAPA URB",
        "subrubro": 51, "grupo": "5",
        "precio": 63599.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "949030", "color": "NEGRO DORADO",
        "desc_corta": "949030 NEGRO/DORADO FASCITE ZAPA URB",
        "subrubro": 51, "grupo": "5",
        "precio": 63599.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "970120", "color": "NEGRO PRETO",
        "desc_corta": "970120 NEGRO/NEGRO FABI ZAPATILLA EVA",
        "subrubro": 52, "grupo": "5",
        "precio": 44999.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "970120", "color": "NEGRO BRANCO",
        "desc_corta": "970120 NEGRO/BLANCO FABI ZAPATILLA EVA",
        "subrubro": 52, "grupo": "5",
        "precio": 44999.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
    {
        "modelo": "970120", "color": "OURO METALIZADA",
        "desc_corta": "970120 DORADO METALIZADO FABI ZAPATILLA EVA",
        "subrubro": 52, "grupo": "5",
        "precio": 44999.50,
        "talles": ["36","37","38","39","40","41"],
        "curva": [1, 2, 3, 3, 2, 1],   # 1 caja
    },
]


# ══════════════════════════════════════════════════════════════
# FASE 1: ALTA DE ARTÍCULOS
# ══════════════════════════════════════════════════════════════

def fase1_alta_articulos(dry_run=True):
    """Crea artículos Piccadilly usando paso2_buscar_articulo.dar_de_alta()."""
    from paso2_buscar_articulo import dar_de_alta

    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    total_arts = sum(len(m["talles"]) for m in MODELOS)
    print(f"\n{'='*70}")
    print(f"  FASE 1: ALTA DE {total_arts} ARTÍCULOS PICCADILLY — {modo}")
    print(f"{'='*70}")

    articulos_creados = {}
    total = 0
    errores = 0

    for i, modelo in enumerate(MODELOS, 1):
        mod_num = modelo["modelo"]
        color = modelo["color"]
        precio = modelo["precio"]
        precio_costo = round(precio * (1 - DESCUENTO/100), 4)

        print(f"\n  [{i}/{len(MODELOS)}] {mod_num} {color}")
        print(f"    Precio fábrica: ${precio:,.2f} | Desc: {DESCUENTO}% | Costo: ${precio_costo:,.2f}")
        print(f"    Talles: {modelo['talles'][0]}-{modelo['talles'][-1]} | Pares: {sum(modelo['curva'])}")

        for talle, cant in zip(modelo["talles"], modelo["curva"]):
            desc1 = modelo["desc_corta"]
            # Sinónimo: 713 + modelo(6) + color(3) + talle(2)
            color_code = color.replace(" ", "")[:3].upper()
            sinonimo = f"713{mod_num}{color_code}{talle.zfill(2)}"

            datos = {
                "descripcion_1":    desc1,
                "descripcion_3":    f"PICCADILLY {mod_num}",
                "descripcion_4":    color,
                "descripcion_5":    talle,
                "codigo_sinonimo":  sinonimo,
                "subrubro":         modelo["subrubro"],
                "marca":            MARCA,
                "linea":            LINEA,
                "rubro":            1,           # DAMAS (todo Piccadilly)
                "grupo":            modelo["grupo"],
                "proveedor":        PROVEEDOR,
                "codigo_proveedor": mod_num,
                "precio_fabrica":   precio,
                "descuento":        DESCUENTO,
                "descuento_1":      0,
                "descuento_2":      0,
                "precio_costo":     precio_costo,
                "precio_sugerido":  round(precio_costo, 2),
                "utilidad_1":       UTILIDAD_1,
                "utilidad_2":       UTILIDAD_2,
                "utilidad_3":       UTILIDAD_3,
                "utilidad_4":       UTILIDAD_4,
                "precio_1":         round(precio_costo * (1 + UTILIDAD_1 / 100), 2),
                "precio_2":         round(precio_costo * (1 + UTILIDAD_2 / 100), 2),
                "precio_3":         round(precio_costo * (1 + UTILIDAD_3 / 100), 2),
                "precio_4":         round(precio_costo * (1 + UTILIDAD_4 / 100), 2),
                "formula":          FORMULA,
            }

            codigo = dar_de_alta(datos, dry_run=dry_run)
            key = (mod_num, color, talle)
            if codigo and codigo > 0:
                articulos_creados[key] = codigo
                total += 1
            elif codigo == -1:
                articulos_creados[key] = -1
                total += 1
            else:
                errores += 1

    print(f"\n  Resumen Fase 1: {total} artículos {'simulados' if dry_run else 'creados'}, {errores} errores")
    return articulos_creados


# ══════════════════════════════════════════════════════════════
# FASE 2: INSERTAR NOTA DE PEDIDO
# ══════════════════════════════════════════════════════════════

def fase2_insertar_pedido(articulos_creados, dry_run=True):
    """Inserta UNA nota de pedido con todos los renglones (288 pares)."""
    from paso4_insertar_pedido import insertar_pedido

    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 2: NOTA DE PEDIDO PICCADILLY — {modo}")
    print(f"{'='*70}")

    # Anti-duplicado
    if not dry_run:
        import pyodbc as _pyo
        _c = _pyo.connect(CONN_COMPRAS)
        _cur = _c.cursor()
        _cur.execute(
            "SELECT numero FROM MSGESTION03.dbo.pedico2 "
            "WHERE codigo=8 AND cuenta=713 AND observaciones LIKE '%OV 806124%'"
        )
        _dup = _cur.fetchone()
        _c.close()
        if _dup:
            print(f"  ⚠️  YA EXISTE pedido para OV 806124 → #{_dup[0]}")
            print(f"  → SALTANDO para evitar duplicado")
            return _dup[0]

    cabecera = {
        "empresa":           EMPRESA,
        "cuenta":            PROVEEDOR,
        "denominacion":      DENOMINACION,
        "fecha_comprobante": FECHA_PEDIDO,
        "fecha_entrega":     FECHA_ENTREGA,
        "observaciones":     OBSERVACIONES,
    }

    renglones = []
    for modelo in MODELOS:
        mod_num = modelo["modelo"]
        color = modelo["color"]
        for talle, cant in zip(modelo["talles"], modelo["curva"]):
            key = (mod_num, color, talle)
            codigo = articulos_creados.get(key)
            if not codigo:
                print(f"  ⚠️  Sin código para {mod_num} {color} T{talle} — saltando")
                continue

            renglones.append({
                "articulo":        codigo if codigo > 0 else 0,
                "descripcion":     modelo["desc_corta"][:60],
                "codigo_sinonimo": "",
                "cantidad":        cant,
                "precio":          modelo["precio"],
            })

    total_pares = sum(r["cantidad"] for r in renglones)
    total_bruto = sum(r["cantidad"] * r["precio"] for r in renglones)
    neto = total_bruto * (1 - DESCUENTO/100)

    print(f"  Renglones:    {len(renglones)}")
    print(f"  Total pares:  {total_pares}")
    print(f"  Total bruto:  ${total_bruto:,.0f}")
    print(f"  Desc 7%:      -${total_bruto * DESCUENTO/100:,.0f}")
    print(f"  Neto:         ${neto:,.0f}")

    if renglones:
        num = insertar_pedido(cabecera, renglones, dry_run=dry_run)
        print(f"  → Pedido PICCADILLY: número {num}")
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

    total_cajas = 0
    total_pares = 0
    total_bruto = 0
    for m in MODELOS:
        pares = sum(m["curva"])
        cajas = pares // 12
        total_cajas += cajas
        total_pares += pares
        total_bruto += pares * m["precio"]

    print(f"\n  PICCADILLY OI26 — DISTRINANDO MODA (prov 713)")
    print(f"  Modelos/colores: {len(MODELOS)}")
    print(f"  Cajas: {total_cajas} | Pares: {total_pares}")
    print(f"  Bruto: ${total_bruto:,.0f} | Desc: {DESCUENTO}% | Neto: ${total_bruto*(1-DESCUENTO/100):,.0f}")

    # Fase 1: Alta de artículos
    arts = fase1_alta_articulos(dry_run=dry_run)

    # Fase 2: Nota de pedido (UNA SOLA)
    if arts:
        fase2_insertar_pedido(arts, dry_run=dry_run)
    else:
        print("\n  ❌ No se crearon artículos — no se puede crear pedido")

    print(f"\n{'='*70}")
    print(f"  {'DRY-RUN completado' if dry_run else 'EJECUCIÓN completada'}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
