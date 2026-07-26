import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import NamedTuple

from src.core.models import FundingRate, Ticker


class StateKey(NamedTuple):
    exchange: str
    symbol: str


class MarketState:
    """In-memory market data cache. Updated by ingestion feeds, read by screener."""

    def __init__(self, sample_interval_s: float = 10.0, funding_history_limit: int = 4096) -> None:
        self._funding: dict[StateKey, FundingRate] = {}
        self._funding_history: dict[StateKey, deque[FundingRate]] = {}
        self._tickers: dict[StateKey, Ticker] = {}
        self._updated_at: dict[StateKey, datetime] = {}
        self._signaled: dict[str, tuple[float, float]] = {}  # symbol -> (timestamp, score)
        self._sample_interval_s = sample_interval_s
        self._funding_history_limit = funding_history_limit
        self._lock = asyncio.Lock()

    async def update_funding(self, exchange: str, rates: dict[str, FundingRate]) -> None:
        now = datetime.now(timezone.utc)
        async with self._lock:
            for symbol, rate in rates.items():
                key = StateKey(exchange, symbol)
                self._funding[key] = rate
                self._funding_history.setdefault(
                    key, deque(maxlen=self._funding_history_limit)
                ).append(rate)
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
            self._funding_history.setdefault(
                key, deque(maxlen=self._funding_history_limit)
            ).append(rate)
            self._updated_at[key] = datetime.now(timezone.utc)

    async def update_single_ticker(self, exchange: str, symbol: str, ticker: Ticker) -> None:
        async with self._lock:
            key = StateKey(exchange, symbol)
            self._tickers[key] = ticker
            self._updated_at[key] = datetime.now(timezone.utc)

    def get_funding(self, exchange: str) -> dict[str, FundingRate]:
        return {
            key.symbol: rate
            for key, rate in self._funding.items()
            if key.exchange == exchange
        }

    def get_tickers(self, exchange: str) -> dict[str, Ticker]:
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
        return (datetime.now(timezone.utc) - updated).total_seconds() > max_age_s

    def get_funding_persistence_hours(self, long_exchange: str, short_exchange: str, symbol: str) -> float:
        long_history = self._funding_history.get(StateKey(long_exchange, symbol))
        short_history = self._funding_history.get(StateKey(short_exchange, symbol))
        if not long_history or not short_history:
            return 0.0

        consecutive_samples = 0
        for long_rate, short_rate in zip(reversed(long_history), reversed(short_history)):
            if short_rate.apr <= long_rate.apr:
                break
            consecutive_samples += 1

        return consecutive_samples * self._sample_interval_s / 3600

    def record_signal(self, symbol: str, score: float) -> None:
        self._signaled[symbol] = (datetime.now(timezone.utc).timestamp(), score)

    def get_last_signal(self, symbol: str) -> tuple[float, float] | None:
        """Returns (timestamp, score) of last signal for symbol, or None."""
        return self._signaled.get(symbol)

    def prune_signals(self, max_age_s: float) -> None:
        now = datetime.now(timezone.utc).timestamp()
        expired = [s for s, (ts, _) in self._signaled.items() if now - ts > max_age_s]
        for s in expired:
            del self._signaled[s]
