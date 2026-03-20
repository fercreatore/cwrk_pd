"""
Cross-Analysis Engine — Cruce de todas las variables de Market Intelligence.

Combina datos de ML, Google Trends, competidores, costos de importación
y presencia digital para generar un score compuesto de oportunidad.

Uso:
    from market_intelligence.cross_analysis import CrossAnalyzer
    ca = CrossAnalyzer(exchange_rate=1250)
    result = ca.full_cross_analysis(
        query="valijas carry on",
        landed_cost_usd=12,
        competitors=[{"name": "Samsonite", "instagram": "samsonite_ar", ...}],
    )
"""

import json
import os
from datetime import datetime

from .ml_scraper import MLScraper
from .analyzer import MarketAnalyzer, fetch_exchange_rate
from .trends import get_trends, seasonal_projection, get_related_queries
from .instagram import InstagramAuditor
from .facebook import FacebookAuditor
from .website_audit import WebsiteAuditor
from .whatsapp import WhatsAppChecker

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class CrossAnalyzer:
    """Motor de análisis cruzado multivariable."""

    def __init__(self, exchange_rate=None, ml_commission=16):
        self.exchange_rate = exchange_rate or fetch_exchange_rate()
        self.ml_commission = ml_commission
        self.scraper = MLScraper()
        self.analyzer = MarketAnalyzer(exchange_rate=self.exchange_rate)
        os.makedirs(DATA_DIR, exist_ok=True)

    def market_depth_analysis(self, items, analysis):
        """Analizar profundidad y estructura del mercado ML.

        Cruza: precios x marcas x envío x descuentos
        """
        if not items:
            return {}

        prices = [i["price"] for i in items if i["price"] > 0]
        if not prices:
            return {}

        # Concentration index (Herfindahl-like for brands)
        brand_counts = {}
        for i in items:
            b = i.get("brand") or "Sin marca"
            brand_counts[b] = brand_counts.get(b, 0) + 1

        total = len(items)
        hhi = sum((c / total) ** 2 for c in brand_counts.values())
        top_brand_share = max(brand_counts.values()) / total if brand_counts else 0

        # Price dispersion
        import statistics
        price_std = statistics.stdev(prices) if len(prices) > 1 else 0
        price_cv = price_std / statistics.mean(prices) if statistics.mean(prices) > 0 else 0

        # Discount depth
        discounted = [i for i in items if i.get("original_price", 0) > 0 and i["price"] > 0]
        avg_discount_depth = 0
        max_discount = 0
        if discounted:
            discounts = [(i["original_price"] - i["price"]) / i["original_price"] * 100 for i in discounted]
            avg_discount_depth = sum(discounts) / len(discounts)
            max_discount = max(discounts)

        # Free shipping correlation with price
        free_ship_prices = [i["price"] for i in items if i["free_shipping"] and i["price"] > 0]
        paid_ship_prices = [i["price"] for i in items if not i["free_shipping"] and i["price"] > 0]
        free_ship_avg = sum(free_ship_prices) / len(free_ship_prices) if free_ship_prices else 0
        paid_ship_avg = sum(paid_ship_prices) / len(paid_ship_prices) if paid_ship_prices else 0

        # Market maturity signals
        has_branded = sum(1 for i in items if i.get("brand")) / total if total > 0 else 0
        has_free_ship = sum(1 for i in items if i["free_shipping"]) / total if total > 0 else 0

        maturity = "MADURO" if (has_branded > 0.5 and has_free_ship > 0.7) else \
                   "EN CRECIMIENTO" if has_branded > 0.3 else "EMERGENTE"

        return {
            "total_items": total,
            "unique_brands": len(brand_counts),
            "brand_concentration_hhi": round(hhi, 3),
            "top_brand": max(brand_counts, key=brand_counts.get),
            "top_brand_share_pct": round(top_brand_share * 100, 1),
            "price_std_dev": round(price_std),
            "price_coefficient_variation": round(price_cv, 2),
            "avg_discount_depth_pct": round(avg_discount_depth, 1),
            "max_discount_pct": round(max_discount, 1),
            "free_shipping_avg_price": round(free_ship_avg),
            "paid_shipping_avg_price": round(paid_ship_avg),
            "market_maturity": maturity,
            "branded_ratio": round(has_branded * 100, 1),
            "free_shipping_ratio": round(has_free_ship * 100, 1),
        }

    def price_elasticity_map(self, analysis, landed_cost_usd):
        """Mapear elasticidad de precio — cuánto margen hay en cada segmento.

        Cruza: precios x segmentos x costo landed
        """
        landed_ars = landed_cost_usd * self.exchange_rate
        commission = self.ml_commission / 100

        segments = analysis.get("segments", {})
        elasticity = {}

        for seg_name, seg in segments.items():
            seg_range = seg.get("range", "")
            count = seg.get("count", 0)

            # Parse price from range string
            prices_in_seg = []
            for item in seg.get("items", []):
                if isinstance(item, dict) and "price" in item:
                    prices_in_seg.append(item["price"])

            if not prices_in_seg:
                continue

            avg_seg_price = sum(prices_in_seg) / len(prices_in_seg)
            net_price = avg_seg_price * (1 - commission)
            margin = (net_price - landed_ars) / net_price * 100 if net_price > 0 else 0

            elasticity[seg_name] = {
                "avg_price": round(avg_seg_price),
                "items_count": count,
                "net_after_commission": round(net_price),
                "margin_pct": round(margin, 1),
                "profit_per_unit_ars": round(net_price - landed_ars),
                "viable": margin >= 25,
                "attractiveness": "ALTA" if margin >= 40 else "MEDIA" if margin >= 25 else "BAJA",
            }

        return elasticity

    def seasonal_opportunity_score(self, query, landed_cost_usd, ml_analysis):
        """Cruzar estacionalidad con margen para timing de importación.

        Cruza: Google Trends x precios ML x costos
        """
        trends_df = get_trends([query.split()[0]], months=12)
        if trends_df is None:
            return {"available": False, "note": "Google Trends no disponible"}

        projection = seasonal_projection(trends_df, forecast_days=90)
        related = get_related_queries(query.split()[0])

        landed_ars = landed_cost_usd * self.exchange_rate
        median_price = ml_analysis.get("price_median", 0)
        commission = self.ml_commission / 100
        net_price = median_price * (1 - commission)
        base_margin = (net_price - landed_ars) / net_price * 100 if net_price > 0 else 0

        seasonal_data = {}
        for keyword, trend_data in projection.items():
            factor = trend_data.get("seasonal_factor", 1.0)
            # Higher demand = potential for higher prices
            adjusted_margin = base_margin * (1 + (factor - 1) * 0.3)  # 30% price sensitivity
            seasonal_data[keyword] = {
                "current_interest": trend_data.get("current_interest", 0),
                "projected_interest": trend_data.get("projected_interest", 0),
                "seasonal_factor": factor,
                "trend_direction": trend_data.get("trend", "stable"),
                "target_period": trend_data.get("target_period", ""),
                "base_margin_pct": round(base_margin, 1),
                "seasonally_adjusted_margin_pct": round(adjusted_margin, 1),
                "import_timing": "OPTIMO" if factor > 1.2 else
                                "BUENO" if factor > 1.0 else
                                "ESPERAR" if factor < 0.8 else "NEUTRAL",
            }

        return {
            "available": True,
            "seasonal_analysis": seasonal_data,
            "related_queries": related,
            "recommendation": self._timing_recommendation(seasonal_data),
        }

    def _timing_recommendation(self, seasonal_data):
        """Generar recomendación de timing basada en estacionalidad."""
        if not seasonal_data:
            return "Sin datos suficientes"

        avg_factor = sum(d["seasonal_factor"] for d in seasonal_data.values()) / len(seasonal_data)
        if avg_factor > 1.2:
            return "IMPORTAR AHORA — demanda creciente, buen momento para stockear"
        elif avg_factor > 1.0:
            return "BUEN MOMENTO — demanda estable o levemente creciente"
        elif avg_factor > 0.8:
            return "ESPERAR SI ES POSIBLE — demanda en baja estacional"
        else:
            return "NO IMPORTAR — temporada baja, riesgo de stock parado"

    def competitive_landscape(self, ml_analysis, competitor_reports=None):
        """Mapear paisaje competitivo cruzando ML con presencia digital.

        Cruza: marcas ML x competidores auditados x presencia digital
        """
        landscape = {
            "ml_brands": {},
            "digital_leaders": [],
            "gaps": [],
            "competitive_intensity": "BAJA",
        }

        # ML brand analysis
        top_brands = ml_analysis.get("top_brands", [])
        total_items = ml_analysis.get("total_items", 1)

        for brand, count in top_brands:
            landscape["ml_brands"][brand] = {
                "ml_listings": count,
                "ml_share_pct": round(count / total_items * 100, 1),
                "digital_presence": None,
            }

        # Cross with competitor audits if available
        if competitor_reports:
            for report in competitor_reports:
                name = report.get("competitor", "")
                summary = report.get("summary", {})
                score = summary.get("digital_presence_score", 0)
                channels = summary.get("channels_active", [])

                landscape["digital_leaders"].append({
                    "name": name,
                    "digital_score": score,
                    "channels": channels,
                    "strengths": summary.get("strengths", [])[:3],
                })

                # Try to match competitor to ML brand
                for brand_name in landscape["ml_brands"]:
                    if brand_name.lower() in name.lower() or name.lower() in brand_name.lower():
                        landscape["ml_brands"][brand_name]["digital_presence"] = score

            landscape["digital_leaders"].sort(key=lambda x: x["digital_score"], reverse=True)

            # Find gaps (brands with ML presence but weak digital)
            for brand, data in landscape["ml_brands"].items():
                if data["ml_share_pct"] >= 5 and (data["digital_presence"] is None or data["digital_presence"] < 40):
                    landscape["gaps"].append({
                        "brand": brand,
                        "ml_share": data["ml_share_pct"],
                        "digital_score": data["digital_presence"],
                        "opportunity": "Marca con presencia ML pero débil digital — posible target"
                    })

        # Competitive intensity
        n_brands = len(top_brands)
        if n_brands >= 8 and ml_analysis.get("total_items", 0) > 100:
            landscape["competitive_intensity"] = "ALTA"
        elif n_brands >= 4:
            landscape["competitive_intensity"] = "MEDIA"

        return landscape

    def opportunity_matrix(self, categories_data):
        """Generar matriz de oportunidad para múltiples categorías.

        Cruza: margen x tamaño mercado x estacionalidad x competencia
        Input: list of dicts with keys: query, margin, market_size, brand_count,
               seasonal_factor, competitive_intensity
        """
        if not categories_data:
            return []

        matrix = []
        for cat in categories_data:
            # Composite score (0-100)
            margin_score = min(cat.get("margin", 0) / 60 * 100, 100)  # 60% margin = max
            size_score = min(cat.get("market_size", 0) / 200 * 100, 100)  # 200 items = max
            seasonal_score = min(cat.get("seasonal_factor", 1.0) / 1.5 * 100, 100)

            # Low competition = high score
            intensity = cat.get("competitive_intensity", "MEDIA")
            competition_score = {"BAJA": 100, "MEDIA": 60, "ALTA": 30}.get(intensity, 50)

            composite = (
                margin_score * 0.35 +
                size_score * 0.25 +
                seasonal_score * 0.20 +
                competition_score * 0.20
            )

            quadrant = self._classify_quadrant(margin_score, size_score)

            matrix.append({
                "category": cat.get("query", "?"),
                "margin_pct": cat.get("margin", 0),
                "market_size": cat.get("market_size", 0),
                "seasonal_factor": cat.get("seasonal_factor", 1.0),
                "competitive_intensity": intensity,
                "margin_score": round(margin_score, 1),
                "size_score": round(size_score, 1),
                "seasonal_score": round(seasonal_score, 1),
                "competition_score": round(competition_score, 1),
                "composite_score": round(composite, 1),
                "quadrant": quadrant,
            })

        matrix.sort(key=lambda x: x["composite_score"], reverse=True)
        return matrix

    def _classify_quadrant(self, margin_score, size_score):
        """Clasificar en cuadrante estratégico."""
        high_margin = margin_score >= 50
        high_size = size_score >= 50
        if high_margin and high_size:
            return "ESTRELLA"
        elif high_margin and not high_size:
            return "NICHO RENTABLE"
        elif not high_margin and high_size:
            return "VOLUMEN"
        else:
            return "DESCARTE"

    def full_cross_analysis(self, query, landed_cost_usd, ml_pages=2,
                            competitors=None):
        """Análisis cruzado completo — el reporte definitivo.

        Returns:
            dict con todas las dimensiones cruzadas
        """
        # 1. ML Scan
        items = self.scraper.search(query, pages=ml_pages)
        ml_analysis = self.scraper.analyze(items)

        # 2. Market depth
        depth = self.market_depth_analysis(items, ml_analysis)

        # 3. Price elasticity
        elasticity = self.price_elasticity_map(ml_analysis, landed_cost_usd)

        # 4. Cost breakdown
        costs = self.analyzer.calculate_landed_cost(landed_cost_usd * 0.7)  # Estimate FOB from landed
        opportunity = self.analyzer.opportunity_analysis(ml_analysis, landed_cost_usd, self.ml_commission)

        # 5. Seasonal timing
        seasonal = self.seasonal_opportunity_score(query, landed_cost_usd, ml_analysis)

        # 6. Competitive landscape
        competitor_reports = []
        if competitors:
            from .skills import SkillsAudit
            audit = SkillsAudit(exchange_rate=self.exchange_rate)
            for comp in competitors:
                report = audit.full_competitor_audit(**comp)
                competitor_reports.append(report)

        landscape = self.competitive_landscape(ml_analysis, competitor_reports)

        # 7. Final verdict
        verdict = self._generate_verdict(opportunity, depth, seasonal, landscape)

        report = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "exchange_rate": self.exchange_rate,
            "ml_commission_pct": self.ml_commission,
            "landed_cost_usd": landed_cost_usd,
            "market_overview": ml_analysis,
            "market_depth": depth,
            "price_elasticity": elasticity,
            "cost_analysis": costs,
            "opportunity": opportunity,
            "seasonal": seasonal,
            "competitive_landscape": landscape,
            "competitor_reports": competitor_reports,
            "verdict": verdict,
        }

        # Save
        self._save(report, f"cross_analysis_{query.replace(' ', '_')}")
        return report

    def _generate_verdict(self, opportunity, depth, seasonal, landscape):
        """Generar veredicto final cruzando todas las variables."""
        scores = {}

        # Margin score (0-25)
        margin = opportunity.get("margin_at_median", 0)
        if margin >= 40:
            scores["margin"] = 25
        elif margin >= 25:
            scores["margin"] = 18
        elif margin >= 15:
            scores["margin"] = 10
        else:
            scores["margin"] = 3

        # Market score (0-25)
        maturity = depth.get("market_maturity", "EMERGENTE")
        brands = depth.get("unique_brands", 0)
        if maturity == "EN CRECIMIENTO" and brands < 8:
            scores["market"] = 25
        elif maturity == "EMERGENTE":
            scores["market"] = 20
        elif maturity == "MADURO" and brands < 5:
            scores["market"] = 15
        else:
            scores["market"] = 8

        # Seasonal score (0-25)
        seasonal_data = seasonal.get("seasonal_analysis", {})
        if seasonal_data:
            avg_factor = sum(d["seasonal_factor"] for d in seasonal_data.values()) / len(seasonal_data)
            if avg_factor > 1.2:
                scores["seasonal"] = 25
            elif avg_factor > 1.0:
                scores["seasonal"] = 18
            elif avg_factor > 0.8:
                scores["seasonal"] = 10
            else:
                scores["seasonal"] = 5
        else:
            scores["seasonal"] = 12  # Neutral if no data

        # Competition score (0-25)
        intensity = landscape.get("competitive_intensity", "MEDIA")
        gaps = len(landscape.get("gaps", []))
        if intensity == "BAJA":
            scores["competition"] = 25
        elif intensity == "MEDIA" and gaps > 0:
            scores["competition"] = 18
        elif intensity == "MEDIA":
            scores["competition"] = 12
        else:
            scores["competition"] = 5

        total = sum(scores.values())

        if total >= 80:
            verdict = "OPORTUNIDAD EXCEPCIONAL"
            action = "Importar ya, alta prioridad"
        elif total >= 60:
            verdict = "OPORTUNIDAD FUERTE"
            action = "Importar, prioridad media-alta"
        elif total >= 45:
            verdict = "VIABLE CON PRECAUCIONES"
            action = "Evaluar volumen mínimo y timing"
        elif total >= 30:
            verdict = "MARGINAL"
            action = "Solo si hay ventaja logística o de canal"
        else:
            verdict = "NO RECOMENDADO"
            action = "Buscar otra categoría"

        return {
            "total_score": total,
            "max_score": 100,
            "verdict": verdict,
            "action": action,
            "breakdown": scores,
            "positioning": opportunity.get("positioning", ""),
        }

    def _save(self, data, label):
        """Guardar reporte cruzado."""
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        path = os.path.join(DATA_DIR, f"{label}_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return path

    def load_historical(self, query_filter=None, limit=20):
        """Cargar análisis cruzados previos para comparación temporal."""
        files = sorted(
            [f for f in os.listdir(DATA_DIR) if f.startswith("cross_analysis_")],
            reverse=True,
        )
        if query_filter:
            slug = query_filter.replace(" ", "_").lower()
            files = [f for f in files if slug in f.lower()]

        results = []
        for f in files[:limit]:
            try:
                with open(os.path.join(DATA_DIR, f)) as fh:
                    data = json.load(fh)
                    results.append(data)
            except Exception:
                continue
        return results

    def trend_over_time(self, query_filter=None):
        """Comparar evolución de métricas entre scans previos."""
        historical = self.load_historical(query_filter)
        if len(historical) < 2:
            return None

        evolution = []
        for h in historical:
            opp = h.get("opportunity", {})
            depth = h.get("market_depth", {})
            verdict = h.get("verdict", {})
            evolution.append({
                "timestamp": h.get("timestamp", ""),
                "query": h.get("query", ""),
                "exchange_rate": h.get("exchange_rate", 0),
                "median_price": h.get("market_overview", {}).get("price_median", 0),
                "margin_pct": opp.get("margin_at_median", 0),
                "total_items": depth.get("total_items", 0),
                "unique_brands": depth.get("unique_brands", 0),
                "composite_score": verdict.get("total_score", 0),
            })

        return evolution
