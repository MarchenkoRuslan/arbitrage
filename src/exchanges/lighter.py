from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger

from src.core.config import Settings
from src.core.http import ResilientClient
from src.core.models import FundingRate, Ticker
from src.core.normalize import lighter_symbol_to_normalized, rate_to_apr
from src.exchanges.schemas import LighterOrderBook

FUNDING_PERIOD_HOURS = 1


class LighterConnector:
    """Fetches funding rates and tickers from Lighter via orderBookDetails.

    Funding rate is approximated as (mark_price - index_price) / index_price / 8,
    which mirrors Lighter's hourly funding formula (premium divided by 8).
    Lighter charges zero trading fees.
    """

    name = "lighter"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = ResilientClient(
            base_url=settings.lighter_base_url,
            timeout=settings.http_timeout,
            max_retries=settings.http_max_retries,
        )

    async def get_market_data(self) -> tuple[dict[str, FundingRate], dict[str, Ticker]]:
        resp = await self._client.get("/api/v1/orderBookDetails", params={"filter": "perp"})
        payload = resp.json()
        books_raw: list[dict] = payload.get("order_book_details", [])

        if not books_raw and payload:
            logger.warning("Lighter returned non-empty response with no order_book_details")

        rates: dict[str, FundingRate] = {}
        tickers: dict[str, Ticker] = {}
        now = datetime.now(timezone.utc)

        for raw in books_raw:
            try:
                book = LighterOrderBook(**raw)
            except Exception as e:
                logger.warning("Lighter: failed to parse order book entry {}: {}", raw.get("symbol", "?"), e)
                continue

            if book.market_type != "perp" or book.status != "active":
                continue

            try:
                mark = Decimal(book.mark_price)
                index = Decimal(book.index_price)
            except (ValueError, ArithmeticError):
                continue

            if mark <= 0 or index <= 0:
                continue

            symbol = lighter_symbol_to_normalized(book.symbol)
            # Funding rate: (mark - index) / index / 8 (hourly, per Lighter formula)
            rate = (mark - index) / index / 8
            rates[symbol] = FundingRate(
                symbol=symbol,
                period_hours=FUNDING_PERIOD_HOURS,
                apr=rate_to_apr(rate, FUNDING_PERIOD_HOURS),
                timestamp=now,
            )
            tickers[symbol] = Ticker(
                symbol=symbol,
                mark_price=mark,
                index_price=index,
                volume_24h=book.daily_quote_token_volume,
                open_interest=book.open_interest,
            )

        logger.debug("Lighter: parsed {} active perp markets", len(rates))
        return rates, tickers

    async def close(self) -> None:
        await self._client.close()
