import asyncio
from datetime import datetime, timezone
from typing import NamedTuple

from src.core.models import FundingRate, Ticker


class StateKey(NamedTuple):
    exchange: str
    symbol: str


class MarketState:
    """In-memory market data cache. Updated by ingestion feeds, read by screener."""

    def __init__(self) -> None:
        self._funding: dict[StateKey, FundingRate] = {}
        self._tickers: dict[StateKey, Ticker] = {}
        self._updated_at: dict[StateKey, datetime] = {}
        self._lock = asyncio.Lock()

    async def update_funding(self, exchange: str, rates: dict[str, FundingRate]) -> None:
        now = datetime.now(timezone.utc)
        async with self._lock:
            for symbol, rate in rates.items():
                key = StateKey(exchange, symbol)
                self._funding[key] = rate
                self._updated_at[key] = now

    async def update_tickers(self, exchange: str, tickers: dict[str, Ticker]) -> None:
        now = datetime.now(timezone.utc)
        async with self._lock:
            for symbol, ticker in tickers.items():
                key = StateKey(exchange, symbol)
                self._tickers[key] = ticker
                self._updated_at[key] = now

    async def update_single_funding(self, exchange: str, symbol: str, rate: FundingRate) -> None:
        async with self._lock:
            key = StateKey(exchange, symbol)
            self._funding[key] = rate
            self._updated_at[key] = datetime.now(timezone.utc)

    async def update_single_ticker(self, exchange: str, symbol: str, ticker: Ticker) -> None:
        async with self._lock:
            key = StateKey(exchange, symbol)
            self._tickers[key] = ticker
            self._updated_at[key] = datetime.now(timezone.utc)

    def get_funding(self, exchange: str) -> dict[str, FundingRate]:
        """Non-blocking read — returns snapshot of current state for one exchange."""
        return {
            key.symbol: rate
            for key, rate in self._funding.items()
            if key.exchange == exchange
        }

    def get_tickers(self, exchange: str) -> dict[str, Ticker]:
        """Non-blocking read — returns snapshot of current state for one exchange."""
        return {
            key.symbol: ticker
            for key, ticker in self._tickers.items()
            if key.exchange == exchange
        }

    def get_last_update(self, exchange: str, symbol: str) -> datetime | None:
        return self._updated_at.get(StateKey(exchange, symbol))

    def is_stale(self, exchange: str, symbol: str, max_age_s: float = 30.0) -> bool:
        updated = self._updated_at.get(StateKey(exchange, symbol))
        if updated is None:
            return True
        age = (datetime.now(timezone.utc) - updated).total_seconds()
        return age > max_age_s
