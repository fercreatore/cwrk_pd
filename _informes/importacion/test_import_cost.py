# -*- coding: utf-8 -*-
"""
Tests para import_cost.py

Correr con:
    cd /home/user/cwrk_pd/_informes/importacion
    python3 test_import_cost.py

O desde la raíz del repo:
    python3 -m _informes.importacion.test_import_cost
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from import_cost import (
    calcular_logistica_unitaria,
    calcular_costo_importacion,
    calcular_precios_venta,
    calcular_fob_maximo,
    ALICUOTAS,
)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

_errors = []

def check(name, got, expected, tol=0):
    ok = abs(got - expected) <= tol
    status = PASS if ok else FAIL
    if not ok:
        _errors.append(name)
    print("  {} {:55s} got={:,.0f}  expected={:,.0f}{}".format(
        status, name, got, expected,
        "" if ok else "  DIFF={:+,.0f}".format(got - expected)
    ))
    return ok


print("=" * 70)
print("TEST 1 — Forward: caso DEPLOY_IMPORTACIONES.txt")
print("  FOB real=8, FOB aduana=15.70, logistica=3.4466, TC=1200")
print("-" * 70)

r = calcular_costo_importacion(
    fob_real=8.00,
    fob_aduana=15.70,
    logistica_unitaria=3.4466,
    tipo_cambio=1200,
)
check("costo_economico_ars",        r["costo_economico_ars"],      19020,  tol=2)
check("costo_financiero_ars",       r["costo_financiero_ars"],     32303,  tol=5)
check("sobrecosto_dumping_ars",     r["sobrecosto_dumping_ars"],   2125,   tol=2)
check("pct_sobrecosto_sobre_real",  r["pct_sobrecosto_sobre_real"], 22.1,  tol=0.1)
check("cif_ars",                    r["cif_ars"],                  22976,  tol=2)  # 19.1466 × 1200
check("derecho_ars",                r["derecho_ars"],              4595,   tol=2)  # 3.8293 × 1200
check("estadistica_ars",            r["estadistica_ars"],          689,    tol=2)  # 0.5744 × 1200

print()
print("=" * 70)
print("TEST 2 — Forward: sin dumping (fob_real = fob_aduana)")
print("  FOB=10, logistica=2, TC=1200")
print("-" * 70)

r2 = calcular_costo_importacion(
    fob_real=10.0,
    fob_aduana=10.0,
    logistica_unitaria=2.0,
    tipo_cambio=1200,
)
# CIF = 12 USD, DI = 2.40, TE = 0.36 → econ = (10+2) × 1.23 = 14.76 USD = 17712 ARS
check("costo_economico_ars (sin dumping)", r2["costo_economico_ars"], 17712, tol=2)
check("sobrecosto_dumping_ars = 0",        r2["sobrecosto_dumping_ars"], 0,   tol=1)
check("diferencial_dumping_usd = 0",       r2["diferencial_dumping_usd"], 0,  tol=0.001)

print()
print("=" * 70)
print("TEST 3 — Forward: fob_real=0 → asume sin dumping")
print("-" * 70)
r3 = calcular_costo_importacion(
    fob_real=0,
    fob_aduana=10.0,
    logistica_unitaria=2.0,
    tipo_cambio=1200,
)
check("costo_economico_ars (fob_real=0)", r3["costo_economico_ars"], 17712, tol=2)

print()
print("=" * 70)
print("TEST 4 — Precios de venta con IIBB 3.5%")
print("  costo_econ_ars=17712, margenes: contado=100%, lista=120%")
print("-" * 70)

precios = calcular_precios_venta(
    costo_economico_ars=17712,
    margenes={"contado": 100, "lista": 120},
    iibb_pct=0.035,
)
# contado: 17712 × 2.00 × 1.035 = 36,654.96 → redondeado $36,700
# lista:   17712 × 2.20 × 1.035 = 40,320.46 → redondeado $40,400
contado_exacto   = 17712 * 2.00 * 1.035
lista_exacto     = 17712 * 2.20 * 1.035
check("contado exacto",            precios["contado"]["exacto"],    round(contado_exacto, 2), tol=0.02)
check("lista exacto",              precios["lista"]["exacto"],      round(lista_exacto, 2),   tol=0.02)
# redondeado = ceil al 100 más cercano
import math
check("contado redondeado",        precios["contado"]["redondeado"], int(math.ceil(contado_exacto/100)*100), tol=0)
check("lista redondeado",          precios["lista"]["redondeado"],   int(math.ceil(lista_exacto/100)*100),   tol=0)

print()
print("=" * 70)
print("TEST 5 — Reverse: precio venta→FOB, sin logística variable")
print("  venta=$80.000, margen=120%, TC=1200, logistica=3 USD")
print("-" * 70)

rev = calcular_fob_maximo(
    precio_venta_ars=80000,
    margen_pct=120,
    tipo_cambio=1200,
    logistica_unitaria_usd=3.0,
    flete_pct=0.0,
    seguro_pct=0.0,
)
# Verificar razonabilidad: FOB de un zapato a ese precio debe ser ~USD 15-25
fob = rev["fob_maximo_usd"]
# Usamos check manual para el rango:
if 10 <= fob <= 40:
    print("  {} {:55s} fob={:.2f} USD".format(PASS, "fob_maximo_usd en rango [10, 40] USD", fob))
else:
    print("  {} {:55s} fob={:.2f} USD FUERA DE RANGO".format(FAIL, "fob_maximo_usd en rango [10, 40] USD", fob))
    _errors.append("fob_maximo_usd en rango [10, 40] USD")

print("  > fob_maximo_usd = {:.4f} USD".format(fob))
print("  > costo_economico_ars = {:,.0f}".format(rev["costo_economico_ars"]))
print("  > cif_usd = {:.4f}".format(rev["cif_usd"]))

print()
print("=" * 70)
print("TEST 6 — Roundtrip: forward(fob=X) → venta → reverse → fob≈X")
print("  FOB=12 USD, logistica=2 USD, TC=1200, margen=100%")
print("-" * 70)

fob_original = 12.0
log_fijo = 2.0
tc = 1200
margen = 100.0

fwd = calcular_costo_importacion(
    fob_real=fob_original,
    fob_aduana=fob_original,
    logistica_unitaria=log_fijo,
    tipo_cambio=tc,
)
pventa = calcular_precios_venta(
    fwd["costo_economico_ars"],
    {"contado": margen},
    iibb_pct=ALICUOTAS["iibb_santa_fe"],
)
venta_exacta = pventa["contado"]["exacto"]

rev2 = calcular_fob_maximo(
    precio_venta_ars=venta_exacta,
    margen_pct=margen,
    tipo_cambio=tc,
    logistica_unitaria_usd=log_fijo,
    flete_pct=0.0,
    seguro_pct=0.0,
)
diff_roundtrip = abs(rev2["fob_maximo_usd"] - fob_original)
if diff_roundtrip < 0.01:
    print("  {} {:55s} diff={:.6f} USD".format(PASS, "roundtrip fob error < 0.01 USD", diff_roundtrip))
else:
    print("  {} {:55s} diff={:.6f} USD".format(FAIL, "roundtrip fob error < 0.01 USD", diff_roundtrip))
    _errors.append("roundtrip fob error")
print("  > fob_original={:.4f}  rev_fob={:.4f}  diff={:.6f}".format(
    fob_original, rev2["fob_maximo_usd"], diff_roundtrip))

print()
print("=" * 70)
print("TEST 7 — Logística unitaria desde contenedor")
print("  flete=3800, interno=1300, despacho=350, fob_total=24825.90, fob_sku=15.70")
print("-" * 70)

lu = calcular_logistica_unitaria(
    flete_maritimo=3800,
    flete_interno=1300,
    despachante=350,
    valor_fob_aduana_total=24825.90,
    fob_aduana_producto=15.70,
)
# share = 15.70/24825.90 = 0.0006324
# total = 5450 × 0.0006324 = 3.4464 USD (≈ el valor del DEPLOY)
check("logistica_unitaria_usd", lu, 3.4464, tol=0.01)
print("  > logistica_unitaria = {:.4f} USD  (DEPLOY usa 3.4466)".format(lu))

print()
print("=" * 70)
print("TEST 8 — Reverse con flete % (sin logística fija conocida)")
print("  venta=$50.000, margen=80%, TC=1200, flete 10%, seguro 1%")
print("-" * 70)

rev3 = calcular_fob_maximo(
    precio_venta_ars=50000,
    margen_pct=80,
    tipo_cambio=1200,
    logistica_unitaria_usd=0.0,
    flete_pct=0.10,
    seguro_pct=0.01,
)
fob3 = rev3["fob_maximo_usd"]
if fob3 > 0:
    print("  {} {:55s} fob={:.2f} USD".format(PASS, "fob > 0 con flete%", fob3))
else:
    print("  {} {:55s} fob={:.2f} USD".format(FAIL, "fob > 0 con flete%", fob3))
    _errors.append("fob > 0 con flete%")
# Verificar que la verificación forward da precio venta cercano
if rev3["verificacion"]:
    v_econ = rev3["verificacion"]["costo_economico_ars"]
    # precio_venta debería ser ≈ v_econ × (1 + 80/100) × (1 + iibb)
    p_check = v_econ * 1.80 * (1 + ALICUOTAS["iibb_santa_fe"])
    diff_p = abs(p_check - 50000)
    if diff_p < 10:
        print("  {} {:55s} diff_precio={:.0f} ARS".format(PASS, "verificacion roundtrip flete%", diff_p))
    else:
        print("  {} {:55s} diff_precio={:.0f} ARS".format(FAIL, "verificacion roundtrip flete%", diff_p))
        _errors.append("verificacion roundtrip flete%")

print()
print("=" * 70)
if _errors:
    print("\033[91mFAILED — {} test(s) fallaron: {}\033[0m".format(len(_errors), ", ".join(_errors)))
    sys.exit(1)
else:
    print("\033[92mAll tests PASSED\033[0m")
    sys.exit(0)
