from decimal import Decimal

import pytest

from src.core.config import Settings
from src.exchanges.aster import AsterConnector
from src.exchanges.hyperliquid import HyperliquidConnector
from src.exchanges.schemas import AsterPremiumIndex, AsterTicker24h, HLAssetCtx, HLAssetInfo


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_hyperliquid_parse_rates_and_tickers_skips_missing_fields() -> None:
    connector = HyperliquidConnector(Settings())

    rates, tickers = connector._parse_rates_and_tickers(
        universe=[
            HLAssetInfo(name="btc"),
            HLAssetInfo(name="eth"),
        ],
        asset_ctxs=[
            HLAssetCtx(
                funding="0.0002",
                markPx="100",
                oraclePx="101",
                dayNtlVlm="12345",
            ),
            HLAssetCtx(
                funding=None,
                markPx=None,
                oraclePx="200",
                dayNtlVlm="999",
            ),
        ],
    )

    assert list(rates) == ["BTC"]
    assert list(tickers) == ["BTC"]
    assert rates["BTC"].rate == Decimal("0.0002")
    assert rates["BTC"].apr == 175.2
    assert tickers["BTC"].mark_price == Decimal("100")
    assert tickers["BTC"].index_price == Decimal("101")
    assert tickers["BTC"].volume_24h == 12345.0


@pytest.mark.asyncio
async def test_aster_get_funding_rates_normalizes_symbols_and_skips_missing_rates(monkeypatch) -> None:
    connector = AsterConnector(Settings())

    async def fake_get(path: str):
        assert path == "/fapi/v1/premiumIndex"
        return _FakeResponse(
            [
                AsterPremiumIndex(symbol="btcusdt", lastFundingRate="0.0001", markPrice="100").model_dump(mode="json"),
                AsterPremiumIndex(symbol="ETHUSDT", lastFundingRate=None, markPrice="200").model_dump(mode="json"),
            ]
        )

    monkeypatch.setattr(connector._client, "get", fake_get)

    rates = await connector.get_funding_rates()

    assert list(rates) == ["BTC"]
    assert rates["BTC"].rate == Decimal("0.0001")
    assert rates["BTC"].period_hours == 8
    assert rates["BTC"].apr == 10.95


@pytest.mark.asyncio
async def test_aster_get_tickers_uses_last_price_fallback_and_normalizes_symbols(monkeypatch) -> None:
    connector = AsterConnector(Settings())

    async def fake_get(path: str):
        assert path == "/fapi/v1/ticker/24hr"
        return _FakeResponse(
            [
                AsterTicker24h(
                    symbol="btcusdt",
                    markPrice=None,
                    lastPrice="64000",
                    indexPrice="63950",
                    quoteVolume="2500000",
                ).model_dump(mode="json"),
                AsterTicker24h(
                    symbol="ethusdt",
                    markPrice=None,
                    lastPrice=None,
                    indexPrice="3500",
                    quoteVolume="500000",
                ).model_dump(mode="json"),
            ]
        )

    monkeypatch.setattr(connector._client, "get", fake_get)

    tickers = await connector.get_tickers()

    assert list(tickers) == ["BTC"]
    assert tickers["BTC"].mark_price == Decimal("64000")
    assert tickers["BTC"].index_price == Decimal("63950")
    assert tickers["BTC"].volume_24h == 2500000.0