from typing import Literal

from pydantic import BaseModel, Field

from src.core.models import ValidatedOpportunity


class OpportunityItem(BaseModel):
    symbol: str
    long_exchange: str
    short_exchange: str
    persistence_hours: float | None = None
    long_rate_apr: float
    short_rate_apr: float
    funding_diff_apr: float
    funding_edge_bps: float
    basis_bps: float
    basis_bonus_bps: float
    fee_impact_bps: float
    min_profitable_hours: float | None = None
    hours_to_breakeven: float | None = None
    combined_score: float
    basis_trend: float | None = None
    liquidity_tier: Literal["H", "M", "L"] | None = None
    status: Literal["ready", "watching", "blocked"]
    reasons: list[str] = Field(default_factory=list)


class OpportunitiesResponse(BaseModel):
    count: int
    ready_count: int
    updated_at: str | None = None
    opportunities: list[OpportunityItem]


def build_opportunities_response(
    validated: list[ValidatedOpportunity],
    updated_at: str | None = None,
) -> OpportunitiesResponse:
    items = [
        OpportunityItem(
            symbol=v.opportunity.symbol,
            long_exchange=v.opportunity.long_exchange,
            short_exchange=v.opportunity.short_exchange,
            persistence_hours=v.opportunity.persistence_hours,
            long_rate_apr=v.opportunity.long_rate_apr,
            short_rate_apr=v.opportunity.short_rate_apr,
            funding_diff_apr=v.opportunity.funding_diff_apr,
            funding_edge_bps=v.opportunity.funding_edge_bps,
            basis_bps=v.opportunity.basis_bps,
            basis_bonus_bps=v.opportunity.basis_bonus_bps,
            fee_impact_bps=v.opportunity.fee_impact_bps,
            min_profitable_hours=v.opportunity.min_profitable_hours,
            hours_to_breakeven=v.opportunity.hours_to_breakeven,
            combined_score=v.opportunity.combined_score,
            basis_trend=v.opportunity.basis_trend,
            liquidity_tier=v.opportunity.liquidity_tier,
            status=v.status,
            reasons=v.reasons,
        )
        for v in validated
    ]
    return OpportunitiesResponse(
        count=len(items),
        ready_count=sum(1 for i in items if i.status == "ready"),
        updated_at=updated_at,
        opportunities=items,
    )


class ConfigResponse(BaseModel):
    api_host: str
    api_port: int
    min_score_bps: float
    min_volume_24h: float
    min_open_interest: float
    min_persistence_hours: float
    anti_churn_cooldown_s: float
    anti_churn_score_multiplier: float
    hl_fee_per_side: float
    lighter_fee_per_side: float
    expected_hold_hours: float
    basis_weight: float
    liquidity_weight: float
    max_basis_bps: float
    loop_interval_s: float
    stale_data_s: float


class StatusResponse(BaseModel):
    uptime_s: float
    started_at: str
    last_updated_at: str | None = None
    last_poll_started_at: str | None = None
    last_poll_finished_at: str | None = None
    last_poll_duration_ms: float | None = None
    poll_count_total: int
    poll_count_success: int
    poll_count_failed: int
    exchange_last_ok: dict[str, bool | None]
