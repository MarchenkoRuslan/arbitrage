from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.core.config import Settings
from src.core.models import FundingRate, Ticker
from src.core.state import MarketState
from src.screener.finder import find_opportunities, find_opportunities_from_state


def _funding(symbol: str, apr: float) -> FundingRate:
    return FundingRate(
        symbol=symbol,
        rate=Decimal("0.0001"),
        period_hours=1,
        apr=apr,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _ticker(symbol: str, mark_price: str, volume_24h: float = 1_000_000) -> Ticker:
    return Ticker(
        symbol=symbol,
        mark_price=Decimal(mark_price),
        index_price=Decimal(mark_price),
        volume_24h=volume_24h,
    )


def test_find_opportunities_sorts_by_combined_score_and_sets_direction() -> None:
    settings = Settings(
        min_score_apr=1.0,
        fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.1,
    )

    opportunities = find_opportunities(
        hl_rates={
            "BTC": _funding("BTC", 12.0),
            "ETH": _funding("ETH", 40.0),
        },
        aster_rates={
            "BTC": _funding("BTC", 20.0),
            "ETH": _funding("ETH", 15.0),
        },
        hl_tickers={
            "BTC": _ticker("BTC", "100"),
            "ETH": _ticker("ETH", "200"),
        },
        aster_tickers={
            "BTC": _ticker("BTC", "101"),
            "ETH": _ticker("ETH", "202"),
        },
        settings=settings,
    )

    assert [op.symbol for op in opportunities] == ["ETH", "BTC"]

    eth = opportunities[0]
    assert eth.long_exchange == "aster"
    assert eth.short_exchange == "hyperliquid"
    assert eth.funding_diff_apr == 25.0
    assert eth.basis_bps == 99.5
    assert eth.combined_score == 34.95

    btc = opportunities[1]
    assert btc.long_exchange == "hyperliquid"
    assert btc.short_exchange == "aster"
    assert btc.funding_diff_apr == 8.0
    assert btc.basis_bps == 99.5
    assert btc.combined_score == 17.95


def test_find_opportunities_filters_scores_below_threshold() -> None:
    settings = Settings(
        min_score_apr=20.0,
        fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.0,
    )

    opportunities = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 12.0)},
        aster_rates={"BTC": _funding("BTC", 20.0)},
        hl_tickers={"BTC": _ticker("BTC", "100")},
        aster_tickers={"BTC": _ticker("BTC", "101")},
        settings=settings,
    )

    assert opportunities == []


@pytest.mark.asyncio
async def test_find_opportunities_from_state_reads_cached_market_data() -> None:
    settings = Settings(
        min_score_apr=1.0,
        fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.0,
    )
    state = MarketState()

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("aster", {"BTC": _funding("BTC", 11.0)})
    await state.update_tickers("hyperliquid", {"BTC": _ticker("BTC", "100")})
    await state.update_tickers("aster", {"BTC": _ticker("BTC", "100")})

    opportunities = find_opportunities_from_state(state, settings)

    assert len(opportunities) == 1
    assert opportunities[0].symbol == "BTC"
    assert opportunities[0].long_exchange == "hyperliquid"
    assert opportunities[0].short_exchange == "aster"
    assert opportunities[0].combined_score == 6.0