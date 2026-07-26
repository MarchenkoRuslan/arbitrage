from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.core.config import Settings
from src.core.models import ArbitrageOpportunity, FundingRate, Ticker
from src.core.state import MarketState
from src.screener.validator import validate_opportunities


def _opp(symbol: str = "BTC", score: float = 50.0, persistence: float = 6.0,
         min_profitable_hours: float | None = 10.0) -> ArbitrageOpportunity:
    return ArbitrageOpportunity(
        symbol=symbol,
        long_exchange="hyperliquid",
        short_exchange="lighter",
        persistence_hours=persistence,
        long_rate_apr=5.0,
        short_rate_apr=20.0,
        funding_diff_apr=15.0,
        funding_edge_bps=score + 7.0,
        basis_bps=10.0,
        basis_bonus_bps=5.0,
        fee_impact_bps=7.0,
        min_profitable_hours=min_profitable_hours,
        hours_to_breakeven=None,
        combined_score=score,
    )


def _funding(symbol: str, apr: float) -> FundingRate:
    return FundingRate(symbol=symbol, rate=Decimal("0.0001"), period_hours=1,
                       apr=apr, timestamp=datetime(2026, 1, 1, tzinfo=UTC))


@pytest.mark.asyncio
async def test_validator_marks_ready_when_all_checks_pass() -> None:
    settings = Settings(min_persistence_hours=0.0, expected_hold_hours=72.0, stale_data_s=60.0)
    state = MarketState(sample_interval_s=3600)

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 20.0)})
    await state.update_tickers("hyperliquid", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})
    await state.update_tickers("lighter", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})

    opps = [_opp("BTC", score=50.0)]
    result = validate_opportunities(opps, state, settings)

    assert len(result) == 1
    assert result[0].status == "ready"
    assert result[0].reasons == []


@pytest.mark.asyncio
async def test_validator_marks_watching_when_persistence_insufficient() -> None:
    settings = Settings(min_persistence_hours=6.0, expected_hold_hours=72.0, stale_data_s=60.0)
    state = MarketState(sample_interval_s=3600)

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 20.0)})
    await state.update_tickers("hyperliquid", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})
    await state.update_tickers("lighter", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})

    opps = [_opp("BTC", score=50.0, persistence=2.0)]
    result = validate_opportunities(opps, state, settings)

    assert result[0].status == "watching"
    assert "persistence" in result[0].reasons[0]


@pytest.mark.asyncio
async def test_validator_marks_blocked_when_breakeven_exceeds_hold() -> None:
    settings = Settings(min_persistence_hours=0.0, expected_hold_hours=72.0, stale_data_s=60.0)
    state = MarketState(sample_interval_s=3600)

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 20.0)})
    await state.update_tickers("hyperliquid", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})
    await state.update_tickers("lighter", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})

    opps = [_opp("BTC", score=50.0, min_profitable_hours=100.0)]
    result = validate_opportunities(opps, state, settings)

    assert result[0].status == "blocked"
    assert "break-even" in result[0].reasons[0]


@pytest.mark.asyncio
async def test_validator_detects_funding_direction_flip() -> None:
    settings = Settings(min_persistence_hours=0.0, expected_hold_hours=72.0, stale_data_s=60.0,
                        loop_interval_s=3600)
    state = MarketState(sample_interval_s=3600)

    # Simulate alternating direction: HL>Lighter, HL<Lighter, HL>Lighter
    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 20.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 20.0)})
    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 20.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 5.0)})

    await state.update_tickers("hyperliquid", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})
    await state.update_tickers("lighter", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})

    opps = [_opp("BTC", score=50.0)]
    result = validate_opportunities(opps, state, settings)

    assert result[0].status == "watching"
    assert "flipped" in result[0].reasons[0]


@pytest.mark.asyncio
async def test_validator_sorts_ready_before_watching() -> None:
    settings = Settings(min_persistence_hours=6.0, expected_hold_hours=72.0, stale_data_s=60.0)
    state = MarketState(sample_interval_s=3600)

    await state.update_funding("hyperliquid", {"ETH": _funding("ETH", 5.0), "BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"ETH": _funding("ETH", 30.0), "BTC": _funding("BTC", 20.0)})
    await state.update_tickers("hyperliquid", {
        "ETH": Ticker(symbol="ETH", mark_price=Decimal("200"), volume_24h=1e6),
        "BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6),
    })
    await state.update_tickers("lighter", {
        "ETH": Ticker(symbol="ETH", mark_price=Decimal("200"), volume_24h=1e6),
        "BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6),
    })

    opps = [
        _opp("BTC", score=50.0, persistence=2.0),  # fails persistence → watching
        _opp("ETH", score=30.0, persistence=8.0),  # passes → ready
    ]
    result = validate_opportunities(opps, state, settings)

    assert result[0].status == "ready"
    assert result[0].opportunity.symbol == "ETH"
    assert result[1].status == "watching"
    assert result[1].opportunity.symbol == "BTC"


@pytest.mark.asyncio
async def test_validator_anti_churn_suppresses_repeated_signal() -> None:
    settings = Settings(
        min_persistence_hours=0.0, expected_hold_hours=72.0, stale_data_s=60.0,
        anti_churn_cooldown_s=14400.0, anti_churn_score_multiplier=1.5,
    )
    state = MarketState(sample_interval_s=3600)

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 20.0)})
    await state.update_tickers("hyperliquid", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})
    await state.update_tickers("lighter", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})

    opps = [_opp("BTC", score=50.0)]

    # First call: should be ready and record signal
    result1 = validate_opportunities(opps, state, settings)
    assert result1[0].status == "ready"

    # Second call with same score: should be watching (cooldown)
    result2 = validate_opportunities(opps, state, settings)
    assert result2[0].status == "watching"
    assert "cooldown" in result2[0].reasons[0]

    # Third call with score > 1.5x: should be ready again
    high_opps = [_opp("BTC", score=80.0)]
    result3 = validate_opportunities(high_opps, state, settings)
    assert result3[0].status == "ready"
