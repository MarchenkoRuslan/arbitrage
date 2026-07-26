# Agent Instructions

## Scope

This repository is a Python 3.12+ funding rate arbitrage screener for two pure DEX venues: **Hyperliquid** and **Lighter**.

The current implementation is a read-only screener. Trading, risk automation, and alerting are planned but not part of the active runtime yet.

## Project Map

- `src/core/` contains application orchestration, config, HTTP utilities, shared models, normalization, and state.
- `src/exchanges/` contains venue-specific connectors (`hyperliquid.py`, `lighter.py`) and shared schemas (`schemas.py`).
- `src/screener/` contains opportunity selection and ranking logic.
- `src/output/` contains console rendering.
- `docs/` contains architecture, strategy, risk, API, and roadmap notes.

## Working Rules

- Keep all new documentation, comments, commit messages, and user-facing text in English.
- Prefer minimal, targeted changes over broad refactors.
- Preserve the current architecture: exchange connectors -> shared market state -> screener -> console output.
- Use Decimal for prices and order quantities. Use float for rates and scoring (rates are inherently imprecise estimates from approximated formulas).
- Do not add execution-engine or risk-automation behavior unless the task explicitly asks for it.
- Keep the screener path read-only unless the task explicitly involves order placement or account actions.
- Reuse the existing connector and normalization patterns instead of introducing exchange-specific shortcuts in unrelated layers.
- Keep environment-driven configuration in `src/core/config.py` rather than scattering constants across modules.
- No VOOI dependency: both exchanges are accessed via their own public REST APIs, no authentication required.

## Implementation Expectations

- When changing exchange behavior, prefer updating the owning connector in `src/exchanges/`.
- When changing ranking or thresholds, prefer updating the screener logic in `src/screener/` and related config in `src/core/config.py`.
- Keep `src/core/app.py` as the orchestration boundary, not a dumping ground for venue-specific logic.
- Maintain the current project style: straightforward asyncio, small modules, and explicit data flow.
- Avoid speculative abstractions unless at least two concrete call sites need them.
- Lighter funding rate is approximated from `(mark_price - index_price) / index_price / 8` — do not change this without updating the relevant doc and tests.

## Validation

- Install dependencies with `python -m pip install -e ".[dev]"`.
- Run the app with `python -m src.main` or `python -m src.main --loop`.
- Use `pytest` for tests and `ruff check .` for linting when a task touches Python code.
- Prefer the narrowest validation that covers the changed slice before widening scope.

## Documentation

- Keep README and docs aligned with the current implementation status.
- Prefer short, concrete explanations over roadmap-style prose.
- If a task changes behavior, update the relevant doc page only when the behavior is user-visible or architectural.
