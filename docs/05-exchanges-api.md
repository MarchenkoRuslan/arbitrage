# Exchanges and APIs

## Active Venues

| Exchange | Type | Funding Period | Fee | Auth | Status |
|---|---|---|---|---|---|
| Hyperliquid | DEX (Layer 1) | 1h | 0.035% taker | None | ✅ Active |
| Lighter | DEX (ZK Rollup / ETH) | 1h (approximated) | 0% | None | ✅ Active |

Both APIs are public REST — no API keys, no KYC, no registration required.

---

## Hyperliquid

```
Base URL: https://api.hyperliquid.xyz

POST /info {"type": "metaAndAssetCtxs"}
  → [{"universe": [{"name": "BTC", ...}]}, [{"funding": "0.0001", "markPx": "64000", ...}]]
  Returns: funding rate + mark/oracle price + volume + OI for all markets in one call

Funding period: 1h
Symbol format: bare coin name (BTC, ETH, SOL...)
Markets: ~232 perps
```

APR conversion: `rate × 8760 × 100`

---

## Lighter

```
Base URL: https://mainnet.zklighter.elliot.ai

GET /api/v1/orderBookDetails?filter=perp
  → {"order_book_details": [{"symbol": "ETH", "market_type": "perp", "status": "active",
                               "mark_price": "1893.79", "index_price": "1894.65",
                               "daily_quote_token_volume": 203656594, ...}]}
  Returns: all perp markets with mark/index price and 24h volume in one call

Funding period: 1h (payments every hour)
Funding rate approximation: (mark_price - index_price) / index_price / 8
Symbol format: bare coin name (ETH, BTC, SOL...)
Markets: ~219 active perps
Trading fee: 0% (zero-fee DEX)
```

Lighter’s funding formula per their docs:
```
premium_t = (ImpactBidPrice - index) or (index - ImpactAskPrice) / index
hourly_premium = average(premium_t) × FundingPremiumMultiplier
fundingRate = clamp(smallClampedPremium, -4%, +4%) / 8
```

The screener uses the simplified approximation `(mark - index) / index / 8`, which
closely tracks the actual rate for liquid markets and is sufficient for screening.

---

## Symbol Normalization

Both exchanges use bare coin names (BTC, ETH, SOL). No transformation needed —
`hl_symbol_to_normalized` and `lighter_symbol_to_normalized` both return `symbol.upper()`.

---

## Fee Model

```
Roundtrip cost = (hl_fee_per_side + lighter_fee_per_side) × 2 × 100 bps
              = (0.035% + 0.0%) × 2 × 100
              = 7 bps
```

Lighter charges zero trading fees, so the entire friction is Hyperliquid’s taker fee.

---

## Common Markets (as of 2026-07)

~92 symbols traded on both exchanges, including: BTC, ETH, SOL, AVAX, SUI, DOGE,
LINK, AAVE, WLD, ENA, TAO, NEAR, ADA, XMR, HYPE, TRUMP, KAITO, JUP, and more.
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
