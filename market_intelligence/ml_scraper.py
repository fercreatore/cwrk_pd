"""
Scraper de MercadoLibre Argentina para inteligencia de mercado.
Extrae listings, precios, marcas y análisis por categoría.

Uso:
    from market_intelligence.ml_scraper import MLScraper
    scraper = MLScraper()
    results = scraper.search("valijas de viaje")
    analysis = scraper.analyze(results)
"""

import requests
import re
import json
import time
import os
from datetime import datetime
from bs4 import BeautifulSoup
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class MLScraper:
    BASE_URL = "https://listado.mercadolibre.com.ar"
    API_URL = "https://api.mercadolibre.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self._init_session()
        os.makedirs(DATA_DIR, exist_ok=True)

    def _init_session(self):
        """Get cookies from ML homepage."""
        try:
            self.session.get("https://www.mercadolibre.com.ar", timeout=10)
        except Exception:
            pass

    def search(self, query, pages=3, sort="relevance"):
        """
        Search ML for a query. Returns list of product dicts.

        Args:
            query: search string (e.g. "valijas de viaje")
            pages: number of result pages to fetch (1 page ~ 60 items)
            sort: "relevance" or "price_asc" or "price_desc"
        """
        all_items = []
        seen_ids = set()

        for page in range(pages):
            url = self._build_search_url(query, page, sort)
            items = self._fetch_page(url)

            for item in items:
                if item["item_id"] and item["item_id"] not in seen_ids:
                    seen_ids.add(item["item_id"])
                    all_items.append(item)
                elif not item["item_id"]:
                    # Deduplicate by title+price
                    key = f"{item['title']}_{item['price']}"
                    if key not in seen_ids:
                        seen_ids.add(key)
                        all_items.append(item)

            if page < pages - 1:
                time.sleep(1.5)  # Rate limit

        return all_items

    def _build_search_url(self, query, page=0, sort="relevance"):
        q = query.replace(" ", "-")
        url = f"{self.BASE_URL}/{q}"

        params = []
        if page > 0:
            offset = page * 50 + 1
            params.append(f"_Desde_{offset}")

        sort_map = {
            "price_asc": "_OrderId_PRICE",
            "price_desc": "_OrderId_PRICE*DESC",
        }
        if sort in sort_map:
            params.append(sort_map[sort])

        if params:
            url += "_" + "_".join(params)

        return url

    def _fetch_page(self, url):
        """Fetch and parse a single search results page."""
        try:
            r = self.session.get(url, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            return []

        return self._parse_listings(r.text)

    def _parse_listings(self, html):
        """Parse product cards from ML search results HTML."""
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_=re.compile(r"poly-card"))

        items = []
        seen_in_page = set()

        for card in cards:
            item = self._parse_card(card)
            if not item or not item["title"]:
                continue

            # Deduplicate within page (ML renders 2x per card)
            dedup_key = f"{item['title']}_{item['price']}"
            if dedup_key in seen_in_page:
                continue
            seen_in_page.add(dedup_key)

            items.append(item)

        return items

    def _parse_card(self, card):
        """Extract product data from a single card element."""
        title_el = card.find(class_=re.compile(r"poly-component__title"))
        price_el = card.find(class_="andes-money-amount__fraction")
        link_el = card.find("a", href=True)

        title = title_el.text.strip() if title_el else ""
        if not title:
            return None

        # Price
        price = 0
        if price_el:
            price_txt = price_el.text.strip().replace(".", "").replace(",", "")
            if price_txt.isdigit():
                price = int(price_txt)

        # Item ID from link
        item_id = ""
        link = ""
        if link_el:
            link = link_el.get("href", "")
            m = re.search(r"(MLA-?\d+)", link)
            if m:
                item_id = m.group(1).replace("-", "")

        # Shipping info
        shipping_el = card.find(class_=re.compile(r"poly-component__shipping"))
        free_shipping = False
        if shipping_el:
            free_shipping = "gratis" in shipping_el.text.lower()

        # Brand extraction from title
        brand = self._extract_brand(title)

        # Installments
        installment_el = card.find(class_=re.compile(r"poly-component__installments"))
        installments = installment_el.text.strip() if installment_el else ""

        # Original price (before discount)
        original_price = 0
        orig_el = card.find(class_=re.compile(r"andes-money-amount--previous"))
        if orig_el:
            frac = orig_el.find(class_="andes-money-amount__fraction")
            if frac:
                orig_txt = frac.text.strip().replace(".", "").replace(",", "")
                if orig_txt.isdigit():
                    original_price = int(orig_txt)

        return {
            "title": title,
            "price": price,
            "original_price": original_price,
            "item_id": item_id,
            "brand": brand,
            "free_shipping": free_shipping,
            "installments": installments,
            "link": link,
        }

    # Marcas conocidas por rubro — extensible
    BRANDS_BY_CATEGORY = {
        "valijas": [
            "Samsonite", "Delsey", "Roncato", "American Tourister",
            "Unicross", "Wilson", "Amayra", "Travel Tech", "Blaque",
            "Cecchini", "Primicia", "Cacharel", "It Luggage",
            "National Geographic", "Swiss", "Saxoline", "Everlast",
            "Totto", "Xtrem", "Head", "Fila",
        ],
        "calzado": [
            "Nike", "Adidas", "Topper", "Reebok", "Puma", "Fila",
            "Diadora", "Atomik", "Olympikus", "Vans", "Converse",
            "New Balance", "Skechers", "Hoka", "Asics", "Ringo",
            "Carmel", "Souter", "Wake", "GTN",
        ],
        "puertas": [
            "Oblak", "Nexo", "Craftmaster", "Valentini", "Platinum",
            "Aberplast", "Durlock", "Maderera", "Tab",
        ],
        "general": [
            "Samsung", "Apple", "Xiaomi", "Motorola", "Sony",
        ],
    }

    def _extract_brand(self, title, category=None):
        """Try to extract brand from product title.

        Args:
            title: product title string
            category: optional category key to use specific brand list.
                      If None, searches all known brands.
        """
        title_lower = title.lower()

        if category and category in self.BRANDS_BY_CATEGORY:
            brands = self.BRANDS_BY_CATEGORY[category]
        else:
            # Merge all brands (deduplicated)
            seen = set()
            brands = []
            for cat_brands in self.BRANDS_BY_CATEGORY.values():
                for b in cat_brands:
                    if b.lower() not in seen:
                        seen.add(b.lower())
                        brands.append(b)

        for brand in brands:
            if brand.lower() in title_lower:
                return brand
        return ""

    def get_category_info(self, query):
        """Get ML category data for a search term."""
        try:
            r = self.session.get(
                f"{self.API_URL}/sites/MLA/domain_discovery/search",
                params={"q": query},
                timeout=10
            )
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def get_category_detail(self, category_id):
        """Get category details including total items."""
        try:
            r = self.session.get(
                f"{self.API_URL}/categories/{category_id}",
                timeout=10
            )
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def analyze(self, items):
        """Analyze a list of scraped items and return market insights."""
        if not items:
            return {"error": "No items to analyze"}

        prices = [i["price"] for i in items if i["price"] > 0]
        prices.sort()

        brands = Counter(i["brand"] for i in items if i["brand"])
        shipping = sum(1 for i in items if i["free_shipping"])

        # Price segments
        if prices:
            q1 = prices[len(prices) // 4]
            median = prices[len(prices) // 2]
            q3 = prices[3 * len(prices) // 4]
        else:
            q1 = median = q3 = 0

        # Discount analysis
        discounted = [i for i in items if i["original_price"] > 0 and i["price"] > 0]
        avg_discount = 0
        if discounted:
            discounts = [(i["original_price"] - i["price"]) / i["original_price"] * 100
                         for i in discounted]
            avg_discount = sum(discounts) / len(discounts)

        # Price segments for import analysis
        segments = {
            "economico": {"range": f"$0 - ${q1:,}", "count": 0, "items": []},
            "medio": {"range": f"${q1:,} - ${median:,}", "count": 0, "items": []},
            "medio_alto": {"range": f"${median:,} - ${q3:,}", "count": 0, "items": []},
            "premium": {"range": f"${q3:,}+", "count": 0, "items": []},
        }
        for i in items:
            p = i["price"]
            if p <= 0:
                continue
            if p <= q1:
                seg = "economico"
            elif p <= median:
                seg = "medio"
            elif p <= q3:
                seg = "medio_alto"
            else:
                seg = "premium"
            segments[seg]["count"] += 1
            if len(segments[seg]["items"]) < 3:
                segments[seg]["items"].append({"title": i["title"][:60], "price": p})

        return {
            "total_items": len(items),
            "items_with_price": len(prices),
            "price_min": min(prices) if prices else 0,
            "price_max": max(prices) if prices else 0,
            "price_median": median,
            "price_avg": sum(prices) // len(prices) if prices else 0,
            "price_q1": q1,
            "price_q3": q3,
            "top_brands": brands.most_common(10),
            "free_shipping_pct": round(shipping / len(items) * 100, 1) if items else 0,
            "discounted_pct": round(len(discounted) / len(items) * 100, 1) if items else 0,
            "avg_discount_pct": round(avg_discount, 1),
            "segments": segments,
            "timestamp": datetime.now().isoformat(),
        }

    def save_results(self, items, analysis, query):
        """Save raw items and analysis to JSON files."""
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        slug = re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")

        raw_path = os.path.join(DATA_DIR, f"{slug}_{ts}_raw.json")
        analysis_path = os.path.join(DATA_DIR, f"{slug}_{ts}_analysis.json")

        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

        # Convert Counter to list for JSON
        analysis_json = dict(analysis)
        analysis_json["query"] = query
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(analysis_json, f, ensure_ascii=False, indent=2, default=str)

        return raw_path, analysis_path

    def full_scan(self, queries, pages=3):
        """
        Run a complete market scan for multiple queries.
        Returns dict of {query: {items, analysis}}.
        """
        results = {}
        for q in queries:
            print(f"\n{'='*60}")
            print(f"Scanning: {q}")
            print(f"{'='*60}")

            items = self.search(q, pages=pages)
            analysis = self.analyze(items)
            self.save_results(items, analysis, q)

            results[q] = {"items": items, "analysis": analysis}

            self._print_summary(q, analysis)

            if q != queries[-1]:
                time.sleep(2)

        return results

    def _print_summary(self, query, a):
        """Print analysis summary to console."""
        print(f"\n  Items: {a['total_items']} (con precio: {a['items_with_price']})")
        print(f"  Precio: ${a['price_min']:,} — ${a['price_max']:,}")
        print(f"  Mediana: ${a['price_median']:,} | Promedio: ${a['price_avg']:,}")
        print(f"  Q1: ${a['price_q1']:,} | Q3: ${a['price_q3']:,}")
        print(f"  Envío gratis: {a['free_shipping_pct']}%")
        print(f"  Con descuento: {a['discounted_pct']}% (prom: {a['avg_discount_pct']}%)")

        if a["top_brands"]:
            brands_str = ", ".join(f"{b}({c})" for b, c in a["top_brands"][:5])
            print(f"  Marcas top: {brands_str}")

        print(f"\n  Segmentos:")
        for seg_name, seg in a["segments"].items():
            print(f"    {seg_name:12s}: {seg['range']:>30s} → {seg['count']} items")


def import_opportunity_score(landed_cost_usd, exchange_rate, ml_median_price,
                              ml_commission_pct=16):
    """
    Calculate import opportunity score.

    Args:
        landed_cost_usd: costo puesto en Argentina (FOB + flete + derechos + imp)
        exchange_rate: tipo de cambio USD/ARS
        ml_median_price: precio mediana en ML (ARS)
        ml_commission_pct: comisión ML (default 16% premium)

    Returns:
        dict with margin analysis
    """
    landed_ars = landed_cost_usd * exchange_rate
    ml_net = ml_median_price * (1 - ml_commission_pct / 100)
    margin = (ml_net - landed_ars) / ml_net * 100 if ml_net > 0 else 0

    # Suggested prices by margin target
    targets = {"minimo_30": 30, "objetivo_40": 40, "premium_50": 50}
    suggested = {}
    for name, target_margin in targets.items():
        suggested[name] = round(landed_ars / (1 - target_margin / 100 - ml_commission_pct / 100))

    return {
        "landed_cost_usd": landed_cost_usd,
        "landed_cost_ars": round(landed_ars),
        "exchange_rate": exchange_rate,
        "ml_median_price": ml_median_price,
        "ml_net_after_commission": round(ml_net),
        "margin_at_median_pct": round(margin, 1),
        "viable": margin >= 25,
        "suggested_prices": suggested,
    }


if __name__ == "__main__":
    scraper = MLScraper()

    queries = [
        "valijas de viaje",
        "carry on cabina",
        "set valijas",
        "bolsos de viaje",
        "mochila viaje grande",
        "neceser viaje",
        "organizador de valija",
    ]

    results = scraper.full_scan(queries, pages=2)

    print("\n" + "=" * 60)
    print("RESUMEN COMPARATIVO")
    print("=" * 60)
    for q, data in results.items():
        a = data["analysis"]
        print(f"  {q:30s} | ${a['price_median']:>10,} mediana | {a['total_items']:3d} items")
