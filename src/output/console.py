from src.core.models import ArbitrageOpportunity


def print_opportunities(opps: list[ArbitrageOpportunity], max_rows: int = 20) -> None:
    """Render opportunities table to stdout."""
    if not opps:
        return

    header = f"{'Symbol':<10} {'Long':<12} {'Short':<12} {'Diff APR%':>10} {'Basis bps':>10} {'Score%':>8}"
    print("\n" + header)
    print("-" * len(header))

    for opp in opps[:max_rows]:
        print(
            f"{opp.symbol:<10} {opp.long_exchange:<12} {opp.short_exchange:<12} "
            f"{opp.funding_diff_apr:>10.2f} {opp.basis_bps:>10.2f} {opp.combined_score:>8.2f}"
        )

    print(f"\nTotal opportunities: {len(opps)}")
