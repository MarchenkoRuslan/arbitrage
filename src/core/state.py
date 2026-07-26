import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import NamedTuple

from src.core.models import FundingRate, Ticker


class StateKey(NamedTuple):
    exchange: str
    symbol: str


class FundingSnapshot(NamedTuple):
    """A paired observation of funding rates from both exchanges in one poll cycle."""
    timestamp: datetime
    hl_rate: FundingRate | None
    lighter_rate: FundingRate | None


class MarketState:
    """In-memory market data cache. Updated by ingestion feeds, read by screener."""

    def __init__(self, sample_interval_s: float = 10.0, funding_history_limit: int = 4096) -> None:
        self._funding: dict[StateKey, FundingRate] = {}
        self._funding_history: dict[StateKey, deque[FundingRate]] = {}
        self._snapshots: dict[str, deque[FundingSnapshot]] = {}
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

    def record_snapshot(
        self,
        symbol: str,
        hl_rate: FundingRate | None,
        lighter_rate: FundingRate | None,
    ) -> None:
        """Record a paired funding observation from a single poll cycle."""
        snap = FundingSnapshot(
            timestamp=datetime.now(timezone.utc),
            hl_rate=hl_rate,
            lighter_rate=lighter_rate,
        )
        self._snapshots.setdefault(
            symbol, deque(maxlen=self._funding_history_limit)
        ).append(snap)

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
        """Count consecutive recent snapshots where short_exchange rate > long_exchange rate."""
        history = self._snapshots.get(symbol)
        if not history:
            return 0.0

        consecutive_samples = 0
        for snap in reversed(history):
            long_rate = self._snap_rate_for(snap, long_exchange)
            short_rate = self._snap_rate_for(snap, short_exchange)
            if long_rate is None or short_rate is None:
                break
            if short_rate.apr <= long_rate.apr:
                break
            consecutive_samples += 1

        return consecutive_samples * self._sample_interval_s / 3600

    def get_recent_flip_count(
        self,
        long_exchange: str,
        short_exchange: str,
        symbol: str,
        lookback_samples: int,
    ) -> int:
        """Count funding direction flips in the last N snapshots."""
        history = self._snapshots.get(symbol)
        if not history:
            return 0

        recent = list(history)[-lookback_samples:]
        flips = 0
        prev_favorable: bool | None = None
        for snap in recent:
            long_rate = self._snap_rate_for(snap, long_exchange)
            short_rate = self._snap_rate_for(snap, short_exchange)
            if long_rate is None or short_rate is None:
                continue
            favorable = short_rate.apr > long_rate.apr
            if prev_favorable is not None and favorable != prev_favorable:
                flips += 1
            prev_favorable = favorable

        return flips

    @staticmethod
    def _snap_rate_for(snap: FundingSnapshot, exchange: str) -> FundingRate | None:
        if exchange == "hyperliquid":
            return snap.hl_rate
        if exchange == "lighter":
            return snap.lighter_rate
        return None

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
