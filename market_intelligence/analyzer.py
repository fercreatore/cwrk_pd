"""
Análisis consolidado de oportunidades de importación.
Combina datos de ML scraping + Google Trends + costos de importación.

Uso:
    from market_intelligence.analyzer import MarketAnalyzer
    analyzer = MarketAnalyzer()
    report = analyzer.full_report("valijas de viaje", landed_cost_usd=18)
"""

import json
import os
import requests
from datetime import datetime
from .ml_scraper import MLScraper, import_opportunity_score
from .trends import get_trends, seasonal_projection

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Fallback si la API no responde
DEFAULT_EXCHANGE_RATE = 1250  # ARS/USD (fallback)


def fetch_exchange_rate(fallback=DEFAULT_EXCHANGE_RATE):
    """Obtener tipo de cambio USD→ARS blue/oficial desde API pública.

    Intenta DolarApi.com (gratis, sin auth). Si falla, retorna fallback.
    """
    try:
        r = requests.get("https://dolarapi.com/v1/dolares/blue", timeout=5)
        if r.status_code == 200:
            data = r.json()
            # Promedio compra/venta
            return (data.get("compra", fallback) + data.get("venta", fallback)) / 2
    except Exception:
        pass
    try:
        r = requests.get("https://dolarapi.com/v1/dolares/oficial", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return (data.get("compra", fallback) + data.get("venta", fallback)) / 2
    except Exception:
        pass
    return fallback

# Costos de importación Argentina (calzado/marroquinería)
IMPORT_COSTS = {
    "derecho_importacion": 0.20,     # 20% sobre CIF
    "tasa_estadistica": 0.03,        # 3% sobre CIF
    "iva": 0.21,                     # 21%
    "percepcion_iva": 0.20,          # 20%
    "percepcion_ganancias": 0.06,    # 6%
    "flete_internacional_pct": 0.10, # ~10% del FOB
    "seguro_pct": 0.01,              # ~1% del FOB
}


class MarketAnalyzer:
    def __init__(self, exchange_rate=None, auto_fetch_rate=True):
        if exchange_rate:
            self.exchange_rate = exchange_rate
        elif auto_fetch_rate:
            self.exchange_rate = fetch_exchange_rate()
        else:
            self.exchange_rate = DEFAULT_EXCHANGE_RATE
        self.scraper = MLScraper()

    def calculate_landed_cost(self, fob_usd, freight_pct=None, insurance_pct=None):
        """
        Calcula costo landed (puesto en Argentina) desde FOB.

        Args:
            fob_usd: precio FOB por unidad en USD
            freight_pct: flete como % del FOB (default 10%)
            insurance_pct: seguro como % del FOB (default 1%)

        Returns:
            dict con desglose de costos
        """
        freight = fob_usd * (freight_pct or IMPORT_COSTS["flete_internacional_pct"])
        insurance = fob_usd * (insurance_pct or IMPORT_COSTS["seguro_pct"])
        cif = fob_usd + freight + insurance

        derecho = cif * IMPORT_COSTS["derecho_importacion"]
        tasa = cif * IMPORT_COSTS["tasa_estadistica"]
        base_imp = cif + derecho + tasa

        iva = base_imp * IMPORT_COSTS["iva"]
        perc_iva = base_imp * IMPORT_COSTS["percepcion_iva"]
        perc_gan = base_imp * IMPORT_COSTS["percepcion_ganancias"]

        # Costo económico (sin percepciones que son crédito fiscal)
        costo_economico = cif + derecho + tasa + iva
        # Costo financiero (desembolso real)
        costo_financiero = costo_economico + perc_iva + perc_gan

        return {
            "fob_usd": fob_usd,
            "freight_usd": round(freight, 2),
            "insurance_usd": round(insurance, 2),
            "cif_usd": round(cif, 2),
            "derecho_importacion_usd": round(derecho, 2),
            "tasa_estadistica_usd": round(tasa, 2),
            "iva_usd": round(iva, 2),
            "percepcion_iva_usd": round(perc_iva, 2),
            "percepcion_ganancias_usd": round(perc_gan, 2),
            "costo_economico_usd": round(costo_economico, 2),
            "costo_financiero_usd": round(costo_financiero, 2),
            "costo_economico_ars": round(costo_economico * self.exchange_rate),
            "costo_financiero_ars": round(costo_financiero * self.exchange_rate),
            "markup_sobre_fob": round(costo_economico / fob_usd, 2),
        }

    def opportunity_analysis(self, ml_analysis, landed_cost_usd, ml_commission=16):
        """
        Analiza oportunidad comparando costo landed vs mercado ML.

        Returns dict with viability assessment.
        """
        if not ml_analysis or ml_analysis.get("error"):
            return {"viable": False, "reason": "No market data"}

        median_price = ml_analysis["price_median"]
        q1_price = ml_analysis["price_q1"]

        landed_ars = landed_cost_usd * self.exchange_rate

        # Net revenue after ML commission
        net_median = median_price * (1 - ml_commission / 100)
        net_q1 = q1_price * (1 - ml_commission / 100)

        margin_median = (net_median - landed_ars) / net_median * 100 if net_median > 0 else 0
        margin_q1 = (net_q1 - landed_ars) / net_q1 * 100 if net_q1 > 0 else 0

        # Break-even price (minimum ML listing price for 25% margin)
        min_margin = 25
        denominator = 1 - min_margin / 100 - ml_commission / 100
        if denominator <= 0:
            breakeven_price = float('inf')
        else:
            breakeven_price = landed_ars / denominator

        # Price positioning
        if breakeven_price == float('inf'):
            positioning = "INVIABLE - margen + comisión >= 100%"
        elif breakeven_price < q1_price:
            positioning = "FUERTE - podés competir en precio bajo"
        elif breakeven_price < median_price:
            positioning = "VIABLE - competitivo en rango medio"
        elif breakeven_price < ml_analysis["price_q3"]:
            positioning = "AJUSTADO - solo viable en rango alto"
        else:
            positioning = "INVIABLE - costo muy alto vs mercado"

        # Suggested prices
        suggested = {}
        for label, margin in [("agresivo_30", 30), ("target_40", 40), ("premium_50", 50)]:
            denom = 1 - margin / 100 - ml_commission / 100
            if denom <= 0:
                suggested[label] = None
            else:
                suggested[label] = round(landed_ars / denom)

        return {
            "landed_cost_ars": round(landed_ars),
            "ml_median_price": median_price,
            "ml_q1_price": q1_price,
            "net_after_commission_median": round(net_median),
            "margin_at_median": round(margin_median, 1),
            "margin_at_q1": round(margin_q1, 1),
            "breakeven_price_25pct": round(breakeven_price),
            "positioning": positioning,
            "viable": margin_median >= 25,
            "suggested_prices": suggested,
        }

    def full_report(self, query, fob_usd=None, landed_cost_usd=None, pages=2):
        """
        Generate complete market intelligence report.

        Args:
            query: ML search query
            fob_usd: FOB price per unit (calculates full landed cost)
            landed_cost_usd: direct landed cost if known (overrides fob_usd calc)
            pages: ML search pages

        Returns:
            Complete report dict
        """
        print(f"Scanning ML for: {query}...")
        items = self.scraper.search(query, pages=pages)
        ml_analysis = self.scraper.analyze(items)

        report = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "exchange_rate": self.exchange_rate,
            "market": ml_analysis,
        }

        # Cost analysis
        if fob_usd:
            costs = self.calculate_landed_cost(fob_usd)
            report["costs"] = costs
            effective_landed = costs["costo_economico_usd"]
        elif landed_cost_usd:
            effective_landed = landed_cost_usd
            report["costs"] = {"landed_cost_usd": landed_cost_usd}
        else:
            effective_landed = None

        # Opportunity analysis
        if effective_landed:
            report["opportunity"] = self.opportunity_analysis(
                ml_analysis, effective_landed
            )

        # Google Trends (may fail due to rate limits)
        print(f"Checking Google Trends...")
        trends_df = get_trends([query.split()[0]], months=12)
        if trends_df is not None:
            projection = seasonal_projection(trends_df, forecast_days=90)
            report["trends"] = projection
        else:
            report["trends"] = {"note": "Google Trends unavailable (rate limited)"}

        # Save
        self.scraper.save_results(items, report, query)

        return report

    def compare_categories(self, queries_with_costs, pages=2):
        """
        Compare multiple product categories for import opportunity.

        Args:
            queries_with_costs: list of (query, fob_usd_or_landed) tuples

        Returns:
            Ranked list of opportunities
        """
        opportunities = []

        for query, cost in queries_with_costs:
            report = self.full_report(query, landed_cost_usd=cost, pages=pages)
            opp = report.get("opportunity", {})
            opp["query"] = query
            opp["market_size"] = report["market"]["total_items"]
            opportunities.append(opp)

        # Rank by margin
        opportunities.sort(key=lambda x: x.get("margin_at_median", -999), reverse=True)

        return opportunities

    def print_report(self, report):
        """Pretty-print a full report."""
        print(f"\n{'='*65}")
        print(f"MARKET INTELLIGENCE: {report['query'].upper()}")
        print(f"{'='*65}")
        print(f"Fecha: {report['timestamp'][:10]} | TC: ${self.exchange_rate:,} ARS/USD")

        m = report["market"]
        print(f"\n--- MERCADO ML ---")
        print(f"Items encontrados: {m['total_items']}")
        print(f"Rango precios: ${m['price_min']:,} — ${m['price_max']:,}")
        print(f"Q1: ${m['price_q1']:,} | Mediana: ${m['price_median']:,} | Q3: ${m['price_q3']:,}")
        if m["top_brands"]:
            print(f"Marcas top: {', '.join(f'{b}({c})' for b,c in m['top_brands'][:5])}")
        print(f"Envío gratis: {m['free_shipping_pct']}%")

        if "costs" in report and "cif_usd" in report["costs"]:
            c = report["costs"]
            print(f"\n--- COSTOS IMPORTACION ---")
            print(f"FOB: USD {c['fob_usd']}")
            print(f"CIF: USD {c['cif_usd']}")
            print(f"Costo económico: USD {c['costo_economico_usd']} = ${c['costo_economico_ars']:,} ARS")
            print(f"Costo financiero: USD {c['costo_financiero_usd']} = ${c['costo_financiero_ars']:,} ARS")
            print(f"Markup sobre FOB: {c['markup_sobre_fob']}x")

        if "opportunity" in report:
            o = report["opportunity"]
            print(f"\n--- OPORTUNIDAD ---")
            print(f"Costo landed: ${o['landed_cost_ars']:,} ARS")
            print(f"Margen a mediana ML: {o['margin_at_median']}%")
            print(f"Margen a Q1 ML: {o['margin_at_q1']}%")
            print(f"Precio break-even (25% margin): ${o['breakeven_price_25pct']:,}")
            print(f"Posicionamiento: {o['positioning']}")
            print(f"Precios sugeridos:")
            for label, price in o["suggested_prices"].items():
                print(f"  {label:15s}: ${price:,}")

        if "trends" in report and "note" not in report["trends"]:
            print(f"\n--- TENDENCIA 90 DIAS ---")
            for kw, t in report["trends"].items():
                print(f"  {kw}: {t['trend']} (factor: {t['seasonal_factor']}x)")
                print(f"    Actual: {t['current_interest']} → Proyectado: {t['projected_interest']}")


if __name__ == "__main__":
    analyzer = MarketAnalyzer(exchange_rate=1250)

    # Valija carry on - FOB ~$8 USD (China)
    report = analyzer.full_report("carry on cabina rigida", fob_usd=8)
    analyzer.print_report(report)

    # Set de valijas - FOB ~$20 USD
    report = analyzer.full_report("set valijas rigidas", fob_usd=20)
    analyzer.print_report(report)
