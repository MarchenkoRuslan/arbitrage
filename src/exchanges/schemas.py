from pydantic import BaseModel


# ── Hyperliquid ────────────────────────────────────────────────────────────────

class HLAssetInfo(BaseModel):
    name: str


class HLAssetCtx(BaseModel):
    funding: str | None = None
    markPx: str | None = None
    oraclePx: str | None = None
    dayNtlVlm: str | None = None
    openInterest: str | None = None


# ── Lighter ────────────────────────────────────────────────────────────────────

class LighterOrderBook(BaseModel):
    symbol: str
    market_id: int
    market_type: str
    status: str
    mark_price: str
    index_price: str
    daily_quote_token_volume: float = 0.0
    open_interest: float | None = None
