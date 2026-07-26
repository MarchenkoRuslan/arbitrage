# Funding Rate Arbitrage System

## Обзор

Автоматизированная система арбитража ставок финансирования (funding rate) на криптовалютных perpetual futures биржах. Система состоит из двух основных компонентов:

1. **Screener** — мониторинг и поиск арбитражных возможностей по ставкам фандинга между биржами
2. **Trading Engine** — одновременное открытие хеджированных позиций на нескольких биржах

## Стратегии

- **Futures + Futures** — противоположные позиции на разных биржах, заработок на разнице funding rate
- **Spot + Futures** — покупка на споте + шорт на фьючерсах при положительном фандинге
- **Basis + Funding Combined** — заработок на сближении цен + фандинг как двойной источник профита
- **Funding Insurance** — фандинг покрывает негативный базис (страховка)

## Стек технологий

- **Язык:** Python 3.12+
- **Async:** asyncio + aiohttp
- **Биржевые API:** ccxt (unified) + native adapters
- **Data:** pandas, numpy
- **Storage:** PostgreSQL + Redis
- **UI:** FastAPI + WebSocket dashboard

## Структура проекта

```
arbitrage/
├── docs/                    # Документация и спецификации
├── src/
│   ├── core/               # Базовые типы, конфигурация, утилиты
│   ├── exchanges/          # Адаптеры бирж (unified interface)
│   ├── screener/           # Модуль скрининга возможностей
│   ├── strategy/           # Логика стратегий и economics
│   ├── execution/          # Исполнение ордеров, хеджирование
│   ├── risk/               # Риск-менеджмент и лимиты
│   ├── data/               # Сбор и хранение данных
│   └── api/                # REST/WS API для dashboard
├── tests/
├── config/
└── scripts/
```

## Быстрый старт

```bash
# TODO: будет добавлено по мере разработки
```

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
