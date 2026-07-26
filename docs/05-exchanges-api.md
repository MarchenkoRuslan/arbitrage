# Биржи и API

## Фокус: DEX-first

Стратегия начинается с DEX (Hyperliquid, Aster) — наименьшие комиссии, 1h funding, нет KYC.
CEX добавляются позже как дополнительные venues.

## Целевые биржи (v1 — DEX only)

| Биржа | Funding Period | Тип | Приоритет | Статус |
|-------|---------------|-----|-----------|--------|
| Hyperliquid | 1h | DEX | **P0** | Основная |
| Aster | 8h | DEX/CEX | **P0** | Вторая нога |

## Расширение (v2+)

| Биржа | Funding Period | Тип | Приоритет |
|-------|---------------|-----|-----------|
| Lighter | varies | DEX | P1 |
| dYdX v4 | 1h | DEX | P2 |
| Bybit | 8h | CEX | P2 |
| Binance | 8h | CEX | P3 |

## Ключевые endpoints

### Hyperliquid (подробнее: [docs/api/hyperliquid.md](api/hyperliquid.md))
```
POST /info {"type": "metaAndAssetCtxs"}    # Funding rates + market info  
POST /info {"type": "allMids"}             # Все мид-цены
POST /info {"type": "l2Book", "coin": X}   # Orderbook
POST /info {"type": "clearinghouseState"}  # Позиции + баланс
POST /exchange {"action": {"type": "order"}}  # Trading (signed)
WS: allMids, l2Book, userFills, userFundings
```

### Aster (подробнее: [docs/api/aster.md](api/aster.md))
```
Base URL: https://fapi.asterdex.com
Auth: V3 (EIP-712, рекомендуемый) или V1 (HMAC, legacy)
Интерфейс: Binance-совместимый (символы BTCUSDT, стандартные params)

GET /fapi/v1/premiumIndex         # Funding rate + mark price
GET /fapi/v1/fundingRate          # История funding
POST /fapi/v1/order               # Ордер
WS: <symbol>@bookTicker, mini_ticker
```

## Нормализация

### Periods → APR
```python
def normalize_to_annual(rate: Decimal, period_hours: int) -> Decimal:
    periods_per_year = Decimal(8760) / Decimal(period_hours)
    return rate * periods_per_year * Decimal(100)

# Hyperliquid: 0.003% за 1h → 26.28% APR
# Aster: 0.01% за 8h → 10.95% APR
```

### Symbols
```python
# Hyperliquid: coin name only ("BTC", "ETH", "ANSEM")
# Aster: Binance-style ("BTCUSDT", "ETHUSDT", "ANSEMUSDT")

SYMBOL_MAP = {
    "BTC": {"hyperliquid": "BTC", "aster": "BTCUSDT"},
    "ETH": {"hyperliquid": "ETH", "aster": "ETHUSDT"},
    "ANSEM": {"hyperliquid": "ANSEM", "aster": "ANSEMUSDT"},
}
```

## Общая архитектура подключения

Оба venue используют EIP-712 signing → общий signing utility:
```python
# Shared pattern:
# 1. Construct typed data payload
# 2. Sign with private key (eth_account)
# 3. Submit action + signature + nonce

# Hyperliquid: POST /exchange {action, nonce, signature}
# Aster V3: Similar EIP-712 pattern
```

## Аутентификация

- **Hyperliquid (DEX):** EIP-712 typed data подпись. API Wallet (approveAgent) для delegated trading.
- **Aster V3 (DEX):** EIP-712 typed data подпись (аналогично HL). Поддержка agent keys.
- **Aster V1 (legacy):** API Key + HMAC-SHA256 (Binance-like). Новые ключи не создаются с марта 2026.
- **CEX (будущее):** API Key + Secret. Права: Read + Trade. НЕ давать Withdraw.

## Python SDK dependencies

```
# Текущий код (Phase 1)
httpx                      # REST connectors
websockets                 # WS feeds
pydantic                   # response validation schemas

# Дальше (Phase 3, execution)
eth-account                # EIP-712 signing (V3)
```

Примечание:

- На текущей стадии используется `httpx` с собственными адаптерами.
- Официальные SDK можно подключить позже, если они дадут преимущество в execution-части.
