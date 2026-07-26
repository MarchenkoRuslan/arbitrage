from decimal import Decimal

from pydantic import BaseModel


class ArbitrageOpportunity(BaseModel):
    symbol: str
    long_exchange: str
    short_exchange: str
    long_base_symbol: str
    short_base_symbol: str
    net_apr: float
    apr_1h: float
    apr_24h: float
    apr_7d: float | None
    gross_spread_hourly: float
    long_funding_rate: Decimal
    short_funding_rate: Decimal
    volume_24h_usd: float
    long_max_leverage: int
    short_max_leverage: int
