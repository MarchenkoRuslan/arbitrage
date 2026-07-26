from decimal import Decimal

import pytest

from src.core.config import Settings
from src.exchanges.hyperliquid import HyperliquidConnector
from src.exchanges.schemas import HLAssetCtx, HLAssetInfo, LighterOrderBook


def test_hyperliquid_parse_rates_and_tickers_skips_missing_fields() -> None:
    connector = HyperliquidConnector(Settings())
    rates, tickers = connector._parse_rates_and_tickers(
        universe=[HLAssetInfo(name="btc"), HLAssetInfo(name="eth")],
        asset_ctxs=[
            HLAssetCtx(funding="0.0002", markPx="100", oraclePx="101",
                       dayNtlVlm="12345", openInterest="9876.5"),
            HLAssetCtx(funding=None, markPx=None, oraclePx="200", dayNtlVlm="999"),
        ],
    )
    assert list(rates) == ["BTC"]
    assert list(tickers) == ["BTC"]
    assert rates["BTC"].rate == Decimal("0.0002")
    assert rates["BTC"].period_hours == 1
    assert tickers["BTC"].mark_price == Decimal("100")
    assert tickers["BTC"].index_price == Decimal("101")
    assert tickers["BTC"].volume_24h == 12345.0


def test_lighter_connector_computes_funding_rate_from_mark_index() -> None:
    raw = {
        "symbol": "ETH", "market_id": 0, "market_type": "perp", "status": "active",
        "mark_price": "2000.0", "index_price": "1992.0",
        "daily_quote_token_volume": 5_000_000.0, "open_interest": 1000.0,
    }
    book = LighterOrderBook(**raw)
    mark = Decimal(book.mark_price)
    index = Decimal(book.index_price)
    rate = (mark - index) / index / 8
    assert float(rate) == pytest.approx(0.000502, rel=1e-3)


def test_lighter_connector_skips_inactive_markets() -> None:
    # LighterOrderBook with status != "active" should be skipped by connector
    raw = {
        "symbol": "OLD", "market_id": 99, "market_type": "perp", "status": "closed",
        "mark_price": "100.0", "index_price": "100.0",
        "daily_quote_token_volume": 0.0,
    }
    book = LighterOrderBook(**raw)
    assert book.status != "active"


def test_lighter_connector_skips_spot_markets() -> None:
    raw = {
        "symbol": "USDC", "market_id": 1, "market_type": "spot", "status": "active",
        "mark_price": "1.0", "index_price": "1.0",
        "daily_quote_token_volume": 1_000_000.0,
    }
    book = LighterOrderBook(**raw)
    assert book.market_type != "perp"
