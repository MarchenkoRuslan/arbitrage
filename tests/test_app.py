import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.core.app import App
from src.core.config import Settings
from src.core.models import FundingRate, Ticker


def _funding(symbol: str, apr: float) -> FundingRate:
    from datetime import UTC, datetime

    return FundingRate(
        symbol=symbol, period_hours=1,
        apr=apr, timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _ticker(symbol: str) -> Ticker:
    return Ticker(symbol=symbol, mark_price=Decimal("100"), index_price=Decimal("100"),
                  volume_24h=1_000_000)


@pytest.mark.asyncio
async def test_poll_once_continues_when_hyperliquid_fails() -> None:
    settings = Settings(
        min_score_bps=0.0, min_volume_24h=0.0, min_persistence_hours=0.0,
        hl_fee_per_side=0.0, lighter_fee_per_side=0.0,
        expected_hold_hours=72.0, basis_weight=0.0, stale_data_s=60.0,
    )
    app = App(settings)

    # HL raises, Lighter succeeds
    app.hl.get_market_data = AsyncMock(side_effect=Exception("HL down"))
    app.lighter.get_market_data = AsyncMock(return_value=(
        {"BTC": _funding("BTC", 10.0)},
        {"BTC": _ticker("BTC")},
    ))

    await app.poll_once()

    # Lighter data should be in state
    lighter_funding = app.state.get_funding("lighter")
    assert "BTC" in lighter_funding
    assert lighter_funding["BTC"].apr == 10.0

    # HL should have no data
    assert app.state.get_funding("hyperliquid") == {}

    await app.shutdown()


@pytest.mark.asyncio
async def test_poll_once_continues_when_lighter_fails() -> None:
    settings = Settings(
        min_score_bps=0.0, min_volume_24h=0.0, min_persistence_hours=0.0,
        hl_fee_per_side=0.0, lighter_fee_per_side=0.0,
        expected_hold_hours=72.0, basis_weight=0.0, stale_data_s=60.0,
    )
    app = App(settings)

    # HL succeeds, Lighter raises
    app.hl.get_market_data = AsyncMock(return_value=(
        {"BTC": _funding("BTC", 15.0)},
        {"BTC": _ticker("BTC")},
    ))
    app.lighter.get_market_data = AsyncMock(side_effect=Exception("Lighter down"))

    await app.poll_once()

    # HL data should be in state
    hl_funding = app.state.get_funding("hyperliquid")
    assert "BTC" in hl_funding
    assert hl_funding["BTC"].apr == 15.0

    # Lighter should have no data
    assert app.state.get_funding("lighter") == {}

    await app.shutdown()


@pytest.mark.asyncio
async def test_poll_once_skips_cycle_when_both_fail() -> None:
    settings = Settings(
        min_score_bps=0.0, min_volume_24h=0.0, min_persistence_hours=0.0,
        hl_fee_per_side=0.0, lighter_fee_per_side=0.0,
        expected_hold_hours=72.0, basis_weight=0.0, stale_data_s=60.0,
    )
    app = App(settings)

    app.hl.get_market_data = AsyncMock(side_effect=Exception("HL down"))
    app.lighter.get_market_data = AsyncMock(side_effect=Exception("Lighter down"))

    # Should not raise — graceful skip
    await app.poll_once()

    assert app.state.get_funding("hyperliquid") == {}
    assert app.state.get_funding("lighter") == {}

    await app.shutdown()


@pytest.mark.asyncio
async def test_poll_once_records_snapshots_only_for_common_symbols() -> None:
    settings = Settings(
        min_score_bps=0.0, min_volume_24h=0.0, min_persistence_hours=0.0,
        hl_fee_per_side=0.0, lighter_fee_per_side=0.0,
        expected_hold_hours=72.0, basis_weight=0.0, stale_data_s=60.0,
    )
    app = App(settings)

    app.hl.get_market_data = AsyncMock(return_value=(
        {"BTC": _funding("BTC", 5.0), "ETH": _funding("ETH", 8.0)},
        {"BTC": _ticker("BTC"), "ETH": _ticker("ETH")},
    ))
    app.lighter.get_market_data = AsyncMock(return_value=(
        {"BTC": _funding("BTC", 12.0), "SOL": _funding("SOL", 6.0)},
        {"BTC": _ticker("BTC"), "SOL": _ticker("SOL")},
    ))

    await app.poll_once()

    # Only BTC is common — should have snapshot
    assert "BTC" in app.state._snapshots
    assert len(app.state._snapshots["BTC"]) == 1
    # ETH and SOL should NOT have snapshots
    assert "ETH" not in app.state._snapshots
    assert "SOL" not in app.state._snapshots

    await app.shutdown()


@pytest.mark.asyncio
async def test_poll_once_counts_failed_when_update_callback_raises() -> None:
    settings = Settings(
        min_score_bps=0.0, min_volume_24h=0.0, min_persistence_hours=0.0,
        hl_fee_per_side=0.0, lighter_fee_per_side=0.0,
        expected_hold_hours=72.0, basis_weight=0.0, stale_data_s=60.0,
    )
    app = App(settings)

    app.hl.get_market_data = AsyncMock(return_value=(
        {"BTC": _funding("BTC", 5.0)},
        {"BTC": _ticker("BTC")},
    ))
    app.lighter.get_market_data = AsyncMock(return_value=(
        {"BTC": _funding("BTC", 15.0)},
        {"BTC": _ticker("BTC")},
    ))

    async def _raise(_: list) -> None:
        raise RuntimeError("callback failed")

    app._on_update = _raise

    with pytest.raises(RuntimeError):
        await app.poll_once()

    assert app.poll_count_total == 1
    assert app.poll_count_success == 0
    assert app.poll_count_failed == 1
    assert app.last_poll_finished_at is not None
    assert app.last_poll_duration_ms is not None

    await app.shutdown()


@pytest.mark.asyncio
async def test_poll_once_cancellation_does_not_count_success_or_failure() -> None:
    settings = Settings(
        min_score_bps=0.0, min_volume_24h=0.0, min_persistence_hours=0.0,
        hl_fee_per_side=0.0, lighter_fee_per_side=0.0,
        expected_hold_hours=72.0, basis_weight=0.0, stale_data_s=60.0,
    )
    app = App(settings)

    gate = asyncio.Event()

    async def _block() -> tuple[dict, dict]:
        await gate.wait()
        return {}, {}

    app.hl.get_market_data = AsyncMock(side_effect=_block)
    app.lighter.get_market_data = AsyncMock(side_effect=_block)

    task = asyncio.create_task(app.poll_once())
    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert app.poll_count_total == 0
    assert app.poll_count_success == 0
    assert app.poll_count_failed == 0
    assert app.last_poll_finished_at is not None
    assert app.last_poll_duration_ms is not None

    await app.shutdown()
