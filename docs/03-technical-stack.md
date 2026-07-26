# Технический стек

## Core

| Компонент | Выбор | Зачем |
|-----------|-------|-------|
| Язык | Python 3.12+ | Экосистема, быстрая разработка |
| Async | asyncio | Параллельные WS соединения |
| Биржи | hyperliquid-python-sdk + aster-connector-python | Native SDKs |
| Signing | eth-account | EIP-712 для обоих venues |
| Types | Pydantic | Валидация, schemas |
| Numbers | Decimal | Точная арифметика цен |

## Инфраструктура

| Компонент | Выбор | Зачем |
|-----------|-------|-------|
| DB | PostgreSQL | История, позиции |
| Cache | Redis | Real-time данные, pub/sub |
| API | FastAPI | REST + WebSocket |
| Notifications | Telegram Bot | Alerts |
| Deploy | Docker | Простой деплой |
| Logs | Loguru | Структурированное логирование |

## Почему Python, а не C++

- Funding arb — **не HFT**. Funding выплаты каждые 1-8 часов.
- Задержка в 1-2 секунды при открытии некритична
- ccxt — самая зрелая unified crypto библиотека
- Один человек может написать и поддерживать всю систему

## Структура кода

```
src/
├── core/
│   ├── config.py          # Конфигурация (env + yaml)
│   ├── models.py          # Pydantic models
│   └── utils.py           # Helpers
├── exchanges/
│   ├── base.py            # Abstract connector
│   ├── binance.py
│   ├── bybit.py
│   ├── okx.py
│   └── hyperliquid.py
├── screener/
│   ├── aggregator.py      # Сбор данных
│   ├── finder.py          # Поиск opportunities
│   └── filters.py         # Фильтрация
├── trader/
│   ├── executor.py        # Открытие/закрытие позиций
│   ├── position_mgr.py    # Управление позициями
│   └── risk.py            # Risk checks
├── notifications/
│   └── telegram.py
└── main.py
```

## Комиссии по биржам

| Биржа | Maker | Taker | Roundtrip |
|-------|-------|-------|-----------|
| Binance | 0.02% | 0.04% | 0.16% |
| Bybit | 0.02% | 0.055% | 0.15% |
| OKX | 0.02% | 0.05% | 0.14% |
| Hyperliquid | 0.01% | 0.035% | 0.09% |
| Bitget | 0.02% | 0.06% | 0.16% |

## Rate Limits

| Биржа | REST | WS | Стратегия |
|-------|------|-----|-----------|
| Binance | 1200 req/min | 200 streams | Batch + WS |
| Bybit | 120 req/min | 500 subs | WS primary |
| OKX | 20 req/2sec | 240 conn | Throttle |
| Hyperliquid | No doc limit | Generous | Monitor 429s |
