from datetime import datetime, timezone

from src.core.config import Settings
from src.core.models import ArbitrageOpportunity, ValidatedOpportunity
from src.core.state import MarketState


def validate_opportunities(
    opportunities: list[ArbitrageOpportunity],
    state: MarketState,
    settings: Settings,
) -> list[ValidatedOpportunity]:
    """Run pre-entry checks on scored opportunities and assign readiness status."""
    state.prune_signals(max_age_s=settings.anti_churn_cooldown_s * 2)
    results: list[ValidatedOpportunity] = []

    for opp in opportunities:
        reasons: list[str] = []

        # 1. Persistence gate
        persistence = opp.persistence_hours or 0.0
        if settings.min_persistence_hours > 0 and persistence < settings.min_persistence_hours:
            reasons.append(f"persistence {persistence:.1f}h < {settings.min_persistence_hours:.1f}h required")

        # 2. Break-even viability
        if opp.min_profitable_hours is not None and opp.min_profitable_hours > settings.expected_hold_hours:
            reasons.append(f"break-even {opp.min_profitable_hours:.1f}h > hold window {settings.expected_hold_hours:.0f}h")

        # 3. Funding sign stability (check if direction flipped recently)
        flip_count = state.get_recent_flip_count(
            opp.long_exchange, opp.short_exchange, opp.symbol, lookback_samples=6
        )
        if flip_count > 0:
            reasons.append(f"funding direction flipped {flip_count}x in last {6 * settings.loop_interval_s / 3600:.1f}h")

        # 4. Data freshness (double-check from validator perspective)
        if state.is_stale("hyperliquid", opp.symbol, max_age_s=settings.stale_data_s):
            reasons.append("hyperliquid data stale")
        if state.is_stale("lighter", opp.symbol, max_age_s=settings.stale_data_s):
            reasons.append("lighter data stale")

        # 5. Anti-churn: suppress repeated signals
        if not reasons:
            last_signal = state.get_last_signal(opp.symbol)
            if last_signal is not None:
                last_ts, last_score = last_signal
                age_s = datetime.now(timezone.utc).timestamp() - last_ts
                if age_s < settings.anti_churn_cooldown_s:
                    if opp.combined_score < last_score * settings.anti_churn_score_multiplier:
                        reasons.append("cooldown active, score not improved enough")

        # Determine status
        if reasons:
            status = "blocked" if any("break-even" in r or "stale" in r for r in reasons) else "watching"
        else:
            status = "ready"
            # Only record signal on first transition; don't re-record on subsequent polls
            last_signal = state.get_last_signal(opp.symbol)
            if last_signal is None:
                state.record_signal(opp.symbol, opp.combined_score)
            else:
                last_ts, _ = last_signal
                age_s = datetime.now(timezone.utc).timestamp() - last_ts
                if age_s >= settings.anti_churn_cooldown_s:
                    state.record_signal(opp.symbol, opp.combined_score)

        results.append(ValidatedOpportunity(opportunity=opp, status=status, reasons=reasons))

    # Sort: ready first, then watching, then blocked — within each group by score desc
    status_order = {"ready": 0, "watching": 1, "blocked": 2}
    results.sort(key=lambda v: (status_order[v.status], -v.opportunity.combined_score))
    return results
