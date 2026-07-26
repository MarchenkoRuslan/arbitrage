from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger

from src.core.config import Settings
from src.core.http import ResilientClient
from src.core.models import FundingRate, Ticker
from src.core.normalize import aster_symbol_to_normalized, rate_to_apr
from src.core.state import MarketState
from src.exchanges.schemas import AsterPremiumIndex, AsterTicker24h

FUNDING_PERIOD_HOURS = 8


class AsterConnector:
    name = "aster"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = ResilientClient(
            base_url=settings.aster_base_url,
            timeout=settings.http_timeout,
            max_retries=settings.http_max_retries,
        )

    async def get_funding_rates(self) -> dict[str, FundingRate]:
        """Fetch funding rates via premiumIndex endpoint."""
        resp = await self._client.get("/fapi/v1/premiumIndex")
        items = [AsterPremiumIndex.model_validate(i) for i in resp.json()]

        rates: dict[str, FundingRate] = {}
        now = datetime.now(timezone.utc)

        for item in items:
            symbol = aster_symbol_to_normalized(item.symbol)
            if item.lastFundingRate is None:
                continue

            rate = Decimal(item.lastFundingRate)
            rates[symbol] = FundingRate(
                symbol=symbol,
                rate=rate,
                period_hours=FUNDING_PERIOD_HOURS,
                apr=rate_to_apr(rate, FUNDING_PERIOD_HOURS),
                timestamp=now,
            )

        logger.debug("Aster: {} funding rates", len(rates))
        return rates

    async def get_tickers(self) -> dict[str, Ticker]:
        """Fetch mark prices and 24h volumes."""
        resp = await self._client.get("/fapi/v1/ticker/24hr")
        items = [AsterTicker24h.model_validate(i) for i in resp.json()]

        tickers: dict[str, Ticker] = {}
        for item in items:
            symbol = aster_symbol_to_normalized(item.symbol)
            mark = item.markPrice or item.lastPrice
            if mark is None:
                continue

            tickers[symbol] = Ticker(
                symbol=symbol,
                mark_price=Decimal(mark),
                index_price=Decimal(item.indexPrice) if item.indexPrice else None,
                volume_24h=float(item.quoteVolume or 0),
            )

        logger.debug("Aster: {} tickers", len(tickers))
        return tickers

    async def get_market_data(self) -> tuple[dict[str, FundingRate], dict[str, Ticker]]:
        """Fetch both rates and tickers (two requests, Aster has no combined endpoint)."""
        rates = await self.get_funding_rates()
        tickers = await self.get_tickers()
        return rates, tickers

    async def start_stream(self, state: MarketState) -> None:
        """Placeholder — WS implementation in aster_ws.py."""
        raise NotImplementedError("Use AsterWsFeed for streaming")

    async def close(self) -> None:
        await self._client.close()
