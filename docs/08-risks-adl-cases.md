# Risks: ADL and Real Cases

## ADL (Auto-Deleveraging)

The exchange can automatically close a profitable position during a liquidation cascade. That breaks the hedge.

```
BEFORE ADL: Long (spot/perp) + Short (perp) = delta neutral
AFTER ADL:  Long remains, Short is closed = directional risk
```

### ANSEM Case
```
Historical case: Spot on MEXC + Short on Aster
Funding: ~5% over 10 days (182% APR)
Event: Robinhood chain meme season -> ANSEM drops 30-40%
ADL: short closed @ $0.22
Next morning: spot sold @ $0.27 -> +$4k (lucky outcome)
Alternative path: spot could have dropped to $0.15 -> loss
```

### ADL Mitigation
- Monitor the ADL indicator (4-5 lights -> warning)
- Use isolated margin to limit damage
- Do not allocate all capital to one pair
- After an ADL event, immediately decide whether to close the second leg or hold it

## Other Risks

### Funding Flip
```
The rate changes sign sharply -> you switch from receiving funding to paying it.
Protection: monitor the predicted rate and auto-close when the sign flips.
```

### Exchange Price Deviation
```
Normal: 0.1-0.3% divergence
Dangerous: >1% (one leg is deeply underwater)
Critical: >3% (liquidation threat)
Protection: margin buffer >2x, alerts, rebalancing
```

### Memecoins
```
- Pump/dump moves of 30-100% within minutes
- ADL probability is much higher
- Recommendation: cap at 10-20% of portfolio exposure
```

## Risk Limits

```yaml
# Per-position
max_position_pct: 20%       # No more than 20% in one pair
max_leverage: 5
margin_alert: 15%
margin_force_close: 8%

# Portfolio
max_positions: 10
max_meme_pct: 20%
max_single_exchange_pct: 40%
max_daily_loss_pct: 5%

# Entry guards
min_volume_24h: $1M
min_open_interest: $500K
min_persistence: 6h
max_adl_quantile: 3
```

## Recovery

### After ADL
1. Detect: the position was closed by the exchange, not by us.
2. Alert: send a critical Telegram notification.
3. Decide: close the second leg safely or manage it with a trailing stop.

### One-Leg Failure During Entry
1. Long opened, short failed -> retry 2-3 times.
2. If it still fails -> close the long leg (rollback).
3. Rollback slippage is the direct cost of the failure.
