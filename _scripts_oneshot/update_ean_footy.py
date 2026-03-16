#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_ean_footy.py
===================
Actualiza el campo codigo_barra de los artículos FOOTY del pedido #1134071
con los EAN reales de la Nota de Pedido Licencias INV 2026.

El EAN de FOOTY es por MODELO (mismo EAN para todos los talles de un modelo).
Se aplica a los 182 artículos del pedido, incluyendo los 31 viejos que
tenían un codigo_barra interno anterior.

Ejecutar en 111 con: py -3 update_ean_footy.py
"""

import pyodbc

CONN_STR = "DRIVER={SQL Server};SERVER=192.168.2.111;UID=am;PWD=dl"

# EAN por modelo, extraído de la NP "NOTA DE PEDIDO CALZADO LICENCIAS INV 26 BAJA.xlsx"
EAN_POR_MODELO = {
    "AV0455":   "7792621178857",
    "FRZ3152":  "7792621207854",
    "LT2451":   "7792621209360",
    "PFRZ6110": "7792621211967",
    "PPP6123":  "7792621211189",
    "PPP6124":  "7792621211134",
    "PPX3941":  "7792621183165",
    "PPX3953":  "7792621207588",
    "PPX5947":  "7792621191474",
    "PPX938":   "7792621177799",
    "PPX942":   "7792621184711",
    "PSP6118":  "7792621211493",
    "PSP6119":  "7792621211424",
    "PST6113":  "7792621211868",
    "PST6115":  "7792621211721",
    "PST6116":  "7792621211653",
    "PWX3585":  "7792621183646",
    "SP0689":   "7792621192594",
    "SP3695":   "7792621208028",
    "SP3696":   "7792621207953",
    "SP3697":   "7792621208967",
    "SP5612":   "7792621212971",
    "SP5613":   "7792621212896",
    "SP5690":   "7792621191313",
    "ST2897":   "7792621209735",
    "ST2898":   "7792621209445",
    "ST3889":   "7792621208516",
    "ST3891":   "7792621208370",
    "ST5877":   "7792621190828",
    "ST879":    "7792621197735",
    "ST881":    "7792621197872",
}

# Artículos del pedido agrupados por modelo
# Incluye los 31 viejos reasignados + los 151 nuevos
ARTS_POR_MODELO = {
    "AV0455":   [360871, 360872, 360873, 360874, 360875, 360876, 360877],
    "FRZ3152":  [360797, 360798, 360799, 360800, 360801, 360802],
    "LT2451":   [360807, 360808, 360809, 360810, 360811, 360812, 360813],
    "PFRZ6110": [360803, 360804, 360805, 360806],
    "PPP6123":  [360721, 360722, 360723, 360724],
    "PPP6124":  [360725, 360726, 360727, 360728],
    "PPX3941":  [344898, 344899, 344900, 344901, 344902],
    "PPX3953":  [360716, 360717, 360718, 360719, 360720],
    "PPX5947":  [351759, 351760, 351761, 351762, 351763],
    "PPX938":   [146119, 146120, 146121, 146122, 146123],
    "PPX942":   [351770, 351771, 351772, 351773, 351774],
    "PSP6118":  [360859, 360860, 360861, 360862, 360863, 360864],
    "PSP6119":  [360865, 360866, 360867, 360868, 360869, 360870],
    "PST6113":  [360779, 360780, 360781, 360782, 360783, 360784],
    "PST6115":  [360785, 360786, 360787, 360788, 360789, 360790],
    "PST6116":  [360791, 360792, 360793, 360794, 360795, 360796],
    "PWX3585":  [344904, 344905, 344906, 344907, 344983, 344984],
    "SP0689":   [360853, 360854, 360855, 360856, 360857, 360858],
    "SP3695":   [360841, 360842, 360843, 360844, 360845, 360846],
    "SP3696":   [360835, 360836, 360837, 360838, 360839, 360840],
    "SP3697":   [360847, 360848, 360849, 360850, 360851, 360852],
    "SP5612":   [360821, 360822, 360823, 360824, 360825, 360826, 360827],
    "SP5613":   [360814, 360815, 360816, 360817, 360818, 360819, 360820],
    "SP5690":   [351752, 351753, 351754, 351755, 351756, 360828, 360829],
    "ST2897":   [360742, 360743, 360744, 360745, 360746, 360747, 360748],
    "ST2898":   [360735, 360736, 360737, 360738, 360739, 360740, 360741],
    "ST3889":   [360755, 360756, 360757, 360758, 360759, 360760],
    "ST3891":   [360749, 360750, 360751, 360752, 360753, 360754],
    "ST5877":   [360761, 360762, 360763, 360764, 360765, 360766],
    "ST879":    [360773, 360774, 360775, 360776, 360777, 360778],
    "ST881":    [360767, 360768, 360769, 360770, 360771, 360772],
}


def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    total_arts = sum(len(v) for v in ARTS_POR_MODELO.values())
    print("=" * 60)
    print(f"UPDATE EAN FOOTY — {len(EAN_POR_MODELO)} modelos, {total_arts} artículos")
    print("=" * 60)

    # ── PASO 1: Verificar estado actual ──
    print("\n── PASO 1: Estado actual de codigo_barra ──")
    all_codes = []
    for arts in ARTS_POR_MODELO.values():
        all_codes.extend(arts)

    cursor.execute("""
        SELECT codigo, codigo_barra
        FROM msgestion01art.dbo.articulo
        WHERE codigo IN ({})
    """.format(",".join("?" * len(all_codes))), all_codes)

    current = {r.codigo: r.codigo_barra for r in cursor.fetchall()}
    con_ean = sum(1 for v in current.values() if v is not None)
    sin_ean = sum(1 for v in current.values() if v is None)
    print(f"  Con codigo_barra: {con_ean} | Sin codigo_barra: {sin_ean} | Total: {len(current)}")

    # ── PASO 2: UPDATE codigo_barra ──
    print(f"\n── PASO 2: UPDATE codigo_barra con EAN de NP ──")
    updated = 0
    skipped = 0

    for modelo, arts in sorted(ARTS_POR_MODELO.items()):
        ean = EAN_POR_MODELO[modelo]
        for codigo in arts:
            old_val = current.get(codigo)
            if old_val is not None and str(old_val) == ean:
                skipped += 1
                continue

            cursor.execute("""
                UPDATE msgestion01art.dbo.articulo
                SET codigo_barra = ?
                WHERE codigo = ?
            """, ean, codigo)
            updated += 1

        print(f"  {modelo}: EAN={ean} → {len(arts)} artículos")

    print(f"\nActualizados: {updated} | Ya tenían el EAN correcto: {skipped}")

    # ── COMMIT ──
    conn.commit()
    print("\n✓ COMMIT OK")

    # ── PASO 3: Verificación ──
    print(f"\n── PASO 3: Verificación ──")
    cursor.execute("""
        SELECT codigo, codigo_barra
        FROM msgestion01art.dbo.articulo
        WHERE codigo IN ({})
    """.format(",".join("?" * len(all_codes))), all_codes)

    after = {r.codigo: str(r.codigo_barra) if r.codigo_barra else None for r in cursor.fetchall()}

    ok = 0
    fail = 0
    for modelo, arts in sorted(ARTS_POR_MODELO.items()):
        ean = EAN_POR_MODELO[modelo]
        for codigo in arts:
            if after.get(codigo) == ean:
                ok += 1
            else:
                fail += 1
                print(f"  ✗ {codigo} ({modelo}): esperado {ean}, tiene {after.get(codigo)}")

    if fail == 0:
        print(f"\n✅ EAN COMPLETO — {ok}/{total_arts} artículos con EAN correcto")
    else:
        print(f"\n⚠️ REVISAR — {ok} OK, {fail} con error")

    conn.close()


if __name__ == "__main__":
    main()
