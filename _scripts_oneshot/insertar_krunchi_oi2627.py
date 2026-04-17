"""
Pedido KRUNCHI OI 2026/27 — CALZALINDO (msgestion01)
Proveedor: 103

Solo 166 HABANO (24p):
- Stock actual 18p cubre hasta junio, quiebra en pleno pico.
- COCO (56p) zafa solo. 165 COCO (15p) se descartó — volumen menor, riesgo acotado.
- CONDICIÓN NO NEGOCIABLE: entrega antes del 1ro de mayo.
  Si llega en julio = temporada perdida (ya pasó en 2023 con 57p que llegaron tarde).

Curva talles: promedio 5 OI (2021-2025), pico en T42.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paso4_insertar_pedido import insertar_pedido

# ─── DETALLE 166 HABANO ────────────────────────────────────────────────────────
# (articulo_codigo, cantidad, precio_costo_referencia)
# Precios del ERP — confirmar con Krunchi al facturar
LINEAS = [
    (294235, 1, 34000),   # 166 HABANO T35
    (294236, 1, 34000),   # 166 HABANO T36
    (294237, 3, 34000),   # 166 HABANO T37
    (294238, 2, 34000),   # 166 HABANO T38
    (241406, 3, 36720),   # 166 HABANO T39
    (241407, 3, 36720),   # 166 HABANO T40
    (241408, 2, 36720),   # 166 HABANO T41
    (241409, 5, 36720),   # 166 HABANO T42  ← pico
    (241410, 2, 36720),   # 166 HABANO T43
    (241411, 2, 36720),   # 166 HABANO T44
]
# Total: 24p | Monto ref: ~$862,240


def main(dry_run=True):
    pares = sum(l[1] for l in LINEAS)
    monto = sum(l[1] * l[2] for l in LINEAS)

    print("=" * 60)
    print("PEDIDO KRUNCHI OI 2026/27 — CALZALINDO")
    print("Proveedor 103 | Entrega requerida: antes del 01/05/2026")
    print("=" * 60)
    print(f"  166 HABANO: {pares}p — ${monto:,.0f} (referencia costo ERP)")
    print()

    print("Curva talles:")
    talles = [35, 36, 37, 38, 39, 40, 41, 42, 43, 44]
    ctds   = [l[1] for l in LINEAS]
    print("  " + "  ".join(f"T{t}" for t in talles))
    print("  " + "   ".join(str(c) for c in ctds))
    print()

    if dry_run:
        print(">>> DRY RUN — no se inserta nada. Usar --ejecutar para confirmar.")
        return

    print("Insertando pedido...")
    lineas_fmt = [
        {"articulo": cod, "cantidad": ctd, "precio": precio}
        for cod, ctd, precio in LINEAS
    ]

    resultado = insertar_pedido(
        proveedor=103,
        empresa="CALZALINDO",
        fecha_entrega="2026-04-30",
        lineas=lineas_fmt,
        observacion="KRUNCHI OI26/27 — 166 HABANO 24p — ENT ANTES 01/05",
    )

    if resultado:
        print(f"Pedido insertado: numero={resultado['numero']}, orden={resultado['orden']}")
    else:
        print("Error al insertar. Ver log arriba.")


if __name__ == "__main__":
    dry_run = "--ejecutar" not in sys.argv
    main(dry_run=dry_run)
