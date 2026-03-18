"""
Skills Library — Auditoría unificada multicanal de competidores.

Combina todos los módulos de market_intelligence en un solo reporte:
- MercadoLibre (precios, marcas, segmentos)
- Instagram (followers, engagement, bio)
- Facebook (likes, followers, categoría)
- WhatsApp Business (presencia, catálogo)
- Website (SEO, SSL, performance, ecommerce)
- Google Trends (estacionalidad)

Uso:
    from market_intelligence.skills import SkillsAudit
    audit = SkillsAudit()

    # Auditoría completa de un competidor
    report = audit.full_competitor_audit(
        name="Samsonite AR",
        website="samsonite.com.ar",
        instagram="samsonite_ar",
        facebook="samsonite.argentina",
        whatsapp="5491112345678",
        ml_query="valijas samsonite",
    )

    # Comparar múltiples competidores
    competitors = [
        {"name": "Samsonite", "website": "samsonite.com.ar", "instagram": "samsonite_ar"},
        {"name": "Delsey", "website": "delsey.com.ar", "instagram": "delsey_ar"},
    ]
    comparison = audit.compare_competitors(competitors)
"""

import json
import os
import time
from datetime import datetime

from .ml_scraper import MLScraper
from .instagram import InstagramAuditor
from .facebook import FacebookAuditor
from .whatsapp import WhatsAppChecker
from .website_audit import WebsiteAuditor
from .analyzer import MarketAnalyzer

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class SkillsAudit:
    """Auditoría unificada multicanal de competidores."""

    def __init__(self, exchange_rate=None):
        self.ml_scraper = MLScraper()
        self.ig_auditor = InstagramAuditor()
        self.fb_auditor = FacebookAuditor()
        self.wa_checker = WhatsAppChecker()
        self.web_auditor = WebsiteAuditor()
        self.analyzer = MarketAnalyzer(exchange_rate=exchange_rate)
        os.makedirs(DATA_DIR, exist_ok=True)

    def full_competitor_audit(self, name, website=None, instagram=None,
                               facebook=None, whatsapp=None, ml_query=None,
                               delay=2):
        """
        Auditoría completa de un competidor en todos los canales disponibles.

        Args:
            name: nombre del competidor
            website: URL del sitio web
            instagram: usuario de Instagram (sin @)
            facebook: page ID de Facebook
            whatsapp: número de WhatsApp
            ml_query: búsqueda en MercadoLibre
            delay: segundos entre cada canal (rate limiting)

        Returns:
            dict con reporte completo multicanal
        """
        report = {
            "competitor": name,
            "timestamp": datetime.now().isoformat(),
            "channels": {},
            "summary": {},
        }

        # 1. Website
        if website:
            report["channels"]["website"] = self.web_auditor.audit(website)
            time.sleep(delay)

        # 2. Instagram
        if instagram:
            report["channels"]["instagram"] = self.ig_auditor.audit_profile(instagram)
            time.sleep(delay)

        # 3. Facebook
        if facebook:
            report["channels"]["facebook"] = self.fb_auditor.audit_page(facebook)
            time.sleep(delay)

        # 4. WhatsApp
        if whatsapp:
            report["channels"]["whatsapp"] = self.wa_checker.check_number(whatsapp)
            time.sleep(delay)

        # 5. MercadoLibre
        if ml_query:
            items = self.ml_scraper.search(ml_query, pages=1)
            analysis = self.ml_scraper.analyze(items)
            report["channels"]["mercadolibre"] = {
                "query": ml_query,
                "total_items": analysis.get("total_items", 0),
                "price_median": analysis.get("price_median", 0),
                "price_range": f"${analysis.get('price_min', 0):,} — ${analysis.get('price_max', 0):,}",
                "free_shipping_pct": analysis.get("free_shipping_pct", 0),
                "top_brands": analysis.get("top_brands", []),
            }

        # Generar summary
        report["summary"] = self._generate_summary(report)

        return report

    def _generate_summary(self, report):
        """Generar resumen ejecutivo del reporte."""
        channels = report["channels"]
        summary = {
            "competitor": report["competitor"],
            "channels_audited": len(channels),
            "digital_presence_score": 0,
            "channels_active": [],
            "channels_missing": [],
            "strengths": [],
            "weaknesses": [],
        }

        max_score = 0

        # Website
        if "website" in channels:
            max_score += 25
            web = channels["website"]
            if web.get("accessible"):
                score = min(web.get("score", 0) / 4, 25)  # Max 25 pts
                summary["digital_presence_score"] += score
                summary["channels_active"].append("website")
                if web.get("score", 0) >= 70:
                    summary["strengths"].append(f"Sitio web sólido (score {web['score']}/100)")
                else:
                    summary["weaknesses"].append(f"Sitio web mejorable (score {web['score']}/100)")
                    if web.get("issues"):
                        summary["weaknesses"].extend(web["issues"][:3])
            else:
                summary["channels_missing"].append("website")
                summary["weaknesses"].append("Sitio web inaccesible")
        else:
            summary["channels_missing"].append("website")

        # Instagram
        if "instagram" in channels:
            max_score += 25
            ig = channels["instagram"]
            if ig.get("accessible"):
                summary["channels_active"].append("instagram")
                followers = ig.get("followers", 0) or 0
                if followers >= 10000:
                    summary["digital_presence_score"] += 25
                    summary["strengths"].append(f"Instagram fuerte ({followers:,} followers)")
                elif followers >= 1000:
                    summary["digital_presence_score"] += 15
                    summary["strengths"].append(f"Instagram activo ({followers:,} followers)")
                else:
                    summary["digital_presence_score"] += 5
                    summary["weaknesses"].append(f"Instagram con poco alcance ({followers:,} followers)")
            else:
                summary["channels_missing"].append("instagram")
        else:
            summary["channels_missing"].append("instagram")

        # Facebook
        if "facebook" in channels:
            max_score += 25
            fb = channels["facebook"]
            if fb.get("accessible"):
                summary["channels_active"].append("facebook")
                followers = fb.get("followers") or fb.get("likes") or 0
                if followers >= 5000:
                    summary["digital_presence_score"] += 25
                    summary["strengths"].append(f"Facebook establecido ({followers:,} seguidores)")
                elif followers >= 500:
                    summary["digital_presence_score"] += 15
                else:
                    summary["digital_presence_score"] += 5
                    summary["weaknesses"].append("Facebook con poco alcance")
            else:
                summary["channels_missing"].append("facebook")
        else:
            summary["channels_missing"].append("facebook")

        # WhatsApp
        if "whatsapp" in channels:
            max_score += 15
            wa = channels["whatsapp"]
            if wa.get("has_whatsapp"):
                summary["channels_active"].append("whatsapp")
                if wa.get("business_name"):
                    summary["digital_presence_score"] += 15
                    summary["strengths"].append("WhatsApp Business activo")
                    if wa.get("has_catalog"):
                        summary["strengths"].append("Catálogo WhatsApp disponible")
                else:
                    summary["digital_presence_score"] += 8
            else:
                summary["channels_missing"].append("whatsapp")
                summary["weaknesses"].append("Sin WhatsApp Business")
        else:
            summary["channels_missing"].append("whatsapp")

        # MercadoLibre
        if "mercadolibre" in channels:
            max_score += 10
            ml = channels["mercadolibre"]
            if ml.get("total_items", 0) > 0:
                summary["channels_active"].append("mercadolibre")
                summary["digital_presence_score"] += 10
                summary["strengths"].append(
                    f"Presencia en ML ({ml['total_items']} items, mediana ${ml['price_median']:,})"
                )

        # Normalizar score a 100
        if max_score > 0:
            summary["digital_presence_score"] = round(
                summary["digital_presence_score"] / max_score * 100
            )

        return summary

    def compare_competitors(self, competitors, delay=3):
        """
        Comparar múltiples competidores en todos sus canales.

        Args:
            competitors: lista de dicts con keys: name, website, instagram,
                        facebook, whatsapp, ml_query (todos opcionales excepto name)
            delay: segundos entre competidores

        Returns:
            dict con comparativa y ranking
        """
        reports = []
        for i, comp in enumerate(competitors):
            name = comp.get("name", f"Competidor {i+1}")
            report = self.full_competitor_audit(
                name=name,
                website=comp.get("website"),
                instagram=comp.get("instagram"),
                facebook=comp.get("facebook"),
                whatsapp=comp.get("whatsapp"),
                ml_query=comp.get("ml_query"),
            )
            reports.append(report)
            if i < len(competitors) - 1:
                time.sleep(delay)

        # Ranking por digital presence score
        ranking = sorted(
            reports,
            key=lambda x: x.get("summary", {}).get("digital_presence_score", 0),
            reverse=True
        )

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "total_competitors": len(competitors),
            "ranking": [],
            "insights": [],
        }

        for i, r in enumerate(ranking, 1):
            s = r.get("summary", {})
            comparison["ranking"].append({
                "rank": i,
                "name": r["competitor"],
                "digital_score": s.get("digital_presence_score", 0),
                "channels_active": len(s.get("channels_active", [])),
                "channels_missing": s.get("channels_missing", []),
                "strengths": s.get("strengths", []),
                "weaknesses": s.get("weaknesses", []),
            })

        # Generate insights
        comparison["insights"] = self._generate_insights(ranking)

        # Save
        self.save_report(comparison, "competitor_comparison")

        return comparison

    def _generate_insights(self, ranked_reports):
        """Generar insights estratégicos de la comparación."""
        insights = []

        if not ranked_reports:
            return insights

        # Quién lidera
        leader = ranked_reports[0]
        leader_name = leader["competitor"]
        leader_score = leader.get("summary", {}).get("digital_presence_score", 0)
        insights.append(
            f"Líder digital: {leader_name} (score {leader_score}/100)"
        )

        # Canales más comunes
        all_active = []
        for r in ranked_reports:
            all_active.extend(r.get("summary", {}).get("channels_active", []))

        if all_active:
            from collections import Counter
            channel_counts = Counter(all_active)
            most_common = channel_counts.most_common(3)
            channels_str = ", ".join(f"{ch} ({ct}/{len(ranked_reports)})" for ch, ct in most_common)
            insights.append(f"Canales más usados: {channels_str}")

        # Oportunidades (canales donde pocos compiten)
        all_missing = []
        for r in ranked_reports:
            all_missing.extend(r.get("summary", {}).get("channels_missing", []))
        if all_missing:
            from collections import Counter
            missing_counts = Counter(all_missing)
            opportunities = [
                ch for ch, ct in missing_counts.most_common()
                if ct >= len(ranked_reports) // 2
            ]
            if opportunities:
                insights.append(
                    f"Oportunidad: pocos competidores en {', '.join(opportunities)}"
                )

        # Debilidades comunes
        all_weaknesses = []
        for r in ranked_reports:
            all_weaknesses.extend(r.get("summary", {}).get("weaknesses", []))
        if all_weaknesses:
            from collections import Counter
            common_weak = Counter(all_weaknesses).most_common(3)
            if common_weak:
                insights.append(
                    f"Debilidades comunes del sector: {common_weak[0][0]}"
                )

        return insights

    def save_report(self, data, label="skills_audit"):
        """Guardar reporte a JSON."""
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        path = os.path.join(DATA_DIR, f"{label}_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return path
