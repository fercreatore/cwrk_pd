"""
Conector IOL (InvertirOnline) — API oficial REST
Docs: https://api.invertironline.com/Help
"""
import os
import requests
from datetime import datetime, timedelta

BASE_URL = "https://api.invertironline.com"


class IOLClient:
    def __init__(self, user=None, password=None):
        self.user = user or os.getenv("IOL_USER")
        self.password = password or os.getenv("IOL_PASSWORD")
        self.token = None
        self.refresh_token = None
        self.token_expiry = None

    def _authenticate(self):
        """Obtiene bearer token via password grant."""
        resp = requests.post(f"{BASE_URL}/token", data={
            "username": self.user,
            "password": self.password,
            "grant_type": "password",
        })
        resp.raise_for_status()
        data = resp.json()
        self.token = data["access_token"]
        self.refresh_token = data.get("refresh_token")
        self.token_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 900))

    def _ensure_token(self):
        if not self.token or (self.token_expiry and datetime.now() >= self.token_expiry):
            if self.refresh_token:
                try:
                    self._refresh()
                    return
                except Exception:
                    pass
            self._authenticate()

    def _refresh(self):
        """Renueva el token usando refresh_token."""
        resp = requests.post(f"{BASE_URL}/token", data={
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        data = resp.json()
        self.token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        self.token_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 900))

    def _headers(self):
        self._ensure_token()
        return {"Authorization": f"Bearer {self.token}"}

    def get_portfolio(self):
        """Retorna las posiciones del portfolio."""
        resp = requests.get(f"{BASE_URL}/api/portafolio", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_account_state(self):
        """Estado de cuenta: saldos, disponible, etc."""
        resp = requests.get(f"{BASE_URL}/api/estadocuenta", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_quote(self, market, ticker):
        """
        Cotización de un título.
        market: 'bCBA' (BYMA), 'nYSE', 'nASDAQ', etc.
        """
        resp = requests.get(
            f"{BASE_URL}/api/{market}/Titulos/{ticker}/cotizacion",
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    def get_operations(self, status="todas", date_from=None, date_to=None):
        """
        Historial de operaciones.
        status: 'todas', 'pendientes', 'canceladas', 'terminadas'
        """
        params = {"filtro.estado": status}
        if date_from:
            params["filtro.fechaDesde"] = date_from  # formato: YYYY-MM-DD
        if date_to:
            params["filtro.fechaHasta"] = date_to
        resp = requests.get(
            f"{BASE_URL}/api/operaciones",
            headers=self._headers(), params=params
        )
        resp.raise_for_status()
        return resp.json()

    def get_panel(self, instrument="acciones", panel="merval", country="argentina"):
        """
        Panel de cotizaciones.
        instrument: acciones, bonos, opciones, cauciones, futuros
        panel: merval, general, panel_general, lider, etc.
        """
        resp = requests.get(
            f"{BASE_URL}/api/Cotizaciones/{instrument}/{panel}/{country}",
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()


def normalize_positions(iol_portfolio):
    """
    Convierte el formato IOL a nuestro formato unificado.
    Retorna lista de dicts con: ticker, name, qty, avg_cost, current_price, currency, source.
    """
    positions = []
    # IOL devuelve por país, dentro de cada uno hay títulos
    if not iol_portfolio:
        return positions

    for country_data in iol_portfolio.get("paises", []):
        for title in country_data.get("titulos", []):
            positions.append({
                "ticker": title.get("simbolo", ""),
                "name": title.get("descripcion", ""),
                "qty": title.get("cantidad", 0),
                "avg_cost": title.get("ppc", 0),  # precio promedio de compra
                "current_price": title.get("ultimoPrecio", 0),
                "market_value": title.get("valorizado", 0),
                "pnl": title.get("gananciaPorcentaje", 0),
                "currency": "ARS" if country_data.get("pais") == "argentina" else "USD",
                "source": "IOL",
                "market": country_data.get("pais", "argentina"),
            })
    return positions
