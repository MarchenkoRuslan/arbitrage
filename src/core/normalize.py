from decimal import Decimal

HOURS_PER_YEAR = 8760


def rate_to_apr(rate: Decimal, period_hours: int) -> float:
    """Convert a periodic funding rate to annualized percentage."""
    return float(rate) * (HOURS_PER_YEAR / period_hours) * 100


def hl_symbol_to_normalized(coin: str) -> str:
    """Hyperliquid uses bare coin names: BTC, ETH, etc."""
    return coin.upper()


def lighter_symbol_to_normalized(symbol: str) -> str:
    """Lighter also uses bare coin names — pass through uppercase."""
    return symbol.upper()
