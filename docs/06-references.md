# References and Sources

## Screeners (Competitors)

| Service | URL | Notes |
|--------|-----|-------------|
| ArbitrageScanner | arbitragescanner.io/funding-rates | Paid, includes educational content |
| VOOI Ultra | ultra.vooi.io | DEX aggregator + arbitrage |
| Coinglass | coinglass.com/ArbitrageList | Free |
| FundingView | fundingview.app/strategy | Strategy-focused |
| Loris Tools | loris.tools | Funding + OI |

## Open-Source Projects Reviewed

| Project | Focus | Key Idea |
|--------|-------|---------------|
| ALLmightyn/FundingArbitrageBot | HL↔Lighter | Entry sequencing, persistence gate, anti-churn |
| rhwhdgks/funding-arb-engine | Binance↔OKX | Maker first-leg, recovery paths, ops console |
| velo-coder/crypto-trading-bot | 12 exchanges | Full-stack FastAPI + Next.js, ccxt |
| pa111111/funding-scout-oss | DEX screener | EV calculator, Kaplan-Meier survival |

## Patterns Worth Adopting

1. **Entry sequencing** — hedge first, exposed second
2. **Maker-first** — limit → wait → taker fallback (saves roughly 0.02-0.04% per leg)
3. **Persistence gate** — do not enter if the rate holds for less than 6h
4. **Round-trip cost model** — accurate calculation of `min_profitable_hours`
5. **Reconciliation** — sync with the exchange after restart
6. **Combined score** — basis + funding - fees
7. **Anti-churn** — avoid flipping a position every 2 hours

## Typical Parameters for a Good Opportunity

| Parameter | Minimum | Good | Excellent |
|----------|---------|------|-----------|
| Funding diff (APR) | > 10% | > 30% | > 100% |
| Volume 24h | > $1M | > $5M | > $20M |
| Open Interest | > $500K | > $2M | > $10M |
| Spread (order book) | < 0.5% | < 0.2% | < 0.1% |
| Persistence | > 6h | > 24h | > 72h |
