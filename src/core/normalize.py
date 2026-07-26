from decimal import Decimal

HOURS_PER_YEAR = 8760


def rate_to_apr(rate: Decimal, period_hours: int) -> float:
    """Convert a periodic funding rate to annualized percentage."""
    periods_per_year = HOURS_PER_YEAR / period_hours
    return float(rate) * periods_per_year * 100


def hl_symbol_to_normalized(coin: str) -> str:
    """Hyperliquid uses bare coin names: BTC, ETH, etc."""
    return coin.upper()


def aster_symbol_to_normalized(symbol: str) -> str:
    """Aster uses Binance-style: BTCUSDT -> BTC."""
    if symbol.endswith("USDT"):
        return symbol[:-4].upper()
    return symbol.upper()


def normalized_to_aster(symbol: str) -> str:
    """Convert normalized symbol back to Aster format."""
    return f"{symbol}USDT"
