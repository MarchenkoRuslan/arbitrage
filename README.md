# DEX Funding Rate Arbitrage Screener

## Overview

Read-only screener for funding rate arbitrage opportunities between Hyperliquid and Lighter.

Current focus: a fast and reliable read-only screener that:
1. Collects funding and price data from two exchanges
2. Normalizes rates into APR
3. Calculates a directional edge score over the expected hold window (funding + favorable basis - fee impact)
4. Validates entry readiness (ready/watching/blocked)
5. Prints ranked opportunities with status and reasons

## Current Status

- Stage: Phase 2 (API layer delivered)
- Implemented: connectors, normalization, state cache, resilient HTTP, scoring, entry validator, anti-churn, CLI output, REST API, WebSocket feed, runtime status endpoint
- Prepared: WS feed modules for the move to event-driven ingestion
- Not implemented yet: execution engine, risk automation, Telegram notifications, web dashboard

## How It Works

Each poll cycle:
1. Fetches market data from Hyperliquid and Lighter in parallel.
2. Updates shared in-memory MarketState.
3. Scores opportunities with basis + funding economics.
4. Validates opportunities with operational checks.
5. Prints a status-ranked table.

## Scoring Model

The core score is calculated in bps over the expected hold window:

```text
combined_score_bps = funding_edge_bps - roundtrip_fee_bps + basis_bonus_bps

funding_edge_bps = funding_diff_apr * (expected_hold_hours / 8760) * 100
roundtrip_fee_bps = (hl_fee_per_side + lighter_fee_per_side) * 2 * 100
basis_bonus_bps = max(0, directional_basis_bps) * basis_weight
```

Notes:
- Directional basis is positive only when the short leg is richer than the long leg.
- For basis denominator, index price is used when both legs have it; otherwise mark-price midpoint is used.
- Negative basis must be covered by funding within the hold window.

## Entry Validation

After scoring, each opportunity is assigned a status:
- READY: all checks passed
- WATCHING: candidate exists, but not stable enough yet
- BLOCKED: currently not tradable under configured constraints

Checks include:
- Persistence gate (`ARB_MIN_PERSISTENCE_HOURS`)
- Break-even viability vs hold window
- Funding direction flip detection
- Data freshness
- Anti-churn cooldown (suppresses repeated signals without meaningful score improvement)

## Current Structure

```
arbitrage/
├── docs/
├── src/
│   ├── api/
│   │   ├── routes.py       # REST endpoints
│   │   ├── schemas.py      # Response models (OpenAPI)
│   │   ├── server.py       # FastAPI app factory + lifespan
│   │   └── ws.py           # WebSocket connection manager
│   ├── core/
│   │   ├── app.py          # Application orchestrator
│   │   ├── config.py       # Environment-based configuration
│   │   ├── http.py         # HTTP client with retry/backoff
│   │   ├── models.py       # Pydantic models
│   │   ├── normalize.py    # APR/symbol normalization
│   │   └── state.py        # In-memory market state cache
│   ├── exchanges/
│   │   ├── hyperliquid.py
│   │   ├── lighter.py
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

## API Server

Start the REST API with Swagger UI and WebSocket feed:

```bash
python -m src.main --serve
```

- Swagger UI: http://127.0.0.1:8000/docs
- `GET /opportunities` — current ranked opportunity list
- `GET /config` — active screener settings (read-only)
- `GET /status` — runtime health and polling metrics
- `WS /ws/opportunities` — receives a JSON frame after each poll cycle

The polling loop runs in the background inside the same process.
Configure host/port with `ARB_API_HOST` and `ARB_API_PORT`.

## Typical Run Setup

For a stricter signal set, start with:

```bash
# Example values
ARB_MIN_SCORE_BPS=8
ARB_MIN_VOLUME_24H=250000
ARB_MIN_OPEN_INTEREST=500000
ARB_MIN_PERSISTENCE_HOURS=2
ARB_ANTI_CHURN_COOLDOWN_S=14400
ARB_ANTI_CHURN_SCORE_MULTIPLIER=1.5
```

## Operator Runbook

Use one of these baseline profiles depending on how selective you want signals to be.

### Conservative

Best when you want fewer but higher-quality opportunities.

```bash
ARB_MIN_SCORE_BPS=12
ARB_MIN_VOLUME_24H=1000000
ARB_MIN_OPEN_INTEREST=1000000
ARB_MIN_PERSISTENCE_HOURS=4
ARB_EXPECTED_HOLD_HOURS=72
ARB_BASIS_WEIGHT=0.4
ARB_STALE_DATA_S=20
ARB_ANTI_CHURN_COOLDOWN_S=21600
ARB_ANTI_CHURN_SCORE_MULTIPLIER=1.7
```

### Balanced

Default profile for regular monitoring with moderate selectivity.

```bash
ARB_MIN_SCORE_BPS=8
ARB_MIN_VOLUME_24H=250000
ARB_MIN_OPEN_INTEREST=500000
ARB_MIN_PERSISTENCE_HOURS=2
ARB_EXPECTED_HOLD_HOURS=72
ARB_BASIS_WEIGHT=0.5
ARB_STALE_DATA_S=30
ARB_ANTI_CHURN_COOLDOWN_S=14400
ARB_ANTI_CHURN_SCORE_MULTIPLIER=1.5
```

### Aggressive

High-frequency signal discovery; more noise, faster reaction.

```bash
ARB_MIN_SCORE_BPS=5
ARB_MIN_VOLUME_24H=100000
ARB_MIN_OPEN_INTEREST=0
ARB_MIN_PERSISTENCE_HOURS=0
ARB_EXPECTED_HOLD_HOURS=48
ARB_BASIS_WEIGHT=0.6
ARB_STALE_DATA_S=45
ARB_ANTI_CHURN_COOLDOWN_S=7200
ARB_ANTI_CHURN_SCORE_MULTIPLIER=1.3
```

### Operating Workflow

1. Pick one profile and set values in `.env`.
2. Start in loop mode:

```bash
python -m src.main --loop
```

3. Watch status distribution in output:
- Too many `BLOCKED`: lower score threshold or reduce persistence requirement.
- Too many `WATCHING`: reduce persistence requirement or anti-churn multiplier.
- Too many `READY`: increase score threshold and/or volume/OI filters.
4. Re-tune one variable at a time and re-run for at least 30-60 minutes before the next adjustment.

## Main Environment Variables

- `ARB_MIN_SCORE_BPS` (default: `5.0`)
- `ARB_MIN_VOLUME_24H` (default: `100000.0`)
- `ARB_MIN_OPEN_INTEREST` (default: `0.0`)
- `ARB_MIN_PERSISTENCE_HOURS` (default: `0.0`)
- `ARB_ANTI_CHURN_COOLDOWN_S` (default: `14400.0`)
- `ARB_ANTI_CHURN_SCORE_MULTIPLIER` (default: `1.5`)
- `ARB_HL_FEE_PER_SIDE` (default: `0.035`)
- `ARB_LIGHTER_FEE_PER_SIDE` (default: `0.0`)
- `ARB_EXPECTED_HOLD_HOURS` (default: `72.0`)
- `ARB_BASIS_WEIGHT` (default: `0.5`)
- `ARB_STALE_DATA_S` (default: `35.0`)
- `ARB_LOOP_INTERVAL_S` (default: `30`)
- `ARB_API_HOST` (default: `127.0.0.1`)
- `ARB_API_PORT` (default: `8000`)

## Limitations

- Read-only: no order placement and no position management.
- No account-level risk checks (margin, leverage, liquidation distance).
- In-memory anti-churn and persistence history reset on restart.

## Documentation

- [Domain Knowledge](docs/01-domain-knowledge.md)
- [System Architecture](docs/02-system-architecture.md)
- [Technical Stack](docs/03-technical-stack.md)
- [Development Roadmap](docs/04-development-roadmap.md)
- [Exchanges and APIs](docs/05-exchanges-api.md)
- [Hyperliquid API Reference](docs/api/hyperliquid.md)
- [Lighter API Reference](docs/api/lighter.md)
- [References and Sources](docs/06-references.md)
- [Basis + Funding Strategy](docs/07-strategy-basis-funding.md)
- [Risks: ADL and Cases](docs/08-risks-adl-cases.md)
- [Reference Projects](docs/09-reference-projects.md)
- [Documentation Maintenance Guide](docs/10-documentation-maintenance.md)
- [Release Notes Template](docs/11-release-notes-template.md)
