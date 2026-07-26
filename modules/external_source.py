from __future__ import annotations

from datetime import datetime
from typing import Optional

import numpy as np

try:
    import yfinance as yf
except Exception:  # pragma: no cover - import guard for optional dependency failures
    yf = None


class ExternalSourceConnector:
    def __init__(self, source: str, symbol: str) -> None:
        self.source = source
        self.symbol = symbol

    def connection_status(self) -> tuple[bool, str]:
        if self.source == "Simulated":
            return True, "Connected to simulated feed"

        if yf is None:
            return False, "yfinance is unavailable. Install dependencies from requirements.txt"

        try:
            ticker = yf.Ticker(self.symbol)
            history = ticker.history(period="1d", interval="1m")
            if history.empty:
                return False, f"No market data returned for {self.symbol}"
            return True, f"Connected to Yahoo Finance for {self.symbol}"
        except Exception as exc:  # pragma: no cover - network errors are runtime dependent
            return False, f"Connection failed: {exc}"

    def fetch_latest_tick(self, fallback_price: float) -> tuple[datetime, float]:
        if self.source == "Simulated":
            change = np.random.normal(0, 1.5)
            return datetime.now(), round(fallback_price + change, 2)

        market_price = self._fetch_live_price()
        if market_price is None:
            change = np.random.normal(0, 1.0)
            return datetime.now(), round(fallback_price + change, 2)

        return datetime.now(), market_price

    def _fetch_live_price(self) -> Optional[float]:
        if yf is None:
            return None

        try:
            ticker = yf.Ticker(self.symbol)
            history = ticker.history(period="1d", interval="1m")
            if history.empty:
                return None
            return round(float(history["Close"].iloc[-1]), 2)
        except Exception:  # pragma: no cover - network errors are runtime dependent
            return None
