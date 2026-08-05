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
    return FundingRate(symbol=symbol, period_hours=1,
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
    result = await validate_opportunities(opps, state, settings)

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
    result = await validate_opportunities(opps, state, settings)

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
    result = await validate_opportunities(opps, state, settings)

    assert result[0].status == "blocked"
    assert "break-even" in result[0].reasons[0]


@pytest.mark.asyncio
async def test_validator_detects_funding_direction_flip() -> None:
    settings = Settings(min_persistence_hours=0.0, expected_hold_hours=72.0, stale_data_s=60.0,
                        loop_interval_s=3600)
    state = MarketState(sample_interval_s=3600)

    # Simulate alternating direction via paired snapshots:
    # HL>Lighter, HL<Lighter, HL>Lighter
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 20.0), "lighter": _funding("BTC", 5.0)})
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 20.0)})
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 20.0), "lighter": _funding("BTC", 5.0)})

    await state.update_tickers("hyperliquid", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})
    await state.update_tickers("lighter", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})

    opps = [_opp("BTC", score=50.0)]
    result = await validate_opportunities(opps, state, settings)

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
    result = await validate_opportunities(opps, state, settings)

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
    result1 = await validate_opportunities(opps, state, settings)
    assert result1[0].status == "ready"

    # Second call with same score: should be watching (cooldown)
    result2 = await validate_opportunities(opps, state, settings)
    assert result2[0].status == "watching"
    assert "cooldown" in result2[0].reasons[0]

    # Third call with score > 1.5x: should be ready again
    high_opps = [_opp("BTC", score=80.0)]
    result3 = await validate_opportunities(high_opps, state, settings)
    assert result3[0].status == "ready"


@pytest.mark.asyncio
async def test_validator_ready_does_not_re_record_signal_on_subsequent_polls() -> None:
    """After a score improvement passes anti-churn, the signal is NOT re-recorded
    on subsequent polls, so the opportunity stays 'ready' indefinitely."""
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

    # First call: ready, signal recorded
    result1 = await validate_opportunities(opps, state, settings)
    assert result1[0].status == "ready"

    # Call with improved score to pass anti-churn
    high_opps = [_opp("BTC", score=80.0)]
    result2 = await validate_opportunities(high_opps, state, settings)
    assert result2[0].status == "ready"

    # Same high score again — should still be ready (signal not re-recorded at new timestamp)
    result3 = await validate_opportunities(high_opps, state, settings)
    assert result3[0].status == "ready"


@pytest.mark.asyncio
async def test_validator_warns_on_large_basis() -> None:
    settings = Settings(min_persistence_hours=0.0, expected_hold_hours=72.0, stale_data_s=60.0,
                        max_basis_bps=30.0)
    state = MarketState(sample_interval_s=3600)

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 20.0)})
    await state.update_tickers("hyperliquid", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})
    await state.update_tickers("lighter", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})

    opp = _opp("BTC", score=50.0)
    opp.basis_bps = 50.0  # exceeds limit
    result = await validate_opportunities([opp], state, settings)

    assert result[0].status == "watching"
    assert "basis" in result[0].reasons[0]
    assert "+50.0" in result[0].reasons[0]  # signed value shown


@pytest.mark.asyncio
async def test_validator_warns_on_basis_instability() -> None:
    settings = Settings(min_persistence_hours=0.0, expected_hold_hours=72.0, stale_data_s=60.0)
    state = MarketState(sample_interval_s=3600)

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 20.0)})
    await state.update_tickers("hyperliquid", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})
    await state.update_tickers("lighter", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})

    opp = _opp("BTC", score=50.0)
    opp.basis_trend = 5.0  # above threshold
    result = await validate_opportunities([opp], state, settings)

    assert result[0].status == "watching"
    assert "unstable" in result[0].reasons[0]
    assert "limit" in result[0].reasons[0]  # shows configurable limit


@pytest.mark.asyncio
async def test_validator_basis_trend_threshold_zero_disables_warning() -> None:
    settings = Settings(
        min_persistence_hours=0.0,
        expected_hold_hours=72.0,
        stale_data_s=60.0,
        max_basis_trend_bps_per_tick=0.0,
    )
    state = MarketState(sample_interval_s=3600)

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 20.0)})
    await state.update_tickers("hyperliquid", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})
    await state.update_tickers("lighter", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})

    opp = _opp("BTC", score=50.0)
    opp.basis_trend = 5.0
    result = await validate_opportunities([opp], state, settings)

    assert result[0].status == "ready"


@pytest.mark.asyncio
async def test_validator_warns_on_funding_timing_asymmetry() -> None:
    settings = Settings(
        min_persistence_hours=0.0,
        expected_hold_hours=72.0,
        stale_data_s=60.0,
        max_funding_timing_asymmetry_hours=0.5,
    )
    state = MarketState(sample_interval_s=3600)

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 20.0)})
    await state.update_tickers("hyperliquid", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})
    await state.update_tickers("lighter", {"BTC": Ticker(symbol="BTC", mark_price=Decimal("100"), volume_24h=1e6)})

    opp = _opp("BTC", score=50.0)
    opp.funding_timing_asymmetry_hours = 1.0
    result = await validate_opportunities([opp], state, settings)

    assert result[0].status == "watching"
    assert "timing asymmetry" in result[0].reasons[0]
