from datetime import datetime, timezone
from decimal import Decimal

import httpx
from loguru import logger

from src.core.config import settings
from src.core.models import FundingRate, Ticker
from src.core.normalize import hl_symbol_to_normalized, rate_to_apr

FUNDING_PERIOD_HOURS = 1


class HyperliquidConnector:
    name = "hyperliquid"

    def __init__(self) -> None:
        self._base_url = settings.hl_base_url
        self._client = httpx.AsyncClient(timeout=10)

    async def get_funding_rates(self) -> dict[str, FundingRate]:
        """Fetch funding rates for all perps via metaAndAssetCtxs."""
        resp = await self._client.post(
            f"{self._base_url}/info",
            json={"type": "metaAndAssetCtxs"},
        )
        resp.raise_for_status()
        data = resp.json()

        meta = data[0]  # universe metadata
        asset_ctxs = data[1]  # per-asset context

        rates: dict[str, FundingRate] = {}
        now = datetime.now(timezone.utc)

        for asset_info, ctx in zip(meta["universe"], asset_ctxs):
            coin = asset_info["name"]
            symbol = hl_symbol_to_normalized(coin)
            funding_str = ctx.get("funding")
            if funding_str is None:
                continue

            rate = Decimal(funding_str)
            rates[symbol] = FundingRate(
                symbol=symbol,
                rate=rate,
                period_hours=FUNDING_PERIOD_HOURS,
                apr=rate_to_apr(rate, FUNDING_PERIOD_HOURS),
                timestamp=now,
            )

        logger.debug("HL: fetched {} funding rates", len(rates))
        return rates

    async def get_tickers(self) -> dict[str, Ticker]:
        """Fetch mark prices and volumes via metaAndAssetCtxs."""
        resp = await self._client.post(
            f"{self._base_url}/info",
            json={"type": "metaAndAssetCtxs"},
        )
        resp.raise_for_status()
        data = resp.json()

        meta = data[0]
        asset_ctxs = data[1]

        tickers: dict[str, Ticker] = {}
        for asset_info, ctx in zip(meta["universe"], asset_ctxs):
            coin = asset_info["name"]
            symbol = hl_symbol_to_normalized(coin)
            mark = ctx.get("markPx")
            if mark is None:
                continue

            tickers[symbol] = Ticker(
                symbol=symbol,
                mark_price=Decimal(mark),
                index_price=Decimal(ctx["oraclePx"]) if ctx.get("oraclePx") else None,
                volume_24h=float(ctx.get("dayNtlVlm", 0)),
            )

        logger.debug("HL: fetched {} tickers", len(tickers))
        return tickers

    async def close(self) -> None:
        await self._client.aclose()
