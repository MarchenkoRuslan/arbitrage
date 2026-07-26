from src.core.models import ArbitrageOpportunity


def print_opportunities(opps: list[ArbitrageOpportunity], max_rows: int = 20) -> None:
    """Render DEX opportunities table to stdout."""
    if not opps:
        return

    header = (
        f"{'Symbol':<10} {'Long':<14} {'Short':<14} {'Net APR%':>9} "
        f"{'1h APR%':>9} {'24h APR%':>9} {'7d APR%':>9} {'Vol 24h USD':>14} {'MaxLev':>8}"
    )
    print("\n" + header)
    print("-" * len(header))

    for opp in opps[:max_rows]:
        apr_7d_str = f"{opp.apr_7d * 100:>8.2f}" if opp.apr_7d is not None else "     n/a"
        long_label = f"{opp.long_exchange}:{opp.long_base_symbol}"[:14]
        short_label = f"{opp.short_exchange}:{opp.short_base_symbol}"[:14]
        max_lev = min(opp.long_max_leverage, opp.short_max_leverage)
        print(
            f"{opp.symbol:<10} {long_label:<14} {short_label:<14} "
            f"{opp.net_apr * 100:>9.2f} {opp.apr_1h * 100:>9.2f} {opp.apr_24h * 100:>9.2f} "
            f"{apr_7d_str:>9} {opp.volume_24h_usd:>14,.0f} {max_lev:>7}x"
        )

    print(f"\nTotal opportunities: {len(opps)}")
