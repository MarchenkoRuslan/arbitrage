# Hyperliquid API Reference

## Base URL
- Mainnet: `https://api.hyperliquid.xyz`
- Info endpoint: `POST /info`
- Exchange endpoint: `POST /exchange`
- WebSocket: `wss://api.hyperliquid.xyz/ws`

## Funding Rate: 1 hour

## Authentication
- Each trade action is signed with a private key (EIP-712 typed data)
- Nonce = current timestamp in milliseconds
- API Wallet (Agent): `approveAgent` - delegated key for trading without the master key

## Key Endpoints

### Info (read-only, unsigned)

| Request | type | Returns |
|--------|------|---------------|
| All mid prices | `allMids` | `{"BTC": "64500.0", "ETH": "3400.0", ...}` |
| Order book | `l2Book` | Up to 20 bid/ask levels |
| Positions | `clearinghouseState` | Positions, margin, PnL |
| Open orders | `openOrders` | All active orders |
| Fills | `userFills` | Up to 2000 fills |
# Hyperliquid API Reference

## Base URL
- Mainnet: `https://api.hyperliquid.xyz`
- Info endpoint: `POST /info`
- Exchange endpoint: `POST /exchange`
- WebSocket: `wss://api.hyperliquid.xyz/ws`

## Funding Rate: 1 Hour

## Authentication
- Each trade action is signed with a private key using EIP-712 typed data
- `nonce` is the current timestamp in milliseconds
- API Wallet (Agent): `approveAgent` provides a delegated key for trading without the master key

## Key Endpoints

### Info (Read-Only, Unsigned)

| Request | type | Returns |
|--------|------|---------|
| All mid prices | `allMids` | `{"BTC": "64500.0", "ETH": "3400.0", ...}` |
| Order book | `l2Book` | Up to 20 bid/ask levels |
| Positions | `clearinghouseState` | Positions, margin, PnL |
| Open orders | `openOrders` | All active orders |
| Fills | `userFills` | Up to 2000 fills |
| Order status | `orderStatus` | By oid or cloid |
| Fees | `userFees` | Current tiers and rates |
| Rate limits | `userRateLimit` | Used and available request budget |
| Meta (instruments) | `meta` | Universe, funding rates, OI, mark prices |

### Fetching Funding Rates
```python
# POST /info
{"type": "metaAndAssetCtxs"}

# Response includes for each asset:
# - funding: current rate (payment for 1 hour)
# - openInterest
# - markPx, oraclePx
# - prevDayPx (for calculating 24h change)
```

### Exchange (Requires Signature)

| Action | type | Description |
|--------|------|-------------|
| Order | `order` | Limit/IOC/ALO + trigger (TP/SL) |
| Cancel | `cancel` | By oid |
| Cancel by cloid | `cancelByCloid` | By client order ID |
| Modify | `modify` | Change price/size |
| Leverage | `updateLeverage` | Set leverage |
| Margin | `updateIsolatedMargin` | Add or remove margin |

### Order Format
```python
{
    "action": {
        "type": "order",
        "orders": [{
            "a": 0,            # asset index (0=BTC, 1=ETH, ...)
            "b": True,         # isBuy
            "p": "64500.0",   # price
            "s": "0.01",      # size
            "r": False,        # reduceOnly
            "t": {"limit": {"tif": "Gtc"}},  # Gtc/Ioc/Alo
        }],
        "grouping": "na",
    },
    "nonce": 1690000000000,    # timestamp ms
    "signature": {...},        # EIP-712
}
```

### Order Types (TIF)
- **GTC** - Good Til Canceled (standard limit)
- **IOC** - Immediate Or Cancel (market-like with a price limit)
- **ALO** - Add Liquidity Only (post-only, maker only)

### Client Order ID
- 128-bit hex string: `0x1234567890abcdef1234567890abcdef`
- Allows order tracking without an oid

## WebSocket

```python
# Connection
ws = websocket.connect("wss://api.hyperliquid.xyz/ws")

# Subscriptions
{"method": "subscribe", "subscription": {"type": "allMids"}}
{"method": "subscribe", "subscription": {"type": "l2Book", "coin": "BTC"}}
{"method": "subscribe", "subscription": {"type": "trades", "coin": "BTC"}}
{"method": "subscribe", "subscription": {"type": "userEvents", "user": "0x..."}}
{"method": "subscribe", "subscription": {"type": "userFills", "user": "0x..."}}
{"method": "subscribe", "subscription": {"type": "userFundings", "user": "0x..."}}
```

## Python SDK
- Official package: `hyperliquid-python-sdk`
- Includes examples for place order, cancel, market data, and vault operations
- Signing uses EIP-712 via `eth_account`

## Rate Limits
- Base limit is proportional to cumulative volume
- `nRequestsCap` = approximately `cumVlm` in USDC
- Extra requests can be purchased for `0.0005` USDC/request via `reserveRequestWeight`
- Dead man's switch: `scheduleCancel` supports auto-cancel after N seconds

## Fees (Base)
- Taker (cross): `0.045%`
- Maker (add): `0.015%`
- VIP tiers reduce fees starting at `$5M` volume
- MM tiers provide maker rebates
- Referral discount: `4%`
- Staking discount: up to `30%`

## Notes
- Asset index: sequential number in `meta.universe` (BTC=0, ETH=1, ...)
- Spot assets: `10000 + index`
- HIP-3 DEX assets: prefix `dex:SYMBOL` (for example `xyz:XYZ100`)
- Minimum order value: `$10`
- Subaccounts are signed by the master key with `vaultAddress`
- Dead man's switch: maximum `10` triggers per day
