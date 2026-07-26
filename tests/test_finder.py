from datetime import UTC, datetime
from decimal import Decimal

from src.core.config import Settings
from src.core.models import FundingRate, Ticker
from src.screener.finder import find_opportunities


def _funding(symbol: str, apr: float) -> FundingRate:
    return FundingRate(symbol=symbol, rate=Decimal("0.0001"), period_hours=1, apr=apr,
                       timestamp=datetime(2026, 1, 1, tzinfo=UTC))


def _ticker(symbol: str, mark_price: str, volume_24h: float = 1_000_000) -> Ticker:
    return Ticker(symbol=symbol, mark_price=Decimal(mark_price),
                  index_price=Decimal(mark_price), volume_24h=volume_24h)


def test_find_opportunities_sorts_by_combined_score_and_sets_direction() -> None:
    settings = Settings(min_score_bps=1.0, min_volume_24h=0.0, hl_fee_per_side=0.0,
                        lighter_fee_per_side=0.0, expected_hold_hours=72.0, basis_weight=0.0)
    opps = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 12.0), "ETH": _funding("ETH", 40.0)},
        lighter_rates={"BTC": _funding("BTC", 20.0), "ETH": _funding("ETH", 15.0)},
        hl_tickers={"BTC": _ticker("BTC", "100"), "ETH": _ticker("ETH", "200")},
        lighter_tickers={"BTC": _ticker("BTC", "100"), "ETH": _ticker("ETH", "200")},
        settings=settings,
    )
    assert len(opps) == 2
    assert opps[0].symbol == "ETH"
    assert opps[0].long_exchange == "lighter"
    assert opps[0].short_exchange == "hyperliquid"
    assert opps[1].symbol == "BTC"
    assert opps[1].long_exchange == "hyperliquid"
    assert opps[1].short_exchange == "lighter"


def test_find_opportunities_filters_by_min_score() -> None:
    settings = Settings(min_score_bps=100.0, min_volume_24h=0.0, hl_fee_per_side=0.0,
                        lighter_fee_per_side=0.0, expected_hold_hours=72.0, basis_weight=0.0)
    opps = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 12.0)},
        lighter_rates={"BTC": _funding("BTC", 20.0)},
        hl_tickers={"BTC": _ticker("BTC", "100")},
        lighter_tickers={"BTC": _ticker("BTC", "100")},
        settings=settings,
    )
    assert opps == []


def test_find_opportunities_filters_low_volume() -> None:
    settings = Settings(min_score_bps=1.0, min_volume_24h=2_000_000.0, hl_fee_per_side=0.0,
                        lighter_fee_per_side=0.0, expected_hold_hours=72.0, basis_weight=0.0)
    opps = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 12.0)},
        lighter_rates={"BTC": _funding("BTC", 20.0)},
        hl_tickers={"BTC": _ticker("BTC", "100", volume_24h=1_000_000.0)},
        lighter_tickers={"BTC": _ticker("BTC", "100", volume_24h=500_000.0)},
        settings=settings,
    )
    assert opps == []


def test_find_opportunities_returns_empty_for_no_common_symbols() -> None:
    settings = Settings(min_score_bps=1.0, min_volume_24h=0.0)
    opps = find_opportunities(
        hl_rates={"BTC": _funding("BTC", 12.0)},
        lighter_rates={"ETH": _funding("ETH", 20.0)},
        hl_tickers={"BTC": _ticker("BTC", "100")},
        lighter_tickers={"ETH": _ticker("ETH", "200")},
        settings=settings,
    )
    assert opps == []
