from src.core.models import ArbitrageOpportunity


def print_opportunities(opps: list[ArbitrageOpportunity], max_rows: int = 20) -> None:
    """Render opportunities table to stdout."""
    if not opps:
        return

    header = (
        f"{'Symbol':<10} {'Long':<12} {'Short':<12} {'Diff APR%':>10} {'Fund bps':>10} "
        f"{'Basis bps':>10} {'Fees bps':>10} {'Edge bps':>10} {'Persist h':>10} {'BE h':>8}"
    )
    print("\n" + header)
    print("-" * len(header))

    for opp in opps[:max_rows]:
        break_even_hours = "-" if opp.min_profitable_hours is None else f"{opp.min_profitable_hours:.2f}"
        persistence_hours = "-" if opp.persistence_hours is None else f"{opp.persistence_hours:.2f}"
        print(
            f"{opp.symbol:<10} {opp.long_exchange:<12} {opp.short_exchange:<12} "
            f"{opp.funding_diff_apr:>10.2f} {opp.funding_edge_bps:>10.2f} {opp.basis_bps:>10.2f} "
            f"{opp.fee_impact_bps:>10.2f} {opp.combined_score:>10.2f} {persistence_hours:>10} {break_even_hours:>8}"
        )

    print(f"\nTotal opportunities: {len(opps)}")
