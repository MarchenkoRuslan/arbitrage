# Strategy: Basis + Funding Combined

## Concept

Dual profit source: price basis (spread convergence) + funding rate.

```
Total_Profit = Basis_Convergence + Funding_Income - Fees
```

## Three Scenarios

| Scenario | Basis | Funding | Action |
|----------|-------|---------|----------|
| Ideal | + (short is richer) | + (short receives funding) | Double profit |
| Funding Insurance | - (against us) | High + | Funding covers the basis loss |
| Basis Play | Large + | Small | Profit from convergence |

## Combined Score

```python
score = funding_24h - roundtrip_fees + basis_bonus

basis_bonus = max(0, basis_bps) * 0.5  # 50% realization assumption
```

If basis is negative, check how many funding hours are needed to cover it:
```python
hours_to_cover = abs(negative_basis_bps) / hourly_funding_bps
if hours_to_cover > max_holding_hours: SKIP
```

## Real Examples

### UMA - ideal case
```
Long Hyperliquid @ $0.3901, Short Aster @ $0.3932
Basis: +80.5 bps, APR: 67%, Fees: ~21 bps
Day 1: basis convergence +59.5 bps + funding 18.4 bps = +78 bps
```

### CASHCAT - funding insurance
```
Basis: -54.9 bps (against us), APR: 145%
Funding: 39.7 bps/day -> breakeven in 1.4 days
Day 3: +119.1 - 54.9 - 21 = +43.2 bps
```

## Exit Signals

| Signal | Action |
|--------|----------|
| Funding changed sign | Close |
| Margin ratio < 10% | Close immediately |
| Basis converged (< 5 bps) | Take profit |
| Spread expanded > 3x | Close at a loss |
| Combined score < 0 | Planned exit |
