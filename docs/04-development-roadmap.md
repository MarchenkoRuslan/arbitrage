# Дорожная карта

## Phase 0: Foundation
**Цель:** Подключиться к Hyperliquid + Aster, получить funding rates

- [ ] Проект (pyproject.toml, структура, .env)
- [ ] Core models (FundingRate, Ticker, Position)
- [ ] Hyperliquid connector (через `hyperliquid-python-sdk`)
  - [ ] Получить meta (все coins, funding rates, mark prices)
  - [ ] Получить orderbook (l2Book)
  - [ ] Подключить WebSocket (allMids)
- [ ] Aster connector (через `aster-connector-python`)
  - [ ] Получить funding rates (premiumIndex)
  - [ ] Получить тикеры (ticker/24hr)
- [ ] Маппинг общих символов между HL и Aster
- [ ] Скрипт: вывести таблицу funding diff

**Готово когда:** скрипт выводит:
```
| Symbol | HL Rate (1h) | Aster Rate (8h) | HL APR | Aster APR | Diff APR |
| ANSEM  | +0.05%       | +0.12%          | 438%   | 131%      | +307%    |
```

---

## Phase 1: Screener MVP
**Цель:** Рабочий скринер Hyperliquid ↔ Aster

- [ ] Aggregator — периодический сбор rates с обеих бирж
- [ ] Нормализация: HL 1h → APR, Aster 8h → APR
- [ ] Opportunity Finder + combined scoring (basis + funding - fees)
- [ ] Фильтры: min APR, min volume, persistence gate
- [ ] Basis calculation (price diff между биржами)
- [ ] CLI вывод opportunities (rich/tabulate)
- [ ] Автообновление каждые 5-10 сек

**Готово когда:** обновляемая таблица top opportunities

---

## Phase 2: Notifications + API
**Цель:** Уведомления и remote доступ

- [ ] Telegram бот (alerts при APR > threshold)
- [ ] FastAPI REST endpoints
- [ ] WebSocket для real-time
- [ ] Простой web dashboard

---

## Phase 3: Execution
**Цель:** Открытие/закрытие позиций на HL + Aster

- [ ] EIP-712 signing utility (shared for both venues)
- [ ] Hyperliquid: place order, cancel, get positions
- [ ] Aster: place order, cancel, get positions
- [ ] Параллельное исполнение (asyncio.gather)
- [ ] Entry sequencing (hedge first)
- [ ] Размер в МОНЕТАХ (не USDT!)
- [ ] Position state management
- [ ] Rollback при failure одной ноги

---

## Phase 4: Risk + Automation
**Цель:** Защита и автоматизация

- [ ] Margin monitoring + alerts
- [ ] ADL detection
- [ ] Funding flip detection + auto-close
- [ ] Auto-entry по правилам
- [ ] Auto-exit по правилам
- [ ] Portfolio limits

---

## Phase 5: Advanced
- [ ] Survival analysis (прогноз длительности окна)
- [ ] Spot + Futures стратегия
- [ ] Backtesting
- [ ] ML predicted rates
