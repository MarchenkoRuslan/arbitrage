from decimal import Decimal

from src.core.normalize import (
    aster_symbol_to_normalized,
    hl_symbol_to_normalized,
    normalized_to_aster,
    rate_to_apr,
)


def test_rate_to_apr_converts_periodic_rate_to_annual_percentage() -> None:
    apr = rate_to_apr(Decimal("0.0001"), period_hours=8)

    assert apr == 10.95


def test_symbol_normalizers_round_trip_between_exchange_formats() -> None:
    assert hl_symbol_to_normalized("btc") == "BTC"
    assert aster_symbol_to_normalized("ethusdt") == "ETH"
    assert aster_symbol_to_normalized("ANSEM") == "ANSEM"
    assert normalized_to_aster("BTC") == "BTCUSDT"