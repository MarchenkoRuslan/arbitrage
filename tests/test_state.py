from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.core.models import FundingRate, Ticker
from src.core.state import MarketState, StateKey


def _funding(symbol: str, apr: float = 12.0) -> FundingRate:
    return FundingRate(
        symbol=symbol,
        period_hours=1,
        apr=apr,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _ticker(symbol: str, mark_price: str = "100") -> Ticker:
    return Ticker(
        symbol=symbol,
        mark_price=Decimal(mark_price),
        index_price=Decimal(mark_price),
        volume_24h=1_000_000,
    )


@pytest.mark.asyncio
async def test_market_state_update_and_snapshot_reads_are_exchange_scoped() -> None:
    state = MarketState()

    await state.update_funding("hyperliquid", {"BTC": _funding("BTC", 10.0)})
    await state.update_tickers("lighter", {"BTC": _ticker("BTC", "101")})

    funding = state.get_funding("hyperliquid")
    tickers = state.get_tickers("lighter")

    assert funding["BTC"].apr == 10.0
    assert tickers["BTC"].mark_price == Decimal("101")
    assert state.get_funding("lighter") == {}
    assert state.get_tickers("hyperliquid") == {}


@pytest.mark.asyncio
async def test_market_state_tracks_last_update_for_single_item_updates() -> None:
    state = MarketState()

    await state.update_single_funding("hyperliquid", "ETH", _funding("ETH", 8.0))
    await state.update_single_ticker("hyperliquid", "ETH", _ticker("ETH", "2500"))

    last_update = state.get_last_update("hyperliquid", "ETH")

    assert last_update is not None
    assert last_update.tzinfo is UTC
    assert state.get_funding("hyperliquid")["ETH"].apr == 8.0
    assert state.get_tickers("hyperliquid")["ETH"].mark_price == Decimal("2500")


@pytest.mark.asyncio
async def test_market_state_is_stale_depends_on_update_age() -> None:
    state = MarketState()

    assert state.is_stale("hyperliquid", "BTC") is True

    await state.update_single_funding("hyperliquid", "BTC", _funding("BTC"))
    assert state.is_stale("hyperliquid", "BTC", max_age_s=30.0) is False

    state._updated_at[StateKey("hyperliquid", "BTC")] = datetime.now(UTC) - timedelta(seconds=31)

    assert state.is_stale("hyperliquid", "BTC", max_age_s=30.0) is True


@pytest.mark.asyncio
async def test_market_state_tracks_consecutive_funding_persistence() -> None:
    state = MarketState(sample_interval_s=3600)

    # Two snapshots where lighter (short) > hyperliquid (long)
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 11.0)})
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 6.0), "lighter": _funding("BTC", 12.0)})

    persistence_hours = state.get_funding_persistence_hours("hyperliquid", "lighter", "BTC")

    assert persistence_hours == 2.0


@pytest.mark.asyncio
async def test_market_state_stops_persistence_on_direction_flip() -> None:
    state = MarketState(sample_interval_s=3600)

    # First snapshot: lighter > hyperliquid (favorable)
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 11.0)})
    # Second snapshot: hyperliquid > lighter (unfavorable flip)
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 14.0), "lighter": _funding("BTC", 12.0)})

    persistence_hours = state.get_funding_persistence_hours("hyperliquid", "lighter", "BTC")

    assert persistence_hours == 0.0


@pytest.mark.asyncio
async def test_market_state_get_recent_flip_count() -> None:
    state = MarketState(sample_interval_s=3600)

    # Alternating direction: favorable, unfavorable, favorable
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 11.0)})
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 14.0), "lighter": _funding("BTC", 12.0)})
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 11.0)})

    flips = state.get_recent_flip_count("hyperliquid", "lighter", "BTC", lookback_samples=6)

    assert flips == 2


@pytest.mark.asyncio
async def test_market_state_flip_count_zero_when_stable() -> None:
    state = MarketState(sample_interval_s=3600)

    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 11.0)})
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 6.0), "lighter": _funding("BTC", 12.0)})
    await state.record_snapshot("BTC", {"hyperliquid": _funding("BTC", 4.0), "lighter": _funding("BTC", 10.0)})

    flips = state.get_recent_flip_count("hyperliquid", "lighter", "BTC", lookback_samples=6)

    assert flips == 0


@pytest.mark.asyncio
async def test_market_state_records_basis_bps_in_snapshot() -> None:
    state = MarketState(sample_interval_s=3600)

    await state.record_snapshot(
        "BTC",
        {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 11.0)},
        tickers={"hyperliquid": _ticker("BTC", "102"), "lighter": _ticker("BTC", "100")},
    )

    history = state.get_snapshots("BTC")
    assert len(history) == 1
    # (102 - 100) / 101 * 10000 ≈ 198.02 bps
    assert history[0].basis_bps is not None
    assert abs(history[0].basis_bps - 198.02) < 0.1


@pytest.mark.asyncio
async def test_market_state_basis_trend_returns_none_without_data() -> None:
    state = MarketState(sample_interval_s=3600)

    assert state.get_basis_trend("hyperliquid", "lighter", "BTC") is None


@pytest.mark.asyncio
async def test_market_state_basis_trend_returns_none_with_single_snapshot() -> None:
    state = MarketState(sample_interval_s=3600)

    await state.record_snapshot(
        "BTC",
        {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 11.0)},
        tickers={"hyperliquid": _ticker("BTC", "102"), "lighter": _ticker("BTC", "100")},
    )

    assert state.get_basis_trend("hyperliquid", "lighter", "BTC") is None


@pytest.mark.asyncio
async def test_market_state_basis_trend_positive_when_spread_widens() -> None:
    state = MarketState(sample_interval_s=3600)

    # short=lighter, long=HL -> directional = lighter - HL (sign=-1 for stored HL-Lighter)
    # Stored: snap1 = (102-100)/101*10000 ≈ 198, snap2 = (103-100)/101.5*10000 ≈ 295
    # Directional: snap1 = -(198) = -198, snap2 = -(295) = -295  -> slope negative
    # But with short=HL, long=Lighter: directional = stored -> slope positive
    await state.record_snapshot(
        "ETH",
        {"hyperliquid": _funding("ETH", 20.0), "lighter": _funding("ETH", 5.0)},
        tickers={"hyperliquid": _ticker("ETH", "100"), "lighter": _ticker("ETH", "100")},
    )
    await state.record_snapshot(
        "ETH",
        {"hyperliquid": _funding("ETH", 20.0), "lighter": _funding("ETH", 5.0)},
        tickers={"hyperliquid": _ticker("ETH", "102"), "lighter": _ticker("ETH", "100")},
    )

    # short=HL -> sign=+1, stored goes from 0 to ~198 -> positive slope
    trend = state.get_basis_trend("lighter", "hyperliquid", "ETH")
    assert trend is not None
    assert trend > 0


@pytest.mark.asyncio
async def test_market_state_basis_trend_negative_when_spread_narrows() -> None:
    state = MarketState(sample_interval_s=3600)

    await state.record_snapshot(
        "ETH",
        {"hyperliquid": _funding("ETH", 20.0), "lighter": _funding("ETH", 5.0)},
        tickers={"hyperliquid": _ticker("ETH", "102"), "lighter": _ticker("ETH", "100")},
    )
    await state.record_snapshot(
        "ETH",
        {"hyperliquid": _funding("ETH", 20.0), "lighter": _funding("ETH", 5.0)},
        tickers={"hyperliquid": _ticker("ETH", "100"), "lighter": _ticker("ETH", "100")},
    )

    # short=HL -> sign=+1, stored goes from ~198 to 0 -> negative slope
    trend = state.get_basis_trend("lighter", "hyperliquid", "ETH")
    assert trend is not None
    assert trend < 0


@pytest.mark.asyncio
async def test_market_state_basis_trend_returns_none_for_invalid_exchange_pair() -> None:
    state = MarketState(sample_interval_s=3600)

    await state.record_snapshot(
        "BTC",
        {"hyperliquid": _funding("BTC", 5.0), "lighter": _funding("BTC", 11.0)},
        tickers={"hyperliquid": _ticker("BTC", "102"), "lighter": _ticker("BTC", "100")},
    )
    await state.record_snapshot(
        "BTC",
        {"hyperliquid": _funding("BTC", 6.0), "lighter": _funding("BTC", 12.0)},
        tickers={"hyperliquid": _ticker("BTC", "103"), "lighter": _ticker("BTC", "100")},
    )

    assert state.get_basis_trend("unknown", "hyperliquid", "BTC") is None
    assert state.get_basis_trend("hyperliquid", "unknown", "BTC") is None
    assert state.get_basis_trend("hyperliquid", "hyperliquid", "BTC") is None


@pytest.mark.asyncio
async def test_market_state_basis_trend_uses_snapshot_index_distance_with_gaps() -> None:
    state = MarketState(sample_interval_s=3600)

    # snap0 basis = 0 bps
    await state.record_snapshot(
        "BTC",
        {"hyperliquid": _funding("BTC", 20.0), "lighter": _funding("BTC", 5.0)},
        tickers={"hyperliquid": _ticker("BTC", "100"), "lighter": _ticker("BTC", "100")},
    )

    # snap1 has no tickers -> basis_bps None (gap)
    await state.record_snapshot(
        "BTC",
        {"hyperliquid": _funding("BTC", 20.0), "lighter": _funding("BTC", 5.0)},
    )

    # snap2 basis ~= 198.02 bps
    await state.record_snapshot(
        "BTC",
        {"hyperliquid": _funding("BTC", 20.0), "lighter": _funding("BTC", 5.0)},
        tickers={"hyperliquid": _ticker("BTC", "102"), "lighter": _ticker("BTC", "100")},
    )

    # Slope should be divided by full span (2 samples), not by count-1 (=1).
    trend = state.get_basis_trend("lighter", "hyperliquid", "BTC", lookback_samples=6)
    assert trend is not None
    assert abs(trend - 99.01) < 0.2