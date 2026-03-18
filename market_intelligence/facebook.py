"""
Auditoría de presencia en Facebook para competidores.

Extrae datos públicos de páginas de Facebook sin necesidad de API key.
Analiza presencia, actividad y engagement desde la información pública.

Uso:
    from market_intelligence.facebook import FacebookAuditor
    auditor = FacebookAuditor()
    result = auditor.audit_page("samsonite.argentina")
    results = auditor.audit_competitors(["samsonite.argentina", "delsey.ar"])
"""

import requests
import re
import json
import time
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class FacebookAuditor:
    """Auditoría de páginas públicas de Facebook."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
        })
        os.makedirs(DATA_DIR, exist_ok=True)

    def audit_page(self, page_id):
        """
        Auditar una página pública de Facebook.

        Args:
            page_id: nombre o ID de la página FB (ej: "samsonite.argentina")

        Returns:
            dict con métricas de la página o error
        """
        page_id = page_id.strip().strip("/")
        page_url = f"https://www.facebook.com/{page_id}/"

        result = {
            "page_id": page_id,
            "url": page_url,
            "timestamp": datetime.now().isoformat(),
            "accessible": False,
            "page_name": None,
            "likes": None,
            "followers": None,
            "category": None,
            "description": None,
            "website": None,
            "phone": None,
            "email": None,
            "address": None,
            "rating": None,
            "is_verified": None,
            "has_shop": None,
            "has_messenger": None,
            "error": None,
        }

        try:
            r = self.session.get(page_url, timeout=15, allow_redirects=True)

            if r.status_code == 404:
                result["error"] = "Página no encontrada"
                return result

            if r.status_code != 200:
                result["error"] = f"HTTP {r.status_code}"
                return result

            result["accessible"] = True
            html = r.text

            # Extraer datos de meta tags
            meta_data = self._extract_meta(html)
            result.update(meta_data)

            # Extraer datos adicionales del HTML
            page_data = self._extract_page_data(html)
            result.update(page_data)

        except requests.exceptions.ConnectionError:
            result["error"] = "No se pudo conectar a Facebook"
        except requests.exceptions.Timeout:
            result["error"] = "Timeout al conectar"
        except Exception as e:
            result["error"] = str(e)

        return result

    def _extract_meta(self, html):
        """Extraer datos de meta tags de Facebook."""
        data = {}

        # og:title - nombre de la página
        title_m = re.search(
            r'<meta\s+(?:property|name)="og:title"\s+content="([^"]+)"',
            html, re.IGNORECASE
        )
        if not title_m:
            title_m = re.search(
                r'content="([^"]+)"\s+(?:property|name)="og:title"',
                html, re.IGNORECASE
            )
        if title_m:
            data["page_name"] = title_m.group(1).strip()

        # og:description
        desc_m = re.search(
            r'<meta\s+(?:property|name)="og:description"\s+content="([^"]+)"',
            html, re.IGNORECASE
        )
        if not desc_m:
            desc_m = re.search(
                r'content="([^"]+)"\s+(?:property|name)="og:description"',
                html, re.IGNORECASE
            )
        if desc_m:
            desc = desc_m.group(1)
            data["description"] = desc

            # Intentar extraer likes del description
            likes_m = re.search(r'([\d,.]+[KkMm]?)\s*(?:likes?|me gusta)', desc)
            if likes_m:
                data["likes"] = self._parse_count(likes_m.group(1))

            followers_m = re.search(r'([\d,.]+[KkMm]?)\s*(?:followers?|seguidores)', desc)
            if followers_m:
                data["followers"] = self._parse_count(followers_m.group(1))

        return data

    def _extract_page_data(self, html):
        """Extraer datos adicionales del HTML de la página."""
        data = {}

        # Likes count
        likes_patterns = [
            r'"page_likers":\{"global_likers_count":(\d+)',
            r'"likeCount":(\d+)',
            r'([\d,.]+)\s*(?:personas indicaron que les gusta|people like this)',
            r'([\d,.]+)\s*(?:me gusta|likes)',
        ]
        for pattern in likes_patterns:
            m = re.search(pattern, html)
            if m:
                data["likes"] = self._parse_count(m.group(1))
                break

        # Followers count
        followers_patterns = [
            r'"follower_count":(\d+)',
            r'"followCount":(\d+)',
            r'([\d,.]+)\s*(?:personas siguen esto|people follow this)',
            r'([\d,.]+)\s*(?:seguidores|followers)',
        ]
        for pattern in followers_patterns:
            m = re.search(pattern, html)
            if m:
                data["followers"] = self._parse_count(m.group(1))
                break

        # Categoría
        cat_m = re.search(r'"category(?:_name)?"\s*:\s*"([^"]+)"', html)
        if cat_m:
            data["category"] = cat_m.group(1)

        # Rating
        rating_m = re.search(r'"overall_star_rating"\s*:\s*([\d.]+)', html)
        if rating_m:
            try:
                data["rating"] = float(rating_m.group(1))
            except ValueError:
                pass

        # Website
        website_m = re.search(r'"website"\s*:\s*"(https?://[^"]+)"', html)
        if website_m:
            data["website"] = website_m.group(1)

        # Verificación
        if '"is_verified":true' in html or '"isVerified":true' in html:
            data["is_verified"] = True
        elif '"is_verified":false' in html:
            data["is_verified"] = False

        # Shop / Tienda
        data["has_shop"] = "shop" in html.lower() or "tienda" in html.lower()

        # Messenger
        data["has_messenger"] = "m.me/" in html or "messenger" in html.lower()

        return data

    def _parse_count(self, text):
        """Convertir '12.3K' o '1,234' a entero."""
        if isinstance(text, int):
            return text
        text = str(text).strip().replace(",", "").replace(".", "")
        multiplier = 1
        if text.upper().endswith("K"):
            multiplier = 1000
            text = text[:-1]
        elif text.upper().endswith("M"):
            multiplier = 1_000_000
            text = text[:-1]
        try:
            return int(float(text) * multiplier)
        except ValueError:
            return None

    def audit_competitors(self, page_ids, delay=3):
        """
        Auditar múltiples páginas de Facebook.

        Args:
            page_ids: lista de page IDs o nombres
            delay: segundos entre requests

        Returns:
            lista de resultados
        """
        results = []
        for i, page_id in enumerate(page_ids):
            result = self.audit_page(page_id)
            results.append(result)
            if i < len(page_ids) - 1:
                time.sleep(delay)
        return results

    def compare_pages(self, results):
        """
        Generar comparativa de páginas auditadas.

        Args:
            results: lista de dicts de audit_page

        Returns:
            dict con ranking y métricas
        """
        valid = [r for r in results if r.get("accessible")]

        if not valid:
            return {"error": "No se pudieron obtener datos de ninguna página"}

        # Ordenar por followers (o likes si no hay followers)
        valid.sort(
            key=lambda x: x.get("followers") or x.get("likes") or 0,
            reverse=True
        )

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "pages_checked": len(results),
            "pages_accessible": len(valid),
            "ranking": [],
        }

        for i, r in enumerate(valid, 1):
            comparison["ranking"].append({
                "rank": i,
                "page_id": r["page_id"],
                "page_name": r.get("page_name"),
                "followers": r.get("followers"),
                "likes": r.get("likes"),
                "category": r.get("category"),
                "rating": r.get("rating"),
                "is_verified": r.get("is_verified"),
                "has_shop": r.get("has_shop"),
                "has_website": bool(r.get("website")),
            })

        return comparison

    def save_audit(self, results, label="facebook_audit"):
        """Guardar resultados a JSON."""
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        path = os.path.join(DATA_DIR, f"{label}_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        return path
