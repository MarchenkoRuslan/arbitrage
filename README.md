# Funding Rate Arbitrage System

## Overview

System for finding funding rate arbitrage opportunities between Hyperliquid and Aster.

Current focus: a fast and reliable read-only screener that:
1. Collects funding and price data from two exchanges
2. Normalizes rates into APR
3. Calculates a combined score (funding edge + basis - fee impact)
4. Prints top opportunities

## Current Status

- Stage: Phase 1 (working screener MVP)
- Implemented: connectors, normalization, state cache, resilient HTTP, scoring, CLI output
- Prepared: WS feed modules for the move to event-driven ingestion
- Not implemented yet: execution engine, risk automation, alerts/API/dashboard

## Current Structure

```
arbitrage/
├── docs/
├── src/
│   ├── core/
│   │   ├── app.py          # Application orchestrator
│   │   ├── config.py       # Environment-based configuration
│   │   ├── http.py         # HTTP client with retry/backoff
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
│   │   └── console.py      # Tabular console output
│   ├── screener/
│   │   └── finder.py       # Opportunity discovery and ranking
│   └── main.py             # CLI entrypoint
├── pyproject.toml
└── README.md
```

## Quick Start

```bash
python -m pip install -e ".[dev]"
python -m src.main
python -m src.main --loop
```

## Main Environment Variables

- `ARB_MIN_SCORE_APR` (default: `5.0`)
- `ARB_FEE_PER_SIDE` (default: `0.05`)
- `ARB_EXPECTED_HOLD_HOURS` (default: `72.0`)
- `ARB_BASIS_WEIGHT` (default: `0.1`)
- `ARB_LOOP_INTERVAL_S` (default: `10`)

## Documentation

- [Domain Knowledge](docs/01-domain-knowledge.md)
- [System Architecture](docs/02-system-architecture.md)
- [Technical Stack](docs/03-technical-stack.md)
- [Development Roadmap](docs/04-development-roadmap.md)
- [Exchanges and APIs](docs/05-exchanges-api.md)
- [References and Sources](docs/06-references.md)
- [Basis + Funding Strategy](docs/07-strategy-basis-funding.md)
- [Risks: ADL and Cases](docs/08-risks-adl-cases.md)
- [Reference Projects](docs/09-reference-projects.md)
