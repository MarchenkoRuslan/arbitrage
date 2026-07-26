from decimal import Decimal

from loguru import logger

from src.core.config import Settings
from src.core.http import ResilientClient
from src.core.models import ArbitrageOpportunity


class VooiConnector:
    """Fetches pre-ranked funding arbitrage opportunities from the VOOI Perps API."""

    def __init__(self, settings: Settings) -> None:
        self._client = ResilientClient(
            base_url=settings.vooi_api_url,
            timeout=settings.http_timeout,
            max_retries=settings.http_max_retries,
            headers={"Authorization": f"Bearer {settings.vooi_bearer_token}"},
        )
        self._target_exchanges: frozenset[str] = frozenset(
            ex.strip() for ex in settings.vooi_target_exchanges.split(",") if ex.strip()
        )
        self._limit = settings.vooi_opportunity_limit

    async def get_opportunities(self) -> list[ArbitrageOpportunity]:
        """Fetch and parse funding strategies from VOOI /funding-strategies."""
        resp = await self._client.get("/funding-strategies", params={"limit": self._limit})
        items = resp.json()
        if not isinstance(items, list):
            logger.warning("VOOI /funding-strategies returned unexpected type: {}", type(items).__name__)
            return []

        results: list[ArbitrageOpportunity] = []
        for raw in items:
            opp = self._parse_opportunity(raw)
            if opp is not None:
                results.append(opp)

        logger.debug("Parsed {}/{} VOOI opportunities for target exchanges {}", len(results), len(items), self._target_exchanges)
        return results

    def _parse_opportunity(self, raw: dict) -> ArbitrageOpportunity | None:
        try:
            long_md: dict = raw.get("longMarketData") or {}
            short_md: dict = raw.get("shortMarketData") or {}
            long_ex: str = long_md.get("exchange") or ""
            short_ex: str = short_md.get("exchange") or ""

            if long_ex not in self._target_exchanges or short_ex not in self._target_exchanges:
                return None

            asset: str = (raw.get("asset") or "").strip()
            if not asset:
                return None

            apr_7d_raw = raw.get("apr7d")
            apr_7d = float(apr_7d_raw) if apr_7d_raw is not None else None

            return ArbitrageOpportunity(
                symbol=asset,
                long_exchange=long_ex,
                short_exchange=short_ex,
                long_base_symbol=str(long_md.get("baseSymbol") or asset),
                short_base_symbol=str(short_md.get("baseSymbol") or asset),
                net_apr=float(raw.get("netApr", 0)),
                apr_1h=float(raw.get("apr1h", 0)),
                apr_24h=float(raw.get("apr24h", 0)),
                apr_7d=apr_7d,
                gross_spread_hourly=float(raw.get("grossSpreadHourly", 0)),
                long_funding_rate=Decimal(str(long_md.get("fundingRate") or "0")),
                short_funding_rate=Decimal(str(short_md.get("fundingRate") or "0")),
                volume_24h_usd=float(raw.get("volume24h") or 0),
                long_max_leverage=int(long_md.get("maxLeverage") or 0),
                short_max_leverage=int(short_md.get("maxLeverage") or 0),
            )
        except (ValueError, ArithmeticError, KeyError, TypeError) as exc:
            logger.debug("Skipping malformed VOOI opportunity: {} — {}", raw.get("asset"), exc)
            return None

    async def close(self) -> None:
        await self._client.close()
