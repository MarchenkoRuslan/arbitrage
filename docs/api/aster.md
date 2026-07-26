# Aster API Reference

## Базовая информация
- **Base URL (Futures):** `https://fapi.asterdex.com`
- **API Version:** V3 (EIP-712) — рекомендуемая; V1 (HMAC) — legacy
- **Python SDK:** `pip install aster-connector-python`
- **GitHub:** github.com/asterdex/api-docs, github.com/asterdex/aster-connector-python
- **Интерфейс:** Binance-совместимый (те же параметры ордеров)
- **Funding Period:** 8h

## Аутентификация

### V3 (Recommended) — EIP-712
- Подпись через EIP-712 typed data (как Hyperliquid)
- Wallet-based auth
- Поддержка agent/delegated keys

### V1 (Legacy) — HMAC
- API Key + Secret (как Binance)
- HMAC-SHA256 подпись
- С марта 2026 новые V1 ключи не создаются

## Python SDK Usage

```python
from aster.rest_api import Client

# Public (без ключей)
client = Client()
print(client.time())

# Private (с ключами, V1 legacy)
client = Client(key='<api_key>', secret='<api_secret>')
print(client.account())

# Создать ордер
params = {
    'symbol': 'BTCUSDT',
    'side': 'SELL',
    'type': 'LIMIT',
    'timeInForce': 'GTC',
    'quantity': 0.002,
    'price': 59808
}
response = client.new_order(**params)
```

## WebSocket

```python
from aster.websocket.client.stream import WebsocketClient as Client

def message_handler(message):
    print(message)

ws_client = Client()
ws_client.start()

# Подписка на тикер
ws_client.mini_ticker(symbol='btcusdt', id=1, callback=message_handler)

# Подписка на orderbook
ws_client.instant_subscribe(
    stream=['btcusdt@bookTicker', 'ethusdt@bookTicker'],
    callback=message_handler,
)
```

## Ключевые endpoints (Binance-like format)

### Market Data (Public)
```
GET /fapi/v1/time                 # Server time
GET /fapi/v1/ticker/24hr          # 24h tickers
GET /fapi/v1/depth                # Orderbook
GET /fapi/v1/premiumIndex         # Funding rate + mark price
GET /fapi/v1/fundingRate          # Funding rate history
```

### Account (Private)
```
GET /fapi/v1/account              # Баланс, позиции
GET /fapi/v1/positionRisk         # Позиции с деталями
GET /fapi/v1/openOrders           # Открытые ордера
```

### Trading (Private)
```
POST /fapi/v1/order               # Новый ордер
DELETE /fapi/v1/order             # Отмена ордера
GET /fapi/v1/order                # Статус ордера
POST /fapi/v1/leverage            # Установить leverage
POST /fapi/v1/marginType          # Cross/Isolated
```

## Формат символов
- Binance-like: `BTCUSDT`, `ETHUSDT`, `ANSEMUST`, etc.
- Много мемкоинов (ANSEM, FARTCOIN, etc.)

## Особенности
- Binance-совместимый REST API (параметры, формат ответов)
- Собственный блокчейн (Aster Chain)
- V3 auth = EIP-712 (shared signing pattern с Hyperliquid)
- Много мемкоинов с высоким funding
- ADL встречается часто на мемкоинах (кейс ANSEM)
- Testnet доступен

## Комиссии (предположительно)
- Taker: ~0.05%
- Maker: ~0.02%
- Точные данные: проверить через API `/fapi/v1/account` или docs

## Rate Limits
- recvWindow: max 60000 ms, default 5000 ms
- Weight limits отображаются в response headers
- Ping каждые 3 мин, pong timeout 10 мин (WS)

## Важно для арбитража
- **Общие пары с Hyperliquid:** BTC, ETH + мемкоины (ANSEM, FARTCOIN, etc.)
- **Funding 8h vs HL 1h:** Нормализовать к единому APR
- **ADL risk выше** на мемкоинах
- **Оба используют EIP-712:** Можно шарить signing utilities
