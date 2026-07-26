# Референсные проекты: паттерны

## Изученные проекты

### 1. FundingArbitrageBot (HL↔Lighter)

**Ключевые паттерны:**
- **Entry sequencing:** hedge first, exposed second (cover-on-timeout)
- **Maker-first:** limit → wait N сек → taker fallback
- **Anti-churn:** shallow flip (noise) vs deep flip (real reversal, close after 3h)
- **Persistence gate:** не входить если rate < 6h подряд
- **Real settlement:** читать actual funding из API, не rate×time

### 2. funding-arb-engine (Binance↔OKX)

**Ключевые паттерны:**
- **Recovery paths:** pair close, emergency flatten, imbalance recovery
- **Entry gates:** exposure cap, rate-limit pressure, margin mode check
- **Ops console:** web UI для manual override (hedge, flatten, pause)
- **Invariant checks:** automated PASS/FAIL reports
- **JSONL events:** structured audit trail

### 3. crypto-trading-bot (12 exchanges)

**Ключевые паттерны:**
- **ccxt для всех бирж** — один ExchangeManager
- **Slippage optimization:** max 0.1% допустимый slippage
- **Exit strategy:** profit target + time-based (max 8h per trade)
- **Strategy validator:** pre-execution checks

### 4. funding-scout-oss (EV Calculator)

**Ключевые паттерны:**
- **Round-trip cost model:** fees + slippage + friction tax
- **min_profitable_hours** = cost / hourly_income
- **Kaplan-Meier survival:** прогноз длительности funding window
- **Plug-in connectors:** один класс на venue с `fetch_snapshot()`

---

## Что берём

### Phase 0-3 (обязательно):
1. ✅ Entry sequencing
2. ✅ Maker-first + taker fallback  
3. ✅ Persistence gate
4. ✅ Round-trip cost model
5. ✅ Reconciliation at restart
6. ✅ Combined score (basis + funding - fees)

### Phase 4-5 (желательно):
7. Anti-churn logic
8. Kaplan-Meier survival
9. Ops console
10. Invariant checks

---

## Наша дифференциация

| | Существующие | Наша |
|---|---|---|
| CEX + DEX | Обычно одно | Обе |
| Scoring | Только funding | Basis + Funding |
| Exchanges | 2 | 6-10 |
| ADL handling | Flatten | Smart recovery |
