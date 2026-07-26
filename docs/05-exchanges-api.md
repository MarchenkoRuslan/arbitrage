# Exchanges and APIs

## Focus: DEX-first

The strategy starts with DEX venues (Hyperliquid, Aster) because they offer the lowest fees, 1h funding, and no KYC.
CEX venues are added later as additional options.

## Target Exchanges (v1 - DEX only)

| Exchange | Funding Period | Type | Priority | Status |
|-------|---------------|-----|-----------|--------|
| Hyperliquid | 1h | DEX | **P0** | Primary |
| Aster | 8h | DEX/CEX | **P0** | Second leg |

## Expansion (v2+)

| Exchange | Funding Period | Type | Priority |
|-------|---------------|-----|-----------|
| Lighter | varies | DEX | P1 |
| dYdX v4 | 1h | DEX | P2 |
| Bybit | 8h | CEX | P2 |
| Binance | 8h | CEX | P3 |

## Key Endpoints

### Hyperliquid (details: [docs/api/hyperliquid.md](api/hyperliquid.md))
```
POST /info {"type": "metaAndAssetCtxs"}    # Funding rates + market info  
POST /info {"type": "allMids"}             # All mid prices
POST /info {"type": "l2Book", "coin": X}   # Order book
POST /info {"type": "clearinghouseState"}  # Positions + balance
POST /exchange {"action": {"type": "order"}}  # Trading (signed)
WS: allMids, l2Book, userFills, userFundings
```

### Aster (details: [docs/api/aster.md](api/aster.md))
```
Base URL: https://fapi.asterdex.com
Auth: V3 (EIP-712, recommended) or V1 (HMAC, legacy)
Interface: Binance-compatible (BTCUSDT symbols, standard params)

GET /fapi/v1/premiumIndex         # Funding rate + mark price
GET /fapi/v1/fundingRate          # Funding history
POST /fapi/v1/order               # Order
WS: <symbol>@bookTicker, mini_ticker
```

## Normalization

### Periods -> APR
```python
def normalize_to_annual(rate: Decimal, period_hours: int) -> Decimal:
    periods_per_year = Decimal(8760) / Decimal(period_hours)
    return rate * periods_per_year * Decimal(100)

# Hyperliquid: 0.003% for 1h -> 26.28% APR
# Aster: 0.01% for 8h -> 10.95% APR
```

### Symbols
```python
# Hyperliquid: coin name only ("BTC", "ETH", "ANSEM")
# Aster: Binance-style ("BTCUSDT", "ETHUSDT", "ANSEMUSDT")

SYMBOL_MAP = {
    "BTC": {"hyperliquid": "BTC", "aster": "BTCUSDT"},
    "ETH": {"hyperliquid": "ETH", "aster": "ETHUSDT"},
    "ANSEM": {"hyperliquid": "ANSEM", "aster": "ANSEMUSDT"},
}
```

## Shared Connectivity Architecture

Both venues use EIP-712 signing -> a shared signing utility makes sense:
```python
# Shared pattern:
# 1. Construct typed data payload
# 2. Sign with private key (eth_account)
# 3. Submit action + signature + nonce

# Hyperliquid: POST /exchange {action, nonce, signature}
# Aster V3: Similar EIP-712 pattern
```

## Authentication

- **Hyperliquid (DEX):** EIP-712 typed data signature. API Wallet (`approveAgent`) for delegated trading.
- **Aster V3 (DEX):** EIP-712 typed data signature (similar to HL). Supports agent keys.
- **Aster V1 (legacy):** API Key + HMAC-SHA256 (Binance-like). New keys are no longer created as of March 2026.
- **CEX (future):** API Key + Secret. Permissions: Read + Trade. Never grant Withdraw.

## Python SDK dependencies

```
# Current code (Phase 1)
httpx                      # REST connectors
websockets                 # WS feeds
pydantic                   # response validation schemas

# Later (Phase 3, execution)
eth-account                # EIP-712 signing (V3)
```

Note:

- At the current stage, the project uses `httpx` with custom adapters.
- Official SDKs can be adopted later if they provide an execution-side advantage.
