from src.core.config import Settings
from src.core.models import ArbitrageOpportunity


def filter_opportunities(
    opps: list[ArbitrageOpportunity],
    settings: Settings,
) -> list[ArbitrageOpportunity]:
    """Filter and rank VOOI funding strategy opportunities for DEX-to-DEX arbitrage.

    Filters applied (in order):
    1. Volume: both legs must have volume_24h_usd >= min_volume_24h
    2. Positive spread: grossSpreadHourly > 0
    3. Multi-timeframe APR sanity: apr_1h > 0 and apr_24h > 0
    4. Optional 7d check: apr_7d > 0 when present
    5. Max leverage sanity: both legs must have maxLeverage >= 2
    6. Min net APR: net_apr >= min_net_apr
    7. Spike filter (optional): apr_1h / apr_24h <= max_apr_ratio_1h_24h
    8. Spike filter (optional): apr_24h / apr_7d <= max_apr_ratio_24h_7d
    """
    results: list[ArbitrageOpportunity] = []
    for opp in opps:
        if opp.volume_24h_usd < settings.min_volume_24h:
            continue
        if opp.gross_spread_hourly <= 0:
            continue
        if opp.apr_1h <= 0 or opp.apr_24h <= 0:
            continue
        if opp.apr_7d is not None and opp.apr_7d <= 0:
            continue
        if opp.long_max_leverage < 2 or opp.short_max_leverage < 2:
            continue
        if opp.net_apr < settings.min_net_apr:
            continue
        if settings.max_apr_ratio_1h_24h > 0 and opp.apr_24h > 0:
            if opp.apr_1h / opp.apr_24h > settings.max_apr_ratio_1h_24h:
                continue
        if settings.max_apr_ratio_24h_7d > 0 and opp.apr_7d is not None and opp.apr_7d > 0:
            if opp.apr_24h / opp.apr_7d > settings.max_apr_ratio_24h_7d:
                continue
        results.append(opp)

    results.sort(key=lambda o: o.net_apr, reverse=True)
    return results
