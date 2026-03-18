"""
Auditoría de presencia en Instagram para competidores.

Extrae datos públicos de perfiles de Instagram sin necesidad de API key.
Usa web scraping de perfiles públicos para obtener métricas básicas.

Uso:
    from market_intelligence.instagram import InstagramAuditor
    auditor = InstagramAuditor()
    result = auditor.audit_profile("calzalindo_ok")
    results = auditor.audit_competitors(["samsonite_ar", "delsey_ar"])
"""

import requests
import re
import json
import time
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class InstagramAuditor:
    """Auditoría de perfiles públicos de Instagram."""

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

    def audit_profile(self, username):
        """
        Auditar un perfil público de Instagram.

        Args:
            username: nombre de usuario IG (sin @)

        Returns:
            dict con métricas del perfil o error
        """
        username = username.lstrip("@").strip()
        profile_url = f"https://www.instagram.com/{username}/"

        result = {
            "username": username,
            "url": profile_url,
            "timestamp": datetime.now().isoformat(),
            "accessible": False,
            "followers": None,
            "following": None,
            "posts_count": None,
            "bio": None,
            "full_name": None,
            "is_business": None,
            "is_verified": None,
            "external_url": None,
            "profile_pic_url": None,
            "error": None,
        }

        try:
            r = self.session.get(profile_url, timeout=15, allow_redirects=True)

            if r.status_code == 404:
                result["error"] = "Perfil no encontrado"
                return result

            if r.status_code != 200:
                result["error"] = f"HTTP {r.status_code}"
                return result

            # Instagram carga datos en JSON embebido en el HTML
            result["accessible"] = True
            html = r.text

            # Intentar extraer datos del meta tag og:description
            meta = self._extract_meta(html)
            if meta:
                result.update(meta)

            # Intentar extraer del JSON embebido
            json_data = self._extract_json_data(html)
            if json_data:
                result.update(json_data)

            # Extraer bio del meta description
            bio = self._extract_bio(html)
            if bio:
                result["bio"] = bio

        except requests.exceptions.ConnectionError:
            result["error"] = "No se pudo conectar a Instagram"
        except requests.exceptions.Timeout:
            result["error"] = "Timeout al conectar"
        except Exception as e:
            result["error"] = str(e)

        return result

    def _extract_meta(self, html):
        """Extraer métricas de las meta tags de Instagram."""
        data = {}

        # og:description suele tener: "X Followers, Y Following, Z Posts - ..."
        og_match = re.search(
            r'<meta\s+(?:property|name)="og:description"\s+content="([^"]+)"',
            html, re.IGNORECASE
        )
        if not og_match:
            og_match = re.search(
                r'content="([^"]+)"\s+(?:property|name)="og:description"',
                html, re.IGNORECASE
            )

        if og_match:
            desc = og_match.group(1)

            # Parse "123K Followers, 456 Following, 789 Posts"
            followers_m = re.search(r'([\d,.]+[KkMm]?)\s*Followers', desc)
            following_m = re.search(r'([\d,.]+[KkMm]?)\s*Following', desc)
            posts_m = re.search(r'([\d,.]+[KkMm]?)\s*Posts', desc)

            if followers_m:
                data["followers"] = self._parse_count(followers_m.group(1))
            if following_m:
                data["following"] = self._parse_count(following_m.group(1))
            if posts_m:
                data["posts_count"] = self._parse_count(posts_m.group(1))

            # Bio is after the dash
            bio_m = re.search(r'Posts\s*[-–—]\s*(.+)', desc)
            if bio_m:
                data["bio"] = bio_m.group(1).strip().strip('"')

        # og:title tiene el nombre completo
        title_match = re.search(
            r'<meta\s+(?:property|name)="og:title"\s+content="([^"]+)"',
            html, re.IGNORECASE
        )
        if not title_match:
            title_match = re.search(
                r'content="([^"]+)"\s+(?:property|name)="og:title"',
                html, re.IGNORECASE
            )
        if title_match:
            title = title_match.group(1)
            # Formato: "Nombre (@usuario) • Instagram photos and videos"
            name_m = re.match(r'(.+?)\s*\(@', title)
            if name_m:
                data["full_name"] = name_m.group(1).strip()

        return data

    def _extract_json_data(self, html):
        """Intentar extraer datos del JSON embebido en el HTML."""
        data = {}

        # Buscar SharedData en scripts
        shared_match = re.search(
            r'window\._sharedData\s*=\s*({.+?});</script>',
            html, re.DOTALL
        )
        if shared_match:
            try:
                shared = json.loads(shared_match.group(1))
                user = (shared.get("entry_data", {})
                        .get("ProfilePage", [{}])[0]
                        .get("graphql", {})
                        .get("user", {}))
                if user:
                    data["followers"] = user.get("edge_followed_by", {}).get("count")
                    data["following"] = user.get("edge_follow", {}).get("count")
                    data["posts_count"] = user.get("edge_owner_to_timeline_media", {}).get("count")
                    data["bio"] = user.get("biography")
                    data["full_name"] = user.get("full_name")
                    data["is_business"] = user.get("is_business_account")
                    data["is_verified"] = user.get("is_verified")
                    data["external_url"] = user.get("external_url")
                    data["profile_pic_url"] = user.get("profile_pic_url_hd")
            except (json.JSONDecodeError, IndexError, KeyError):
                pass

        # Buscar verificación
        if '"is_verified":true' in html:
            data["is_verified"] = True
        elif '"is_verified":false' in html:
            data["is_verified"] = False

        # Buscar cuenta business
        if '"is_business_account":true' in html:
            data["is_business"] = True

        return data

    def _extract_bio(self, html):
        """Extraer bio del meta description."""
        desc_match = re.search(
            r'<meta\s+name="description"\s+content="([^"]+)"',
            html, re.IGNORECASE
        )
        if not desc_match:
            desc_match = re.search(
                r'content="([^"]+)"\s+name="description"',
                html, re.IGNORECASE
            )
        if desc_match:
            desc = desc_match.group(1)
            # Formato: "X Followers ... - Bio text here"
            bio_m = re.search(r'Posts\s*[-–—]\s*(.+)', desc)
            if bio_m:
                return bio_m.group(1).strip().strip('"')
        return None

    def _parse_count(self, text):
        """Convertir '12.3K' o '1.5M' o '1,234' a número entero."""
        text = text.strip().replace(",", "")
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

    def audit_competitors(self, usernames, delay=3):
        """
        Auditar múltiples perfiles de Instagram.

        Args:
            usernames: lista de usernames
            delay: segundos entre requests (rate limiting)

        Returns:
            lista de resultados de auditoría
        """
        results = []
        for i, username in enumerate(usernames):
            result = self.audit_profile(username)
            results.append(result)
            if i < len(usernames) - 1:
                time.sleep(delay)
        return results

    def compare_profiles(self, results):
        """
        Generar tabla comparativa de perfiles auditados.

        Args:
            results: lista de dicts devueltos por audit_profile/audit_competitors

        Returns:
            dict con ranking y comparación
        """
        valid = [r for r in results if r.get("accessible") and r.get("followers") is not None]

        if not valid:
            return {"error": "No se pudieron obtener datos de ningún perfil"}

        # Ordenar por followers desc
        valid.sort(key=lambda x: x.get("followers", 0), reverse=True)

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "profiles_checked": len(results),
            "profiles_accessible": len(valid),
            "ranking": [],
        }

        for i, r in enumerate(valid, 1):
            comparison["ranking"].append({
                "rank": i,
                "username": r["username"],
                "followers": r["followers"],
                "following": r["following"],
                "posts": r["posts_count"],
                "is_business": r.get("is_business"),
                "is_verified": r.get("is_verified"),
                "has_website": bool(r.get("external_url")),
                "bio_length": len(r.get("bio", "") or ""),
            })

        # Estadísticas
        follower_counts = [r["followers"] for r in valid if r["followers"]]
        if follower_counts:
            comparison["stats"] = {
                "max_followers": max(follower_counts),
                "min_followers": min(follower_counts),
                "avg_followers": sum(follower_counts) // len(follower_counts),
                "total_reach": sum(follower_counts),
            }

        return comparison

    def save_audit(self, results, label="instagram_audit"):
        """Guardar resultados de auditoría a JSON."""
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        path = os.path.join(DATA_DIR, f"{label}_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        return path
