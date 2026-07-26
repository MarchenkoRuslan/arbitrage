# Риски: ADL и реальные кейсы

## ADL (Auto-Deleveraging)

Биржа автоматически закрывает прибыльные позиции при каскаде ликвидаций. Ломает хедж.

```
ДО ADL:  Long (спот/перп) + Short (перп) = delta neutral ✓
ПОСЛЕ:   Long остался, Short закрыт = directional risk!
```

### Кейс ANSEM
```
Позиция: Spot MEXC + Short Aster
Funding: ~5% за 10 дней (182% APR)
Событие: мем-сезон Robinhood chain → ANSEM -30-40%
ADL: шорт закрыт @ $0.22
Утро: спот продан @ $0.27 → +$4k (повезло)
Альтернатива: спот мог упасть до $0.15 → убыток
```

### Митигация ADL
- Мониторить ADL indicator (4-5 ламп → предупреждение)
- Isolated margin (ограничить убыток)
- Не ставить весь капитал в одну пару
- При ADL event → немедленно решить: закрыть вторую ногу или держать

## Другие риски

### Funding Flip
```
Rate резко меняет знак → из получателя в плательщика.
Защита: мониторинг predicted rate, auto-close при смене знака.
```

### Exchange Price Deviation
```
Нормально: 0.1-0.3% расхождение
Опасно: >1% (одна нога в убытке)
Критично: >3% (угроза ликвидации)
Защита: margin buffer >2x, alerts, ребалансировка
```

### Мемкоины
```
- Pump/dump 30-100% за минуты
- ADL вероятность НАМНОГО выше
- Рекомендация: max 10-20% портфеля
```

## Risk Limits

```yaml
# Per-position
max_position_pct: 20%       # Не более 20% в одну пару
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

### После ADL
1. Detect: позиция закрыта не нами
2. Alert: Telegram CRITICAL
3. Decide: закрыть вторую ногу (safe) или trailing stop (risky)

### Failure одной ноги при открытии
1. Long открыт, Short failed → retry 2-3 раза
2. Всё ещё failed → закрыть Long (rollback)
3. Slippage от rollback = стоимость ошибки
