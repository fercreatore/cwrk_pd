"""
Auditoría técnica y SEO de sitios web de competidores.

Analiza SSL, velocidad de respuesta, meta tags SEO, mobile-friendliness,
redes sociales vinculadas, ecommerce y tecnologías detectadas.

Uso:
    from market_intelligence.website_audit import WebsiteAuditor
    auditor = WebsiteAuditor()
    result = auditor.audit("https://www.calzalindo.com.ar")
    results = auditor.audit_competitors(["calzalindo.com.ar", "samsonite.com.ar"])
"""

import requests
import re
import json
import time
import os
import ssl
import socket
from datetime import datetime
from urllib.parse import urlparse, urljoin

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class WebsiteAuditor:
    """Auditoría técnica y SEO de sitios web."""

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

    def audit(self, url):
        """
        Auditoría completa de un sitio web.

        Args:
            url: URL del sitio (con o sin https://)

        Returns:
            dict con todas las métricas de auditoría
        """
        url = self._normalize_url(url)
        parsed = urlparse(url)
        domain = parsed.netloc

        result = {
            "url": url,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "accessible": False,
            "ssl": {},
            "performance": {},
            "seo": {},
            "social_links": {},
            "ecommerce": {},
            "technologies": [],
            "score": 0,
            "issues": [],
            "error": None,
        }

        # 1. SSL Check
        result["ssl"] = self._check_ssl(domain)

        # 2. HTTP Response + Performance
        try:
            start = time.time()
            r = self.session.get(url, timeout=20, allow_redirects=True)
            elapsed = time.time() - start

            if r.status_code != 200:
                result["error"] = f"HTTP {r.status_code}"
                result["performance"]["status_code"] = r.status_code
                return result

            result["accessible"] = True
            result["performance"] = self._analyze_performance(r, elapsed)
            html = r.text

            # 3. SEO Analysis
            result["seo"] = self._analyze_seo(html, url)

            # 4. Social Media Links
            result["social_links"] = self._find_social_links(html)

            # 5. Ecommerce Features
            result["ecommerce"] = self._detect_ecommerce(html, url)

            # 6. Technologies
            result["technologies"] = self._detect_technologies(html, r.headers)

            # 7. Mobile check
            result["mobile"] = self._check_mobile(html)

            # 8. Calculate score
            result["score"], result["issues"] = self._calculate_score(result)

        except requests.exceptions.ConnectionError:
            result["error"] = "No se pudo conectar al sitio"
        except requests.exceptions.Timeout:
            result["error"] = "Timeout (>20s)"
        except Exception as e:
            result["error"] = str(e)

        return result

    def _normalize_url(self, url):
        """Normalizar URL agregando https:// si falta."""
        url = url.strip().rstrip("/")
        if not url.startswith("http"):
            url = "https://" + url
        return url

    def _check_ssl(self, domain):
        """Verificar certificado SSL."""
        result = {
            "has_ssl": False,
            "valid": False,
            "issuer": None,
            "expires": None,
            "error": None,
        }
        try:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
                s.settimeout(10)
                s.connect((domain, 443))
                cert = s.getpeercert()
                result["has_ssl"] = True
                result["valid"] = True

                # Issuer
                issuer_parts = dict(x[0] for x in cert.get("issuer", []))
                result["issuer"] = issuer_parts.get("organizationName", "Unknown")

                # Expiry
                not_after = cert.get("notAfter")
                if not_after:
                    result["expires"] = not_after

        except ssl.SSLCertVerificationError as e:
            result["has_ssl"] = True
            result["valid"] = False
            result["error"] = str(e)
        except Exception as e:
            result["error"] = str(e)

        return result

    def _analyze_performance(self, response, elapsed):
        """Analizar performance de la respuesta HTTP."""
        return {
            "status_code": response.status_code,
            "response_time_ms": round(elapsed * 1000),
            "content_length_kb": round(len(response.content) / 1024, 1),
            "redirects": len(response.history),
            "final_url": response.url,
            "server": response.headers.get("Server", "Unknown"),
            "content_type": response.headers.get("Content-Type", ""),
            "has_gzip": "gzip" in response.headers.get("Content-Encoding", ""),
            "has_cache": bool(response.headers.get("Cache-Control")),
        }

    def _analyze_seo(self, html, url):
        """Análisis SEO básico del HTML."""
        seo = {
            "title": None,
            "title_length": 0,
            "meta_description": None,
            "meta_description_length": 0,
            "h1_count": 0,
            "h1_texts": [],
            "h2_count": 0,
            "has_canonical": False,
            "canonical_url": None,
            "has_robots_meta": False,
            "has_og_tags": False,
            "has_structured_data": False,
            "images_without_alt": 0,
            "total_images": 0,
            "internal_links": 0,
            "external_links": 0,
            "has_sitemap_link": False,
            "has_lang": False,
            "lang": None,
        }

        # Title
        title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_m:
            seo["title"] = title_m.group(1).strip()
            seo["title_length"] = len(seo["title"])

        # Meta description
        desc_m = re.search(
            r'<meta\s+name="description"\s+content="([^"]*)"',
            html, re.IGNORECASE
        )
        if not desc_m:
            desc_m = re.search(
                r'content="([^"]*)"\s+name="description"',
                html, re.IGNORECASE
            )
        if desc_m:
            seo["meta_description"] = desc_m.group(1)
            seo["meta_description_length"] = len(seo["meta_description"])

        # H1 tags
        h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
        seo["h1_count"] = len(h1_matches)
        seo["h1_texts"] = [re.sub(r'<[^>]+>', '', h).strip() for h in h1_matches[:5]]

        # H2 tags
        seo["h2_count"] = len(re.findall(r'<h2[^>]*>', html, re.IGNORECASE))

        # Canonical
        canon_m = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', html, re.IGNORECASE)
        if canon_m:
            seo["has_canonical"] = True
            seo["canonical_url"] = canon_m.group(1)

        # Robots meta
        seo["has_robots_meta"] = bool(re.search(r'<meta\s+name="robots"', html, re.IGNORECASE))

        # Open Graph
        seo["has_og_tags"] = bool(re.search(r'property="og:', html, re.IGNORECASE))

        # Structured data (JSON-LD)
        seo["has_structured_data"] = bool(
            re.search(r'application/ld\+json', html, re.IGNORECASE)
        )

        # Images
        images = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
        seo["total_images"] = len(images)
        seo["images_without_alt"] = sum(
            1 for img in images if 'alt=' not in img.lower() or 'alt=""' in img.lower()
        )

        # Links
        parsed = urlparse(url)
        links = re.findall(r'href="([^"]+)"', html)
        for link in links:
            if link.startswith("#") or link.startswith("javascript:"):
                continue
            link_parsed = urlparse(link)
            if link_parsed.netloc and link_parsed.netloc != parsed.netloc:
                seo["external_links"] += 1
            else:
                seo["internal_links"] += 1

        # Sitemap
        seo["has_sitemap_link"] = "sitemap" in html.lower()

        # Language
        lang_m = re.search(r'<html[^>]+lang="([^"]+)"', html, re.IGNORECASE)
        if lang_m:
            seo["has_lang"] = True
            seo["lang"] = lang_m.group(1)

        return seo

    def _find_social_links(self, html):
        """Encontrar links a redes sociales en el HTML."""
        social = {
            "instagram": None,
            "facebook": None,
            "twitter": None,
            "youtube": None,
            "tiktok": None,
            "linkedin": None,
            "whatsapp": None,
            "pinterest": None,
        }

        patterns = {
            "instagram": r'href="(https?://(?:www\.)?instagram\.com/[^"]+)"',
            "facebook": r'href="(https?://(?:www\.)?facebook\.com/[^"]+)"',
            "twitter": r'href="(https?://(?:www\.)?(?:twitter|x)\.com/[^"]+)"',
            "youtube": r'href="(https?://(?:www\.)?youtube\.com/[^"]+)"',
            "tiktok": r'href="(https?://(?:www\.)?tiktok\.com/[^"]+)"',
            "linkedin": r'href="(https?://(?:www\.)?linkedin\.com/[^"]+)"',
            "whatsapp": r'href="(https?://(?:wa\.me|api\.whatsapp\.com)/[^"]+)"',
            "pinterest": r'href="(https?://(?:www\.)?pinterest\.com/[^"]+)"',
        }

        for network, pattern in patterns.items():
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                social[network] = m.group(1)

        return social

    def _detect_ecommerce(self, html, url):
        """Detectar features de ecommerce."""
        ecom = {
            "has_cart": False,
            "has_product_pages": False,
            "has_prices": False,
            "has_search": False,
            "has_login": False,
            "has_payment_methods": False,
            "payment_methods": [],
            "platform": None,
        }

        html_lower = html.lower()

        # Cart / Carrito
        ecom["has_cart"] = any(kw in html_lower for kw in [
            "carrito", "cart", "checkout", "agregar al carrito", "add to cart",
            "shopping-cart", "shopping_cart",
        ])

        # Products
        ecom["has_product_pages"] = any(kw in html_lower for kw in [
            "/product", "/producto", "product-card", "product_card",
            "data-product", "product-item",
        ])

        # Prices
        ecom["has_prices"] = bool(re.search(r'\$[\d.,]+', html))

        # Search
        ecom["has_search"] = any(kw in html_lower for kw in [
            'type="search"', "buscador", "search-input", "search_input",
            'name="q"', 'name="search"',
        ])

        # Login
        ecom["has_login"] = any(kw in html_lower for kw in [
            "iniciar sesión", "login", "mi cuenta", "sign in", "registrarse",
        ])

        # Payment methods
        payments = {
            "mercadopago": ["mercadopago", "mercado pago", "mp-"],
            "visa": ["visa"],
            "mastercard": ["mastercard"],
            "amex": ["american express", "amex"],
            "naranja": ["naranja"],
            "transferencia": ["transferencia", "wire transfer"],
            "efectivo": ["efectivo", "cash"],
        }
        for method, keywords in payments.items():
            if any(kw in html_lower for kw in keywords):
                ecom["payment_methods"].append(method)
        ecom["has_payment_methods"] = len(ecom["payment_methods"]) > 0

        # Platform detection
        platforms = {
            "Tiendanube": ["tiendanube", "nuvemshop", "//d26lpennugtm8s"],
            "Shopify": ["shopify", "cdn.shopify"],
            "WooCommerce": ["woocommerce", "wp-content/plugins/woocommerce"],
            "Magento": ["magento", "mage/"],
            "PrestaShop": ["prestashop", "presta"],
            "VTEX": ["vtex", "vteximg"],
            "Empretienda": ["empretienda"],
            "MercadoShops": ["mercadoshops"],
        }
        for platform, keywords in platforms.items():
            if any(kw in html_lower for kw in keywords):
                ecom["platform"] = platform
                break

        return ecom

    def _detect_technologies(self, html, headers):
        """Detectar tecnologías usadas en el sitio."""
        techs = []
        html_lower = html.lower()

        detections = {
            "Google Analytics": ["google-analytics", "gtag(", "ga('", "googletagmanager"],
            "Google Tag Manager": ["googletagmanager.com/gtm"],
            "Facebook Pixel": ["fbq(", "facebook.com/tr", "facebook-domain-verification"],
            "jQuery": ["jquery"],
            "Bootstrap": ["bootstrap"],
            "React": ["react", "__next"],
            "Vue.js": ["vue.js", "vue.min.js", "__vue__"],
            "WordPress": ["wp-content", "wordpress"],
            "Font Awesome": ["font-awesome", "fontawesome"],
            "Google Fonts": ["fonts.googleapis.com"],
            "reCAPTCHA": ["recaptcha", "grecaptcha"],
            "Hotjar": ["hotjar"],
            "Crisp": ["crisp.chat"],
            "Tawk.to": ["tawk.to"],
            "WhatsApp Widget": ["wa.me", "whatsapp-widget", "btn-whatsapp"],
            "MercadoPago SDK": ["mercadopago", "sdk.mercadopago"],
            "Cloudflare": ["cloudflare"],
        }

        for tech, keywords in detections.items():
            if any(kw in html_lower for kw in keywords):
                techs.append(tech)

        # Server header
        server = headers.get("Server", "")
        if server and server not in techs:
            techs.append(f"Server: {server}")

        # X-Powered-By
        powered = headers.get("X-Powered-By", "")
        if powered:
            techs.append(f"Powered by: {powered}")

        return techs

    def _check_mobile(self, html):
        """Verificar señales de mobile-friendliness."""
        mobile = {
            "has_viewport": False,
            "has_responsive_meta": False,
            "has_media_queries": False,
        }

        # Viewport meta tag
        viewport_m = re.search(r'<meta[^>]+name="viewport"[^>]+>', html, re.IGNORECASE)
        if viewport_m:
            mobile["has_viewport"] = True
            if "width=device-width" in viewport_m.group(0).lower():
                mobile["has_responsive_meta"] = True

        # CSS media queries (inline)
        mobile["has_media_queries"] = bool(
            re.search(r'@media[^{]*\(.*width', html, re.IGNORECASE)
        )

        return mobile

    def _calculate_score(self, result):
        """Calcular score de 0-100 y listar issues."""
        score = 0
        issues = []

        # SSL (15 pts)
        if result["ssl"].get("valid"):
            score += 15
        elif result["ssl"].get("has_ssl"):
            score += 5
            issues.append("SSL: certificado inválido o expirado")
        else:
            issues.append("SSL: sin HTTPS")

        # Performance (15 pts)
        perf = result.get("performance", {})
        resp_time = perf.get("response_time_ms", 9999)
        if resp_time < 1000:
            score += 15
        elif resp_time < 3000:
            score += 10
            issues.append(f"Performance: respuesta lenta ({resp_time}ms)")
        else:
            score += 5
            issues.append(f"Performance: respuesta muy lenta ({resp_time}ms)")

        if perf.get("has_gzip"):
            score += 3
        else:
            issues.append("Performance: sin compresión gzip")

        # SEO (30 pts)
        seo = result.get("seo", {})
        if seo.get("title"):
            if 30 <= seo["title_length"] <= 60:
                score += 5
            else:
                score += 2
                issues.append(f"SEO: título longitud {seo['title_length']} (ideal 30-60)")
        else:
            issues.append("SEO: sin tag <title>")

        if seo.get("meta_description"):
            if 120 <= seo["meta_description_length"] <= 160:
                score += 5
            else:
                score += 2
                issues.append("SEO: meta description longitud subóptima")
        else:
            issues.append("SEO: sin meta description")

        if seo.get("h1_count") == 1:
            score += 5
        elif seo.get("h1_count", 0) > 1:
            score += 2
            issues.append(f"SEO: {seo['h1_count']} tags H1 (debería ser 1)")
        else:
            issues.append("SEO: sin tag H1")

        if seo.get("has_canonical"):
            score += 3
        else:
            issues.append("SEO: sin canonical URL")

        if seo.get("has_og_tags"):
            score += 3
        else:
            issues.append("SEO: sin Open Graph tags")

        if seo.get("has_structured_data"):
            score += 4
        else:
            issues.append("SEO: sin datos estructurados (JSON-LD)")

        if seo.get("has_lang"):
            score += 2
        else:
            issues.append("SEO: sin atributo lang en <html>")

        if seo.get("total_images", 0) > 0:
            alt_ratio = 1 - (seo["images_without_alt"] / seo["total_images"])
            if alt_ratio >= 0.9:
                score += 3
            else:
                issues.append(f"SEO: {seo['images_without_alt']}/{seo['total_images']} imágenes sin alt")

        # Mobile (10 pts)
        mobile = result.get("mobile", {})
        if mobile.get("has_responsive_meta"):
            score += 10
        elif mobile.get("has_viewport"):
            score += 5
            issues.append("Mobile: viewport sin width=device-width")
        else:
            issues.append("Mobile: sin meta viewport (no mobile-friendly)")

        # Social (10 pts)
        social = result.get("social_links", {})
        social_count = sum(1 for v in social.values() if v)
        if social_count >= 3:
            score += 10
        elif social_count >= 1:
            score += 5
            missing = [k for k, v in social.items() if not v and k in ["instagram", "facebook", "whatsapp"]]
            if missing:
                issues.append(f"Social: falta link a {', '.join(missing)}")
        else:
            issues.append("Social: sin links a redes sociales")

        # Ecommerce (12 pts)
        ecom = result.get("ecommerce", {})
        if ecom.get("has_cart"):
            score += 3
        if ecom.get("has_search"):
            score += 3
        if ecom.get("has_payment_methods"):
            score += 3
        if ecom.get("platform"):
            score += 3

        return min(score, 100), issues

    def audit_competitors(self, urls, delay=3):
        """
        Auditar múltiples sitios web.

        Args:
            urls: lista de URLs o dominios
            delay: segundos entre requests

        Returns:
            lista de resultados
        """
        results = []
        for i, url in enumerate(urls):
            result = self.audit(url)
            results.append(result)
            if i < len(urls) - 1:
                time.sleep(delay)
        return results

    def compare_sites(self, results):
        """
        Comparar sitios auditados.

        Returns:
            dict con ranking por score y comparativa
        """
        valid = [r for r in results if r.get("accessible")]

        if not valid:
            return {"error": "No se pudo acceder a ningún sitio"}

        valid.sort(key=lambda x: x.get("score", 0), reverse=True)

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "sites_checked": len(results),
            "sites_accessible": len(valid),
            "ranking": [],
        }

        for i, r in enumerate(valid, 1):
            social = r.get("social_links", {})
            ecom = r.get("ecommerce", {})
            comparison["ranking"].append({
                "rank": i,
                "domain": r["domain"],
                "score": r["score"],
                "response_ms": r.get("performance", {}).get("response_time_ms"),
                "has_ssl": r.get("ssl", {}).get("valid", False),
                "seo_title": bool(r.get("seo", {}).get("title")),
                "mobile_ready": r.get("mobile", {}).get("has_responsive_meta", False),
                "social_channels": sum(1 for v in social.values() if v),
                "ecommerce_platform": ecom.get("platform"),
                "issues_count": len(r.get("issues", [])),
            })

        return comparison

    def save_audit(self, results, label="website_audit"):
        """Guardar resultados a JSON."""
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        path = os.path.join(DATA_DIR, f"{label}_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        return path
