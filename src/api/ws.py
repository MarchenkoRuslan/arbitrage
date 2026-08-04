import asyncio

from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts updates."""

    def __init__(self, *, send_timeout_s: float = 2.0) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._send_timeout_s = send_timeout_s

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)

    async def broadcast(self, data: dict) -> None:
        async with self._lock:
            targets = list(self._connections)
        if not targets:
            return

        async def _send_one(ws: WebSocket) -> WebSocket | None:
            try:
                await asyncio.wait_for(ws.send_json(data), timeout=self._send_timeout_s)
                return None
            except asyncio.CancelledError:
                raise
            except Exception:
                return ws

        results = await asyncio.gather(*(_send_one(ws) for ws in targets))
        stale = [ws for ws in results if ws is not None]
        if stale:
            async with self._lock:
                for ws in stale:
                    self._connections.discard(ws)
