# Development Roadmap

## Phase 0: Foundation
**Goal:** Connect to Hyperliquid + Aster and retrieve funding rates

- [x] Project scaffold (pyproject.toml, structure, .env)
- [x] Core models (FundingRate, Ticker)
- [x] Hyperliquid REST connector
  - [x] Fetch meta (coins, funding rates, mark prices)
  - [ ] Fetch order book (l2Book)
  - [x] Prepare WebSocket feed (allMids)
- [x] Aster REST connector
  - [x] Fetch funding rates (premiumIndex)
  - [x] Fetch tickers (ticker/24hr)
  - [x] Prepare WebSocket feed (miniTicker)
- [x] Map shared symbols between HL and Aster
- [x] Script: print the funding diff table

**Done when:** the script prints:
```
| Symbol | HL Rate (1h) | Aster Rate (8h) | HL APR | Aster APR | Diff APR |
| ANSEM  | +0.05%       | +0.12%          | 438%   | 131%      | +307%    |
```

---

## Phase 1: Screener MVP
**Goal:** Working Hyperliquid ↔ Aster screener

- [x] Aggregator - periodic collection of rates from both exchanges
- [x] Normalization: HL 1h -> APR, Aster 8h -> APR
- [x] Opportunity Finder + combined scoring (basis + funding - fees)
- [ ] Filters: min APR, min volume, persistence gate
- [x] Basis calculation (price diff between exchanges)
- [x] CLI output for opportunities
- [x] Auto-refresh every 5-10 seconds
- [x] In-memory market state for a zero-IO hot path
- [x] Resilient HTTP (retry/backoff/rate-limit handling)
- [ ] WS ingestion as the primary runtime mode

**Done when:** a live-updating top opportunities table is available

---

## Phase 2: Notifications + API
**Goal:** Notifications and remote access

- [ ] Telegram bot (alerts when APR > threshold)
- [ ] FastAPI REST endpoints
- [ ] WebSocket for real-time updates
- [ ] Simple web dashboard

---

## Phase 3: Execution
**Goal:** Open and close positions on HL + Aster

- [ ] EIP-712 signing utility (shared for both venues)
- [ ] Hyperliquid: place order, cancel, get positions
- [ ] Aster: place order, cancel, get positions
- [ ] Parallel execution (asyncio.gather)
- [ ] Entry sequencing (hedge first)
- [ ] Position sizing in COINS (not USDT)
- [ ] Position state management
- [ ] Rollback if one leg fails

---

## Phase 4: Risk + Automation
**Goal:** Protection and automation

- [ ] Margin monitoring + alerts
- [ ] ADL detection
- [ ] Funding flip detection + auto-close
- [ ] Rule-based auto-entry
- [ ] Rule-based auto-exit
- [ ] Portfolio limits

---

## Phase 5: Advanced
- [ ] Survival analysis (window duration forecasting)
- [ ] Spot + Futures strategy
- [ ] Backtesting
- [ ] ML predicted rates

---

## Current Stage

- Actual state: late Phase 1
- Already running in production: polling-based MVP screener
- Next key step: move ingestion to a WS-first mode and add a persistence gate
