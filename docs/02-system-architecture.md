# System Architecture

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     ARBITRAGE SYSTEM                         │
│                                                             │
│  ┌──────────────┐                  ┌──────────────────────┐  │
│  │ Hyperliquid  │                  │       Lighter        │  │
│  └──────┬───────┘                  └─────────┬────────────┘  │
│         └──────────────┬─────────────────────┘               │
│                        │                                      │
│              ┌─────────▼──────────┐                           │
│              │ Ingestion Layer    │ ← REST polling (WS planned) │
│              └─────────┬──────────┘                           │
│                        │                                      │
│              ┌─────────▼──────────┐                           │
│              │ MarketState Cache  │ ← In-memory shared state │
│              └─────────┬──────────┘                           │
│                        │                                      │
│              ┌─────────▼──────────┐                           │
│              │ Screener           │ ← scoring + ranking      │
│              └─────────┬──────────┘                           │
│                        │                                      │
│              ┌─────────▼──────────┐                           │
│              │ Output/Alerts      │ ← CLI + REST API + WS    │
│              └────────────────────┘                           │
│                                                             │
│              ┌────────────────────┐                           │
│              │ FastAPI Server     │ ← /opportunities, /config │
│              │  + WS broadcast    │   /status, /ws/opportunities │
│              └────────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Modules

### 1. Exchange Connectors

Unified interface for venues (native adapters + protocol).

```python
class ExchangeConnector(Protocol):
  async def get_funding_rates(self) -> dict[str, FundingRate]
  async def get_tickers(self) -> dict[str, Ticker]
  async def get_market_data(self) -> tuple[dict[str, FundingRate], dict[str, Ticker]]
  async def start_stream(self, state: MarketState) -> None
  async def close(self) -> None
```

### 2. Screener

Collect funding rates from all exchanges -> find pairs with the largest spread -> rank them.

```python
@dataclass
class ArbitrageOpportunity:
    symbol: str
    long_exchange: str
    short_exchange: str
    funding_diff_apr: float     # Funding rate spread (APR)
    basis_bps: float            # Directional basis, positive when short is richer
    combined_score: float       # Expected net edge over hold window, in bps
    basis_trend: float | None   # Basis slope in bps/sample (positive = widening)
    liquidity_tier: str | None  # H/M/L relative to volume gate
```

**Logic:**
1. Ingestion updates `MarketState` (REST polling now, WS-first later)
2. For each shared symbol, determine the long/short direction by APR
3. Calculate directional basis, expected funding edge, and combined score
4. Filter by minimum score and liquidity/open-interest guards
5. Pass candidates through entry validator (ready/watching/blocked)
6. Rank output by status then `combined_score`

### 3. App Orchestrator

- Manages lifecycle: startup, polling loop, graceful shutdown
- Updates `MarketState`
- Runs the screener and output layer

### 4. Trader (Execution, planned)

Simultaneous position open/close flow.

**Principles:**
- Entry sequencing: hedge leg first, exposed leg second
- Maker-first: limit order → wait → fallback to taker
- Size positions in COINS (not USDT)
- Roll back if one leg fails
- Reconcile state after restart

### 5. Risk/Monitor (planned)

- Margin ratio monitoring
- ADL detection
- Funding rate change alerts
- Spread expansion alerts
- Auto-close on critical events
- Telegram notifications

---

## Data Flows

```
Current runtime (polling):
  Exchanges → Connectors → MarketState → Screener → CLI + REST API + WS

Target runtime (WS-first):
  WS Feeds + REST Snapshot/Recovery → MarketState → Screener → Alerts/API

Position opening:
  Signal → Risk Check → Size Calc → Parallel Orders → Position Record

Monitoring (continuous):
  Exchanges → Prices/Margin/Funding → Monitor → Alerts/Auto-actions

Position closing:
  Signal → Parallel Close → PnL Calc → Record
```

---

## Operating Modes

1. **Screener-only** - shows opportunities but does not trade
2. **Manual** — planned
3. **Semi-auto** — planned
4. **Full-auto** — planned

## Validation

- Install dependencies with `python -m pip install -e ".[dev]"`.
- Run the app with `python -m src.main`, `python -m src.main --loop`, or `python -m src.main --serve`.
- Use `pytest` for tests and `ruff check .` for linting when a task touches Python code.

## Documentation

- Keep README and docs aligned with the current implementation status.
- Prefer short, concrete explanations over roadmap-style prose.
