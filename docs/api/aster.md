# Aster API Reference

## Basic Information
- **Base URL (Futures):** `https://fapi.asterdex.com`
- **API Version:** V3 (EIP-712) is recommended; V1 (HMAC) is legacy
- **Python SDK:** `pip install aster-connector-python`
- **GitHub:** github.com/asterdex/api-docs, github.com/asterdex/aster-connector-python
- **Interface:** Binance-compatible (same order parameters)
- **Funding Period:** 8h

## Authentication

### V3 (Recommended) - EIP-712
- Signature via EIP-712 typed data, similar to Hyperliquid
- Wallet-based auth
- Supports agent/delegated keys

### V1 (Legacy) - HMAC
- API Key + Secret, similar to Binance
- HMAC-SHA256 signature
- As of March 2026, new V1 keys are no longer issued

## Python SDK Usage

```python
from aster.rest_api import Client

# Public client without keys
client = Client()
print(client.time())

# Private client with keys, V1 legacy mode
client = Client(key='<api_key>', secret='<api_secret>')
print(client.account())

# Place an order
params = {
    'symbol': 'BTCUSDT',
    'side': 'SELL',
    'type': 'LIMIT',
    'timeInForce': 'GTC',
    'quantity': 0.002,
    'price': 59808,
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

# Subscribe to ticker updates
ws_client.mini_ticker(symbol='btcusdt', id=1, callback=message_handler)

# Subscribe to order book updates
ws_client.instant_subscribe(
    stream=['btcusdt@bookTicker', 'ethusdt@bookTicker'],
    callback=message_handler,
)
```

## Key Endpoints (Binance-like Format)

### Market Data (Public)
```
GET /fapi/v1/time                 # Server time
GET /fapi/v1/ticker/24hr          # 24h tickers
GET /fapi/v1/depth                # Order book
GET /fapi/v1/premiumIndex         # Funding rate + mark price
GET /fapi/v1/fundingRate          # Funding rate history
```

### Account (Private)
```
GET /fapi/v1/account              # Balance, positions
GET /fapi/v1/positionRisk         # Positions with details
GET /fapi/v1/openOrders           # Open orders
```

### Trading (Private)
```
POST /fapi/v1/order               # New order
DELETE /fapi/v1/order             # Cancel order
GET /fapi/v1/order                # Order status
POST /fapi/v1/leverage            # Set leverage
POST /fapi/v1/marginType          # Cross/Isolated
```

## Symbol Format
- Binance-like: `BTCUSDT`, `ETHUSDT`, `ANSEMUSDT`, etc.
- Many memecoins are listed, including ANSEM and FARTCOIN

## Notes
- Binance-compatible REST API (parameters and response format)
- Runs on its own chain (Aster Chain)
- V3 auth uses EIP-712, which aligns with Hyperliquid's signing pattern
- Many memecoins show elevated funding rates
- ADL is more common on memecoins, including the ANSEM case
- Testnet is available

## Fees (Estimated)
- Taker: ~0.05%
- Maker: ~0.02%
- Exact values should be verified through `/fapi/v1/account` or the official docs

## Rate Limits
- `recvWindow`: max 60000 ms, default 5000 ms
- Weight limits are exposed in response headers
- Ping every 3 minutes, pong timeout 10 minutes (WS)

## Important for Arbitrage
- **Shared pairs with Hyperliquid:** BTC, ETH, plus memecoins such as ANSEM and FARTCOIN
- **Funding 8h vs HL 1h:** normalize both to the same APR basis
- **ADL risk is higher** on memecoins
- **Both use EIP-712:** signing utilities can be shared
