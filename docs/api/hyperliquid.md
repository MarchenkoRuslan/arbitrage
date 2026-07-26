# Hyperliquid API Reference

## Scope in This Repository

Current runtime uses Hyperliquid as a read-only data source for the screener.
Trading endpoints are documented for planned execution phases, but are not used by
the active runtime.

## Base URLs

- Mainnet REST: `https://api.hyperliquid.xyz`
- Info endpoint: `POST /info`
- Exchange endpoint: `POST /exchange`
- WebSocket: `wss://api.hyperliquid.xyz/ws`

## Funding Interval

- Funding settlement period: 1 hour
- APR conversion used by screener: `hourly_rate * 8760 * 100`

## Active Read-Only Endpoint (Used Now)

### Funding and Market Snapshot

```json
{"type": "metaAndAssetCtxs"}
```

Request:
- `POST /info`

Used response fields per asset:
- `funding`
- `markPx`
- `oraclePx`
- `openInterest`
- `dayNtlVlm`

## Additional Info Endpoints (Reference)

| Request | type | Returns |
|---|---|---|
| All mid prices | `allMids` | Mid prices map by symbol |
| Order book | `l2Book` | Up to 20 bid/ask levels |
| Positions | `clearinghouseState` | Positions, margin, PnL |
| Open orders | `openOrders` | Active orders |
| Fills | `userFills` | User fills |
| Order status | `orderStatus` | Order by oid or cloid |
| Fees | `userFees` | Current fee tiers |
| Rate limits | `userRateLimit` | Budget usage and cap |
| Meta | `meta` | Instruments universe |

## Trading Authentication (Execution Phase)

- Hyperliquid trade actions are signed with EIP-712 typed data.
- `nonce` is current Unix timestamp in milliseconds.
- API Wallet (`approveAgent`) can delegate trading without the master key.

## Exchange Actions (Execution Phase)

| Action | type | Description |
|---|---|---|
| Place order | `order` | Limit/IOC/ALO and trigger orders |
| Cancel | `cancel` | Cancel by oid |
| Cancel by client id | `cancelByCloid` | Cancel by cloid |
| Modify | `modify` | Change size and/or price |
| Update leverage | `updateLeverage` | Set leverage |
| Update isolated margin | `updateIsolatedMargin` | Add/remove margin |

## WebSocket (Planned for WS Ingestion)

Common subscriptions:
- `allMids`
- `l2Book`
- `trades`
- `userEvents`
- `userFills`
- `userFundings`

## Notes

- Perp symbols are bare coin names (`BTC`, `ETH`, `SOL`, ...).
- Asset index order follows `meta.universe`.
- Spot assets use index offset (`10000 + index`).
- The screener fee model is configured in settings (`ARB_HL_FEE_PER_SIDE`) rather than hardcoded in connector logic.
