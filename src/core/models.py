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


class ArbitrageOpportunity(BaseModel):
    symbol: str
    long_exchange: str
    short_exchange: str
    long_rate_apr: float
    short_rate_apr: float
    funding_diff_apr: float
    basis_bps: float
    combined_score: float
