import asyncio
from collections import deque
from datetime import datetime, timezone

from src.core.models import FundingRate, Ticker


class StateKey(str):
    pass


def _key(exchange: str, symbol: str) -> str:
    return f"{exchange}::{symbol}"


class MarketState:
    """In-memory market data cache keyed by (exchange, symbol)."""

    def __init__(self, sample_interval_s: float = 10.0, funding_history_limit: int = 4096) -> None:
        self._funding: dict[str, FundingRate] = {}
        self._funding_history: dict[str, deque[FundingRate]] = {}
        self._tickers: dict[str, Ticker] = {}
        self._updated_at: dict[str, datetime] = {}
        self._sample_interval_s = sample_interval_s
        self._funding_history_limit = funding_history_limit
        self._lock = asyncio.Lock()

    async def update_funding(self, exchange: str, rates: dict[str, FundingRate]) -> None:
        now = datetime.now(timezone.utc)
        async with self._lock:
            for symbol, rate in rates.items():
                k = _key(exchange, symbol)
                self._funding[k] = rate
                self._funding_history.setdefault(k, deque(maxlen=self._funding_history_limit)).append(rate)
                self._updated_at[k] = now

    async def update_tickers(self, exchange: str, tickers: dict[str, Ticker]) -> None:
        now = datetime.now(timezone.utc)
        async with self._lock:
            for symbol, ticker in tickers.items():
                k = _key(exchange, symbol)
                self._tickers[k] = ticker
                self._updated_at[k] = now

    def get_funding(self, exchange: str) -> dict[str, FundingRate]:
        prefix = f"{exchange}::"
        return {k[len(prefix):]: v for k, v in self._funding.items() if k.startswith(prefix)}

    def get_tickers(self, exchange: str) -> dict[str, Ticker]:
        prefix = f"{exchange}::"
        return {k[len(prefix):]: v for k, v in self._tickers.items() if k.startswith(prefix)}

    def get_last_update(self, exchange: str, symbol: str) -> datetime | None:
        return self._updated_at.get(_key(exchange, symbol))

    def is_stale(self, exchange: str, symbol: str, max_age_s: float = 30.0) -> bool:
        updated = self._updated_at.get(_key(exchange, symbol))
        if updated is None:
            return True
        return (datetime.now(timezone.utc) - updated).total_seconds() > max_age_s

    def get_funding_persistence_hours(self, long_exchange: str, short_exchange: str, symbol: str) -> float:
        long_hist = self._funding_history.get(_key(long_exchange, symbol))
        short_hist = self._funding_history.get(_key(short_exchange, symbol))
        if not long_hist or not short_hist:
            return 0.0
        count = 0
        for lr, sr in zip(reversed(long_hist), reversed(short_hist)):
            if sr.apr <= lr.apr:
                break
            count += 1
        return count * self._sample_interval_s / 3600
