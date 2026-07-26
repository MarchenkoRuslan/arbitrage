from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger

from src.core.config import Settings
from src.core.http import ResilientClient
from src.core.models import FundingRate, Ticker
from src.core.normalize import hl_symbol_to_normalized, rate_to_apr
from src.core.state import MarketState
from src.exchanges.schemas import HLAssetCtx, HLAssetInfo

FUNDING_PERIOD_HOURS = 1


class HyperliquidConnector:
    name = "hyperliquid"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = ResilientClient(
            base_url=settings.hl_base_url,
            timeout=settings.http_timeout,
            max_retries=settings.http_max_retries,
        )

    async def _fetch_meta_and_asset_ctxs(self) -> tuple[list[HLAssetInfo], list[HLAssetCtx]]:
        resp = await self._client.post(
            "/info",
            json={"type": "metaAndAssetCtxs"},
        )
        data = resp.json()
        universe = [HLAssetInfo.model_validate(a) for a in data[0]["universe"]]
        asset_ctxs = [HLAssetCtx.model_validate(c) for c in data[1]]
        if len(universe) != len(asset_ctxs):
            logger.warning(
                "HL metaAndAssetCtxs length mismatch: universe={} asset_ctxs={}",
                len(universe), len(asset_ctxs),
            )
        return universe, asset_ctxs

    def _parse_rates_and_tickers(
        self,
        universe: list[HLAssetInfo],
        asset_ctxs: list[HLAssetCtx],
    ) -> tuple[dict[str, FundingRate], dict[str, Ticker]]:
        rates: dict[str, FundingRate] = {}
        tickers: dict[str, Ticker] = {}
        now = datetime.now(timezone.utc)

        for asset_info, ctx in zip(universe, asset_ctxs):
            symbol = hl_symbol_to_normalized(asset_info.name)

            if ctx.funding is not None:
                rate = Decimal(ctx.funding)
                rates[symbol] = FundingRate(
                    symbol=symbol,
                    period_hours=FUNDING_PERIOD_HOURS,
                    apr=rate_to_apr(rate, FUNDING_PERIOD_HOURS),
                    timestamp=now,
                )

            if ctx.markPx is not None:
                tickers[symbol] = Ticker(
                    symbol=symbol,
                    mark_price=Decimal(ctx.markPx),
                    index_price=Decimal(ctx.oraclePx) if ctx.oraclePx else None,
                    volume_24h=float(ctx.dayNtlVlm or 0),
                    open_interest=float(ctx.openInterest) if ctx.openInterest is not None else None,
                )

        return rates, tickers

    async def get_market_data(self) -> tuple[dict[str, FundingRate], dict[str, Ticker]]:
        """Fetch rates and tickers in one request."""
        universe, asset_ctxs = await self._fetch_meta_and_asset_ctxs()
        rates, tickers = self._parse_rates_and_tickers(universe, asset_ctxs)
        logger.debug("HL: {} rates, {} tickers", len(rates), len(tickers))
        return rates, tickers

    async def get_funding_rates(self) -> dict[str, FundingRate]:
        rates, _ = await self.get_market_data()
        return rates

    async def get_tickers(self) -> dict[str, Ticker]:
        _, tickers = await self.get_market_data()
        return tickers

    async def start_stream(self, state: MarketState) -> None:
        """Placeholder — WS implementation in hyperliquid_ws.py."""
        raise NotImplementedError("Use HyperliquidWsFeed for streaming")

    async def close(self) -> None:
        await self._client.close()
