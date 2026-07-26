# Дорожная карта

## Phase 0: Foundation
**Цель:** Подключиться к Hyperliquid + Aster, получить funding rates

- [x] Проект (pyproject.toml, структура, .env)
- [x] Core models (FundingRate, Ticker)
- [x] Hyperliquid REST connector
  - [x] Получить meta (coins, funding rates, mark prices)
  - [ ] Получить orderbook (l2Book)
  - [x] Подготовлен WebSocket feed (allMids)
- [x] Aster REST connector
  - [x] Получить funding rates (premiumIndex)
  - [x] Получить тикеры (ticker/24hr)
  - [x] Подготовлен WebSocket feed (miniTicker)
- [x] Маппинг общих символов между HL и Aster
- [x] Скрипт: вывести таблицу funding diff

**Готово когда:** скрипт выводит:
```
| Symbol | HL Rate (1h) | Aster Rate (8h) | HL APR | Aster APR | Diff APR |
| ANSEM  | +0.05%       | +0.12%          | 438%   | 131%      | +307%    |
```

---

## Phase 1: Screener MVP
**Цель:** Рабочий скринер Hyperliquid ↔ Aster

- [x] Aggregator — периодический сбор rates с обеих бирж
- [x] Нормализация: HL 1h → APR, Aster 8h → APR
- [x] Opportunity Finder + combined scoring (basis + funding - fees)
- [ ] Фильтры: min APR, min volume, persistence gate
- [x] Basis calculation (price diff между биржами)
- [x] CLI вывод opportunities
- [x] Автообновление каждые 5-10 сек
- [x] In-memory market state для zero-IO hot path
- [x] Resilient HTTP (retry/backoff/rate-limit handling)
- [ ] WS ingestion как основной runtime режим

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

---

## Текущая стадия

- Фактическое состояние: поздний Phase 1
- На проде уже работает: polling-based MVP screener
- Следующий ключевой шаг: перевести ingestion в WS-first режим и добавить persistence gate
