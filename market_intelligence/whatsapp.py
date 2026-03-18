"""
Checker de presencia WhatsApp Business para competidores.

Verifica si un número tiene WhatsApp Business, si tiene catálogo,
y analiza el link wa.me para determinar presencia comercial.

Uso:
    from market_intelligence.whatsapp import WhatsAppChecker
    checker = WhatsAppChecker()
    result = checker.check_number("+5493462123456")
    result = checker.check_wame_link("https://wa.me/5493462123456")
"""

import requests
import re
import json
import time
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class WhatsAppChecker:
    """Checker de presencia WhatsApp Business."""

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

    def check_number(self, phone_number, message=""):
        """
        Verificar presencia de WhatsApp Business para un número.

        Args:
            phone_number: número con código de país (ej: "+5493462123456" o "5493462123456")
            message: mensaje pre-cargado opcional

        Returns:
            dict con resultado del check
        """
        # Normalizar número
        clean_number = self._normalize_number(phone_number)
        wame_url = f"https://wa.me/{clean_number}"
        if message:
            wame_url += f"?text={requests.utils.quote(message)}"

        result = {
            "phone_number": phone_number,
            "clean_number": clean_number,
            "wa_me_url": wame_url,
            "timestamp": datetime.now().isoformat(),
            "wa_me_accessible": False,
            "has_whatsapp": None,
            "business_name": None,
            "business_description": None,
            "has_catalog": None,
            "catalog_url": None,
            "profile_pic": None,
            "error": None,
        }

        # Check wa.me link
        try:
            r = self.session.get(wame_url, timeout=15, allow_redirects=True)

            if r.status_code == 200:
                result["wa_me_accessible"] = True
                result["has_whatsapp"] = True
                html = r.text

                # Extraer datos del HTML de wa.me
                wa_data = self._extract_wame_data(html)
                result.update(wa_data)

            elif r.status_code == 404:
                result["has_whatsapp"] = False
                result["error"] = "Número no tiene WhatsApp"
            else:
                result["error"] = f"HTTP {r.status_code}"

        except requests.exceptions.ConnectionError:
            result["error"] = "No se pudo conectar a wa.me"
        except requests.exceptions.Timeout:
            result["error"] = "Timeout"
        except Exception as e:
            result["error"] = str(e)

        # Check catálogo de WhatsApp Business
        catalog_result = self._check_catalog(clean_number)
        result.update(catalog_result)

        return result

    def check_wame_link(self, url):
        """
        Verificar un link wa.me directamente.

        Args:
            url: URL completa wa.me (ej: "https://wa.me/5493462123456")

        Returns:
            dict con resultado
        """
        # Extraer número del link
        m = re.search(r'wa\.me/(\d+)', url)
        if not m:
            return {"error": "URL wa.me inválida", "url": url}
        return self.check_number(m.group(1))

    def _normalize_number(self, phone):
        """Normalizar número de teléfono a formato internacional sin +."""
        # Remover todo excepto dígitos
        clean = re.sub(r'[^\d]', '', phone)

        # Si empieza con 0, asumir Argentina y agregar 54
        if clean.startswith("0"):
            clean = "54" + clean[1:]

        # Si no empieza con código de país (menos de 10 dígitos), asumir AR
        if len(clean) < 10:
            clean = "549" + clean  # 54 = Argentina, 9 = celular

        return clean

    def _extract_wame_data(self, html):
        """Extraer datos disponibles del HTML de wa.me."""
        data = {}

        # og:title puede tener nombre del negocio
        title_m = re.search(
            r'<meta\s+property="og:title"\s+content="([^"]+)"',
            html, re.IGNORECASE
        )
        if not title_m:
            title_m = re.search(
                r'content="([^"]+)"\s+property="og:title"',
                html, re.IGNORECASE
            )
        if title_m:
            title = title_m.group(1)
            # Si no es genérico ("WhatsApp"), es un business name
            if "whatsapp" not in title.lower() or len(title) > 20:
                data["business_name"] = title

        # og:description
        desc_m = re.search(
            r'<meta\s+property="og:description"\s+content="([^"]+)"',
            html, re.IGNORECASE
        )
        if not desc_m:
            desc_m = re.search(
                r'content="([^"]+)"\s+property="og:description"',
                html, re.IGNORECASE
            )
        if desc_m:
            desc = desc_m.group(1)
            if "whatsapp" not in desc.lower():
                data["business_description"] = desc

        # Profile pic
        img_m = re.search(
            r'<meta\s+property="og:image"\s+content="([^"]+)"',
            html, re.IGNORECASE
        )
        if img_m:
            data["profile_pic"] = img_m.group(1)

        return data

    def _check_catalog(self, phone_number):
        """Verificar si tiene catálogo de WhatsApp Business."""
        catalog_url = f"https://wa.me/c/{phone_number}"
        result = {
            "has_catalog": False,
            "catalog_url": None,
        }

        try:
            r = self.session.get(catalog_url, timeout=10, allow_redirects=True)
            if r.status_code == 200 and "catalog" in r.text.lower():
                result["has_catalog"] = True
                result["catalog_url"] = catalog_url
        except Exception:
            pass

        return result

    def audit_competitors(self, phone_numbers, delay=2):
        """
        Auditar múltiples números de WhatsApp Business.

        Args:
            phone_numbers: lista de números o dicts con {name, phone}
            delay: segundos entre checks

        Returns:
            lista de resultados
        """
        results = []
        for i, item in enumerate(phone_numbers):
            if isinstance(item, dict):
                phone = item.get("phone", "")
                name = item.get("name", "")
            else:
                phone = item
                name = ""

            result = self.check_number(phone)
            if name:
                result["competitor_name"] = name

            results.append(result)
            if i < len(phone_numbers) - 1:
                time.sleep(delay)

        return results

    def compare_presence(self, results):
        """
        Comparar presencia de WhatsApp Business entre competidores.

        Returns:
            dict con resumen comparativo
        """
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "total_checked": len(results),
            "with_whatsapp": sum(1 for r in results if r.get("has_whatsapp")),
            "with_business": sum(1 for r in results if r.get("business_name")),
            "with_catalog": sum(1 for r in results if r.get("has_catalog")),
            "details": [],
        }

        for r in results:
            detail = {
                "name": r.get("competitor_name", r.get("clean_number", "?")),
                "phone": r.get("clean_number"),
                "has_whatsapp": r.get("has_whatsapp", False),
                "is_business": bool(r.get("business_name")),
                "business_name": r.get("business_name"),
                "has_catalog": r.get("has_catalog", False),
                "wa_me_url": r.get("wa_me_url"),
            }
            comparison["details"].append(detail)

        return comparison

    def save_audit(self, results, label="whatsapp_audit"):
        """Guardar resultados a JSON."""
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        path = os.path.join(DATA_DIR, f"{label}_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        return path
