# insertar_knu_gtn.py
# Inserta el pedido KNU GTN confirmado (3 colores, 124 pares)
# EJECUTAR EN EL 111:
#   python insertar_knu_gtn.py --dry-run     ← solo muestra, no escribe
#   python insertar_knu_gtn.py --ejecutar    ← escribe en producción
#
# Usa paso4_insertar_pedido.py y config.py del mismo directorio

import sys
from datetime import date
from paso4_insertar_pedido import insertar_pedido

# ── CABECERA ─────────────────────────────────────────────
cabecera = {
    "empresa":           "CALZALINDO",      # GTN = 100% base 01
    "cuenta":            104,
    "denominacion":      '"EL GITANO" - GTN',
    "fecha_comprobante": date(2026, 3, 6),
    "fecha_entrega":     date(2026, 3, 20),
    "observaciones":     "Pedido KNU Invierno 2026 - Mar/Abr (2 meses). 124 pares.",
}

# ── RENGLONES ────────────────────────────────────────────
# KNU NEGRO/BLANCO — 68 pares
# KNU NEGRO/NGO/BLANCO — 34 pares
# KNU GRIS/BLANCO — 22 pares

renglones = [
    # ── KNU NEGRO/BLANCO (talles 34-44) ──
    {"articulo": 308884, "descripcion": "KNU NEGRO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK0034", "cantidad":  2, "precio": 22000},
    {"articulo": 308874, "descripcion": "KNU NEGRO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK0035", "cantidad":  4, "precio": 22000},
    {"articulo": 308875, "descripcion": "KNU NEGRO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK0036", "cantidad":  6, "precio": 22000},
    {"articulo": 308876, "descripcion": "KNU NEGRO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK0037", "cantidad":  4, "precio": 22000},
    {"articulo": 308877, "descripcion": "KNU NEGRO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK0038", "cantidad": 16, "precio": 22000},
    {"articulo": 308878, "descripcion": "KNU NEGRO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK0039", "cantidad": 12, "precio": 22000},
    {"articulo": 308879, "descripcion": "KNU NEGRO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK0040", "cantidad":  8, "precio": 22000},
    {"articulo": 308880, "descripcion": "KNU NEGRO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK0041", "cantidad":  8, "precio": 22000},
    {"articulo": 308881, "descripcion": "KNU NEGRO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK0042", "cantidad":  4, "precio": 22000},
    {"articulo": 308882, "descripcion": "KNU NEGRO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK0043", "cantidad":  2, "precio": 22000},
    {"articulo": 308883, "descripcion": "KNU NEGRO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK0044", "cantidad":  2, "precio": 22000},
    # ── KNU NEGRO/NGO/BLANCO (talles 35-43) ──
    {"articulo": 316676, "descripcion": "KNU NEGRO/NGO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1035", "cantidad":  2, "precio": 22000},
    {"articulo": 316677, "descripcion": "KNU NEGRO/NGO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1036", "cantidad":  4, "precio": 22000},
    {"articulo": 316678, "descripcion": "KNU NEGRO/NGO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1037", "cantidad":  8, "precio": 22000},
    {"articulo": 316679, "descripcion": "KNU NEGRO/NGO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1038", "cantidad":  6, "precio": 22000},
    {"articulo": 316680, "descripcion": "KNU NEGRO/NGO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1039", "cantidad":  4, "precio": 22000},
    {"articulo": 316681, "descripcion": "KNU NEGRO/NGO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1040", "cantidad":  4, "precio": 22000},
    {"articulo": 316682, "descripcion": "KNU NEGRO/NGO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1041", "cantidad":  2, "precio": 22000},
    {"articulo": 316683, "descripcion": "KNU NEGRO/NGO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1042", "cantidad":  2, "precio": 22000},
    {"articulo": 316684, "descripcion": "KNU NEGRO/NGO/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1043", "cantidad":  2, "precio": 22000},
    # ── KNU GRIS/BLANCO (talles 35-44, sin 41) ──
    {"articulo": 309410, "descripcion": "KNU GRIS/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1335", "cantidad":  4, "precio": 22000},
    {"articulo": 309411, "descripcion": "KNU GRIS/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1336", "cantidad":  2, "precio": 22000},
    {"articulo": 309412, "descripcion": "KNU GRIS/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1337", "cantidad":  2, "precio": 22000},
    {"articulo": 309413, "descripcion": "KNU GRIS/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1338", "cantidad":  2, "precio": 22000},
    {"articulo": 309414, "descripcion": "KNU GRIS/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1339", "cantidad":  2, "precio": 22000},
    {"articulo": 309415, "descripcion": "KNU GRIS/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1340", "cantidad":  2, "precio": 22000},
    {"articulo": 309417, "descripcion": "KNU GRIS/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1342", "cantidad":  4, "precio": 22000},
    {"articulo": 309418, "descripcion": "KNU GRIS/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1343", "cantidad":  2, "precio": 22000},
    {"articulo": 309419, "descripcion": "KNU GRIS/BLANCO ZAPA COMB DET LATERAL", "codigo_sinonimo": "104KNUSK1344", "cantidad":  2, "precio": 22000},
]

# ── MAIN ─────────────────────────────────────────────────
if __name__ == "__main__":
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]

    dry_run = modo != "--ejecutar"

    total_pares = sum(r["cantidad"] for r in renglones)
    total_monto = sum(r["cantidad"] * r["precio"] for r in renglones)

    print(f"\n{'='*60}")
    print(f"PEDIDO KNU GTN — {total_pares} pares — ${total_monto:,.0f}")
    print(f"{'='*60}")
    print(f"  Negro/Blanco:     {sum(r['cantidad'] for r in renglones[:11])} pares")
    print(f"  Negro/Ngo/Blanco: {sum(r['cantidad'] for r in renglones[11:20])} pares")
    print(f"  Gris/Blanco:      {sum(r['cantidad'] for r in renglones[20:])} pares")
    print(f"  Base destino:     MSGESTION01 (CALZALINDO)")
    print(f"{'='*60}")

    if not dry_run:
        confirmacion = input("\n¿Confirmar INSERT en producción? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("Cancelado.")
            sys.exit(0)

    numero = insertar_pedido(cabecera, renglones, dry_run=dry_run)

    if numero and not dry_run:
        print(f"\nVerificar en SSMS:")
        print(f"  SELECT * FROM MSGESTION01.dbo.pedico2 WHERE numero = {numero}")
        print(f"  SELECT * FROM MSGESTION01.dbo.pedico1 WHERE numero = {numero}")
