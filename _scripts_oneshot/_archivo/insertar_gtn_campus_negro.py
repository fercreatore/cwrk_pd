# insertar_gtn_campus_negro.py
# Inserta el pedido GTN Campus Negro - 26 pares (CALZALINDO / msgestion01)
# EJECUTAR:
#   OPENSSL_CONF=_scripts_oneshot/openssl_legacy.cnf python3 _scripts_oneshot/insertar_gtn_campus_negro.py --dry-run
#   OPENSSL_CONF=_scripts_oneshot/openssl_legacy.cnf python3 _scripts_oneshot/insertar_gtn_campus_negro.py --ejecutar

import sys
from datetime import date
from paso4_insertar_pedido import insertar_pedido

# ── CABECERA ──────────────────────────────────────────────
cabecera = {
    "empresa":           "CALZALINDO",      # GTN = 100% base 01
    "cuenta":            104,
    "denominacion":      '"EL GITANO" - GTN',
    "fecha_comprobante": date(2026, 3, 30),
    "fecha_entrega":     date(2026, 4, 30),
    "observaciones":     "Pedido CAMPUS NEGRO Invierno 2026. 26 pares.",
}

# ── RENGLONES ──────────────────────────────────────────────
# CAMPUS NEGRO/NEGRO — 16 pares (talles 35-40)
# Artículos: 343160-343165 (sinonimo 104AMPUS00XX, precio_fabrica $23.000)
# Curva: T35:2, T36:3, T37:3, T38:3, T39:3, T40:2

# CAMPUS NEGRO/NEGRO/BLANCO — 10 pares (talles 35-40)
# Artículos: 325785-325790 (sinonimo 104CAMPU10XX, precio_fabrica $22.000)
# Curva: T35:1, T36:2, T37:2, T38:2, T39:2, T40:1

renglones = [
    # ── CAMPUS NEGRO/NEGRO (talles 35-40) — 16 pares ──
    {"articulo": 343160, "descripcion": "CAMPUS NEGRO/NEGRO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104AMPUS0035", "cantidad": 2, "precio": 23000},
    {"articulo": 343161, "descripcion": "CAMPUS NEGRO/NEGRO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104AMPUS0036", "cantidad": 3, "precio": 23000},
    {"articulo": 343162, "descripcion": "CAMPUS NEGRO/NEGRO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104AMPUS0037", "cantidad": 3, "precio": 23000},
    {"articulo": 343163, "descripcion": "CAMPUS NEGRO/NEGRO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104AMPUS0038", "cantidad": 3, "precio": 23000},
    {"articulo": 343164, "descripcion": "CAMPUS NEGRO/NEGRO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104AMPUS0039", "cantidad": 3, "precio": 23000},
    {"articulo": 343165, "descripcion": "CAMPUS NEGRO/NEGRO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104AMPUS0040", "cantidad": 2, "precio": 23000},
    # ── CAMPUS NEGRO/NEGRO/BLANCO (talles 35-40) — 10 pares ──
    {"articulo": 325785, "descripcion": "CAMPUS NEGRO/NEGRO/BLANCO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104CAMPU0035", "cantidad": 1, "precio": 22000},
    {"articulo": 325786, "descripcion": "CAMPUS NEGRO/NEGRO/BLANCO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104CAMPU1036", "cantidad": 2, "precio": 22000},
    {"articulo": 325787, "descripcion": "CAMPUS NEGRO/NEGRO/BLANCO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104CAMPU1037", "cantidad": 2, "precio": 22000},
    {"articulo": 325788, "descripcion": "CAMPUS NEGRO/NEGRO/BLANCO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104CAMPU1038", "cantidad": 2, "precio": 22000},
    {"articulo": 325789, "descripcion": "CAMPUS NEGRO/NEGRO/BLANCO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104CAMPU1039", "cantidad": 2, "precio": 22000},
    {"articulo": 325790, "descripcion": "CAMPUS NEGRO/NEGRO/BLANCO ZAPA URB AC DET 3 TIRAS", "codigo_sinonimo": "104CAMPU1040", "cantidad": 1, "precio": 22000},
]

# ── MAIN ──────────────────────────────────────────────────
if __name__ == "__main__":
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]

    dry_run = modo != "--ejecutar"

    pares_negro_negro     = sum(r["cantidad"] for r in renglones[:6])
    pares_negro_ngo_blanco = sum(r["cantidad"] for r in renglones[6:])
    total_pares = sum(r["cantidad"] for r in renglones)
    total_monto = sum(r["cantidad"] * r["precio"] for r in renglones)

    print(f"\n{'='*60}")
    print(f"PEDIDO CAMPUS GTN — {total_pares} pares — ${total_monto:,.0f}")
    print(f"{'='*60}")
    print(f"  Campus Negro/Negro:         {pares_negro_negro} pares @ $23.000")
    print(f"  Campus Negro/Negro/Blanco:  {pares_negro_ngo_blanco} pares @ $22.000")
    print(f"  Base destino:               MSGESTION01 (CALZALINDO)")
    print(f"{'='*60}")
    print()

    for r in renglones:
        print(f"  [{r['codigo_sinonimo']}] {r['descripcion'][:45]:<45} x{r['cantidad']:>2}  ${r['precio']:>7,.0f}")

    print(f"\n  TOTAL: {total_pares} pares — ${total_monto:,.0f}")
    print()

    if dry_run:
        print("  [DRY RUN] No se escribió nada. Pasá --ejecutar para confirmar.")
    else:
        confirmacion = input("¿Confirmar INSERT en producción? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("Cancelado.")
            sys.exit(0)

    numero = insertar_pedido(cabecera, renglones, dry_run=dry_run)

    if numero and not dry_run:
        print(f"\nVerificar en SSMS:")
        print(f"  SELECT * FROM MSGESTION01.dbo.pedico2 WHERE numero = {numero}")
        print(f"  SELECT * FROM MSGESTION01.dbo.pedico1 WHERE numero = {numero}")
