import math
from datetime import datetime

from src.core.config import Settings
from src.core.models import ArbitrageOpportunity, FundingRate, Ticker
from src.core.state import MarketState


def _hours_to_next_funding(ts: datetime, period_hours: int) -> float | None:
    if period_hours <= 0:
        return None
    period_s = period_hours * 3600
    elapsed_s = ts.timestamp() % period_s
    remaining_s = period_s - elapsed_s
    if remaining_s == period_s:
        remaining_s = 0.0
    return remaining_s / 3600


def _funding_timing_asymmetry_hours(
    long_h2f: float | None,
    short_h2f: float | None,
    long_period_h: int,
    short_period_h: int,
) -> float | None:
    if long_h2f is None or short_h2f is None:
        return None
    if long_period_h <= 0 or short_period_h <= 0 or long_period_h != short_period_h:
        return None
    period = float(long_period_h)
    diff = abs(short_h2f - long_h2f)
    return min(diff, period - diff)


def find_opportunities_from_state(state: MarketState, settings: Settings) -> list[ArbitrageOpportunity]:
    """Find opportunities using current MarketState cache (zero I/O)."""
    hl_rates = state.get_funding("hyperliquid")
    lighter_rates = state.get_funding("lighter")
    hl_tickers = state.get_tickers("hyperliquid")
    lighter_tickers = state.get_tickers("lighter")

    directions: dict[str, tuple[str, str]] = {}
    persistence_by_symbol: dict[str, float] = {}
    fresh_symbols: set[str] = set()
    for symbol in set(hl_rates) & set(lighter_rates) & set(hl_tickers) & set(lighter_tickers):
        if state.is_stale("hyperliquid", symbol, max_age_s=settings.stale_data_s):
            continue
        if state.is_stale("lighter", symbol, max_age_s=settings.stale_data_s):
            continue

        if hl_rates[symbol].apr > lighter_rates[symbol].apr:
            long_exchange = "lighter"
            short_exchange = "hyperliquid"
        else:
            long_exchange = "hyperliquid"
            short_exchange = "lighter"

        persistence_hours = state.get_funding_persistence_hours(long_exchange, short_exchange, symbol)
        if persistence_hours < settings.min_persistence_hours:
            continue

        directions[symbol] = (long_exchange, short_exchange)
        persistence_by_symbol[symbol] = persistence_hours
        fresh_symbols.add(symbol)

    opportunities = find_opportunities(
        {s: hl_rates[s] for s in fresh_symbols},
        {s: lighter_rates[s] for s in fresh_symbols},
        {s: hl_tickers[s] for s in fresh_symbols},
        {s: lighter_tickers[s] for s in fresh_symbols},
        settings,
        directions=directions,
    )

    for opp in opportunities:
        opp.persistence_hours = round(persistence_by_symbol.get(opp.symbol, 0.0), 2)
        trend = state.get_basis_trend(opp.long_exchange, opp.short_exchange, opp.symbol)
        opp.basis_trend = round(trend, 4) if trend is not None else None

    return opportunities


def find_opportunities(
    hl_rates: dict[str, FundingRate],
    lighter_rates: dict[str, FundingRate],
    hl_tickers: dict[str, Ticker],
    lighter_tickers: dict[str, Ticker],
    settings: Settings,
    directions: dict[str, tuple[str, str]] | None = None,
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

        min_vol = min(hl_tick.volume_24h, lighter_tick.volume_24h)
        if min_vol < settings.min_volume_24h:
            continue

        # OI filter: require minimum reported OI across exchanges above threshold
        if settings.min_open_interest > 0:
            hl_oi = hl_tick.open_interest
            lighter_oi = lighter_tick.open_interest
            if hl_oi is None and lighter_oi is None:
                continue
            effective_oi = min(
                hl_oi if hl_oi is not None else float("inf"),
                lighter_oi if lighter_oi is not None else float("inf"),
            )
            if effective_oi < settings.min_open_interest:
                continue

        # Use pre-computed direction if available, otherwise compute here
        if directions and symbol in directions:
            long_exchange, short_exchange = directions[symbol]
        elif hl.apr > lighter.apr:
            long_exchange, short_exchange = "lighter", "hyperliquid"
        else:
            long_exchange, short_exchange = "hyperliquid", "lighter"

        if long_exchange == "hyperliquid":
            long_rate_apr, short_rate_apr = hl.apr, lighter.apr
            long_rate, short_rate = hl, lighter
            long_tick, short_tick = hl_tick, lighter_tick
        else:
            long_rate_apr, short_rate_apr = lighter.apr, hl.apr
            long_rate, short_rate = lighter, hl
            long_tick, short_tick = lighter_tick, hl_tick

        funding_diff_apr = short_rate_apr - long_rate_apr

        # Skip zero funding edge — not a funding arbitrage opportunity
        if funding_diff_apr <= 0:
            continue

        funding_edge_bps = funding_diff_apr * (hold_hours / 8760) * 100
        hourly_funding_bps = funding_edge_bps / hold_hours if hold_hours > 0 else 0.0

        # Directional basis: positive when the short leg is richer than the long leg.
        # Use index_price as denominator when both legs provide it (more accurate).
        basis_bps = 0.0
        if long_tick.mark_price > 0 and short_tick.mark_price > 0:
            if long_tick.index_price is not None and short_tick.index_price is not None:
                idx_avg = float(long_tick.index_price + short_tick.index_price) / 2
                denom = idx_avg if idx_avg > 0 else float(long_tick.mark_price + short_tick.mark_price) / 2
            else:
                denom = float(long_tick.mark_price + short_tick.mark_price) / 2
            basis_bps = float(short_tick.mark_price - long_tick.mark_price) / denom * 10000

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

        long_h2f = _hours_to_next_funding(long_rate.timestamp, long_rate.period_hours)
        short_h2f = _hours_to_next_funding(short_rate.timestamp, short_rate.period_hours)
        asymmetry_h = _funding_timing_asymmetry_hours(
            long_h2f,
            short_h2f,
            long_rate.period_hours,
            short_rate.period_hours,
        )
        timing_penalty_bps = (
            asymmetry_h * settings.timing_penalty_bps_per_hour
            if asymmetry_h is not None
            else 0.0
        )

        liquidity_bps = 0.0
        if settings.liquidity_weight > 0 and settings.min_volume_24h > 0:
            vol_ratio = min_vol / settings.min_volume_24h
            liquidity_bps = math.log2(max(vol_ratio, 1.0)) * settings.liquidity_weight

        if min_vol >= settings.min_volume_24h * 10:
            liquidity_tier = "H"
        elif min_vol >= settings.min_volume_24h * 3:
            liquidity_tier = "M"
        else:
            liquidity_tier = "L"

        combined_score = funding_edge_bps - roundtrip_fee_bps + basis_bonus_bps + liquidity_bps - timing_penalty_bps

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
                long_hours_to_next_funding=round(long_h2f, 2) if long_h2f is not None else None,
                short_hours_to_next_funding=round(short_h2f, 2) if short_h2f is not None else None,
                funding_timing_asymmetry_hours=round(asymmetry_h, 2) if asymmetry_h is not None else None,
                funding_timing_penalty_bps=round(timing_penalty_bps, 2),
                min_profitable_hours=round(min_profitable_hours, 2) if min_profitable_hours is not None else None,
                hours_to_breakeven=round(hours_to_breakeven, 2) if hours_to_breakeven is not None else None,
                combined_score=round(combined_score, 2),
                liquidity_tier=liquidity_tier,
            )
        )

    opportunities.sort(key=lambda o: o.combined_score, reverse=True)
    return opportunities
