from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.core.config import Settings
from src.core.models import FundingRate, Ticker
from src.core.state import MarketState, StateKey
from src.screener.finder import (
    _funding_timing_asymmetry_hours,
    _hours_to_next_funding,
    find_opportunities,
    find_opportunities_from_state,
)


def _funding(symbol: str, apr: float) -> FundingRate:
    return FundingRate(
        symbol=symbol,
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
        min_score_bps=1.0,
        min_volume_24h=0.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.5,
    )

    opportunities = find_opportunities(
        hl_rates={
            "BTC": _funding("BTC", 12.0),
            "ETH": _funding("ETH", 40.0),
        },
        lighter_rates={
            "BTC": _funding("BTC", 20.0),
            "ETH": _funding("ETH", 15.0),
        },
        hl_tickers={
            "BTC": _ticker("BTC", "100"),
            "ETH": _ticker("ETH", "202"),
        },
        lighter_tickers={
            "BTC": _ticker("BTC", "101"),
            "ETH": _ticker("ETH", "200"),
        },
        settings=settings,
    )

    assert [op.symbol for op in opportunities] == ["ETH", "BTC"]

    eth = opportunities[0]
    assert eth.long_exchange == "lighter"
    assert eth.short_exchange == "hyperliquid"
    assert eth.funding_diff_apr == 25.0
    assert eth.funding_edge_bps == 20.55
    assert eth.basis_bps == 99.5
    assert eth.basis_bonus_bps == 49.75
    assert eth.fee_impact_bps == 0.0
    assert eth.min_profitable_hours == 0.0
    assert eth.hours_to_breakeven is None
    assert eth.combined_score == 70.3

    btc = opportunities[1]
    assert btc.long_exchange == "hyperliquid"
    assert btc.short_exchange == "lighter"
    assert btc.funding_diff_apr == 8.0
    assert btc.funding_edge_bps == 6.58
    assert btc.basis_bps == 99.5
    assert btc.basis_bonus_bps == 49.75
    assert btc.fee_impact_bps == 0.0
    assert btc.min_profitable_hours == 0.0
    assert btc.combined_score == 56.33


def test_find_opportunities_filters_scores_below_threshold() -> None:
    settings = Settings(
        min_score_bps=20.0,
        min_volume_24h=0.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.0,
    )

    opportunities = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 12.0)},
        lighter_rates={"BTC": _funding("BTC", 20.0)},
        hl_tickers={"BTC": _ticker("BTC", "100")},
        lighter_tickers={"BTC": _ticker("BTC", "101")},
        settings=settings,
    )

    assert opportunities == []


def test_find_opportunities_skips_negative_basis_when_funding_cannot_cover_hold_window() -> None:
    settings = Settings(
        min_score_bps=1.0,
        min_volume_24h=0.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.5,
    )

    opportunities = find_opportunities(
        hl_rates={"ETH": _funding("ETH", 40.0)},
        lighter_rates={"ETH": _funding("ETH", 15.0)},
        hl_tickers={"ETH": _ticker("ETH", "200")},
        lighter_tickers={"ETH": _ticker("ETH", "202")},
        settings=settings,
    )

    assert opportunities == []


def test_find_opportunities_filters_low_volume_symbols() -> None:
    settings = Settings(
        min_score_bps=1.0,
        min_volume_24h=1_000_000.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.5,
    )

    opportunities = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 12.0)},
        lighter_rates={"BTC": _funding("BTC", 20.0)},
        hl_tickers={"BTC": _ticker("BTC", "100", volume_24h=999_999.0)},
        lighter_tickers={"BTC": _ticker("BTC", "101", volume_24h=2_000_000.0)},
        settings=settings,
    )

    assert opportunities == []


def test_find_opportunities_filters_low_open_interest() -> None:
    settings = Settings(
        min_score_bps=1.0,
        min_volume_24h=0.0,
        min_open_interest=500_000.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.0,
    )

    hl_tick = Ticker(symbol="BTC", mark_price=Decimal("100"), index_price=Decimal("100"),
                     volume_24h=1_000_000, open_interest=400_000.0)
    lighter_tick = Ticker(symbol="BTC", mark_price=Decimal("100"), index_price=Decimal("100"),
                          volume_24h=1_000_000, open_interest=600_000.0)

    opportunities = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 5.0)},
        lighter_rates={"BTC": _funding("BTC", 20.0)},
        hl_tickers={"BTC": hl_tick},
        lighter_tickers={"BTC": lighter_tick},
        settings=settings,
    )

    assert opportunities == []


def test_find_opportunities_uses_index_price_for_basis_when_available() -> None:
    settings = Settings(
        min_score_bps=0.0,
        min_volume_24h=0.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.5,
    )

    # Short = HL (higher APR), Long = Lighter (lower APR)
    # Short mark = 202, Long mark = 200, index_price = 199 on both
    hl_tick = Ticker(symbol="ETH", mark_price=Decimal("202"), index_price=Decimal("199"),
                     volume_24h=1_000_000)
    lighter_tick = Ticker(symbol="ETH", mark_price=Decimal("200"), index_price=Decimal("199"),
                          volume_24h=1_000_000)

    opportunities = find_opportunities(
        hl_rates={"ETH": _funding("ETH", 40.0)},
        lighter_rates={"ETH": _funding("ETH", 15.0)},
        hl_tickers={"ETH": hl_tick},
        lighter_tickers={"ETH": lighter_tick},
        settings=settings,
    )

    assert len(opportunities) == 1
    # basis = (202 - 200) / 199 * 10000 = 100.5 bps (uses index avg as denom)
    assert opportunities[0].basis_bps == 100.5


def test_find_opportunities_uses_asymmetric_roundtrip_fees() -> None:
    settings = Settings(
        min_score_bps=0.0,
        min_volume_24h=0.0,
        hl_fee_per_side=0.035,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.0,
    )

    opportunities = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 5.0)},
        lighter_rates={"BTC": _funding("BTC", 35.0)},
        hl_tickers={"BTC": _ticker("BTC", "100")},
        lighter_tickers={"BTC": _ticker("BTC", "100")},
        settings=settings,
    )

    assert len(opportunities) == 1
    assert opportunities[0].fee_impact_bps == 7.0


@pytest.mark.asyncio
async def test_find_opportunities_from_state_reads_cached_market_data() -> None:
    settings = Settings(
        min_score_bps=1.0,
        min_volume_24h=0.0,
        min_persistence_hours=0.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.0,
    )
    state = MarketState(sample_interval_s=3600)

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 11.0)})
    await state.update_tickers("hyperliquid", {"BTC": _ticker("BTC", "100")})
    await state.update_tickers("lighter", {"BTC": _ticker("BTC", "100")})
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 11.0)})

    opportunities = find_opportunities_from_state(state, settings)

    assert len(opportunities) == 1
    assert opportunities[0].symbol == "BTC"
    assert opportunities[0].long_exchange == "hyperliquid"
    assert opportunities[0].short_exchange == "lighter"
    assert opportunities[0].persistence_hours == 1.0
    assert opportunities[0].funding_edge_bps == 4.93
    assert opportunities[0].combined_score == 4.93
    assert opportunities[0].liquidity_tier == "H"  # min_volume_24h=0 → all tier H
    assert opportunities[0].basis_trend is None  # need ≥2 snapshots with tickers for trend


def test_find_opportunities_assigns_liquidity_tier() -> None:
    settings = Settings(
        min_score_bps=0.0,
        min_volume_24h=100_000.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.0,
    )

    opportunities = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 5.0), "ETH": _funding("ETH", 5.0), "SOL": _funding("SOL", 5.0)},
        lighter_rates={"BTC": _funding("BTC", 20.0), "ETH": _funding("ETH", 20.0), "SOL": _funding("SOL", 20.0)},
        hl_tickers={
            "BTC": _ticker("BTC", "100", volume_24h=2_000_000),
            "ETH": _ticker("ETH", "100", volume_24h=500_000),
            "SOL": _ticker("SOL", "100", volume_24h=150_000),
        },
        lighter_tickers={
            "BTC": _ticker("BTC", "100", volume_24h=2_000_000),
            "ETH": _ticker("ETH", "100", volume_24h=500_000),
            "SOL": _ticker("SOL", "100", volume_24h=150_000),
        },
        settings=settings,
    )

    tiers = {o.symbol: o.liquidity_tier for o in opportunities}
    assert tiers["BTC"] == "H"   # 2M >= 100K*10
    assert tiers["ETH"] == "M"   # 500K >= 100K*3
    assert tiers["SOL"] == "L"   # 150K < 100K*3


def test_find_opportunities_liquidity_weight_boosts_score() -> None:
    base_settings = Settings(
        min_score_bps=0.0,
        min_volume_24h=100_000.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.0,
        liquidity_weight=0.0,
    )
    weighted_settings = base_settings.model_copy(update={"liquidity_weight": 2.0})

    base_opps = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 5.0)},
        lighter_rates={"BTC": _funding("BTC", 20.0)},
        hl_tickers={"BTC": _ticker("BTC", "100", volume_24h=1_000_000)},
        lighter_tickers={"BTC": _ticker("BTC", "100", volume_24h=1_000_000)},
        settings=base_settings,
    )
    weighted_opps = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 5.0)},
        lighter_rates={"BTC": _funding("BTC", 20.0)},
        hl_tickers={"BTC": _ticker("BTC", "100", volume_24h=1_000_000)},
        lighter_tickers={"BTC": _ticker("BTC", "100", volume_24h=1_000_000)},
        settings=weighted_settings,
    )

    assert weighted_opps[0].combined_score > base_opps[0].combined_score


def test_hours_to_next_funding_helper() -> None:
    ts = datetime(2026, 1, 1, 0, 30, tzinfo=UTC)

    assert _hours_to_next_funding(ts, 1) == 0.5
    assert _hours_to_next_funding(ts, 8) == 7.5
    assert _hours_to_next_funding(ts, 0) is None


def test_find_opportunities_applies_timing_asymmetry_penalty() -> None:
    settings = Settings(
        min_score_bps=0.0,
        min_volume_24h=0.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.0,
        timing_penalty_bps_per_hour=2.0,
    )

    hl_rate = FundingRate(
        symbol="ETH",
        period_hours=1,
        apr=40.0,
        timestamp=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
    )
    lighter_rate = FundingRate(
        symbol="ETH",
        period_hours=1,
        apr=15.0,
        timestamp=datetime(2026, 1, 1, 0, 30, tzinfo=UTC),
    )

    opportunities = find_opportunities(
        hl_rates={"ETH": hl_rate},
        lighter_rates={"ETH": lighter_rate},
        hl_tickers={"ETH": _ticker("ETH", "100")},
        lighter_tickers={"ETH": _ticker("ETH", "100")},
        settings=settings,
    )

    assert len(opportunities) == 1
    assert opportunities[0].long_hours_to_next_funding == 0.5
    assert opportunities[0].short_hours_to_next_funding == 0.0
    assert opportunities[0].funding_timing_asymmetry_hours == 0.5
    assert opportunities[0].funding_timing_penalty_bps == 1.0
    assert opportunities[0].combined_score == 19.55


def test_funding_timing_asymmetry_uses_circular_distance() -> None:
    # 5 min before and 5 min after hourly boundary should be 10 min apart, not 50 min.
    asymmetry = _funding_timing_asymmetry_hours(0.08, 0.92, 1, 1)

    assert asymmetry is not None
    assert abs(asymmetry - 0.16) < 0.01


def test_funding_timing_asymmetry_none_when_periods_differ() -> None:
    asymmetry = _funding_timing_asymmetry_hours(0.5, 0.5, 1, 8)

    assert asymmetry is None


@pytest.mark.asyncio
async def test_find_opportunities_from_state_skips_stale_symbols() -> None:
    settings = Settings(
        min_score_bps=1.0,
        min_volume_24h=0.0,
        min_persistence_hours=0.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.0,
        stale_data_s=30.0,
    )
    state = MarketState()

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 11.0)})
    await state.update_tickers("hyperliquid", {"BTC": _ticker("BTC", "100")})
    await state.update_tickers("lighter", {"BTC": _ticker("BTC", "100")})

    state._updated_at[StateKey("hyperliquid", "BTC")] = datetime.now(UTC) - timedelta(seconds=31)

    opportunities = find_opportunities_from_state(state, settings)

    assert opportunities == []


@pytest.mark.asyncio
async def test_find_opportunities_from_state_applies_persistence_gate() -> None:
    settings = Settings(
        min_score_bps=1.0,
        min_volume_24h=0.0,
        min_persistence_hours=2.0,
        hl_fee_per_side=0.0,
        lighter_fee_per_side=0.0,
        expected_hold_hours=72.0,
        basis_weight=0.0,
    )
    state = MarketState(sample_interval_s=3600)

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 11.0)})
    await state.update_tickers("hyperliquid", {"BTC": _ticker("BTC", "100")})
    await state.update_tickers("lighter", {"BTC": _ticker("BTC", "100")})
    # Only one snapshot — persistence = 1h, below 2h gate
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 11.0)})

    assert find_opportunities_from_state(state, settings) == []

    # Second snapshot — persistence = 2h, meets gate
    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 5.0)})
    await state.update_funding("lighter", {"BTC": _funding("BTC", 11.0)})
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 11.0)})

    opportunities = find_opportunities_from_state(state, settings)

    assert len(opportunities) == 1
    assert opportunities[0].persistence_hours == 2.0