from datetime import datetime, timezone
from decimal import Decimal

import httpx
from loguru import logger

from src.core.config import settings
from src.core.models import FundingRate, Ticker
from src.core.normalize import aster_symbol_to_normalized, rate_to_apr

FUNDING_PERIOD_HOURS = 8


class AsterConnector:
    name = "aster"

    def __init__(self) -> None:
        self._base_url = settings.aster_base_url
        self._client = httpx.AsyncClient(timeout=10)

    async def get_funding_rates(self) -> dict[str, FundingRate]:
        """Fetch funding rates via premiumIndex endpoint."""
        resp = await self._client.get(f"{self._base_url}/fapi/v1/premiumIndex")
        resp.raise_for_status()
        data = resp.json()

        rates: dict[str, FundingRate] = {}
        now = datetime.now(timezone.utc)

        for item in data:
            raw_symbol = item["symbol"]
            symbol = aster_symbol_to_normalized(raw_symbol)
            rate_str = item.get("lastFundingRate")
            if rate_str is None:
                continue

            rate = Decimal(rate_str)
            rates[symbol] = FundingRate(
                symbol=symbol,
                rate=rate,
                period_hours=FUNDING_PERIOD_HOURS,
                apr=rate_to_apr(rate, FUNDING_PERIOD_HOURS),
                timestamp=now,
            )

        logger.debug("Aster: fetched {} funding rates", len(rates))
        return rates

    async def get_tickers(self) -> dict[str, Ticker]:
        """Fetch mark prices and 24h volumes."""
        resp = await self._client.get(f"{self._base_url}/fapi/v1/ticker/24hr")
        resp.raise_for_status()
        data = resp.json()

        tickers: dict[str, Ticker] = {}
        for item in data:
            raw_symbol = item["symbol"]
            symbol = aster_symbol_to_normalized(raw_symbol)

            mark = item.get("markPrice") or item.get("lastPrice")
            if mark is None:
                continue

            tickers[symbol] = Ticker(
                symbol=symbol,
                mark_price=Decimal(mark),
                index_price=Decimal(item["indexPrice"]) if item.get("indexPrice") else None,
                volume_24h=float(item.get("quoteVolume", 0)),
            )

        logger.debug("Aster: fetched {} tickers", len(tickers))
        return tickers

    async def close(self) -> None:
        await self._client.aclose()
