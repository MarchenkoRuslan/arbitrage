# Strategy: Basis + Funding Combined

## Concept

Dual profit source: price basis (spread convergence) + funding rate.

All numerical examples below are illustrative and should be interpreted with the
current configured fee model in `ARB_HL_FEE_PER_SIDE` and `ARB_LIGHTER_FEE_PER_SIDE`.

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
score_bps = funding_edge_bps - roundtrip_fees_bps + basis_bonus_bps + liquidity_bps

basis_bonus_bps = max(0, directional_basis_bps) * basis_weight  # default 0.5
funding_edge_bps = funding_diff_apr * (expected_hold_hours / 8760) * 100
liquidity_bps = log2(min_volume / min_volume_gate) * liquidity_weight  # 0 when weight is 0
```

Directional basis is positive only when the short leg is richer than the long leg.

If basis is negative, check how many funding hours are needed to cover it:
```python
hours_to_cover = abs(negative_basis_bps) / hourly_funding_bps
if hours_to_cover > expected_hold_hours: SKIP
```

## Real Examples

### UMA - ideal case
```
Long Hyperliquid @ $0.3901, Short Lighter @ $0.3932
Basis: +80.5 bps, APR: 67%, Fees: ~7 bps
Day 1: basis convergence +59.5 bps + funding 18.4 bps = +70.9 bps
```

### CASHCAT - funding insurance
```
Basis: -54.9 bps (against us), APR: 145%
Funding: 39.7 bps/day -> breakeven in 1.4 days
Day 3: +119.1 - 54.9 - 7 = +57.2 bps
```

## Exit Signals

| Signal | Action |
|--------|----------|
| Funding changed sign | Close |
| Margin ratio < 10% | Close immediately |
| Basis converged (< 5 bps) | Take profit |
| Spread expanded > 3x | Close at a loss |
| Combined score < 0 | Planned exit |
