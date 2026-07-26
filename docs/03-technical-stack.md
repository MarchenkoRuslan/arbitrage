# Technical Stack

## Core

| Component | Choice | Why |
|-----------|-------|-------|
| Language | Python 3.12+ | Ecosystem and fast development |
| Async | asyncio | Parallel IO workloads |
| HTTP | httpx | Async REST requests |
| Types | Pydantic | Validation and schemas |
| Settings | pydantic-settings | Env-based configuration |
| Logging | loguru | Structured logging |
| Numbers | Decimal | Precise arithmetic for prices and rates |

## Infrastructure

| Component | Choice | Why |
|-----------|-------|-------|
| Runtime | In-memory state | Minimal hot-path latency |
| Resilience | Retry/backoff HTTP client | Stability during network failures |
| Package | pyproject + editable install | Simple development workflow |
| Tests | pytest + pytest-asyncio | Validation for async logic |

## Code Structure

```
src/
├── core/
│   ├── app.py             # Application orchestrator
│   ├── config.py          # Environment configuration (ARB_ prefix)
│   ├── http.py            # Retry/backoff HTTP client
│   ├── models.py          # FundingRate, Ticker, ArbitrageOpportunity
│   ├── normalize.py       # APR conversion, symbol normalization
│   └── state.py           # MarketState in-memory cache
├── exchanges/
│   ├── hyperliquid.py     # Hyperliquid REST connector
│   ├── lighter.py         # Lighter REST connector
│   └── schemas.py         # Pydantic schemas for raw API responses
├── output/
│   └── console.py         # Tabular stdout output
├── screener/
│   └── finder.py          # Opportunity search and scoring
└── main.py
```

## Dependencies

```toml
[dependencies]
httpx          # async HTTP with retry
pydantic       # data validation
pydantic-settings  # env-driven config
loguru         # structured logging

[dev]
pytest
pytest-asyncio
ruff
```

No WebSocket runtime dependency is used at this stage — both exchanges are polled via REST.
WebSocket ingestion is planned in roadmap phases.

Dev:

- `pytest`
- `pytest-asyncio`
- `ruff`
