# Domain Knowledge: Funding Rate Arbitrage

## 1. What Is a Funding Rate

**Funding Rate** is a periodic payment between holders of long and short positions on perpetual futures contracts. The mechanism keeps the futures price anchored to the spot price.

### Payment Mechanics
- **Positive funding** -> longs pay shorts
- **Negative funding** -> shorts pay longs
- **Payment interval:** every 1h / 4h / 8h depending on the exchange
- **Payment formula:** `Payment = Position_Size * Funding_Rate`

### Why Differences Appear Across Exchanges
- Different trader mix (retail vs institutional)
- Different liquidity and open interest
- Different funding rate formulas
- Different settlement timing (not synchronized)
- New listings attract speculative flow

---

## 2. Funding Arbitrage Strategies

### 2.1 Futures + Futures (Primary)

Open opposite positions on two exchanges for the same asset.

```
Example:
- Exchange A: FARTCOIN/USDT Short (funding +0.01%/1h -> we receive)
- Exchange B: FARTCOIN/USDT Long  (funding -0.001%/4h -> we receive)

Result: positions are price-hedged, and we earn funding on both sides
```

**Entry condition:** funding rate difference between exchanges is greater than total fees (entry + exit)

**Key principle:** positions are opened **with equal coin quantity**, not equal dollar notional.

### 2.2 Spot + Futures

Buy the asset on spot and open a short on futures when funding is positive.

```
Example:
- Exchange A (spot): Buy 1 ETH @ $3000
- Exchange B (futures): Short 1 ETH @ $3010 (funding +0.03%/8h)

Result:
- Spot funding = 0
- Futures leg receives funding every 8 hours
- Price exposure is hedged
```

**Pros:** no liquidation risk on the spot leg
**Cons:** capital is locked on spot without leverage

### 2.3 Basis + Funding Combined

Earn from price convergence between exchanges while also receiving funding.

```
Example (UMA):
- Hyperliquid: Long @ $0.3901
- Aster: Short @ $0.3932
- Basis: +80.5 bps (short exchange is richer, which helps us)
- Funding APR: 67%
- Fees: ~21 bps

Profit: basis convergence (+59.5 bps) + funding (18.4 bps/day)
```

**Synergy:** around funding settlement, prices often compress toward spot, which can accelerate basis convergence.

---

## 3. Trade Economics

### 3.1 Combined Score (Ranking Formula)

```
combined_score = funding_24h - roundtrip_fees + basis_bonus

Where:
- funding_24h = funding_rate_diff * periods_per_day in bps
- roundtrip_fees = (taker_fee_A + taker_fee_B) * 2  (entry + exit)
- basis_bonus = max(0, basis_bps) * 0.5  (50% realization assumption)
```

### 3.2 Minimum Entry Threshold

```
Min_Funding_Income > Total_Fees

Typical taker fees: 0.04% - 0.075%
Roundtrip (entry + exit on both exchanges): 0.16% - 0.30%

min_profitable_hours = roundtrip_cost / hourly_funding_income
```

### 3.3 Annualized Return (APR)

```
APR = funding_rate_diff * periods_per_year * 100%

Example: 0.01% for 8h -> 0.01% * 1095 = 10.95% APR
With 5x leverage: about 54.75% APR before fees
```

---

## 4. Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| ADL | The exchange closes a profitable position -> hedge breaks | Monitor ADL indicator, use isolated margin |
| Liquidation | Sharp price move -> one leg is liquidated | Low leverage (3-5x), margin alerts |
| Funding flip | The rate changes sign -> you pay instead of receive | Monitor predicted rate, auto-close |
| Price deviation | Prices diverge by more than 1% across exchanges | Rebalancing, margin buffer |
| Slippage | Low liquidity -> expensive entry/exit | Check order book depth |
| Exchange risk | Trading freeze, delisting | Diversify across exchanges |

### ANSEM Case (Real)
- Spot on MEXC + Short on Aster, funding about 5% over 10 days (182% APR)
- Overnight ANSEM drops 30-40% -> short closed by ADL @ $0.22
- Lucky outcome: spot sold @ $0.27 -> +$4k
- Alternative outcome: if spot had dropped below $0.22 -> loss

---

## 5. Key Screener Metrics

| Metric | Description |
|--------|-------------|
| Funding Rate | Current rate on each exchange |
| Funding Diff | Difference between exchanges |
| APR | Annualized return |
| Basis (bps) | Price difference between exchanges |
| Combined Score | funding + basis - fees |
| Volume 24h | Trading volume |
| Open Interest | Open positions |
| Persistence | How many hours the rate holds |
| Min Profitable Hours | Minimum time required to reach profitability |

---

## 6. Funding Intervals by Exchange

| Exchange | Period | Notes |
|----------|--------|-------|
| Binance | 8h | Standard |
| Bybit | 8h | Standard |
| OKX | 8h | Standard |
| Hyperliquid | 1h | Frequent settlements |
| dYdX | 1h | Frequent settlements |
| Bitget | 8h | Standard |
| Gate.io | 8h | Standard |
| Aster | 8h | Heavy memecoin coverage |

---

## 7. Terminology

- **Perpetual Futures (Perps)** - perpetual contracts with no expiry
- **Funding Rate** - periodic payment between long and short holders
- **Mark Price** - fair price used for PnL and liquidation calculations
- **Basis** - price difference for the same asset across different exchanges
- **ADL (Auto-Deleveraging)** - forced closure of profitable positions
- **Delta-Neutral** - hedged position with no directional exposure
- **Persistence Gate** - requirement that a rate holds for N hours before entry
- **Roundtrip Cost** - total entry and exit fees across both exchanges
- **Dollar-Seconds** - time-integrated exposure, used as a risk measure
