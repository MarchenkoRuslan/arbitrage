from src.core.models import ValidatedOpportunity


def print_opportunities(validated: list[ValidatedOpportunity], max_rows: int = 20) -> None:
    """Render Hyperliquid vs Lighter arbitrage table to stdout."""
    if not validated:
        return

    header = (
        f"{'Symbol':<10} {'Long':<12} {'Short':<12} {'Diff APR%':>10} "
        f"{'Fund bps':>10} {'Basis bps':>10} {'Fees bps':>8} {'Score bps':>10} "
        f"{'BE h':>8} {'L h2f':>7} {'S h2f':>7} {'TPen':>6} {'Trnd':>4} {'Liq':>3} {'Status':<10}"
    )
    print("\n" + header)
    print("-" * len(header))

    for item in validated[:max_rows]:
        opp = item.opportunity
        be_h = "-" if opp.min_profitable_hours is None else f"{opp.min_profitable_hours:.1f}"
        long_h2f = "-" if opp.long_hours_to_next_funding is None else f"{opp.long_hours_to_next_funding:.1f}"
        short_h2f = "-" if opp.short_hours_to_next_funding is None else f"{opp.short_hours_to_next_funding:.1f}"
        timing_pen = f"{opp.funding_timing_penalty_bps:.1f}"
        trend_str = "-"
        if opp.basis_trend is not None:
            if opp.basis_trend > 0.5:
                trend_str = "UP"
            elif opp.basis_trend < -0.5:
                trend_str = "DN"
            else:
                trend_str = "FL"
        liq_str = opp.liquidity_tier or "-"
        status_str = item.status.upper()
        if item.reasons:
            status_str += f" ({item.reasons[0]})"
        print(
            f"{opp.symbol:<10} {opp.long_exchange:<12} {opp.short_exchange:<12} "
            f"{opp.funding_diff_apr:>10.2f} {opp.funding_edge_bps:>10.2f} "
            f"{opp.basis_bps:>10.2f} {opp.fee_impact_bps:>8.2f} "
            f"{opp.combined_score:>10.2f} {be_h:>8} {long_h2f:>7} {short_h2f:>7} {timing_pen:>6} "
            f"{trend_str:>4} {liq_str:>3} {status_str:<10}"
        )

    ready = sum(1 for v in validated if v.status == "ready")
    print(f"\nTotal: {len(validated)} | Ready: {ready}")
