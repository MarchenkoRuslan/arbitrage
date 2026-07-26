from decimal import Decimal

import pytest

from src.core.normalize import hl_symbol_to_normalized, lighter_symbol_to_normalized, rate_to_apr


def test_rate_to_apr_converts_1h_periodic_rate() -> None:
    assert rate_to_apr(Decimal("0.0001"), period_hours=1) == pytest.approx(87.6)


def test_rate_to_apr_converts_8h_periodic_rate() -> None:
    assert rate_to_apr(Decimal("0.0001"), period_hours=8) == pytest.approx(10.95)


def test_hl_and_lighter_symbol_normalizers_uppercase() -> None:
    assert hl_symbol_to_normalized("btc") == "BTC"
    assert hl_symbol_to_normalized("ETH") == "ETH"
    assert lighter_symbol_to_normalized("sol") == "SOL"
    assert lighter_symbol_to_normalized("DOGE") == "DOGE"
