from pydantic import BaseModel


# --- Hyperliquid ---

class HLAssetInfo(BaseModel):
    name: str
    szDecimals: int | None = None


class HLAssetCtx(BaseModel):
    funding: str | None = None
    markPx: str | None = None
    oraclePx: str | None = None
    dayNtlVlm: str | None = None
    openInterest: str | None = None


# --- Aster ---

class AsterPremiumIndex(BaseModel):
    symbol: str
    lastFundingRate: str | None = None
    markPrice: str | None = None
    nextFundingTime: int | None = None


class AsterTicker24h(BaseModel):
    symbol: str
    markPrice: str | None = None
    lastPrice: str | None = None
    indexPrice: str | None = None
    quoteVolume: str | None = None
    volume: str | None = None
