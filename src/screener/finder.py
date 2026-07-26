from src.core.config import Settings
from src.core.models import ArbitrageOpportunity, FundingRate, Ticker
from src.core.state import MarketState


def find_opportunities_from_state(state: MarketState, settings: Settings) -> list[ArbitrageOpportunity]:
    """Find opportunities using current MarketState cache (zero I/O)."""
    hl_rates = state.get_funding("hyperliquid")
    lighter_rates = state.get_funding("lighter")
    hl_tickers = state.get_tickers("hyperliquid")
    lighter_tickers = state.get_tickers("lighter")

    fresh_symbols: set[str] = set()
    for symbol in set(hl_rates) & set(lighter_rates) & set(hl_tickers) & set(lighter_tickers):
        if state.is_stale("hyperliquid", symbol, max_age_s=settings.stale_data_s):
            continue
        if state.is_stale("lighter", symbol, max_age_s=settings.stale_data_s):
            continue
        fresh_symbols.add(symbol)

    return find_opportunities(
        {s: hl_rates[s] for s in fresh_symbols},
        {s: lighter_rates[s] for s in fresh_symbols},
        {s: hl_tickers[s] for s in fresh_symbols},
        {s: lighter_tickers[s] for s in fresh_symbols},
        settings,
    )


def find_opportunities(
    hl_rates: dict[str, FundingRate],
    lighter_rates: dict[str, FundingRate],
    hl_tickers: dict[str, Ticker],
    lighter_tickers: dict[str, Ticker],
    settings: Settings,
) -> list[ArbitrageOpportunity]:
    """Find funding arbitrage opportunities between Hyperliquid and Lighter."""
    roundtrip_fee_bps = (settings.hl_fee_per_side + settings.lighter_fee_per_side) * 2 * 100
    hold_hours = settings.expected_hold_hours

    opportunities: list[ArbitrageOpportunity] = []

    for symbol in set(hl_rates) & set(lighter_rates):
        hl = hl_rates[symbol]
        lighter = lighter_rates[symbol]
        hl_tick = hl_tickers.get(symbol)
        lighter_tick = lighter_tickers.get(symbol)
        if hl_tick is None or lighter_tick is None:
            continue

        if min(hl_tick.volume_24h, lighter_tick.volume_24h) < settings.min_volume_24h:
            continue

        if hl.apr > lighter.apr:
            long_exchange, short_exchange = "lighter", "hyperliquid"
            long_rate_apr, short_rate_apr = lighter.apr, hl.apr
            long_tick, short_tick = lighter_tick, hl_tick
        else:
            long_exchange, short_exchange = "hyperliquid", "lighter"
            long_rate_apr, short_rate_apr = hl.apr, lighter.apr
            long_tick, short_tick = hl_tick, lighter_tick

        funding_diff_apr = short_rate_apr - long_rate_apr
        funding_edge_bps = funding_diff_apr * (hold_hours / 8760) * 100
        hourly_funding_bps = funding_edge_bps / hold_hours if hold_hours > 0 else 0.0

        basis_bps = 0.0
        if long_tick.mark_price > 0 and short_tick.mark_price > 0:
            mid = float(long_tick.mark_price + short_tick.mark_price) / 2
            basis_bps = float(short_tick.mark_price - long_tick.mark_price) / mid * 10000

        hours_to_breakeven = None
        if basis_bps < 0 and hourly_funding_bps > 0:
            hours_to_cover = abs(basis_bps) / hourly_funding_bps
            hours_to_breakeven = hours_to_cover
            if hours_to_cover > hold_hours:
                continue
        elif basis_bps < 0 and hourly_funding_bps <= 0:
            continue

        basis_bonus_bps = max(0.0, basis_bps) * settings.basis_weight
        min_profitable_hours = roundtrip_fee_bps / hourly_funding_bps if hourly_funding_bps > 0 else None
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
