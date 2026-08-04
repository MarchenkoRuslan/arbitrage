# Development Roadmap

## Phase 0: Foundation ✅
**Goal:** Connect to two DEX venues and retrieve funding rates

- [x] Project scaffold (pyproject.toml, structure, .env)
- [x] Core models (FundingRate, Ticker, ArbitrageOpportunity)
- [x] Hyperliquid REST connector (`POST /info metaAndAssetCtxs`)
- [x] Lighter REST connector (`GET /api/v1/orderBookDetails`)
- [x] Funding rate approximation for Lighter: `(mark − index) / index / 8`
- [x] Map shared symbols between HL and Lighter (92 common markets as of 2026-07)
- [x] Resilient HTTP client (retry + backoff + rate-limit handling)

---

## Phase 1: Screener MVP ✅
**Goal:** Working Hyperliquid ↔ Lighter screener

- [x] Parallel fetch from both DEXes (`asyncio.gather`)
- [x] APR normalization (both exchanges: 1h period)
- [x] Combined scoring: funding edge − fees + basis bonus
- [x] Fee model: HL 3.5 bps/side, Lighter 0 bps → 7 bps roundtrip
- [x] Volume filter, staleness check, negative-basis breakeven check
- [x] Open-interest filter (configurable)
- [x] Index-aware basis denominator (fallback to mark midpoint)
- [x] CLI output (ranked table with Score bps, Diff APR%, Basis bps, BE h)
- [x] Auto-refresh loop (`--loop` flag)
- [x] In-memory MarketState for zero-IO hot path
- [x] Persistence tracking in MarketState
- [x] Entry validator (ready/watching/blocked)
- [x] Anti-churn signal cooldown

**Live output sample:**
```
Symbol     Long         Short         Diff APR%   Fund bps  Score bps    BE h
AERO       lighter      hyperliquid      177.75     146.09     143.45      3.5
KAITO      lighter      hyperliquid      172.71     141.95     139.92      3.5
(31 opportunities found)
```

---

## Phase 2: Notifications + API
**Goal:** Notifications and remote access

- [ ] Telegram bot (alerts when APR > threshold)
- [x] FastAPI REST endpoints (`/opportunities`, `/config`, `/status`) with Swagger UI
- [x] WebSocket for real-time updates (`/ws/opportunities`)
- [ ] Simple web dashboard

---

## Phase 3: WS Ingestion
**Goal:** Replace REST polling with event-driven feeds

- [ ] Hyperliquid WS (`allMids` for price updates)
- [ ] Lighter WS (orderbook stream)
- [ ] Hybrid mode: REST snapshot on startup, WS incremental updates

---

## Phase 4: Execution
**Goal:** Open and close positions on HL + Lighter

- [ ] Hyperliquid: EIP-712 signing, place/cancel orders, positions
- [ ] Lighter: SDK signing, place/cancel orders, positions
- [ ] Delta-neutral two-leg opener with rollback on partial fill
- [ ] Position monitor + close logic
- [ ] Parallel execution (asyncio.gather)
- [ ] Entry sequencing (hedge first)
- [ ] Position sizing in COINS (not USDT)
- [ ] Position state management
- [ ] Rollback if one leg fails

---

## Phase 5: Risk + Automation
**Goal:** Protection and automation

- [ ] Margin monitoring + alerts
- [ ] ADL detection
- [ ] Funding flip detection + auto-close
- [ ] Rule-based auto-entry
- [ ] Rule-based auto-exit
- [ ] Portfolio limits

---

## Phase 6: Advanced
- [ ] Survival analysis (window duration forecasting)
- [ ] Spot + Futures strategy
- [ ] Backtesting
- [ ] ML predicted rates

---

## Current Stage

- Actual state: Phase 2 (API layer delivered)
- Already running in production: polling-based screener with validator, anti-churn, REST API + WS
- Next key step: Telegram notifications or WS-first ingestion

---

## Ongoing Track: Documentation Maintenance

**Goal:** Keep docs, plans, and instructions synchronized with implementation.

- [x] Add dedicated API docs for both active exchanges (Hyperliquid + Lighter)
- [x] Remove duplicated and stale sections from API references
- [x] Align README/docs links with current structure
- [x] Add explicit documentation maintenance workflow and update checklist
- [x] Add CI check to fail on broken doc links
- [x] Extend doc checks to validate markdown heading anchors
- [x] Add release-note template for behavior-changing updates
