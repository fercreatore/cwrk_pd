"""
Rebalanceo por contribución mensual.
No vende nada — solo decide cómo distribuir el aporte nuevo para acercarse al target.
"""
from csv_parser import load_all_portfolios, DOLAR_MEP
from config_fo import TARGET_ALLOCATION, APORTE_MENSUAL_ARS


def calculate_rebalance(aporte_ars=None, dolar_mep=None):
    """
    Calcula cómo distribuir el aporte mensual para acercarse al target allocation.

    Retorna dict con:
        - current: allocation actual por clase
        - target: allocation target
        - gap: diferencia actual vs target
        - recommendation: cuánto poner en cada clase este mes
        - portfolio_total_usd: valor total actual
        - aporte_usd: valor del aporte en USD
    """
    if aporte_ars is None:
        aporte_ars = APORTE_MENSUAL_ARS
    if dolar_mep is None:
        dolar_mep = DOLAR_MEP

    aporte_usd = aporte_ars / dolar_mep

    positions, cash_list, _ = load_all_portfolios()

    # Totales por clase
    by_class = {}
    total_positions = 0
    for p in positions:
        cls = p["asset_class"]
        by_class[cls] = by_class.get(cls, 0) + p["market_value_usd"]
        total_positions += p["market_value_usd"]

    # Cash
    cash_usd = sum(
        c["amount"] if c["currency"] == "USD" else c["amount"] / dolar_mep
        for c in cash_list
    )

    portfolio_total = total_positions + cash_usd
    new_total = portfolio_total + aporte_usd  # total post-aporte

    # Allocation actual (%)
    current_alloc = {}
    for cls in set(list(TARGET_ALLOCATION.keys()) + list(by_class.keys())):
        current_alloc[cls] = (by_class.get(cls, 0) / portfolio_total * 100) if portfolio_total > 0 else 0

    # Calcular cuánto DEBERÍA tener cada clase en el nuevo total
    # vs cuánto tiene ahora → la diferencia es lo que compramos
    recommendation = {}
    gaps = {}

    for cls, target_pct in TARGET_ALLOCATION.items():
        target_usd_post = new_total * target_pct / 100  # lo que debería tener post-aporte
        current_usd = by_class.get(cls, 0)               # lo que tiene hoy
        needed = target_usd_post - current_usd            # cuánto falta

        gaps[cls] = {
            "current_pct": current_alloc.get(cls, 0),
            "target_pct": target_pct,
            "gap_pct": current_alloc.get(cls, 0) - target_pct,
            "current_usd": current_usd,
            "target_usd_post": target_usd_post,
            "needed_usd": needed,
        }

    # Distribuir el aporte proporcionalmente a lo que más falta
    # Solo asignamos a clases que están SUBPONDERADAS (needed > 0)
    total_needed = sum(max(g["needed_usd"], 0) for g in gaps.values())

    if total_needed > 0:
        for cls, gap in gaps.items():
            if gap["needed_usd"] > 0:
                # Proporción del aporte que va a esta clase
                share = gap["needed_usd"] / total_needed
                alloc_usd = aporte_usd * share
                alloc_ars = alloc_usd * dolar_mep
            else:
                alloc_usd = 0
                alloc_ars = 0

            recommendation[cls] = {
                "alloc_usd": alloc_usd,
                "alloc_ars": alloc_ars,
                "alloc_pct": (alloc_usd / aporte_usd * 100) if aporte_usd > 0 else 0,
                "post_aporte_pct": ((by_class.get(cls, 0) + alloc_usd) / new_total * 100),
            }
    else:
        # Todo está sobreponderado — poner todo en la clase más subponderada
        least_over = min(gaps.items(), key=lambda x: x[1]["gap_pct"])
        for cls in TARGET_ALLOCATION:
            if cls == least_over[0]:
                recommendation[cls] = {
                    "alloc_usd": aporte_usd,
                    "alloc_ars": aporte_ars,
                    "alloc_pct": 100,
                    "post_aporte_pct": ((by_class.get(cls, 0) + aporte_usd) / new_total * 100),
                }
            else:
                recommendation[cls] = {
                    "alloc_usd": 0,
                    "alloc_ars": 0,
                    "alloc_pct": 0,
                    "post_aporte_pct": (by_class.get(cls, 0) / new_total * 100),
                }

    return {
        "current": current_alloc,
        "target": TARGET_ALLOCATION,
        "gaps": gaps,
        "recommendation": recommendation,
        "portfolio_total_usd": portfolio_total,
        "new_total_usd": new_total,
        "aporte_usd": aporte_usd,
        "aporte_ars": aporte_ars,
        "dolar_mep": dolar_mep,
    }


def print_rebalance_report(result=None):
    """Imprime el reporte de rebalanceo."""
    if result is None:
        result = calculate_rebalance()

    r = result
    print(f"{'='*65}")
    print(f"  REBALANCEO MENSUAL — Family Office")
    print(f"{'='*65}")
    print(f"  Portfolio actual:  US$ {r['portfolio_total_usd']:>10,.0f}")
    print(f"  Aporte mensual:    $ {r['aporte_ars']:>12,.0f} ARS = US$ {r['aporte_usd']:,.0f}")
    print(f"  Dólar MEP:         $ {r['dolar_mep']:,.0f}")
    print(f"  Portfolio post:    US$ {r['new_total_usd']:>10,.0f}")
    print()

    print(f"  {'Clase':<25s} {'Actual':>7s} {'Target':>7s} {'Gap':>7s} → {'Comprar':>12s} {'Post':>7s}")
    print(f"  {'-'*25} {'-'*7} {'-'*7} {'-'*7}   {'-'*12} {'-'*7}")

    for cls in sorted(r["target"].keys(), key=lambda x: r["recommendation"].get(x, {}).get("alloc_usd", 0), reverse=True):
        gap = r["gaps"][cls]
        rec = r["recommendation"][cls]
        actual = gap["current_pct"]
        target = gap["target_pct"]
        gap_pct = gap["gap_pct"]
        comprar_ars = rec["alloc_ars"]
        post = rec["post_aporte_pct"]

        arrow = "←" if comprar_ars > 0 else " "
        print(f"  {cls:<25s} {actual:>6.1f}% {target:>6.1f}% {gap_pct:>+6.1f}%   $ {comprar_ars:>10,.0f} {post:>6.1f}% {arrow}")

    print()
    total_check = sum(rec["alloc_ars"] for rec in r["recommendation"].values())
    print(f"  Total a comprar: $ {total_check:,.0f} ARS")
    print()

    # Sugerencias concretas
    print(f"  SUGERENCIAS CONCRETAS:")
    print(f"  {'-'*50}")
    for cls in sorted(r["target"].keys(), key=lambda x: r["recommendation"].get(x, {}).get("alloc_usd", 0), reverse=True):
        rec = r["recommendation"][cls]
        if rec["alloc_ars"] < 1000:
            continue
        ars = rec["alloc_ars"]
        usd = rec["alloc_usd"]
        if cls == "CEDEARs":
            print(f"  → {cls}: $ {ars:,.0f} ARS (US$ {usd:,.0f})")
            print(f"    Opciones: NVDA, MELI, AVGO en dip")
        elif cls == "Crypto":
            print(f"  → {cls}: $ {ars:,.0f} ARS (US$ {usd:,.0f})")
            print(f"    Opciones: IBIT, MSTR")
        elif cls == "Acciones AR":
            print(f"  → {cls}: $ {ars:,.0f} ARS (US$ {usd:,.0f})")
            print(f"    Opciones: TGNO4, AUSO, TRAN (post crash Merval -26%)")
        elif cls == "Bonos Soberanos AR":
            print(f"  → {cls}: $ {ars:,.0f} ARS (US$ {usd:,.0f})")
            print(f"    Opciones: GD35, AE38 (carry ~10% USD)")
        elif cls == "FCI / Money Market":
            print(f"  → {cls}: $ {ars:,.0f} ARS (US$ {usd:,.0f})")
            print(f"    Opciones: COCOUSDPA (liquidez para dips)")


if __name__ == "__main__":
    print_rebalance_report()
