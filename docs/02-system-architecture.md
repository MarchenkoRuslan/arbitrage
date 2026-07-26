# System Architecture

## High-Level Diagram

```
+---------------------------------------------------------------+
|                      ARBITRAGE SYSTEM                         |
|                                                               |
|   +------------------+         +------------------+          |
|   |  Hyperliquid     |         |     Lighter      |          |
|   |  DEX (Layer 1)   |         |  DEX (ZK / ETH)  |          |
|   |  POST /info      |         |  GET /orderBook  |          |
|   |  232 markets     |         |  219 markets     |          |
|   |  1h funding      |         |  1h funding, 0 fee          |
|   +--------+---------+         +--------+---------+          |
|            |   asyncio.gather()          |                    |
|            +------------+----------------+                    |
|                         |                                     |
|             +-----------v-----------+                         |
|             |    MarketState Cache  |  <- per exchange+symbol |
|             |    staleness check    |     funding history     |
|             +-----------+-----------+                         |
|                         |                                     |
|             +-----------v-----------+                         |
|             |       Screener        |  <- scoring + ranking   |
|             +-----------+-----------+                         |
|                         |                                     |
|             +-----------v-----------+                         |
|             |    Console Output     |  <- ranked table        |
|             +-----------------------+                         |
+---------------------------------------------------------------+
```

---

## Poll Cycle (every `loop_interval_s` seconds)

```
App.poll_once()
  +-- asyncio.gather(
  |     HyperliquidConnector.get_market_data()   # POST /info -> (rates, tickers)
  |     LighterConnector.get_market_data()       # GET /orderBookDetails -> (rates, tickers)
  |   )
  +-- state.update_funding/tickers (both exchanges)
  +-- find_opportunities_from_state(state, settings)
  +-- print_opportunities(opps)
```

---

## Modules

### 1. Exchange Connectors

Each connector is self-contained with no shared state.

**HyperliquidConnector** (`src/exchanges/hyperliquid.py`)
- Single call: `POST /info {"type": "metaAndAssetCtxs"}` returns funding + tickers
- Funding period: 1h. Rate is the raw periodic value from the exchange.
- No authentication required.

**LighterConnector** (`src/exchanges/lighter.py`)
- Single call: `GET /api/v1/orderBookDetails?filter=perp` returns all perp markets
- Funding rate approximated as `(mark_price - index_price) / index_price / 8` (hourly)
- Zero trading fees. No authentication required.

### 2. MarketState

Asyncio-safe in-memory cache keyed by `exchange::symbol`.
- Stores `FundingRate` and `Ticker` per (exchange, symbol)
- Tracks update timestamps for staleness checks (`stale_data_s`)
- Maintains funding history deques for future persistence scoring

### 3. Screener (`src/screener/finder.py`)

```
combined_score_bps = funding_edge_bps - roundtrip_fee_bps + basis_bonus_bps

funding_edge_bps  = funding_diff_apr x (hold_hours / 8760) x 100
roundtrip_fee_bps = (hl_fee_per_side + lighter_fee_per_side) x 2 x 100  # = 7 bps
basis_bonus_bps   = max(0, directional_basis_bps) x basis_weight
```

Filters applied:
1. Both symbols present and not stale
2. `min(hl_volume, lighter_volume) >= min_volume_24h`
3. Negative basis: skip if funding cannot cover the loss within the hold window
4. `combined_score >= min_score_bps`

### 4. App Orchestrator (`src/core/app.py`)

- Manages connector lifecycle and graceful shutdown
- Runs parallel fetch via `asyncio.gather`
- Drives the polling loop at configurable interval

### 5. Trader (Execution, planned)

Not implemented. Planned: simultaneous delta-neutral position open on both DEXes.
