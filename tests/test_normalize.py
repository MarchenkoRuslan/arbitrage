from src.core.normalize import vooi_symbol_normalized


def test_vooi_symbol_normalized_uppercases_symbol() -> None:
    assert vooi_symbol_normalized("btc") == "BTC"
    assert vooi_symbol_normalized("ETH") == "ETH"
    assert vooi_symbol_normalized("sol") == "SOL"


def test_vooi_symbol_normalized_handles_prefixed_symbols() -> None:
    # HIP-3 non-crypto symbols pass through as-is (uppercased)
    assert vooi_symbol_normalized("xyz:MU") == "XYZ:MU"
    assert vooi_symbol_normalized("alias:YZY") == "ALIAS:YZY"