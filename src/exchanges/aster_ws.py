import asyncio
import json

import websockets
from loguru import logger

from src.core.config import Settings
from src.core.state import MarketState
from src.exchanges.aster import AsterConnector


class AsterWsFeed:
    """WebSocket feed for Aster — streams miniTicker for real-time price updates."""

    def __init__(self, settings: Settings, state: MarketState) -> None:
        self._ws_url = settings.aster_ws_url
        self._state = state
        self._settings = settings
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start WS feed. First loads snapshot via REST, then subscribes to updates."""
        self._running = True
        # Initial snapshot
        connector = AsterConnector(self._settings)
        try:
            rates, tickers = await connector.get_market_data()
            await self._state.update_funding("aster", rates)
            await self._state.update_tickers("aster", tickers)
            logger.info("Aster WS: initial snapshot loaded ({} symbols)", len(rates))
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
                    # Subscribe to all miniTicker stream
                    await ws.send(json.dumps({
                        "method": "SUBSCRIBE",
                        "params": ["!miniTicker@arr"],
                        "id": 1,
                    }))
                    logger.debug("Aster WS: subscribed to miniTicker")

                    async for raw_msg in ws:
                        if not self._running:
                            break
                        await self._handle_message(raw_msg)

            except (websockets.ConnectionClosed, OSError) as e:
                if not self._running:
                    break
                logger.warning("Aster WS disconnected: {}, reconnecting in {:.0f}s", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    async def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        # miniTicker array stream
        if not isinstance(msg, list):
            return

        from decimal import Decimal
        from src.core.models import Ticker
        from src.core.normalize import aster_symbol_to_normalized

        for item in msg:
            if item.get("e") != "24hrMiniTicker":
                continue
            raw_symbol = item.get("s", "")
            symbol = aster_symbol_to_normalized(raw_symbol)
            mark = item.get("c")  # close price as proxy
            if mark is None:
                continue

            ticker = Ticker(
                symbol=symbol,
                mark_price=Decimal(mark),
                index_price=None,
                volume_24h=float(item.get("q", 0)),
            )
            await self._state.update_single_ticker("aster", symbol, ticker)

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.debug("Aster WS: stopped")
