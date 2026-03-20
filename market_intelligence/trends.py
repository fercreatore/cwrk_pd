"""
Google Trends integration para estacionalidad y demanda.
Complementa los datos de ML con señales de demanda futura.

Uso:
    from market_intelligence.trends import get_trends, seasonal_projection
    df = get_trends(["valijas", "carry on"], months=12)
    proj = seasonal_projection(df, forecast_days=90)
"""

import time
from datetime import datetime, timedelta

try:
    from pytrends.request import TrendReq
    HAS_PYTRENDS = True
except ImportError:
    HAS_PYTRENDS = False


def get_trends(keywords, months=12, geo="AR", max_retries=3):
    """
    Get Google Trends data for keywords in Argentina.

    Args:
        keywords: list of up to 5 keywords
        months: lookback period
        geo: country code
        max_retries: retry count on rate limit

    Returns:
        pandas DataFrame with weekly interest, or None on failure
    """
    if not HAS_PYTRENDS:
        print("pytrends not installed. Run: pip install pytrends")
        return None

    pytrends = TrendReq(hl="es-AR", tz=180)
    timeframe = f"today {months}-m"

    for attempt in range(max_retries):
        try:
            pytrends.build_payload(keywords[:5], timeframe=timeframe, geo=geo)
            df = pytrends.interest_over_time()
            if not df.empty:
                df = df.drop(columns=["isPartial"], errors="ignore")
                return df
            return None
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait = (attempt + 1) * 30
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  Google Trends error: {e}")
                return None

    return None


def seasonal_projection(df, forecast_days=90):
    """
    Project demand based on seasonal patterns.

    Uses year-over-year comparison to estimate what demand
    will look like in forecast_days from now.

    Returns dict with projections per keyword.
    """
    if df is None or df.empty:
        return {}

    today = datetime.now()
    target_start = today + timedelta(days=forecast_days - 30)
    target_end = today + timedelta(days=forecast_days + 30)

    results = {}
    for col in df.columns:
        # Current period average (last 4 weeks)
        recent = df[col].tail(4).mean()

        # Same period last year — handle month boundaries (Jan=1, Dec=12)
        target_month = target_start.month
        target_months = set()
        for offset in [-1, 0, 1]:
            m = target_month + offset
            if m < 1:
                m += 12
            elif m > 12:
                m -= 12
            target_months.add(m)
        last_year_data = df[
            df.index.month.isin(target_months) &
            (df.index.year == today.year - 1)
        ]

        if not last_year_data.empty:
            # Current period last year — handle month boundaries
            current_months = set()
            for offset in [-1, 0]:
                m = today.month + offset
                if m < 1:
                    m += 12
                current_months.add(m)
            current_last_year = df[
                df.index.month.isin(current_months) &
                (df.index.year == today.year - 1)
            ]

            if not current_last_year.empty and current_last_year[col].mean() > 0:
                seasonal_factor = last_year_data[col].mean() / current_last_year[col].mean()
            else:
                seasonal_factor = 1.0

            projected = recent * seasonal_factor
        else:
            seasonal_factor = 1.0
            projected = recent

        trend_direction = "up" if seasonal_factor > 1.1 else ("down" if seasonal_factor < 0.9 else "stable")

        results[col] = {
            "current_interest": round(recent, 1),
            "projected_interest": round(projected, 1),
            "seasonal_factor": round(seasonal_factor, 2),
            "trend": trend_direction,
            "target_period": f"{target_start.strftime('%b')} - {target_end.strftime('%b %Y')}",
        }

    return results


def get_related_queries(keyword, geo="AR"):
    """Get related and rising queries for a keyword."""
    if not HAS_PYTRENDS:
        return {}

    pytrends = TrendReq(hl="es-AR", tz=180)
    try:
        pytrends.build_payload([keyword], timeframe="today 3-m", geo=geo)
        related = pytrends.related_queries()
        result = {}
        if keyword in related:
            top = related[keyword].get("top")
            rising = related[keyword].get("rising")
            if top is not None and not top.empty:
                result["top"] = top.head(10).to_dict("records")
            if rising is not None and not rising.empty:
                result["rising"] = rising.head(10).to_dict("records")
        return result
    except Exception as e:
        print(f"  Related queries error: {e}")
        return {}
