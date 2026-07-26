from typing import Protocol

from src.core.models import FundingRate, Ticker


class ExchangeConnector(Protocol):
    name: str

    async def get_funding_rates(self) -> dict[str, FundingRate]: ...
    async def get_tickers(self) -> dict[str, Ticker]: ...
