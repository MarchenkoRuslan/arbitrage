from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class FundingRate(BaseModel):
    symbol: str
    rate: Decimal
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
    min_profitable_hours: float | None = None
    hours_to_breakeven: float | None = None
    combined_score: float
