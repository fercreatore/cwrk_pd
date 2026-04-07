"""
Pedido KRUNCHI OI 2026/27 — CALZALINDO (msgestion01)
Proveedor: 103

Análisis base:
  - 166 HABANO: vel_real=2.04p/mes (vel pico ~11p/mes). Stock actual 18p → quiebra en junio sin reposición.
  - 165 COCO:   vel_real=0.86p/mes (vel pico ~4p/mes).  Stock actual 15p → cubre 3 meses.
  - CONDICIÓN CLAVE: entrega ANTES del 1ro de mayo. Si llega en julio = temporada perdida (2023: 456p en jul-ago → vendieron 67p).

Curva talles basada en 5 OI (2021-2025), años con y sin quiebre ponderados.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paso4_insertar_pedido import insertar_pedido

# ─── LÍNEAS DEL PEDIDO ─────────────────────────────────────────────────────────
# (articulo_codigo, cantidad, precio_unitario)
# Precio = precio_costo del ERP (referencia — confirmar con Krunchi al facturar)

LINEAS_166_HABANO = [
    # codigo   ctd  costo_unit    descripcion
    (294235,   1,   34000),   # 166 HABANO T35
    (294236,   1,   34000),   # 166 HABANO T36
    (294237,   3,   34000),   # 166 HABANO T37
    (294238,   2,   34000),   # 166 HABANO T38
    (241406,   3,   36720),   # 166 HABANO T39
    (241407,   3,   36720),   # 166 HABANO T40
    (241408,   2,   36720),   # 166 HABANO T41
    (241409,   5,   36720),   # 166 HABANO T42  ← pico curva
    (241410,   2,   36720),   # 166 HABANO T43
    (241411,   2,   36720),   # 166 HABANO T44
]
# Total: 24p | Monto ref: 1p T35-38=34k, T39-44=36.72k → $862,240

LINEAS_165_COCO = [
    # codigo   ctd  costo_unit    descripcion
    (37743,    1,   25160),   # 165 COCO T19
    (37744,    1,   25160),   # 165 COCO T20
    (37745,    2,   25160),   # 165 COCO T21
    (37746,    2,   25160),   # 165 COCO T22
    (37747,    4,   25160),   # 165 COCO T23  ← pico curva
    (37748,    2,   25160),   # 165 COCO T24
    (37749,    2,   25160),   # 165 COCO T25
    (37750,    2,   25160),   # 165 COCO T26
    (37751,    2,   28560),   # 165 COCO T27
    (37752,    1,   28560),   # 165 COCO T28
    (37753,    2,   28560),   # 165 COCO T29
    (37755,    1,   28560),   # 165 COCO T31
    (37757,    2,   28560),   # 165 COCO T33
]
# Total: 24p | Monto ref: T19-26=25.16k, T27-33=28.56k → $631,040

# ─── RESUMEN ───────────────────────────────────────────────────────────────────
def calcular_totales(lineas, nombre):
    pares = sum(l[1] for l in lineas)
    monto = sum(l[1] * l[2] for l in lineas)
    print(f"  {nombre}: {pares}p — ${monto:,.0f}")
    return pares, monto


def main(dry_run=True):
    print("=" * 60)
    print("PEDIDO KRUNCHI OI 2026/27 — CALZALINDO")
    print("Proveedor 103 | Entrega requerida: antes del 01/05/2026")
    print("=" * 60)

    p1, m1 = calcular_totales(LINEAS_166_HABANO, "166 HABANO (acordonada adulto)")
    p2, m2 = calcular_totales(LINEAS_165_COCO,   "165 COCO   (abrojo niño)")
    total_p = p1 + p2
    total_m = m1 + m2
    print(f"  {'─'*40}")
    print(f"  TOTAL: {total_p}p — ${total_m:,.0f}")
    print()

    # Curva zapatero visual
    print("CURVA 166 HABANO:")
    cabecera = [str(l[2]//1000) + "k" for l in LINEAS_166_HABANO]  # noqa — solo debug
    talles_h = [35,36,37,38,39,40,41,42,43,44]
    ctds_h   = [l[1] for l in LINEAS_166_HABANO]
    print("  T" + " | T".join(str(t) for t in talles_h))
    print("   " + " |  ".join(str(c) for c in ctds_h))

    print("CURVA 165 COCO:")
    talles_c = [19,20,21,22,23,24,25,26,27,28,29,31,33]
    ctds_c   = [l[1] for l in LINEAS_165_COCO]
    print("  T" + " | T".join(str(t) for t in talles_c))
    print("   " + " |  ".join(str(c) for c in ctds_c))
    print()

    if dry_run:
        print(">>> DRY RUN — no se inserta nada. Usar --ejecutar para confirmar.")
        return

    print("Insertando pedido único (ambos modelos, misma entrega)...")
    todas_las_lineas = LINEAS_166_HABANO + LINEAS_165_COCO

    lineas_fmt = [
        {"articulo": cod, "cantidad": ctd, "precio": precio}
        for cod, ctd, precio in todas_las_lineas
    ]

    resultado = insertar_pedido(
        proveedor=103,
        empresa="CALZALINDO",
        fecha_entrega="2026-04-30",
        lineas=lineas_fmt,
        observacion="KRUNCHI OI26/27 — ENT ANTES 01/05 — 166 HABANO 24p + 165 COCO 24p",
    )

    if resultado:
        print(f"✓ Pedido insertado: numero={resultado['numero']}, orden={resultado['orden']}")
        print(f"  pedico2: {resultado.get('pedico2_id')}")
        print(f"  Líneas insertadas: {len(lineas_fmt)}")
    else:
        print("✗ Error al insertar. Ver log arriba.")


if __name__ == "__main__":
    dry_run = "--ejecutar" not in sys.argv
    main(dry_run=dry_run)
