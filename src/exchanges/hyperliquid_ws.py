import asyncio
import json

import websockets
from loguru import logger

from src.core.config import Settings
from src.core.state import MarketState
from src.exchanges.hyperliquid import HyperliquidConnector


class HyperliquidWsFeed:
    """WebSocket feed for Hyperliquid — streams allMids for real-time price updates."""

    def __init__(self, settings: Settings, state: MarketState) -> None:
        self._ws_url = settings.hl_ws_url
        self._state = state
        self._settings = settings
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start WS feed. First loads snapshot via REST, then subscribes to updates."""
        self._running = True
        # Initial snapshot
        connector = HyperliquidConnector(self._settings)
        try:
            rates, tickers = await connector.get_market_data()
            await self._state.update_funding("hyperliquid", rates)
            await self._state.update_tickers("hyperliquid", tickers)
            logger.info("HL WS: initial snapshot loaded ({} symbols)", len(rates))
        finally:
            await connector.close()

        self._task = asyncio.create_task(self._run_loop())

    async def _run_loop(self) -> None:
        """Reconnecting WS loop with exponential backoff."""
        backoff = 1.0
        while self._running:
            try:
                async with websockets.connect(self._ws_url) as ws:
                    backoff = 1.0
                    await ws.send(json.dumps({
                        "method": "subscribe",
                        "subscription": {"type": "allMids"},
                    }))
                    logger.debug("HL WS: subscribed to allMids")

                    async for raw_msg in ws:
                        if not self._running:
                            break
                        await self._handle_message(raw_msg)

            except (websockets.ConnectionClosed, OSError) as e:
                if not self._running:
                    break
                logger.warning("HL WS disconnected: {}, reconnecting in {:.0f}s", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    async def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        channel = msg.get("channel")
        if channel != "allMids":
            return

        data = msg.get("data", {})
        mids = data.get("mids", {})

        from decimal import Decimal
        from src.core.models import Ticker
        from src.core.normalize import hl_symbol_to_normalized

        for coin, price_str in mids.items():
            symbol = hl_symbol_to_normalized(coin)
            ticker = Ticker(
                symbol=symbol,
                mark_price=Decimal(price_str),
                index_price=None,
                volume_24h=0.0,
            )
            await self._state.update_single_ticker("hyperliquid", symbol, ticker)

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.debug("HL WS: stopped")
