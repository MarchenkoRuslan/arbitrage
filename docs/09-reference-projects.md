# Reference Projects: Patterns

## Reviewed Projects

### 1. FundingArbitrageBot (HL↔Lighter)

**Key patterns:**
- **Entry sequencing:** hedge first, exposed second (cover-on-timeout)
- **Maker-first:** limit → wait N seconds → taker fallback
- **Anti-churn:** shallow flip (noise) vs deep flip (real reversal, close after 3h)
- **Persistence gate:** do not enter if the rate stays below 6h consecutively
- **Real settlement:** read actual funding from the API, not rate × time

### 2. funding-arb-engine (Binance↔OKX)

**Key patterns:**
- **Recovery paths:** pair close, emergency flatten, imbalance recovery
- **Entry gates:** exposure cap, rate-limit pressure, margin mode check
- **Ops console:** web UI for manual override (hedge, flatten, pause)
- **Invariant checks:** automated PASS/FAIL reports
- **JSONL events:** structured audit trail

### 3. crypto-trading-bot (12 exchanges)

**Key patterns:**
- **ccxt for all exchanges** — one ExchangeManager
- **Slippage optimization:** max 0.1% acceptable slippage
- **Exit strategy:** profit target + time-based (max 8h per trade)
- **Strategy validator:** pre-execution checks

### 4. funding-scout-oss (EV Calculator)

**Key patterns:**
- **Round-trip cost model:** fees + slippage + friction tax
- **min_profitable_hours** = cost / hourly_income
- **Kaplan-Meier survival:** forecast funding window duration
- **Plug-in connectors:** one class per venue with `fetch_snapshot()`

---

## What We Adopt

### Phase 0-3 (required):
1. ✅ Entry sequencing
2. ✅ Maker-first + taker fallback  
3. ✅ Persistence gate
4. ✅ Round-trip cost model
5. ✅ Reconciliation at restart
6. ✅ Combined score (basis + funding - fees)

### Phase 4-5 (preferred):
7. Anti-churn logic
8. Kaplan-Meier survival
9. Ops console
10. Invariant checks

---

## Our Differentiation

| | Existing tools | Ours |
|---|---|---|
| CEX + DEX | Usually one side only | Both |
| Scoring | Funding only | Basis + Funding |
| Exchanges | 2 | 6-10 |
| ADL handling | Flatten | Smart recovery |
