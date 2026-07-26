# Архитектура системы

## Высокоуровневая схема

```
┌─────────────────────────────────────────────────────────────┐
│                     ARBITRAGE SYSTEM                         │
│                                                             │
│  ┌──────────────┐                  ┌──────────────────────┐  │
│  │ Hyperliquid  │                  │        Aster         │  │
│  └──────┬───────┘                  └─────────┬────────────┘  │
│         └──────────────┬─────────────────────┘               │
│                        │                                      │
│              ┌─────────▼──────────┐                           │
│              │ Ingestion Layer    │ ← REST + WS feeds        │
│              └─────────┬──────────┘                           │
│                        │                                      │
│              ┌─────────▼──────────┐                           │
│              │ MarketState Cache  │ ← In-memory shared state │
│              └─────────┬──────────┘                           │
│                        │                                      │
│              ┌─────────▼──────────┐                           │
│              │ Screener           │ ← scoring + ranking      │
│              └─────────┬──────────┘                           │
│                        │                                      │
│              ┌─────────▼──────────┐                           │
│              │ Output/Alerts      │ ← CLI now, API later     │
│              └────────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Модули

### 1. Exchange Connectors

Единый интерфейс для venues (native adapters + protocol).

```python
class ExchangeConnector(Protocol):
  async def get_funding_rates(self) -> dict[str, FundingRate]
  async def get_tickers(self) -> dict[str, Ticker]
  async def get_market_data(self) -> tuple[dict[str, FundingRate], dict[str, Ticker]]
  async def start_stream(self, state: MarketState) -> None
  async def close(self) -> None
```

### 2. Screener

Сбор funding rates со всех бирж → поиск пар с максимальной разницей → ранжирование.

```python
@dataclass
class ArbitrageOpportunity:
    symbol: str
    long_exchange: str
    short_exchange: str
    funding_diff_apr: Decimal   # Разница ставок (APR)
    basis_bps: Decimal          # Ценовой базис
    combined_score: Decimal     # funding - fee_impact + basis_weight*basis
```

**Логика:**
1. Ingestion обновляет `MarketState` (REST polling, далее WS-first)
2. Для каждого общего символа найти направление long/short по APR
3. Рассчитать basis (price diff) и combined score
4. Отфильтровать: min score (persistence gate в следующем шаге)
5. Ранжировать по combined_score

### 3. App Orchestrator

- Управляет lifecycle: startup, polling loop, graceful shutdown
- Обновляет `MarketState`
- Запускает screener и вывод

### 4. Trader (Execution, planned)

Одновременное открытие/закрытие позиций.

**Принципы:**
- Entry sequencing: hedge-нога первой, exposed — второй
- Maker-first: limit order → wait → fallback to taker
- Размер в МОНЕТАХ (не USDT)
- Rollback при неудаче одной ноги
- Reconciliation при restart

### 5. Risk/Monitor (planned)

- Margin ratio мониторинг
- ADL detection
- Funding rate change alerts
- Spread expansion alerts
- Auto-close при критических событиях
- Telegram notifications

---

## Потоки данных

```
Текущий runtime (polling):
  Exchanges → Connectors → MarketState → Screener → CLI

Целевой runtime (WS-first):
  WS Feeds + REST Snapshot/Recovery → MarketState → Screener → Alerts/API

Открытие позиции:
  Signal → Risk Check → Size Calc → Parallel Orders → Position Record

Мониторинг (непрерывно):
  Exchanges → Prices/Margin/Funding → Monitor → Alerts/Auto-actions

Закрытие:
  Signal → Parallel Close → PnL Calc → Record
```

---

## Режимы работы

1. **Screener-only** — показывает возможности, не торгует
2. **Manual** — planned
3. **Semi-auto** — planned
4. **Full-auto** — planned
