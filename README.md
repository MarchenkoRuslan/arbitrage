# Funding Rate Arbitrage System

## Обзор

Система для поиска арбитражных возможностей по funding rate между Hyperliquid и Aster.

Текущий фокус: быстрый и надежный screener (read-only), который:
1. Собирает funding/price данные с двух бирж
2. Нормализует ставки в APR
3. Считает combined score (funding edge + basis - fee impact)
4. Выводит top opportunities

## Текущий статус

- Stage: Phase 1 (рабочий MVP screener)
- Реализовано: коннекторы, нормализация, state cache, resilient HTTP, scoring, CLI вывод
- Подготовлено: WS feed-модули для перехода на event-driven ingest
- Не реализовано: execution engine, risk automation, alerts/API/dashboard

## Реализованная структура

```
arbitrage/
├── docs/
├── src/
│   ├── core/
│   │   ├── app.py          # Оркестратор приложения
│   │   ├── config.py       # Конфигурация через env
│   │   ├── http.py         # HTTP retry/backoff клиент
│   │   ├── models.py       # Pydantic models
│   │   ├── normalize.py    # APR/symbol normalization
│   │   └── state.py        # In-memory market state cache
│   ├── exchanges/
│   │   ├── base.py
│   │   ├── aster.py
│   │   ├── aster_ws.py
│   │   ├── hyperliquid.py
│   │   ├── hyperliquid_ws.py
│   │   └── schemas.py
│   ├── output/
│   │   └── console.py      # Табличный вывод
│   ├── screener/
│   │   └── finder.py       # Поиск и ранжирование opportunities
│   └── main.py             # CLI entrypoint
├── pyproject.toml
└── README.md
```

## Быстрый старт

```bash
python -m pip install -e ".[dev]"
python -m src.main
python -m src.main --loop
```

## Основные env-параметры

- `ARB_MIN_SCORE_APR` (default: `5.0`)
- `ARB_FEE_PER_SIDE` (default: `0.05`)
- `ARB_EXPECTED_HOLD_HOURS` (default: `72.0`)
- `ARB_BASIS_WEIGHT` (default: `0.1`)
- `ARB_LOOP_INTERVAL_S` (default: `10`)

## Документация

- [Доменные знания](docs/01-domain-knowledge.md)
- [Архитектура системы](docs/02-system-architecture.md)
- [Технический стек](docs/03-technical-stack.md)
- [Дорожная карта](docs/04-development-roadmap.md)
- [Биржи и API](docs/05-exchanges-api.md)
- [Референсы и источники](docs/06-references.md)
- [Стратегия Basis + Funding](docs/07-strategy-basis-funding.md)
- [Риски: ADL и кейсы](docs/08-risks-adl-cases.md)
- [Референсные проекты](docs/09-reference-projects.md)
