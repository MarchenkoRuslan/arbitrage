import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import NamedTuple

from src.core.models import FundingRate, Ticker


class StateKey(NamedTuple):
    exchange: str
    symbol: str


class FundingSnapshot(NamedTuple):
    """A paired observation of funding rates from multiple exchanges in one poll cycle."""
    timestamp: datetime
    rates: dict[str, FundingRate]
    basis_bps: float | None = None


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

    async def record_snapshot(
        self,
        symbol: str,
        rates: dict[str, FundingRate],
        tickers: dict[str, Ticker] | None = None,
    ) -> None:
        """Record a paired funding observation from a single poll cycle."""
        basis_bps: float | None = None
        if tickers:
            hl_tick = tickers.get("hyperliquid")
            lt_tick = tickers.get("lighter")
            if hl_tick and lt_tick and hl_tick.mark_price > 0 and lt_tick.mark_price > 0:
                if hl_tick.index_price is not None and lt_tick.index_price is not None:
                    idx_avg = float(hl_tick.index_price + lt_tick.index_price) / 2
                    denom = idx_avg if idx_avg > 0 else float(hl_tick.mark_price + lt_tick.mark_price) / 2
                else:
                    denom = float(hl_tick.mark_price + lt_tick.mark_price) / 2
                basis_bps = float(hl_tick.mark_price - lt_tick.mark_price) / denom * 10000
        snap = FundingSnapshot(
            timestamp=datetime.now(timezone.utc),
            rates=rates,
            basis_bps=basis_bps,
        )
        async with self._lock:
            self._snapshots.setdefault(
                symbol, deque(maxlen=self._funding_history_limit)
            ).append(snap)

    def get_snapshots(self, symbol: str) -> list["FundingSnapshot"]:
        """Return snapshot history for a symbol (most recent last)."""
        history = self._snapshots.get(symbol)
        return list(history) if history else []

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

    _SUPPORTED_EXCHANGES = frozenset({"hyperliquid", "lighter"})

    def get_basis_trend(
        self,
        long_exchange: str,
        short_exchange: str,
        symbol: str,
        lookback_samples: int = 6,
    ) -> float | None:
        """Basis slope in bps/sample. Positive means spread is widening for the given direction."""
        if short_exchange not in self._SUPPORTED_EXCHANGES:
            return None
        history = self._snapshots.get(symbol)
        if not history:
            return None

        recent_basis = [s.basis_bps for s in list(history)[-lookback_samples:] if s.basis_bps is not None]
        if len(recent_basis) < 2:
            return None

        # Stored basis is (HL_mark - Lighter_mark); flip sign when short=lighter
        sign = 1.0 if short_exchange == "hyperliquid" else -1.0
        values = [b * sign for b in recent_basis]
        return (values[-1] - values[0]) / (len(values) - 1)

    @staticmethod
    def _snap_rate_for(snap: FundingSnapshot, exchange: str) -> FundingRate | None:
        return snap.rates.get(exchange)

    async def record_signal(self, symbol: str, score: float) -> None:
        async with self._lock:
            self._signaled[symbol] = (datetime.now(timezone.utc).timestamp(), score)

    def get_last_signal(self, symbol: str) -> tuple[float, float] | None:
        """Returns (timestamp, score) of last signal for symbol, or None."""
        return self._signaled.get(symbol)

    async def prune_signals(self, max_age_s: float) -> None:
        now = datetime.now(timezone.utc).timestamp()
        async with self._lock:
            expired = [s for s, (ts, _) in self._signaled.items() if now - ts > max_age_s]
            for s in expired:
                del self._signaled[s]
