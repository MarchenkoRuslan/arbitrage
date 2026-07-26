# Hyperliquid API Reference

## Базовый URL
- Mainnet: `https://api.hyperliquid.xyz`
- Info endpoint: `POST /info`
- Exchange endpoint: `POST /exchange`
- WebSocket: `wss://api.hyperliquid.xyz/ws`

## Funding Rate: 1 час

## Аутентификация
- Каждый trade action подписывается приватным ключом (EIP-712 typed data)
- Nonce = текущий timestamp в миллисекундах
- API Wallet (Agent): `approveAgent` — delegated key для торговли без master key

## Ключевые endpoints

### Info (read-only, без подписи)

| Запрос | type | Что возвращает |
|--------|------|---------------|
| Все мид-цены | `allMids` | `{"BTC": "64500.0", "ETH": "3400.0", ...}` |
| Orderbook | `l2Book` | До 20 уровней bids/asks |
| Позиции | `clearinghouseState` | Позиции, маржа, PnL |
| Открытые ордера | `openOrders` | Все активные ордера |
| Заполнения | `userFills` | До 2000 fills |
| Статус ордера | `orderStatus` | По oid или cloid |
| Комиссии | `userFees` | Текущие тиры, ставки |
| Rate limits | `userRateLimit` | Использованные/доступные запросы |
| Meta (instruments) | `meta` | Universe, funding rates, OI, mark prices |

### Получение funding rates
```python
# POST /info
{"type": "metaAndAssetCtxs"}

# Response включает для каждого asset:
# - funding: текущая ставка (выплата за 1 час)
# - openInterest
# - markPx, oraclePx
# - prevDayPx (для расчёта 24h change)
```

### Exchange (требует подпись)

| Действие | type | Описание |
|----------|------|----------|
| Ордер | `order` | Limit/IOC/ALO + trigger (TP/SL) |
| Отмена | `cancel` | По oid |
| Отмена по cloid | `cancelByCloid` | По client order ID |
| Модификация | `modify` | Изменить цену/размер |
| Leverage | `updateLeverage` | Установить плечо |
| Margin | `updateIsolatedMargin` | Добавить/убрать маржу |

### Формат ордера
```python
{
    "action": {
        "type": "order",
        "orders": [{
            "a": 0,          # asset index (0=BTC, 1=ETH, ...)
            "b": True,        # isBuy
            "p": "64500.0",   # price
            "s": "0.01",      # size
            "r": False,       # reduceOnly
            "t": {"limit": {"tif": "Gtc"}}  # Gtc/Ioc/Alo
        }],
        "grouping": "na"
    },
    "nonce": 1690000000000,  # timestamp ms
    "signature": {...}        # EIP-712
}
```

### Order types (TIF)
- **GTC** — Good Til Canceled (обычный limit)
- **IOC** — Immediate Or Cancel (аналог market с price limit)
- **ALO** — Add Liquidity Only (post-only, maker only)

### Client Order ID
- 128-bit hex string: `0x1234567890abcdef1234567890abcdef`
- Позволяет отслеживать ордера без oid

## WebSocket

```python
# Подключение
ws = websocket.connect("wss://api.hyperliquid.xyz/ws")

# Подписки
{"method": "subscribe", "subscription": {"type": "allMids"}}
{"method": "subscribe", "subscription": {"type": "l2Book", "coin": "BTC"}}
{"method": "subscribe", "subscription": {"type": "trades", "coin": "BTC"}}
{"method": "subscribe", "subscription": {"type": "userEvents", "user": "0x..."}}
{"method": "subscribe", "subscription": {"type": "userFills", "user": "0x..."}}
{"method": "subscribe", "subscription": {"type": "userFundings", "user": "0x..."}}
```

## Python SDK
- Официальный: `hyperliquid-python-sdk`
- Примеры: place order, cancel, market data, vault operations
- Signing: EIP-712 через eth_account

## Rate Limits
- Базовый: пропорционален cumulative volume
- `nRequestsCap` = ~cumVlm (в USDC)
- Можно купить доп. requests: 0.0005 USDC/request (`reserveRequestWeight`)
- Dead man's switch: `scheduleCancel` — auto-cancel через N секунд

## Комиссии (базовые)
- Taker (cross): 0.045%
- Maker (add): 0.015%
- VIP тиры снижают (от $5M volume)
- MM тиры дают rebate на maker
- Referral discount: 4%
- Staking discount: до 30%

## Особенности
- Asset index: порядковый номер в `meta.universe` (BTC=0, ETH=1, ...)
- Spot assets: `10000 + index`
- HIP-3 DEX assets: prefix `dex:SYMBOL` (e.g. `xyz:XYZ100`)
- Min order value: $10
- Subaccounts: подписываются master-ключом с `vaultAddress`
- Dead man's switch: max 10 triggers/day
