from decimal import Decimal

from src.core.config import Settings
from src.core.models import ArbitrageOpportunity
from src.screener.finder import filter_opportunities


def _opp(
    symbol: str,
    net_apr: float,
    apr_1h: float = 0.5,
    apr_24h: float = 0.4,
    apr_7d: float | None = 0.3,
    volume: float = 500_000.0,
    long_max_lev: int = 10,
    short_max_lev: int = 10,
    long_ex: str = "hyperliquid",
    short_ex: str = "lighter",
    gross_spread_hourly: float = 0.0001,
) -> ArbitrageOpportunity:
    return ArbitrageOpportunity(
        symbol=symbol,
        long_exchange=long_ex,
        short_exchange=short_ex,
        long_base_symbol=symbol,
        short_base_symbol=symbol,
        net_apr=net_apr,
        apr_1h=apr_1h,
        apr_24h=apr_24h,
        apr_7d=apr_7d,
        gross_spread_hourly=gross_spread_hourly,
        long_funding_rate=Decimal("0.0001"),
        short_funding_rate=Decimal("0.0003"),
        volume_24h_usd=volume,
        long_max_leverage=long_max_lev,
        short_max_leverage=short_max_lev,
    )


def test_filter_opportunities_sorts_by_net_apr_descending() -> None:
    settings = Settings(min_net_apr=0.0, min_volume_24h=0.0)
    opps = [_opp("ETH", 0.30), _opp("BTC", 0.75), _opp("SOL", 0.50)]
    result = filter_opportunities(opps, settings)
    assert [o.symbol for o in result] == ["BTC", "SOL", "ETH"]


def test_filter_opportunities_excludes_below_min_net_apr() -> None:
    settings = Settings(min_net_apr=0.50, min_volume_24h=0.0)
    opps = [_opp("BTC", 0.75), _opp("ETH", 0.30)]
    result = filter_opportunities(opps, settings)
    assert [o.symbol for o in result] == ["BTC"]


def test_filter_opportunities_excludes_below_min_volume() -> None:
    settings = Settings(min_net_apr=0.0, min_volume_24h=500_000.0)
    opps = [_opp("BTC", 0.75, volume=1_000_000.0), _opp("ETH", 0.60, volume=100_000.0)]
    result = filter_opportunities(opps, settings)
    assert [o.symbol for o in result] == ["BTC"]


def test_filter_opportunities_excludes_non_positive_spread() -> None:
    settings = Settings(min_net_apr=0.0, min_volume_24h=0.0)
    opps = [
        _opp("BTC", 0.75, gross_spread_hourly=0.0),
        _opp("ETH", 0.60, gross_spread_hourly=0.0001),
    ]
    result = filter_opportunities(opps, settings)
    assert [o.symbol for o in result] == ["ETH"]


def test_filter_opportunities_excludes_spike_by_1h_24h_ratio() -> None:
    settings = Settings(min_net_apr=0.0, min_volume_24h=0.0, max_apr_ratio_1h_24h=3.0)
    # apr_1h / apr_24h = 2.0 / 0.1 = 20.0 > 3.0 -> excluded
    opps = [
        _opp("BTC", 0.75, apr_1h=2.0, apr_24h=0.1),
        _opp("ETH", 0.60, apr_1h=0.5, apr_24h=0.4),
    ]
    result = filter_opportunities(opps, settings)
    assert [o.symbol for o in result] == ["ETH"]


def test_filter_opportunities_excludes_spike_by_24h_7d_ratio() -> None:
    settings = Settings(min_net_apr=0.0, min_volume_24h=0.0, max_apr_ratio_24h_7d=3.0)
    # apr_24h / apr_7d = 1.5 / 0.1 = 15.0 > 3.0 -> excluded
    opps = [
        _opp("BTC", 0.75, apr_24h=1.5, apr_7d=0.1),
        _opp("ETH", 0.60, apr_24h=0.5, apr_7d=0.4),
    ]
    result = filter_opportunities(opps, settings)
    assert [o.symbol for o in result] == ["ETH"]


def test_filter_opportunities_excludes_low_max_leverage() -> None:
    settings = Settings(min_net_apr=0.0, min_volume_24h=0.0)
    opps = [_opp("BTC", 0.75, long_max_lev=1, short_max_lev=10), _opp("ETH", 0.60)]
    result = filter_opportunities(opps, settings)
    assert [o.symbol for o in result] == ["ETH"]


def test_filter_opportunities_skips_7d_check_when_none() -> None:
    settings = Settings(min_net_apr=0.0, min_volume_24h=0.0)
    opps = [_opp("BTC", 0.75, apr_7d=None)]
    result = filter_opportunities(opps, settings)
    assert len(result) == 1


def test_filter_opportunities_returns_empty_for_no_input() -> None:
    settings = Settings()
    result = filter_opportunities([], settings)
    assert result == []
