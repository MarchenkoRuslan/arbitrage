# Технический стек

## Core

| Компонент | Выбор | Зачем |
|-----------|-------|-------|
| Язык | Python 3.12+ | Экосистема, быстрая разработка |
| Async | asyncio | Параллельные IO задачи |
| HTTP | httpx | Асинхронные REST запросы |
| WS | websockets | Потоковые real-time обновления |
| Types | Pydantic | Валидация, schemas |
| Settings | pydantic-settings | Конфиг из env |
| Logging | loguru | Структурированное логирование |
| Numbers | Decimal | Точная арифметика цен и ставок |

## Инфраструктура

| Компонент | Выбор | Зачем |
|-----------|-------|-------|
| Runtime | In-memory state | Минимальная latency hot path |
| Resilience | Retry/backoff HTTP client | Стабильность при сетевых сбоях |
| Package | pyproject + editable install | Простой dev workflow |
| Tests | pytest + pytest-asyncio | Проверка async логики |

## Почему такой минимум на старте

- Сначала нужен рабочий и проверяемый скринер, а не полный торговый комбайн
- Минимальная архитектура уже учитывает масштабирование: state cache, DI, протоколы, WS модули
- Холодный путь может делать IO, горячий путь скринера работает по данным из памяти

## Структура кода

```
src/
├── core/
│   ├── app.py             # Оркестратор приложения
│   ├── config.py          # Конфигурация (env)
│   ├── http.py            # Retry/backoff HTTP клиент
│   ├── models.py          # Pydantic models
│   ├── normalize.py       # APR и symbol normalization
│   └── state.py           # Shared market state cache
├── exchanges/
│   ├── base.py            # Connector protocol
│   ├── schemas.py         # API response schemas
│   ├── hyperliquid.py     # REST connector
│   ├── hyperliquid_ws.py  # WS feed (prepared)
│   ├── aster.py           # REST connector
│   └── aster_ws.py        # WS feed (prepared)
├── output/
│   └── console.py         # Табличный вывод
├── screener/
│   └── finder.py          # Поиск и scoring opportunities
└── main.py
```

## Текущие зависимости

- `httpx`
- `pydantic`
- `pydantic-settings`
- `loguru`
- `websockets`

Dev:

- `pytest`
- `pytest-asyncio`
- `ruff`
