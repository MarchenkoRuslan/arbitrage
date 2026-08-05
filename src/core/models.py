from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class FundingRate(BaseModel):
    symbol: str
    period_hours: int
    apr: float
    timestamp: datetime


class Ticker(BaseModel):
    symbol: str
    mark_price: Decimal
    index_price: Decimal | None = None
    volume_24h: float
    open_interest: float | None = None


class ArbitrageOpportunity(BaseModel):
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
    long_hours_to_next_funding: float | None = None
    short_hours_to_next_funding: float | None = None
    funding_timing_asymmetry_hours: float | None = None
    funding_timing_penalty_bps: float = 0.0
    min_profitable_hours: float | None = None
    hours_to_breakeven: float | None = None
    combined_score: float
    basis_trend: float | None = None
    liquidity_tier: Literal["H", "M", "L"] | None = None


class ValidatedOpportunity(BaseModel):
    opportunity: ArbitrageOpportunity
    status: Literal["ready", "watching", "blocked"]
    reasons: list[str] = Field(default_factory=list)
