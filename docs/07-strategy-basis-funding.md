# Стратегия: Basis + Funding Combined

## Концепция

Двойной источник прибыли: ценовой базис (spread convergence) + funding rate.

```
Total_Profit = Basis_Convergence + Funding_Income - Fees
```

## Три сценария

| Сценарий | Basis | Funding | Действие |
|----------|-------|---------|----------|
| Идеальный | + (short дороже) | + (short получает) | Двойной профит |
| Funding Insurance | - (против нас) | Высокий + | Фандинг покрывает basis loss |
| Basis Play | Большой + | Маленький | Профит от convergence |

## Combined Score

```python
score = funding_за_24ч - комиссии_roundtrip + basis_bonus

basis_bonus = max(0, basis_bps) × 0.5  # 50% вероятность реализации
```

Если basis отрицательный — проверяем сколько часов funding нужно чтобы покрыть:
```python
hours_to_cover = abs(negative_basis_bps) / hourly_funding_bps
if hours_to_cover > max_holding_hours: SKIP
```

## Реальные примеры

### UMA — идеальный кейс
```
Long Hyperliquid @ $0.3901, Short Aster @ $0.3932
Basis: +80.5 bps, APR: 67%, Fees: ~21 bps
Day 1: basis convergence +59.5 bps + funding 18.4 bps = +78 bps
```

### CASHCAT — funding insurance
```
Basis: -54.9 bps (против нас), APR: 145%
Funding: 39.7 bps/day → breakeven за 1.4 дня
Day 3: +119.1 - 54.9 - 21 = +43.2 bps
```

## Сигналы выхода

| Сигнал | Действие |
|--------|----------|
| Funding сменил знак | Закрыть |
| Margin ratio < 10% | Закрыть немедленно |
| Basis сошёлся (< 5 bps) | Зафиксировать |
| Spread расширился > 3x | Закрыть с убытком |
| Combined score < 0 | Плановое закрытие |
