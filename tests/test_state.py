from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.core.models import FundingRate, Ticker
from src.core.state import MarketState


def _funding(symbol: str, apr: float = 12.0) -> FundingRate:
    return FundingRate(symbol=symbol, rate=Decimal("0.0001"), period_hours=1, apr=apr,
                       timestamp=datetime(2026, 1, 1, tzinfo=UTC))


def _ticker(symbol: str, mark_price: str = "100") -> Ticker:
    return Ticker(symbol=symbol, mark_price=Decimal(mark_price),
                  index_price=Decimal(mark_price), volume_24h=1_000_000)


@pytest.mark.asyncio
async def test_market_state_update_and_snapshot_reads_are_exchange_scoped() -> None:
    state = MarketState()
    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 10.0)})
    await state.update_tickers("lighter", {"BTC": _ticker("BTC", "101")})
    assert state.get_funding("hyperliquid")["BTC"].apr == 10.0
    assert state.get_tickers("lighter")["BTC"].mark_price == Decimal("101")
    assert state.get_funding("lighter") == {}
    assert state.get_tickers("hyperliquid") == {}


@pytest.mark.asyncio
async def test_market_state_is_not_stale_immediately_after_update() -> None:
    state = MarketState()
    await state.update_funding("hyperliquid", {"ETH": _funding("ETH", 8.0)})
    assert state.is_stale("hyperliquid", "ETH", max_age_s=30.0) is False
    assert state.is_stale("hyperliquid", "BTC", max_age_s=30.0) is True


@pytest.mark.asyncio
async def test_market_state_persistence_requires_both_exchange_histories() -> None:
    state = MarketState(sample_interval_s=3600.0)
    assert state.get_funding_persistence_hours("hyperliquid", "lighter", "BTC") == 0.0
    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 20.0)})
    # lighter apr > hl apr -> long=hyperliquid, short=lighter
    hours = state.get_funding_persistence_hours("hyperliquid", "lighter", "BTC")
    assert hours == pytest.approx(1.0)
