# Референсы и источники

## Скринеры (конкуренты)

| Сервис | URL | Особенности |
|--------|-----|-------------|
| ArbitrageScanner | arbitragescanner.io/funding-rates | Платный, обучение |
| VOOI Ultra | ultra.vooi.io | DEX агрегатор + арбитраж |
| Coinglass | coinglass.com/ArbitrageList | Бесплатный |
| FundingView | fundingview.app/strategy | Стратегии |
| Loris Tools | loris.tools | Funding + OI |

## Open-source проекты (изученные)

| Проект | Фокус | Ключевая идея |
|--------|-------|---------------|
| ALLmightyn/FundingArbitrageBot | HL↔Lighter | Entry sequencing, persistence gate, anti-churn |
| rhwhdgks/funding-arb-engine | Binance↔OKX | Maker first-leg, recovery paths, ops console |
| velo-coder/crypto-trading-bot | 12 exchanges | Full-stack FastAPI + Next.js, ccxt |
| pa111111/funding-scout-oss | DEX screener | EV calculator, Kaplan-Meier survival |

## Паттерны из проектов (берём)

1. **Entry sequencing** — hedge first, exposed second
2. **Maker-first** — limit → wait → taker fallback (экономия 0.02-0.04% на ногу)
3. **Persistence gate** — не входить если rate держится < 6h
4. **Round-trip cost model** — точный расчёт min_profitable_hours
5. **Reconciliation** — сверка с биржей при restart
6. **Combined score** — basis + funding - fees
7. **Anti-churn** — не flipping'ать позицию каждые 2 часа

## Типичные параметры хорошей opportunity

| Параметр | Minimum | Good | Excellent |
|----------|---------|------|-----------|
| Funding diff (APR) | > 10% | > 30% | > 100% |
| Volume 24h | > $1M | > $5M | > $20M |
| Open Interest | > $500K | > $2M | > $10M |
| Spread (стакан) | < 0.5% | < 0.2% | < 0.1% |
| Persistence | > 6h | > 24h | > 72h |
