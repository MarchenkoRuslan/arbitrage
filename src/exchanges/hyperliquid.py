from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger

from src.core.config import Settings
from src.core.http import ResilientClient
from src.core.models import FundingRate, Ticker
from src.core.normalize import hl_symbol_to_normalized, rate_to_apr
from src.exchanges.schemas import HLAssetCtx, HLAssetInfo

FUNDING_PERIOD_HOURS = 1


class HyperliquidConnector:
    """Fetches funding rates and tickers from Hyperliquid in a single REST call."""

    name = "hyperliquid"

    def __init__(self, settings: Settings) -> None:
        self._client = ResilientClient(
            base_url=settings.hl_base_url,
            timeout=settings.http_timeout,
            max_retries=settings.http_max_retries,
        )

    async def get_market_data(self) -> tuple[dict[str, FundingRate], dict[str, Ticker]]:
        resp = await self._client.post("/info", json={"type": "metaAndAssetCtxs"})
        data = resp.json()
        universe = [HLAssetInfo(**item) for item in data[0]["universe"]]
        asset_ctxs = [HLAssetCtx(**item) for item in data[1]]
        return self._parse_rates_and_tickers(universe, asset_ctxs)

    def _parse_rates_and_tickers(
        self,
        universe: list[HLAssetInfo],
        asset_ctxs: list[HLAssetCtx],
    ) -> tuple[dict[str, FundingRate], dict[str, Ticker]]:
        rates: dict[str, FundingRate] = {}
        tickers: dict[str, Ticker] = {}
        now = datetime.now(timezone.utc)

        for info, ctx in zip(universe, asset_ctxs):
            if ctx.funding is None or ctx.markPx is None:
                continue
            try:
                symbol = hl_symbol_to_normalized(info.name)
                rate = Decimal(ctx.funding)
                rates[symbol] = FundingRate(
                    symbol=symbol,
                    rate=rate,
                    period_hours=FUNDING_PERIOD_HOURS,
                    apr=rate_to_apr(rate, FUNDING_PERIOD_HOURS),
                    timestamp=now,
                )
                tickers[symbol] = Ticker(
                    symbol=symbol,
                    mark_price=Decimal(ctx.markPx),
                    index_price=Decimal(ctx.oraclePx) if ctx.oraclePx else None,
                    volume_24h=float(ctx.dayNtlVlm or 0),
                    open_interest=float(ctx.openInterest) if ctx.openInterest else None,
                )
            except (ValueError, ArithmeticError) as exc:
                logger.debug("Skipping HL asset {}: {}", info.name, exc)

        logger.debug("Hyperliquid: parsed {} markets", len(rates))
        return rates, tickers

    async def close(self) -> None:
        await self._client.close()
