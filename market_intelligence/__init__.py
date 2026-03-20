# Market Intelligence - Cowork Pedidos
"""
Módulo de inteligencia de mercado para evaluar oportunidades de importación.

Componentes:
    - MLScraper: scraping de MercadoLibre Argentina
    - MarketAnalyzer: análisis de costos de importación y oportunidad
    - Trends: integración Google Trends (estacionalidad)
    - Instagram/Facebook/WhatsApp: auditoría de presencia en redes
    - WebsiteAudit: auditoría SEO y técnica de sitios web
    - SkillsAudit: auditoría unificada multicanal

Uso:
    from market_intelligence import MLScraper, MarketAnalyzer
    scraper = MLScraper()
    items = scraper.search("valijas de viaje")
"""

from .ml_scraper import MLScraper, import_opportunity_score
from .analyzer import MarketAnalyzer
from .trends import get_trends, seasonal_projection, get_related_queries
from .instagram import InstagramAuditor
from .facebook import FacebookAuditor
from .whatsapp import WhatsAppChecker
from .website_audit import WebsiteAuditor
from .skills import SkillsAudit
from .cross_analysis import CrossAnalyzer

__all__ = [
    "MLScraper",
    "MarketAnalyzer",
    "import_opportunity_score",
    "get_trends",
    "seasonal_projection",
    "get_related_queries",
    "InstagramAuditor",
    "FacebookAuditor",
    "WhatsAppChecker",
    "WebsiteAuditor",
    "SkillsAudit",
    "CrossAnalyzer",
]
