from decimal import Decimal

from src.core.config import Settings
from src.exchanges.vooi import VooiConnector


def _raw_opp(
    asset: str = "BTC",
    long_ex: str = "hyperliquid",
    short_ex: str = "lighter",
    net_apr: float = 0.75,
    apr_1h: float = 0.80,
    apr_24h: float = 0.70,
    apr_7d: float | None = 0.60,
    volume: float = 1_000_000.0,
    long_max_lev: int = 10,
    short_max_lev: int = 10,
) -> dict:
    raw: dict = {
        "asset": asset,
        "netApr": net_apr,
        "apr1h": apr_1h,
        "apr24h": apr_24h,
        "grossSpreadHourly": 0.0001,
        "volume24h": volume,
        "longMarketData": {
            "exchange": long_ex,
            "baseSymbol": asset,
            "quoteSymbol": "USDC",
            "fundingRate": "0.0001",
            "maxLeverage": long_max_lev,
        },
        "shortMarketData": {
            "exchange": short_ex,
            "baseSymbol": asset,
            "quoteSymbol": "USDC",
            "fundingRate": "0.0003",
            "maxLeverage": short_max_lev,
        },
    }
    if apr_7d is not None:
        raw["apr7d"] = apr_7d
    return raw


def _connector() -> VooiConnector:
    return VooiConnector(Settings(vooi_bearer_token="test-token", vooi_target_exchanges="hyperliquid,lighter"))


def test_vooi_connector_parses_opportunity_correctly() -> None:
    connector = _connector()
    opp = connector._parse_opportunity(_raw_opp())

    assert opp is not None
    assert opp.symbol == "BTC"
    assert opp.long_exchange == "hyperliquid"
    assert opp.short_exchange == "lighter"
    assert opp.net_apr == 0.75
    assert opp.apr_1h == 0.80
    assert opp.apr_24h == 0.70
    assert opp.apr_7d == 0.60
    assert opp.volume_24h_usd == 1_000_000.0
    assert opp.long_max_leverage == 10
    assert opp.short_max_leverage == 10
    assert opp.long_funding_rate == Decimal("0.0001")
    assert opp.short_funding_rate == Decimal("0.0003")


def test_vooi_connector_skips_opportunity_from_wrong_exchange() -> None:
    connector = _connector()
    opp = connector._parse_opportunity(_raw_opp(long_ex="aster", short_ex="hyperliquid"))
    assert opp is None


def test_vooi_connector_skips_opportunity_with_one_wrong_exchange() -> None:
    connector = _connector()
    opp = connector._parse_opportunity(_raw_opp(long_ex="hyperliquid", short_ex="binance"))
    assert opp is None


def test_vooi_connector_handles_missing_apr7d() -> None:
    connector = _connector()
    raw = _raw_opp(apr_7d=None)
    opp = connector._parse_opportunity(raw)
    assert opp is not None
    assert opp.apr_7d is None


def test_vooi_connector_handles_missing_asset() -> None:
    connector = _connector()
    raw = _raw_opp()
    raw["asset"] = ""
    opp = connector._parse_opportunity(raw)
    assert opp is None


def test_vooi_connector_skips_malformed_opportunity() -> None:
    connector = _connector()
    opp = connector._parse_opportunity({"asset": "BTC", "netApr": 0.5})
    assert opp is None


def test_vooi_connector_target_exchanges_from_settings() -> None:
    connector = VooiConnector(
        Settings(vooi_bearer_token="tok", vooi_target_exchanges="hyperliquid,lighter,aster")
    )
    opp = connector._parse_opportunity(_raw_opp(long_ex="aster", short_ex="hyperliquid"))
    assert opp is not None
    assert opp.long_exchange == "aster"
