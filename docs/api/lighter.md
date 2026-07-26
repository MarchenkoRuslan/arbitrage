# Lighter API Reference

## Scope in This Repository

Current runtime uses Lighter as a read-only market data source for the screener.
Execution endpoints and signing are out of scope for active runtime.

## Base URL

- Mainnet REST: `https://mainnet.zklighter.elliot.ai`

## Funding Interval

- Effective funding period: 1 hour
- In this project, funding is approximated from mark/index prices:

```text
funding_rate_hourly ~= (mark_price - index_price) / index_price / 8
```

The approximation is sufficient for ranking opportunities in a read-only screener.

## Active Read-Only Endpoint (Used Now)

### Perpetual Markets Snapshot

Request:
- `GET /api/v1/orderBookDetails?filter=perp`

Example response shape:

```json
{
  "order_book_details": [
    {
      "symbol": "ETH",
      "market_type": "perp",
      "status": "active",
      "mark_price": "1893.79",
      "index_price": "1894.65",
      "daily_quote_token_volume": 203656594
    }
  ]
}
```

Used fields in connector:
- `symbol`
- `market_type`
- `status`
- `mark_price`
- `index_price`
- `daily_quote_token_volume`

## Runtime Behavior in This Project

- Only active perp markets are used for screening.
- Symbols are normalized as uppercase coin names.
- Ticker and funding snapshots are refreshed by REST polling.

## Notes

- Lighter fee is modeled as `ARB_LIGHTER_FEE_PER_SIDE` in settings (default `0.0`).
- Lighter funding approximation should be changed only together with docs and tests.
