# insertar_carmel_ringo.py
# Inserta pedido CARMEL CANELA (Souter/RINGO) — Reposición invierno 2026
# 30 pares, talles 41-44, split proporcional entre CARMEL 03 y CARMEL 04
#
# ANÁLISIS DE QUIEBRE:
#   T42 quebrado 87% del tiempo (34/39 meses)
#   T43 quebrado 87% del tiempo (34/39 meses)
#   T44 quebrado 79% del tiempo (31/39 meses)
#   Velocidad REAL (cuando hay stock): T42=10.8/mes, T43=9.0/mes, T44=4.4/mes
#   Factor invierno: 22% (derivado de 2023 cuando había stock)
#
# EJECUTAR EN EL 111:
#   py -3 insertar_carmel_ringo.py --dry-run     ← solo muestra, no escribe
#   py -3 insertar_carmel_ringo.py --ejecutar    ← escribe en producción

import sys
from datetime import date
from paso4_insertar_pedido import insertar_pedido

# ── CABECERA ─────────────────────────────────────────────
cabecera = {
    "empresa":           "H4",                # RINGO compras recientes = H4
    "cuenta":            561,
    "denominacion":      "Souter S.A.",
    "fecha_comprobante": date(2026, 3, 7),
    "fecha_entrega":     date(2026, 4, 15),   # ~5 semanas entrega
    "observaciones":     "Reposición CARMEL CANELA invierno 2026. 30 pares. "
                         "Análisis ajustado por quiebre de stock (T42/T43 quebrado 87%). "
                         "Vel. real alta temporada: T42=10.8, T43=9.0, T44=4.4/mes. "
                         "Factor invierno 22%.",
}

# ── RENGLONES ────────────────────────────────────────────
# Split proporcional 03/04 basado en ventas últimos 6 meses:
#   T41: 03=50%, 04=50%  → 1+1 = 2
#   T42: 03=67%, 04=33%  → 9+4 = 13
#   T43: 03=70%, 04=30%  → 8+3 = 11
#   T44: 03=25%, 04=75%  → 1+3 = 4
# Total: 03=19 pares, 04=11 pares = 30 pares

renglones = [
    # ── CARMEL 03 CANELA — DET TALON (19 pares) ──
    {"articulo": 249885, "descripcion": "CARMEL 03 CANELA NAUTICO 2 ELAST DET TALON", "codigo_sinonimo": "561CAR032241", "cantidad":  1, "precio": 34700},  # T41
    {"articulo": 249886, "descripcion": "CARMEL 03 CANELA NAUTICO 2 ELAST DET TALON", "codigo_sinonimo": "561CAR032242", "cantidad":  9, "precio": 34700},  # T42
    {"articulo": 249887, "descripcion": "CARMEL 03 CANELA NAUTICO 2 ELAST DET TALON", "codigo_sinonimo": "561CAR032243", "cantidad":  8, "precio": 34700},  # T43
    {"articulo": 249888, "descripcion": "CARMEL 03 CANELA NAUTICO 2 ELAST DET TALON", "codigo_sinonimo": "561CAR032244", "cantidad":  1, "precio": 34700},  # T44
    # ── CARMEL 04 CANELA — DET CUELLO (11 pares) ──
    {"articulo": 249907, "descripcion": "CARMEL 04 CANELA NAUTICO 2 ELAST DET CUELLO", "codigo_sinonimo": "561CAR042241", "cantidad":  1, "precio": 42800},  # T41
    {"articulo": 249908, "descripcion": "CARMEL 04 CANELA NAUTICO 2 ELAST DET CUELLO", "codigo_sinonimo": "561CAR042242", "cantidad":  4, "precio": 42800},  # T42
    {"articulo": 249909, "descripcion": "CARMEL 04 CANELA NAUTICO 2 ELAST DET CUELLO", "codigo_sinonimo": "561CAR042243", "cantidad":  3, "precio": 42800},  # T43
    {"articulo": 249910, "descripcion": "CARMEL 04 CANELA NAUTICO 2 ELAST DET CUELLO", "codigo_sinonimo": "561CAR042244", "cantidad":  3, "precio": 42800},  # T44
]

# ── MAIN ─────────────────────────────────────────────────
if __name__ == "__main__":
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]

    dry_run = modo != "--ejecutar"

    total_pares = sum(r["cantidad"] for r in renglones)
    total_03 = sum(r["cantidad"] for r in renglones[:4])
    total_04 = sum(r["cantidad"] for r in renglones[4:])
    total_monto = sum(r["cantidad"] * r["precio"] for r in renglones)

    print(f"\n{'='*60}")
    print(f"PEDIDO CARMEL CANELA (RINGO) — {total_pares} pares — ${total_monto:,.0f}")
    print(f"{'='*60}")
    print(f"  CARMEL 03 (DET TALON):  {total_03} pares  @ $34,700")
    print(f"  CARMEL 04 (DET CUELLO): {total_04} pares  @ $42,800")
    print(f"  Proveedor: Souter S.A. (561)")
    print(f"  Base destino: MSGESTION03 (H4)")
    print(f"  Observaciones: Reposición invierno, ajustado por quiebre")
    print(f"{'='*60}")

    if not dry_run:
        confirmacion = input("\n¿Confirmar INSERT en producción? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("Cancelado.")
            sys.exit(0)

    numero = insertar_pedido(cabecera, renglones, dry_run=dry_run)

    if numero and not dry_run:
        print(f"\nVerificar en SSMS:")
        print(f"  SELECT * FROM MSGESTION03.dbo.pedico2 WHERE numero = {numero}")
        print(f"  SELECT * FROM MSGESTION03.dbo.pedico1 WHERE numero = {numero}")
