from decimal import Decimal

from src.core.models import ArbitrageOpportunity
from src.core.state import PollCache


def _opp(symbol: str, net_apr: float = 0.75) -> ArbitrageOpportunity:
    return ArbitrageOpportunity(
        symbol=symbol,
        long_exchange="hyperliquid",
        short_exchange="lighter",
        long_base_symbol=symbol,
        short_base_symbol=symbol,
        net_apr=net_apr,
        apr_1h=0.8,
        apr_24h=0.7,
        apr_7d=0.6,
        gross_spread_hourly=0.0001,
        long_funding_rate=Decimal("0.0001"),
        short_funding_rate=Decimal("0.0003"),
        volume_24h_usd=1_000_000.0,
        long_max_leverage=10,
        short_max_leverage=10,
    )


def test_poll_cache_starts_empty_and_stale() -> None:
    cache = PollCache()
    assert cache.get_opportunities() == []
    assert cache.is_stale() is True
    assert cache.last_updated() is None


def test_poll_cache_update_stores_opportunities() -> None:
    cache = PollCache()
    opps = [_opp("BTC"), _opp("ETH")]
    cache.update(opps)
    result = cache.get_opportunities()
    assert len(result) == 2
    assert result[0].symbol == "BTC"
    assert result[1].symbol == "ETH"


def test_poll_cache_is_fresh_after_update() -> None:
    cache = PollCache()
    cache.update([_opp("BTC")])
    assert cache.is_stale(max_age_s=60.0) is False
    assert cache.last_updated() is not None


def test_poll_cache_returns_copy_of_opportunities() -> None:
    cache = PollCache()
    opps = [_opp("BTC")]
    cache.update(opps)
    result = cache.get_opportunities()
    result.clear()
    assert len(cache.get_opportunities()) == 1


def test_poll_cache_update_replaces_previous() -> None:
    cache = PollCache()
    cache.update([_opp("BTC"), _opp("ETH")])
    cache.update([_opp("SOL")])
    result = cache.get_opportunities()
    assert len(result) == 1
    assert result[0].symbol == "SOL"
