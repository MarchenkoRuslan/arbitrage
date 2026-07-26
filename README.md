# DEX Funding Rate Arbitrage Screener

[![CI](https://github.com/MarchenkoRuslan/arbitrage/actions/workflows/ci.yml/badge.svg)](https://github.com/MarchenkoRuslan/arbitrage/actions/workflows/ci.yml)

## Overview

Read-only screener that finds funding rate arbitrage opportunities between two pure DEX venues:
**Hyperliquid** and **Lighter**.

No API keys. No registration. Connects directly to both exchanges' public REST APIs.

What it does each poll cycle:
1. Fetches funding rates + tickers from Hyperliquid (`POST /info`)
2. Fetches funding rates + tickers from Lighter (`GET /api/v1/orderBookDetails`)
3. Finds common symbols, computes directional edge (funding spread − fees + basis bonus)
4. Prints ranked opportunities to stdout

## Quick Start

```bash
python -m pip install -e ".[dev]"

# Single snapshot
python -m src.main

# Continuous loop (every 30s by default)
python -m src.main --loop
```

## Current Structure

```
arbitrage/
├── docs/                     # Architecture, strategy, API references
├── src/
│   ├── core/
│   │   ├── app.py            # Orchestrator: parallel fetch → state → screener
│   │   ├── config.py         # Environment-based settings (ARB_ prefix)
│   │   ├── http.py           # Resilient HTTP client (retry + backoff)
│   │   ├── models.py         # FundingRate, Ticker, ArbitrageOpportunity
│   │   ├── normalize.py      # APR conversion, symbol normalization
│   │   └── state.py          # In-memory MarketState cache
│   ├── exchanges/
│   │   ├── hyperliquid.py    # Hyperliquid REST connector
│   │   ├── lighter.py        # Lighter REST connector
│   │   └── schemas.py        # Raw API response schemas (Pydantic)
│   ├── output/
│   │   └── console.py        # Tabular stdout output
│   ├── screener/
│   │   └── finder.py         # Scoring: funding edge − fees + basis bonus
│   └── main.py
├── tests/
├── .env                      # Local overrides (not committed)
└── pyproject.toml
```

## Environment Variables

All variables use the `ARB_` prefix. Defaults work out of the box — copy `.env` and adjust as needed.

| Variable | Default | Description |
|---|---|---|
| `ARB_MIN_SCORE_BPS` | `5.0` | Minimum combined score to show |
| `ARB_MIN_VOLUME_24H` | `100000.0` | Min 24h volume on both legs (USD) |
| `ARB_HL_FEE_PER_SIDE` | `0.035` | Hyperliquid taker fee % |
| `ARB_LIGHTER_FEE_PER_SIDE` | `0.0` | Lighter fee % (zero-fee DEX) |
| `ARB_EXPECTED_HOLD_HOURS` | `72.0` | Funding accumulation window |
| `ARB_BASIS_WEIGHT` | `0.5` | Fraction of positive basis counted in score |
| `ARB_STALE_DATA_S` | `30.0` | Max data age before symbol is skipped |
| `ARB_LOOP_INTERVAL_S` | `30` | Poll interval in seconds |
| `ARB_HL_BASE_URL` | `https://api.hyperliquid.xyz` | |
| `ARB_LIGHTER_BASE_URL` | `https://mainnet.zklighter.elliot.ai` | |

## Scoring Formula

```
combined_score_bps = funding_edge_bps - roundtrip_fee_bps + basis_bonus_bps

funding_edge_bps  = funding_diff_apr × (hold_hours / 8760) × 100
roundtrip_fee_bps = (hl_fee_per_side + lighter_fee_per_side) × 2 × 100 = 7 bps
basis_bonus_bps   = max(0, directional_basis_bps) × basis_weight
```

Lighter charges zero trading fees, so the full roundtrip cost is **7 bps** (HL only).

## Output Sample

```
Symbol     Long         Short         Diff APR%   Fund bps  Basis bps Fees bps  Score bps    BE h
----------------------------------------------------------------------------------------------------
AERO       lighter      hyperliquid      177.75     146.09       8.71     7.00     143.45      3.5
KAITO      lighter      hyperliquid      172.71     141.95       9.95     7.00     139.92      3.5
JUP        lighter      hyperliquid      163.08     134.04       6.95     7.00     130.52      3.8

Total opportunities: 31
```

## Status

- **Working**: read-only screener, 200+ markets per exchange, parallel REST polling
- **Not implemented**: execution engine, risk automation, alerts, web dashboard

## Documentation

- [Domain Knowledge](docs/01-domain-knowledge.md)
- [System Architecture](docs/02-system-architecture.md)
- [Technical Stack](docs/03-technical-stack.md)
- [Development Roadmap](docs/04-development-roadmap.md)
- [Exchanges and APIs](docs/05-exchanges-api.md)
- [Basis + Funding Strategy](docs/07-strategy-basis-funding.md)
- [Risks: ADL and Cases](docs/08-risks-adl-cases.md)

