# Technical Stack

## Core

| Component | Choice | Why |
|-----------|-------|-------|
| Language | Python 3.12+ | Ecosystem and fast development |
| Async | asyncio | Parallel IO workloads |
| HTTP | httpx | Async REST requests |
| WS | websockets | Streaming real-time updates |
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

## Why Start This Lean

- The first requirement is a working and testable screener, not a full trading platform
- The minimal architecture already leaves room for scaling: state cache, DI, protocols, WS modules
- The cold path can perform IO while the hot screener path runs from in-memory data

## Code Structure

```
src/
├── core/
│   ├── app.py             # Application orchestrator
│   ├── config.py          # Environment configuration
│   ├── http.py            # Retry/backoff HTTP client
│   ├── models.py          # Pydantic models
│   ├── normalize.py       # APR and symbol normalization
│   └── state.py           # Shared market state cache
├── exchanges/
│   ├── base.py            # Connector protocol
│   ├── schemas.py         # API response schemas
│   ├── hyperliquid.py     # REST connector
│   ├── hyperliquid_ws.py  # WS feed (prepared)
│   ├── aster.py           # REST connector
│   └── aster_ws.py        # WS feed (prepared)
├── output/
│   └── console.py         # Tabular console output
├── screener/
│   └── finder.py          # Opportunity search and scoring
└── main.py
```

## Current Dependencies

- `httpx`
- `pydantic`
- `pydantic-settings`
- `loguru`
- `websockets`

Dev:

- `pytest`
- `pytest-asyncio`
- `ruff`
