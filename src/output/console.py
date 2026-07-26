from src.core.models import ArbitrageOpportunity


def print_opportunities(opps: list[ArbitrageOpportunity], max_rows: int = 20) -> None:
    """Render Hyperliquid vs Lighter arbitrage table to stdout."""
    if not opps:
        return

    header = (
        f"{'Symbol':<10} {'Long':<12} {'Short':<12} {'Diff APR%':>10} "
        f"{'Fund bps':>10} {'Basis bps':>10} {'Fees bps':>8} {'Score bps':>10} {'BE h':>8}"
    )
    print("\n" + header)
    print("-" * len(header))

    for opp in opps[:max_rows]:
        be_h = "-" if opp.min_profitable_hours is None else f"{opp.min_profitable_hours:.1f}"
        print(
            f"{opp.symbol:<10} {opp.long_exchange:<12} {opp.short_exchange:<12} "
            f"{opp.funding_diff_apr:>10.2f} {opp.funding_edge_bps:>10.2f} "
            f"{opp.basis_bps:>10.2f} {opp.fee_impact_bps:>8.2f} "
            f"{opp.combined_score:>10.2f} {be_h:>8}"
        )

    print(f"\nTotal opportunities: {len(opps)}")
