from src.core.config import Settings
from src.core.models import ArbitrageOpportunity, FundingRate, Ticker
from src.core.state import MarketState


def find_opportunities_from_state(state: MarketState, settings: Settings) -> list[ArbitrageOpportunity]:
    """Find opportunities using current MarketState cache (zero I/O)."""
    hl_rates = state.get_funding(exchange="hyperliquid")
    aster_rates = state.get_funding(exchange="aster")
    hl_tickers = state.get_tickers(exchange="hyperliquid")
    aster_tickers = state.get_tickers(exchange="aster")
    return find_opportunities(hl_rates, aster_rates, hl_tickers, aster_tickers, settings)


def find_opportunities(
    hl_rates: dict[str, FundingRate],
    aster_rates: dict[str, FundingRate],
    hl_tickers: dict[str, Ticker],
    aster_tickers: dict[str, Ticker],
    settings: Settings,
) -> list[ArbitrageOpportunity]:
    """Find funding arbitrage opportunities between Hyperliquid and Aster."""
    common_symbols = set(hl_rates.keys()) & set(aster_rates.keys())

    # Fee impact annualized to compare with APR:
    # roundtrip fee is paid once per entry+exit cycle
    # Annualize: (fee_per_side * 2) / (hold_hours / 8760)
    roundtrip_fee_pct = settings.fee_per_side * 2
    fee_apr = roundtrip_fee_pct * (8760 / settings.expected_hold_hours)

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

        # Basis: price difference between venues
        basis_bps = 0.0
        hl_tick = hl_tickers.get(symbol)
        aster_tick = aster_tickers.get(symbol)
        if hl_tick and aster_tick and hl_tick.mark_price > 0:
            price_diff = float(aster_tick.mark_price - hl_tick.mark_price)
            mid = float(hl_tick.mark_price + aster_tick.mark_price) / 2
            basis_bps = (price_diff / mid) * 10000

        # Combined score: funding edge - fees + weighted basis contribution
        combined_score = funding_diff_apr - fee_apr + (basis_bps * settings.basis_weight)

        if combined_score < settings.min_score_apr:
            continue

        opportunities.append(
            ArbitrageOpportunity(
                symbol=symbol,
                long_exchange=long_exchange,
                short_exchange=short_exchange,
                long_rate_apr=round(long_rate_apr, 2),
                short_rate_apr=round(short_rate_apr, 2),
                funding_diff_apr=round(funding_diff_apr, 2),
                basis_bps=round(basis_bps, 2),
                combined_score=round(combined_score, 2),
            )
        )

    opportunities.sort(key=lambda o: o.combined_score, reverse=True)
    return opportunities
