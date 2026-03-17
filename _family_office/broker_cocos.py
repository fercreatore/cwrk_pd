"""
Conector Cocos Capital — via pycocos (no oficial)
Install: pip install pycocos
Requiere: email, password, TOTP secret (base32)
"""
import os

try:
    from pycocos import Cocos
    PYCOCOS_AVAILABLE = True
except ImportError:
    PYCOCOS_AVAILABLE = False


class CocosClient:
    def __init__(self, email=None, password=None, totp_secret=None):
        if not PYCOCOS_AVAILABLE:
            raise ImportError("pycocos no instalado. Correr: pip install pycocos")

        self.email = email or os.getenv("COCOS_EMAIL")
        self.password = password or os.getenv("COCOS_PASSWORD")
        self.totp_secret = totp_secret or os.getenv("COCOS_TOTP_SECRET")
        self.client = None

    def connect(self):
        """Conecta y autentica con Cocos Capital."""
        self.client = Cocos(
            email=self.email,
            password=self.password,
            totp_secret_key=self.totp_secret,
        )
        return self.client

    def _ensure_connected(self):
        if not self.client:
            self.connect()

    def get_portfolio(self):
        """Retorna el portfolio completo."""
        self._ensure_connected()
        return self.client.my_portfolio()

    def get_funds(self):
        """Fondos disponibles por moneda y plazo."""
        self._ensure_connected()
        return self.client.funds_available()

    def get_account_data(self):
        """Datos de la cuenta."""
        self._ensure_connected()
        return self.client.my_data()

    def get_performance(self, timeframe="1Y"):
        """
        Performance del portfolio.
        timeframe: '1D', '1W', '1M', '3M', '6M', '1Y', 'MAX'
        """
        self._ensure_connected()
        return self.client.portfolio_performance(timeframe=timeframe)

    def get_dolar_mep(self):
        """Cotización dólar MEP actual."""
        self._ensure_connected()
        return self.client.get_dolar_mep_info()

    def get_activity(self, date_from, date_to):
        """Historial de actividad entre fechas (YYYY-MM-DD)."""
        self._ensure_connected()
        return self.client.account_activity(date_from=date_from, date_to=date_to)


def normalize_positions(cocos_portfolio):
    """
    Convierte el formato Cocos a nuestro formato unificado.
    Retorna lista de dicts con: ticker, name, qty, avg_cost, current_price, currency, source.
    """
    positions = []
    if not cocos_portfolio:
        return positions

    # pycocos devuelve una lista de posiciones o un dict con posiciones
    items = cocos_portfolio if isinstance(cocos_portfolio, list) else cocos_portfolio.get("positions", [])

    for item in items:
        # La estructura exacta puede variar según la versión de pycocos
        ticker = item.get("ticker", item.get("symbol", ""))
        positions.append({
            "ticker": ticker,
            "name": item.get("name", item.get("description", ticker)),
            "qty": item.get("quantity", item.get("amount", 0)),
            "avg_cost": item.get("avg_cost", item.get("avgPrice", 0)),
            "current_price": item.get("last_price", item.get("lastPrice", 0)),
            "market_value": item.get("market_value", item.get("marketValue", 0)),
            "pnl": item.get("return_pct", item.get("returnPct", 0)),
            "currency": item.get("currency", "ARS"),
            "source": "COCOS",
        })
    return positions
