# Архитектура системы

## Высокоуровневая схема

```
┌─────────────────────────────────────────────────────────────┐
│                     ARBITRAGE SYSTEM                         │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Binance  │  │  Bybit   │  │   OKX    │  │Hyperliquid│  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       └──────────────┼──────────────┼──────────────┘        │
│                      │                                      │
│              ┌───────▼───────┐                               │
│              │  SCREENER     │ ← Сбор rates, поиск пар      │
│              └───────┬───────┘                               │
│                      │                                      │
│              ┌───────▼───────┐                               │
│              │  TRADER       │ ← Открытие/закрытие позиций  │
│              └───────┬───────┘                               │
│                      │                                      │
│              ┌───────▼───────┐                               │
│              │  RISK/MONITOR │ ← Мониторинг, alerts         │
│              └───────────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Модули

### 1. Exchange Connectors

Единый интерфейс для всех бирж (через ccxt + native adapters).

```python
class ExchangeConnector(ABC):
    async def get_funding_rates(self, symbols: list[str]) -> dict[str, FundingRate]
    async def get_tickers(self, symbols: list[str]) -> dict[str, Ticker]
    async def get_positions(self) -> list[Position]
    async def get_balance(self) -> Balance
    async def place_order(self, order: OrderRequest) -> OrderResult
    async def cancel_order(self, order_id: str) -> bool
```

### 2. Screener

Сбор funding rates со всех бирж → поиск пар с максимальной разницей → ранжирование.

```python
@dataclass
class ArbitrageOpportunity:
    symbol: str
    long_exchange: str
    short_exchange: str
    funding_diff: Decimal       # Разница ставок
    apr: Decimal                # Годовая доходность
    basis_bps: Decimal          # Ценовой базис
    combined_score: Decimal     # funding + basis - fees
    volume_min: Decimal         # Минимальный volume
    funding_persistence_h: int  # Сколько часов rate держится
    min_profitable_hours: Decimal
```

**Логика:**
1. Собрать funding rates по всем парам на всех биржах
2. Для каждого символа найти пары бирж с максимальной разницей
3. Рассчитать basis (price diff) и combined score
4. Отфильтровать: min score, min volume, persistence gate
5. Ранжировать по combined_score

### 3. Trader (Execution)

Одновременное открытие/закрытие позиций.

**Принципы:**
- Entry sequencing: hedge-нога первой, exposed — второй
- Maker-first: limit order → wait → fallback to taker
- Размер в МОНЕТАХ (не USDT)
- Rollback при неудаче одной ноги
- Reconciliation при restart

### 4. Risk/Monitor

- Margin ratio мониторинг
- ADL detection
- Funding rate change alerts
- Spread expansion alerts
- Auto-close при критических событиях
- Telegram notifications

---

## Потоки данных

```
Скрининг (каждые 5-10 сек):
  Exchanges → Funding Rates → Screener → Opportunities → Dashboard/Telegram

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
2. **Manual** — скринер + исполнение по команде
3. **Semi-auto** — авто-вход по фильтрам, ручной выход
4. **Full-auto** — полная автоматизация входа/выхода
