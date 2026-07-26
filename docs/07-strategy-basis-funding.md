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
score_bps = funding_edge_bps - roundtrip_fees_bps + basis_bonus_bps

basis_bonus_bps   = max(0, directional_basis_bps) * 0.5
funding_edge_bps  = funding_diff_apr * (expected_hold_hours / 8760) * 100
roundtrip_fees_bps = (hl_fee_per_side + lighter_fee_per_side) * 2 * 100
                   = (0.035 + 0.0) * 2 * 100 = 7 bps
```

Lighter charges zero trading fees — the full roundtrip cost is 7 bps (HL taker only).
Directional basis is positive only when the short leg is richer than the long leg.

If basis is negative, check whether funding can cover it within the hold window:
```python
hours_to_cover = abs(negative_basis_bps) / hourly_funding_bps
if hours_to_cover > expected_hold_hours: SKIP
```

## Example (Hyperliquid + Lighter)

### AERO — ideal case (2026-07-26)
```
Long  Lighter    @ basis side
Short Hyperliquid @ basis side
Diff APR: 177.75%
Funding edge (72h hold): 146.09 bps
Basis bonus: +8.71 bps * 0.5 = +4.36 bps
Fees: 7 bps
Score: 143.45 bps
Breakeven: 3.5h
```

### XMR — funding insurance
```
Long  Lighter    @ basis side
Short Hyperliquid @ basis side
Diff APR: 122.96%
Basis: -5.25 bps (against us)
Hourly funding: ~1.40 bps → breakeven in 3.75h — well within 72h hold
Score: 94.06 bps
```

## Exit Signals

| Signal | Action |
|--------|----------|
| Funding changed sign | Close |
| Margin ratio < 10% | Close immediately |
| Basis converged (< 5 bps) | Take profit |
| Spread expanded > 3x | Close at a loss |
| Combined score < 0 | Planned exit |
