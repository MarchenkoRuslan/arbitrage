from src.core.config import Settings
from src.core.models import ArbitrageOpportunity, FundingRate, Ticker
from src.core.state import MarketState


def find_opportunities_from_state(state: MarketState, settings: Settings) -> list[ArbitrageOpportunity]:
    """Find opportunities using current MarketState cache (zero I/O)."""
    hl_rates = state.get_funding(exchange="hyperliquid")
    aster_rates = state.get_funding(exchange="aster")
    hl_tickers = state.get_tickers(exchange="hyperliquid")
    aster_tickers = state.get_tickers(exchange="aster")

    persistence_by_symbol: dict[str, float] = {}
    fresh_symbols: set[str] = set()
    for symbol in set(hl_rates) & set(aster_rates) & set(hl_tickers) & set(aster_tickers):
        if state.is_stale("hyperliquid", symbol, max_age_s=settings.stale_data_s):
            continue
        if state.is_stale("aster", symbol, max_age_s=settings.stale_data_s):
            continue

        if hl_rates[symbol].apr > aster_rates[symbol].apr:
            long_exchange = "aster"
            short_exchange = "hyperliquid"
        else:
            long_exchange = "hyperliquid"
            short_exchange = "aster"

        persistence_hours = state.get_funding_persistence_hours(long_exchange, short_exchange, symbol)
        if persistence_hours < settings.min_persistence_hours:
            continue

        persistence_by_symbol[symbol] = persistence_hours
        fresh_symbols.add(symbol)

    opportunities = find_opportunities(
        {symbol: hl_rates[symbol] for symbol in fresh_symbols},
        {symbol: aster_rates[symbol] for symbol in fresh_symbols},
        {symbol: hl_tickers[symbol] for symbol in fresh_symbols},
        {symbol: aster_tickers[symbol] for symbol in fresh_symbols},
        settings,
    )

    for opportunity in opportunities:
        opportunity.persistence_hours = round(persistence_by_symbol.get(opportunity.symbol, 0.0), 2)

    return opportunities


def find_opportunities(
    hl_rates: dict[str, FundingRate],
    aster_rates: dict[str, FundingRate],
    hl_tickers: dict[str, Ticker],
    aster_tickers: dict[str, Ticker],
    settings: Settings,
) -> list[ArbitrageOpportunity]:
    """Find funding arbitrage opportunities between Hyperliquid and Aster."""
    common_symbols = set(hl_rates.keys()) & set(aster_rates.keys())

    hold_hours = settings.expected_hold_hours
    roundtrip_fee_bps = (settings.hl_fee_per_side + settings.aster_fee_per_side) * 2 * 100

    opportunities: list[ArbitrageOpportunity] = []

    for symbol in common_symbols:
        hl = hl_rates[symbol]
        aster = aster_rates[symbol]

        # Determine direction: long where funding is lower, short where higher
        if hl.apr > aster.apr:
            long_exchange = "aster"
            short_exchange = "hyperliquid"
            long_rate_apr = aster.apr
            short_rate_apr = hl.apr
        else:
            long_exchange = "hyperliquid"
            short_exchange = "aster"
            long_rate_apr = hl.apr
            short_rate_apr = aster.apr

        funding_diff_apr = short_rate_apr - long_rate_apr
        funding_edge_bps = funding_diff_apr * (hold_hours / 8760) * 100
        hourly_funding_bps = funding_edge_bps / hold_hours if hold_hours > 0 else 0.0

        # Directional basis is positive only when the short leg is richer than the long leg.
        basis_bps = 0.0
        hl_tick = hl_tickers.get(symbol)
        aster_tick = aster_tickers.get(symbol)
        if hl_tick is None or aster_tick is None:
            continue

        if min(hl_tick.volume_24h, aster_tick.volume_24h) < settings.min_volume_24h:
            continue

        if hl_tick.mark_price > 0:
            short_price = hl_tick.mark_price if short_exchange == "hyperliquid" else aster_tick.mark_price
            long_price = aster_tick.mark_price if long_exchange == "aster" else hl_tick.mark_price
            mid = float(hl_tick.mark_price + aster_tick.mark_price) / 2
            basis_bps = (float(short_price - long_price) / mid) * 10000

        hours_to_breakeven = None
        if basis_bps < 0 and hold_hours > 0:
            if hourly_funding_bps <= 0:
                continue

            hours_to_cover = abs(basis_bps) / hourly_funding_bps
            hours_to_breakeven = hours_to_cover
            if hours_to_cover > hold_hours:
                continue

        basis_bonus_bps = max(0.0, basis_bps) * settings.basis_weight
        min_profitable_hours = None
        if hourly_funding_bps > 0:
            min_profitable_hours = roundtrip_fee_bps / hourly_funding_bps

        combined_score = funding_edge_bps - roundtrip_fee_bps + basis_bonus_bps

        if combined_score < settings.min_score_bps:
            continue

        opportunities.append(
            ArbitrageOpportunity(
                symbol=symbol,
                long_exchange=long_exchange,
                short_exchange=short_exchange,
                long_rate_apr=round(long_rate_apr, 2),
                short_rate_apr=round(short_rate_apr, 2),
                funding_diff_apr=round(funding_diff_apr, 2),
                funding_edge_bps=round(funding_edge_bps, 2),
                basis_bps=round(basis_bps, 2),
                basis_bonus_bps=round(basis_bonus_bps, 2),
                fee_impact_bps=round(roundtrip_fee_bps, 2),
                min_profitable_hours=round(min_profitable_hours, 2) if min_profitable_hours is not None else None,
                hours_to_breakeven=round(hours_to_breakeven, 2) if hours_to_breakeven is not None else None,
                combined_score=round(combined_score, 2),
            )
        )

    opportunities.sort(key=lambda o: o.combined_score, reverse=True)
    return opportunities
